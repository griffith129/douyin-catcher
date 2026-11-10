"""A6：在父页面下为每个大类创建「分类 · X」聚合子页（幂等），供内嵌过滤视图使用。

用法：uv run python scripts/create_category_pages.py
"""

import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from douyin_catcher.config import config  # noqa: E402
from notion_demo import list_child_pages  # noqa: E402

_API = "https://api.notion.com/v1"
_HEADERS = {
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {config.NOTION_TOKEN}",
}


def main() -> None:
    parent = config.NOTION_PARENT_PAGE_ID
    index = json.loads(Path("data/note_index.json").read_text(encoding="utf-8"))
    cats = sorted({e["category"] for e in index if e.get("category")})
    print(f"[+] 共 {len(cats)} 个大类: {cats}")

    with httpx.Client(base_url=_API, headers=_HEADERS, timeout=60) as c:
        existing = {p["title"]: p["id"] for p in list_child_pages(c, parent)}
        mapping: dict[str, dict] = {}
        for cat in cats:
            title = f"分类 · {cat}"
            if title in existing:
                mapping[cat] = {"page_id": existing[title], "created": False}
                print(f"[=] 已存在: {title}")
                continue
            r = c.post("/pages", json={
                "parent": {"page_id": parent},
                "properties": {"title": {"title": [{"text": {"content": title}}]}},
                "children": [{
                    "object": "block", "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {
                        "content": "本页聚合「" + cat + "」大类下的全部视频。下方视图实时同步 database；新视频入池后自动出现在此。"}}]}
                }],
            })
            r.raise_for_status()
            mapping[cat] = {"page_id": r.json()["id"], "created": True}
            print(f"[+] 已创建: {title}")
    meta_path = Path("data/demo_meta.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    meta["category_pages"] = mapping
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[+] 映射已写入 demo_meta.json")


if __name__ == "__main__":
    main()
