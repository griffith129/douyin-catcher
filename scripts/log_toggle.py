"""B4：把更新日志升级为 toggle 折叠摘要卡版（收起只见标题+标签，展开显概述卡）。

用法：uv run python scripts/log_toggle.py
"""

import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from douyin_catcher.config import config  # noqa: E402
from douyin_catcher.enrich import summarize_preview  # noqa: E402
from notion_demo import list_child_pages  # noqa: E402

_API = "https://api.notion.com/v1"
_HEADERS = {
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {config.NOTION_TOKEN}",
}
LOG2_TITLE = "更新日志 v2（Demo）"


def _rich(text: str, link: str | None = None) -> list[dict]:
    return [{"type": "text", "text": {"content": text, "link": {"url": link} if link else None}}]


def main() -> None:
    parent = config.NOTION_PARENT_PAGE_ID
    index = {e["title"]: e for e in json.loads(Path("data/note_index.json").read_text(encoding="utf-8"))}
    batches = json.loads(Path("data/batches.json").read_text(encoding="utf-8"))

    with httpx.Client(base_url=_API, headers=_HEADERS, timeout=60) as c:
        children_pages = list_child_pages(c, parent)
        url_map = {p["title"]: p["url"] for p in children_pages}
        # 幂等：归档旧 v2
        for p in children_pages:
            if p["title"] == LOG2_TITLE:
                c.delete(f"/blocks/{p['id']}")

        blocks: list[dict] = []
        for b in batches:
            blocks.append({"object": "block", "type": "heading_2",
                           "heading_2": {"rich_text": _rich(f"📦 {b['batch_id']}（{b['created_at']}，{len(b['items'])} 篇）")}})
            groups: dict[str, list[dict]] = {}
            for it in b["items"]:
                groups.setdefault(it.get("category", "未分类"), []).append(it)
            for cat in sorted(groups):
                blocks.append({"object": "block", "type": "heading_3",
                               "heading_3": {"rich_text": _rich(f"{cat}（{len(groups[cat])}）")}})
                for it in groups[cat]:
                    e = index.get(it["title"], {})
                    tags = e.get("tags", [])
                    toggle_title = it["title"] + ("　｜　" + " / ".join(tags) if tags else "")
                    link = it.get("notion_url") or url_map.get(it["title"], "")
                    kids = [
                        {"object": "block", "type": "callout",
                         "callout": {"rich_text": _rich("📌 " + summarize_preview(e.get("preview", ""))),
                                     "icon": {"emoji": "📝"}}},
                        {"object": "block", "type": "paragraph",
                         "paragraph": {"rich_text": _rich("▶ 打开完整笔记", link or None)}},
                    ]
                    blocks.append({
                        "object": "block", "type": "toggle",
                        "toggle": {"rich_text": _rich(toggle_title, it.get("notion_url") or url_map.get(it["title"]))},
                    })
                    # toggle 的 children 需与 toggle 同请求；上面先 push 空 toggle 再补 children
                    blocks[-1]["toggle"]["children"] = kids
        r = c.post("/pages", json={
            "parent": {"page_id": parent},
            "properties": {"title": {"title": [{"text": {"content": LOG2_TITLE}}]}},
            "children": blocks[:100],  # 单请求上限 100 blocks
        })
        r.raise_for_status()
        page_id = r.json()["id"]
        url = r.json()["url"]
        # 超 100 分批追加
        for i in range(100, len(blocks), 100):
            r = c.patch(f"/blocks/{page_id}/children", json={"children": blocks[i:i + 100]})
            r.raise_for_status()
        print(f"[+] {LOG2_TITLE} 已写入: {url}（{len(blocks)} blocks）")
        meta = json.loads(Path("data/demo_meta.json").read_text(encoding="utf-8"))
        meta["log_url_v2"] = url
        Path("data/demo_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
