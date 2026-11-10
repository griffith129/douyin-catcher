"""修复 11 条旧语义自动收录条目（notion_url 指向行 URL / date / source_url 缺失）。

- index: notion_url ← 总结文档子页面 URL；row_url ← 知识库行；date/source_url ← 笔记 frontmatter
- database 行: 补 采集日期；错误的"打开完整笔记"链接 callout 换为正确指向
- batches.json: 同步条目 notion_url

用法：uv run python scripts/fix_autotax_entries.py
"""

import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from douyin_catcher.config import config  # noqa: E402
from douyin_catcher.note_index import parse_frontmatter  # noqa: E402
from notion_demo import list_child_pages  # noqa: E402

_API = "https://api.notion.com/v1"
_HEADERS = {
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {config.NOTION_TOKEN}",
}
DB_ID = "4148b2bb-7833-81ce-9bb6-de189323b9de"
ROW_URL_PREFIX = "https://app.notion.com/p/"


def _is_row_url(url: str) -> bool:
    return bool(url) and url.startswith(ROW_URL_PREFIX) and "-" not in url.rsplit("/", 1)[-1][:8]


def _norm(s: str) -> str:
    return "".join(s.split()).lower()


def main() -> None:
    index_path = Path("data/note_index.json")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    with httpx.Client(base_url=_API, headers=_HEADERS, timeout=60) as c:
        subpages = {_norm(p["title"]): p["url"] for p in list_child_pages(c, config.NOTION_PARENT_PAGE_ID)}
        # 行（视频ID → {page_id, url}）
        rows: dict[str, dict] = {}
        cursor = None
        while True:
            body: dict = {"page_size": 100}
            if cursor:
                body["start_cursor"] = cursor
            d = c.post(f"/databases/{DB_ID}/query", json=body).json()
            for r in d.get("results", []):
                vid = r["properties"].get("视频ID", {}).get("rich_text")
                vid = vid[0]["plain_text"] if vid else ""
                if vid:
                    rows[vid] = {"id": r["id"], "url": r["url"]}
            if not d.get("has_more"):
                break
            cursor = d.get("next_cursor")

        fixed = 0
        for e in index:
            needs = (
                _is_row_url(e.get("notion_url", ""))
                or not e.get("row_url")
                or not e.get("date")
                or not e.get("source_url")
            )
            if not needs or not e.get("file"):
                continue
            note_file = Path("notes") / e["file"]
            fm = parse_frontmatter(note_file.read_text(encoding="utf-8")) if note_file.exists() else {}
            # 1. 总结文档子页面 URL（按原标题匹配父页面子页）
            sub_url = subpages.get(_norm(e["title"]))
            if not sub_url and fm.get("title"):
                sub_url = subpages.get(_norm(str(fm["title"])))
            if not e.get("source_url") and fm.get("source_url"):
                e["source_url"] = str(fm["source_url"])
            if not e.get("date") and fm.get("captured_at"):
                e["date"] = str(fm["captured_at"])[:10]
            row = rows.get(str(e["aweme_id"]), {})
            if _is_row_url(e.get("notion_url", "")) or not e.get("notion_url"):
                e["notion_url"] = sub_url or e.get("notion_url", "")
            e["row_url"] = row.get("url", e.get("row_url", ""))

            # 2. 修 database 行：采集日期 + 链接 callout
            if row:
                props = {"采集日期": {"date": {"start": e["date"]}}} if e.get("date") else {}
                if props:
                    c.patch(f"/pages/{row['id']}", json={"properties": props})
                blocks = c.get(f"/blocks/{row['id']}/children?page_size=100").json().get("results", [])
                for b in blocks:
                    if b["type"] == "callout" and "打开完整笔记" in "".join(
                        t["plain_text"] for t in b["callout"]["rich_text"]
                    ):
                        link = (b["callout"]["rich_text"][0].get("text", {}) or {}).get("link", {})
                        if not link or link.get("url") != e["notion_url"]:
                            c.delete(f"/blocks/{b['id']}")
                            c.patch(f"/blocks/{row['id']}/children", json={"children": [{
                                "object": "block", "type": "callout",
                                "callout": {
                                    "rich_text": [{"type": "text", "text": {
                                        "content": "▶ 打开完整笔记（总结文档）",
                                        "link": {"url": e["notion_url"]},
                                    }}],
                                    "icon": {"emoji": "📄"},
                                },
                            }]})
                        break
            fixed += 1
            print(f"  ✓ {e['short_title'][:24]} → 子页:{bool(e['notion_url'])} 行:{bool(e['row_url'])} 日期:{e['date']}")

        index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
        # 3. 批次条目同步
        bp = Path("data/batches.json")
        batches = json.loads(bp.read_text(encoding="utf-8"))
        for b in batches:
            for it in b["items"]:
                e = next((x for x in index if str(x["aweme_id"]) == str(it["aweme_id"])), None)
                if e and e.get("notion_url"):
                    it["notion_url"] = e["notion_url"]
        bp.write_text(json.dumps(batches, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[+] 修复完成：{fixed} 条")


if __name__ == "__main__":
    main()
