"""autotax：pipeline 全自动集成——新笔记 → 一次 LLM 分析 → 本地更新 → Notion 插行。

复用既有件：taxonomy.find_similar（防类名漂移）、enrich.summarize_preview、
note_index（索引落盘）、batch_report（批次）、config.NOTION_DB_ID（未配置则跳过插行）。
"""

import json
import re
from datetime import datetime
from pathlib import Path

import httpx

from .batch_report import record_item_into_daily_batch
from .config import config
from .enrich import _llm_text, summarize_preview
from .note_index import load_index, save_index
from .short_title import MAX_LEN, make_unique
from .taxonomy import Taxonomy, load_taxonomy, save_taxonomy

_TAXONOMY_FILE = Path("data/categories.json")
_INDEX_FILE = Path("data/note_index.json")
_BATCHES_FILE = Path("data/batches.json")

_PROMPT = """你是视频知识库的管理员，对下面这篇新入库的视频学习笔记做一次完整分析。

现有大类清单（优先从中选择）：
{cat_lines}

要求：
1. short_title：不超过 {max_len} 字的简洁中文标题。删除 #话题/@用户/推广钩子语，**最大限度保留原标题中的特征字段**（专有名词/数字/核心技术概念），确保与库内其他视频可区分
2. category/subcategory：从清单中选择最合适的大类与细类（细类可自拟，2-8 字）；若所有大类都不合适可创建新大类（2-10 字、宽泛主题），并把 new_category 设为同样的名字
3. 大类必须宽泛，禁止过细（如"agent 开发"这类只装几个视频的类）
4. tags：3-5 个检索用标签（2-6 字，具体可搜索，如"KV Cache""上下文压缩"，禁用"AI""视频"等过泛词）
5. 只输出 JSON：{{"short_title": "...", "category": "...", "subcategory": "...", "new_category": null 或 "...", "tags": ["..."]}}

视频标题：{title}
笔记摘要：{summary}"""


def _normalize(name: str) -> str:
    return re.sub(r"[\s_\-—·、，,。.与和及]+", "", name).lower()


def _find_similar(name: str, existing: list[str]) -> str | None:
    n = _normalize(name)
    for cat in existing:
        c = _normalize(cat)
        if n == c or n in c or c in n:
            return cat
    return None


def build_analysis_prompt(title: str, summary: str, categories: dict[str, list[str]]) -> str:
    cat_lines = "\n".join(
        f"- {cat}（细类：{'、'.join(subs) if subs else '暂无'}）" for cat, subs in categories.items()
    )
    return _PROMPT.format(cat_lines=cat_lines, max_len=MAX_LEN, title=title, summary=summary[:800])


async def analyze_note(title: str, summary: str, categories: dict[str, list[str]], api_key: str) -> dict:
    """一次 LLM 调用产出短标题/分类/标签；提案大类经相似归并。"""
    prompt = build_analysis_prompt(title, summary, categories)
    raw = (await _llm_text(prompt, api_key)).strip()
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        raise ValueError(f"LLM 分析输出无法解析: {raw[:200]}")
    data = json.loads(m.group(0))
    category = str(data.get("category", "")).strip()
    subcategory = str(data.get("subcategory", "")).strip()
    short_title = str(data.get("short_title", "")).strip().strip('"“”')
    tags = [str(t).strip()[:12] for t in (data.get("tags") or []) if str(t).strip()][:5]
    if not (short_title and category and subcategory):
        raise ValueError(f"LLM 分析输出缺少字段: {data}")

    is_new = False
    similar = _find_similar(category, list(categories.keys()))
    if similar:
        category = similar
    elif data.get("new_category"):
        is_new = True
    return {
        "short_title": short_title,
        "category": category,
        "subcategory": subcategory,
        "is_new_category": is_new,
        "tags": tags,
    }


def _unique_short_title(short_title: str, index: list[dict]) -> str:
    """与库内已有短标题查重（沿用 make_unique 的后缀规则）。"""
    existing = [e.get("short_title", "") for e in index]
    return make_unique(existing + [short_title])[-1]


