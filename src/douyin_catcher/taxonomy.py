"""3B 分类体系：清单持久化 + LLM 受限选择 + 提案去重。

设计要点：
- categories.json 是大类的 source of truth（人工可随时编辑）；
- LLM 只能从现有清单中选择，或通过 new_category 字段提案新大类；
- 提案若与现有大类归一化后相似，则归并到现有类（防命名漂移）；
- 真正的新大类返回 is_new_category=True，由调用方决定是否入库。
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from .config import config

_LLM_TIMEOUT = 120


@dataclass
class Taxonomy:
    categories: dict[str, list[str]] = field(default_factory=dict)

    def category_names(self) -> list[str]:
        return list(self.categories.keys())


def save_taxonomy(t: Taxonomy, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps({"categories": t.categories}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_taxonomy(path: str | Path) -> Taxonomy:
    p = Path(path)
    if not p.exists():
        return Taxonomy()
    data = json.loads(p.read_text(encoding="utf-8"))
    return Taxonomy(categories=data.get("categories", {}))


def _normalize(name: str) -> str:
    # 连接字（与/和/及）在命名漂移中常被增删，一并归一化
    return re.sub(r"[\s_\-—·、，,。.与和及]+", "", name).lower()


def find_similar(name: str, existing: list[str]) -> str | None:
    """归一化后精确或子串匹配，返回命中的现有大类名。"""
    n = _normalize(name)
    for cat in existing:
        c = _normalize(cat)
        if n == c or n in c or c in n:
            return cat
    return None


def build_classify_prompt(title: str, summary: str, categories: dict[str, list[str]]) -> str:
    cat_lines = "\n".join(
        f"- {cat}（细类：{'、'.join(subs) if subs else '暂无'}）" for cat, subs in categories.items()
    )
    return f"""你是视频知识库的分类员。请把下面这篇视频学习笔记归入一个最合适的大类和细类。

现有大类清单（优先从中选择）：
{cat_lines}

规则：
1. 若现有大类合适，category 填大类原名，subcategory 填该大类下最合适的细类（现有细类不合适可自拟一个简短细类名，2-8 字）。
2. 若所有现有大类都不合适，可创建新大类：category 填新大类名（2-10 字、宽泛主题，不要过细），new_category 填同样的名字，并在 subcategory 给出该新大类下的细类。
3. 大类必须宽泛（如"AI Agent 与工作流"），禁止过细（如"agent 开发"“agent 架构"这类只能装几个视频的类）。
4. 只输出 JSON，格式：{{"category": "...", "subcategory": "...", "new_category": null 或 "..."}}，不要输出其他内容。

视频标题：{title}
笔记摘要：{summary[:800]}"""


async def _llm_text(prompt: str, api_key: str) -> str:
    """与 summarizer._llm_text 相同的统一调用层（避免跨模块耦合复制于此）。"""
    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(timeout=_LLM_TIMEOUT) as client:
        if config.LLM_API_STYLE == "responses":
            resp = await client.post(
                f"{config.LLM_BASE_URL}/responses",
                headers=headers,
                json={"model": config.LLM_MODEL, "input": prompt, "max_output_tokens": 1024},
            )
            data = resp.json()
            return "".join(
                c.get("text", "") for c in data["output"][0]["content"]
            )
        resp = await client.post(
            f"{config.LLM_BASE_URL}/chat/completions",
            headers=headers,
            json={
                "model": config.LLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1024,
            },
        )
        return resp.json()["choices"][0]["message"]["content"]


async def classify_note(
    title: str,
    summary: str,
    categories: dict[str, list[str]],
    api_key: str,
) -> dict:
    """对单篇笔记做受限分类，返回 {category, subcategory, is_new_category}。"""
    prompt = build_classify_prompt(title, summary, categories)
    raw = (await _llm_text(prompt, api_key)).strip()
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        raise ValueError(f"LLM 分类输出无法解析: {raw[:200]}")
    data = json.loads(m.group(0))
    category = str(data.get("category", "")).strip()
    subcategory = str(data.get("subcategory", "")).strip()
    new_category = data.get("new_category")
    if not category or not subcategory:
        raise ValueError(f"LLM 分类输出缺少字段: {data}")

    is_new = False
    if new_category:
        similar = find_similar(str(new_category), list(categories.keys()))
        if similar:
            # 提案与现有类相似 → 归并
            category = similar
        else:
            is_new = True
    else:
        similar = find_similar(category, list(categories.keys()))
        if similar:
            category = similar
    return {"category": category, "subcategory": subcategory, "is_new_category": is_new}
