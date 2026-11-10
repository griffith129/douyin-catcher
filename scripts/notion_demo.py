"""Notion demo 落地脚本（真实 API 调用）：
1. 拉取父页面现有子页面（标题→URL 映射，供更新日志/本地索引跳转）
2. 方案2（1A+2A）：创建"抖音知识库（Demo）"database，种入分类结果行（含批次 property）
3. 方案1（2C）：写"更新日志（Demo）"页，按大类分组列出本次批次视频链接

用法：uv run python scripts/notion_demo.py
"""

import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from douyin_catcher.config import config  # noqa: E402
from douyin_catcher.notion import extract_page_id  # noqa: E402

_API = "https://api.notion.com/v1"
_HEADERS = {"Notion-Version": "2022-06-28", "Content-Type": "application/json"}
BATCH_NAME = "demo-2026-11-10"
DB_TITLE = "抖音知识库（Demo）"
LOG_TITLE = "更新日志（Demo）"


def client() -> httpx.Client:
    token = config.NOTION_TOKEN
    if not token:
        raise SystemExit("缺少 NOTION_TOKEN")
    _HEADERS["Authorization"] = f"Bearer {token}"
    return httpx.Client(base_url=_API, headers=_HEADERS, timeout=60)


def list_child_pages(c: httpx.Client, parent_page_id: str) -> list[dict]:
    """父页面下全部直接子页面（标题→URL）。用 blocks/children 而非 search——
    Notion search API 对空查询不保证返回全部共享页面。"""
    out, cursor = [], None
    while True:
        params = {"page_size": 100}
        if cursor:
            params["start_cursor"] = cursor
        r = c.get(f"/blocks/{parent_page_id}/children", params=params)
        r.raise_for_status()
        data = r.json()
        for b in data.get("results", []):
            if b.get("type") == "child_page" and not b.get("archived"):
                page_id = b["id"].replace("-", "")
                out.append(
                    {
                        "title": b["child_page"]["title"],
                        "url": f"https://www.notion.so/{page_id}",
                        "id": b["id"],
                    }
                )
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return out


def create_database(c: httpx.Client, parent_page_id: str) -> dict:
    payload = {
        "parent": {"page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": DB_TITLE}}],
        "properties": {
            "Name": {"title": {}},
            "分类": {"select": {}},
            "细类": {"select": {}},
            "作者": {"rich_text": {}},
            "采集日期": {"date": {}},
            "批次": {"select": {}},
            "视频来源": {"url": {}},
        },
    }
    r = c.post("/databases", json=payload)
    r.raise_for_status()
    return r.json()


def insert_row(c: httpx.Client, db_id: str, e: dict) -> dict:
    props = {
        "Name": {"title": [{"text": {"content": e["title"]}}]},
        "分类": {"select": {"name": e.get("category", "未分类")}},
        "细类": {"select": {"name": e.get("subcategory", "-")}},
        "作者": {"rich_text": [{"text": {"content": e.get("author", "")}}]},
        "批次": {"select": {"name": BATCH_NAME}},
    }
    if e.get("date"):
        props["采集日期"] = {"date": {"start": e["date"]}}
    if e.get("source_url"):
        props["视频来源"] = {"url": e["source_url"]}
    children = [
        {
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": e.get("preview", "")[:500]}}],
                "icon": {"emoji": "📌"},
            },
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": "（Demo 行：正式版将上传笔记全文）"}}]},
        },
    ]
    r = c.post("/pages", json={"parent": {"database_id": db_id}, "properties": props, "children": children})
    r.raise_for_status()
    return r.json()


def _rich(text: str) -> list[dict]:
    return [{"type": "text", "text": {"content": text}}]


def write_log_page(c: httpx.Client, parent_page_id: str, batches: list[dict], url_map: dict[str, str]) -> str:
    """2C：更新日志页，每个批次一个章节，视频按大类分组、带跳转链接。"""
    blocks: list[dict] = []
    for b in batches:
        blocks.append(
            {"object": "block", "type": "heading_2", "heading_2": {"rich_text": _rich(f"{b['batch_id']}（{b['created_at']}，共 {len(b['items'])} 篇）")}}
        )
        groups: dict[str, list[dict]] = {}
        for it in b["items"]:
            groups.setdefault(it.get("category", "未分类"), []).append(it)
        for cat in sorted(groups):
            blocks.append({"object": "block", "type": "heading_3", "heading_3": {"rich_text": _rich(cat)}})
            for it in groups[cat]:
                link_url = it.get("notion_url") or url_map.get(it["title"], "")
                rich = [{"type": "text", "text": {"content": it["title"], "link": {"url": link_url} if link_url else None}}]
                blocks.append({"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": rich}})
    r = c.post(
        "/pages",
        json={
            "parent": {"page_id": parent_page_id},
            "properties": {"title": {"title": [{"text": {"content": LOG_TITLE}}]}},
            "children": blocks,
        },
    )
    r.raise_for_status()
    return r.json()["url"]


def main() -> None:
    parent = config.NOTION_PARENT_PAGE_ID
    if not parent:
        raise SystemExit("缺少 NOTION_PARENT_PAGE_ID")
    index = json.loads(Path("data/note_index.json").read_text(encoding="utf-8"))
    classified = [e for e in index if e.get("category")]
    print(f"[+] 索引 {len(index)} 篇，其中已分类 {len(classified)} 篇")

    with client() as c:
        # 1. 现有子页面映射（旧笔记页在 parent 下平铺）
        children = list_child_pages(c, parent)
        url_map = {ch["title"]: ch["url"] for ch in children}
        print(f"[+] 父页面现有子页面 {len(children)} 个")
        # 给本地索补充 Notion URL
        for e in index:
            e["notion_url"] = url_map.get(e["title"], "")

        # 2. 方案2：database + 种子行
        existing_dbs = c.post("/search", json={"query": DB_TITLE, "filter": {"property": "object", "value": "database"}}).json()
        if existing_dbs.get("results"):
            db = existing_dbs["results"][0]
            db_id = db["id"]
            print(f"[=] database 已存在，复用: {db['url']}")
        else:
            db = create_database(c, parent)
            db_id = db["id"]
            print(f"[+] database 已创建: {db['url']}")
        # 幂等：该批次已有行则跳过插入
        existing = c.post(f"/databases/{db_id}/query", json={"page_size": 1}).json()
        already = len(existing.get("results", [])) > 0
        if already:
            print("[=] database 已有数据行，跳过插入")
        else:
            for i, e in enumerate(classified, 1):
                row = insert_row(c, db_id, e)
                e["notion_url"] = e["notion_url"] or row["url"]
                print(f"  [{i}/{len(classified)}] 行已插入: {e['title'][:30]}")

        # 3. 方案1：更新日志页（先归档旧日志页再重写，保持幂等）
        for ch in children:
            if ch["title"] == LOG_TITLE and ch["id"] not in (db_id,):
                c.delete(f"/blocks/{ch['id']}")
                print("[=] 旧日志页已归档")
        batches = json.loads(Path("data/batches.json").read_text(encoding="utf-8"))
        log_url = write_log_page(c, parent, batches, url_map)
        print(f"[+] 更新日志页已写入: {log_url}")

    Path("data/note_index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    Path("data/demo_meta.json").write_text(
        json.dumps(
            {"database_id": db_id, "database_url": db["url"], "log_url": log_url, "batch": BATCH_NAME},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[+] database_id: {db_id}")


if __name__ == "__main__":
    main()