async def _insert_row(entry: dict, db_id: str) -> str:
    """把分析结果作为一行插入 Notion database，返回页面 URL。"""
    headers = {
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.NOTION_TOKEN}",
    }
    props = {
        "Name": {"title": [{"text": {"content": entry["short_title"]}}]},
        "分类": {"select": {"name": entry["category"]}},
        "细类": {"select": {"name": entry["subcategory"]}},
        "标签": {"multi_select": [{"name": t} for t in entry["tags"]]},
        "概述": {"rich_text": [{"text": {"content": entry["preview"]}}]},
        "原标题": {"rich_text": [{"text": {"content": entry["title"]}}]},
        "视频ID": {"rich_text": [{"text": {"content": entry["aweme_id"]}}]},
        "作者": {"rich_text": [{"text": {"content": entry.get("author", "")}}]},
        "批次": {"select": {"name": entry["batch_id"]}},
    }
    if entry.get("date"):
        props["采集日期"] = {"date": {"start": entry["date"]}}
    if entry.get("source_url"):
        props["视频来源"] = {"url": entry["source_url"]}
    children = [
        {
            "object": "block", "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": "📌 " + entry["preview"]}}],
                "icon": {"emoji": "📝"},
            },
        },
        {
            "object": "block", "type": "callout",
            "callout": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": "▶ 打开完整笔记（总结文档）", "link": {"url": entry["notion_url"]}}
                    if entry.get("notion_url")
                    else {"type": "text", "text": {"content": "▶ 打开完整笔记（总结文档）"}},
                }],
                "icon": {"emoji": "📄"},
            },
        },
    ]
    async with httpx.AsyncClient(base_url="https://api.notion.com/v1", headers=headers, timeout=60) as client:
        r = await client.post("/pages", json={
            "parent": {"database_id": db_id},
            "properties": props,
            "children": children,
        })
        r.raise_for_status()
        return r.json().get("url", "")


async def enrich_and_publish(meta: dict, preview: str, api_key: str) -> dict:
    """笔记落盘后的全自动收录：分析 → 本地（taxonomy/index/批次）→ Notion 插行。

    meta 需含 aweme_id/title/author/source_url；preview 为笔记「精华版」首段。
    本地更新先行落盘，Notion 失败仅抛出异常（由调用方降级），本地数据不丢失。
    """
    taxonomy = load_taxonomy(_TAXONOMY_FILE)
    index = load_index(_INDEX_FILE)
    api_key = api_key or config.LLM_API_KEY or config.SILICONFLOW_API_KEY

    analysis = await analyze_note(meta["title"], preview, taxonomy.categories, api_key)
    if analysis["is_new_category"]:
        taxonomy.categories[analysis["category"]] = [analysis["subcategory"]]
        save_taxonomy(taxonomy, _TAXONOMY_FILE)

    entry = {
        "aweme_id": str(meta["aweme_id"]),
        "title": meta["title"],
        "short_title": _unique_short_title(analysis["short_title"], index),
        "author": meta.get("author", ""),
        "date": str(meta.get("captured_at", ""))[:10] or datetime.now().strftime("%Y-%m-%d"),
        "source_url": meta.get("source_url", ""),
        "file": Path(meta.get("note_path", "")).name if meta.get("note_path") else "",
        "preview": summarize_preview(preview),
        "category": analysis["category"],
        "subcategory": analysis["subcategory"],
        "tags": analysis["tags"],
        "is_new_category": analysis["is_new_category"],
        # notion_url = 总结文档（MVP 子页面）；row_url = 知识库行（插行后回填）
        "notion_url": meta.get("notion_page_url", ""),
        "row_url": "",
    }

    batch_id = record_item_into_daily_batch(_BATCHES_FILE, {
        "aweme_id": entry["aweme_id"], "title": entry["short_title"],
        "category": entry["category"], "notion_url": entry["notion_url"],
    })
    entry["batch_id"] = batch_id

    index.append(entry)
    save_index(index, _INDEX_FILE)

    if config.NOTION_DB_ID:
        entry["row_url"] = await _insert_row(entry, config.NOTION_DB_ID)
        save_index(index, _INDEX_FILE)  # 回写 row_url
    return entry
