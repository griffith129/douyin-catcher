"""为 39 篇笔记生成标签（LLM）+ 概述（精华版截断），并回填 Notion database property。

两步：
  uv run python scripts/enrich_notes.py tags    # LLM 提取标签 → data/note_index.json
  uv run python scripts/enrich_notes.py notion  # 回填 概述/标签 property 到 Notion 行
"""

import asyncio
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from douyin_catcher.config import config  # noqa: E402
from douyin_catcher.enrich import extract_tags, summarize_preview  # noqa: E402

INDEX_FILE = Path("data/note_index.json")
DB_ID = "4148b2bb-7833-81ce-9bb6-de189323b9de"
_HEADERS = {
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {config.NOTION_TOKEN}",
}


async def gen_tags() -> None:
    index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    api_key = config.LLM_API_KEY or config.SILICONFLOW_API_KEY
    sem = asyncio.Semaphore(5)

    async def one(e: dict) -> None:
        async with sem:
            try:
                tags = await extract_tags(e["title"], e.get("preview", ""), api_key)
                e["tags"] = tags
                print(f"  {e['title'][:26]} → {', '.join(tags)}")
            except Exception as exc:
                print(f"  FAIL {e['title'][:26]}: {exc}")

    await asyncio.gather(*(one(e) for e in index))
    INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    n = sum(1 for e in index if e.get("tags"))
    print(f"[+] 标签完成：{n}/{len(index)} 篇")


def backfill_notion() -> None:
    index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    with httpx.Client(base_url="https://api.notion.com/v1", headers=_HEADERS, timeout=60) as c:
        # 先确保 database schema 有 概述/标签 property（PATCH 行不能新建 property）
        r = c.patch(
            f"/databases/{DB_ID}",
            json={"properties": {"概述": {"rich_text": {}}, "标签": {"multi_select": {}}}},
        )
        r.raise_for_status()
        print("[+] schema 已含 概述/标签 property")
        # 拉取全部行：优先 视频ID 匹配（Name 已是短标题，不可靠），回退原标题
        rows: dict[str, str] = {}
        fallback: dict[str, str] = {}
        cursor = None
        while True:
            body: dict = {"page_size": 100}
            if cursor:
                body["start_cursor"] = cursor
            data = c.post(f"/databases/{DB_ID}/query", json=body).json()
            for p in data.get("results", []):
                props = p["properties"]
                vid = props.get("视频ID", {}).get("rich_text")
                vid = vid[0]["plain_text"] if vid else ""
                t = props["Name"]["title"]
                title = t[0]["plain_text"] if t else ""
                if vid:
                    rows[vid] = p["id"]
                else:
                    fallback[title] = p["id"]
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
        print(f"[+] database 共 {len(rows) + len(fallback)} 行（视频ID: {len(rows)}，回退标题: {len(fallback)}）")
        done = 0
        for e in index:
            page_id = rows.get(str(e["aweme_id"])) or fallback.get(e["title"])
            if not page_id:
                continue
            props = {
                "概述": {"rich_text": [{"text": {"content": summarize_preview(e.get("preview", ""))}}]},
                "标签": {"multi_select": [{"name": t} for t in e.get("tags", [])]},
            }
            r = c.patch(f"/pages/{page_id}", json={"properties": props})
            r.raise_for_status()
            done += 1
    print(f"[+] 回填完成：{done} 行已写入 概述/标签")


if __name__ == "__main__":
    if sys.argv[-1] == "notion":
        backfill_notion()
    else:
        asyncio.run(gen_tags())
