"""T1 v2 落库：database Name 换为短标题，回填 原标题/视频ID property。

- 行定位：当前 Name（=原标题）匹配一次，之后全部脚本改用 视频ID 定位（幂等）
- 幂等：行已有 视频ID 时跳过重命名（说明已落库过）

用法：uv run python scripts/backfill_titles_v2.py
"""

import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from douyin_catcher.config import config  # noqa: E402

_API = "https://api.notion.com/v1"
_HEADERS = {
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {config.NOTION_TOKEN}",
}
DB_ID = "4148b2bb-7833-81ce-9bb6-de189323b9de"


def main() -> None:
    index = json.loads(Path("data/note_index.json").read_text(encoding="utf-8"))
    with httpx.Client(base_url=_API, headers=_HEADERS, timeout=60) as c:
        # 1. schema：新增 原标题 / 视频ID
        r = c.patch(f"/databases/{DB_ID}", json={
            "properties": {"原标题": {"rich_text": {}}, "视频ID": {"rich_text": {}}}
        })
        r.raise_for_status()
        print("[+] schema 已含 原标题/视频ID")

        # 2. 拉全部行
        rows, cursor = [], None
        while True:
            body: dict = {"page_size": 100}
            if cursor:
                body["start_cursor"] = cursor
            data = c.post(f"/databases/{DB_ID}/query", json=body).json()
            rows.extend(data.get("results", []))
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
        print(f"[+] database 共 {len(rows)} 行")

        # 3. 按 Name（当前=原标题）匹配索引条目
        by_title = {e["title"]: e for e in index}
        done = skip = 0
        for row in rows:
            pid = row["id"]
            props = row["properties"]
            name_t = props["Name"]["title"]
            cur_name = name_t[0]["plain_text"] if name_t else ""
            already = props.get("视频ID", {}).get("rich_text") and props["视频ID"]["rich_text"][0]["plain_text"]
            if already:
                skip += 1
                continue
            e = by_title.get(cur_name)
            if not e or not e.get("short_title"):
                print(f"  !! 未匹配索引: {cur_name[:30]}")
                continue
            body = {"properties": {
                "Name": {"title": [{"text": {"content": e["short_title"]}}]},
                "原标题": {"rich_text": [{"text": {"content": e["title"]}}]},
                "视频ID": {"rich_text": [{"text": {"content": str(e["aweme_id"])}}]},
            }}
            r = c.patch(f"/pages/{pid}", json=body)
            r.raise_for_status()
            done += 1
        print(f"[+] 重命名+回填完成：{done} 行（已落库跳过 {skip} 行）")


if __name__ == "__main__":
    main()
