"""Notion 清理与正式化（一次性运维脚本）：
1. 归档 demo 页面：更新日志（Demo）/ 更新日志 v2（Demo）/【验证样例】/ 分类 · ××
2. database 改名：抖音知识库（Demo）→ 抖音知识库
3. 每行详情：归档"（Demo 行"提示段；确保有"▶ 打开完整笔记"链接 callout

用法：uv run python scripts/notion_cleanup.py
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
DB_ID = "4148b2bb-7833-81ce-9bb6-de189323b9de"
DB_TITLE = "抖音知识库"
ARCHIVE_PREFIXES = ("分类 · ",)
ARCHIVE_TITLES = {"更新日志（Demo）", "更新日志 v2（Demo）",
                  "【验证样例】douyin-catcher 笔记收录结构演示"}


def main() -> None:
    index = {e["aweme_id"]: e for e in json.loads(Path("data/note_index.json").read_text(encoding="utf-8"))}
    with httpx.Client(base_url=_API, headers=_HEADERS, timeout=60) as c:
        # 1. 归档 demo 页面
        for p in list_child_pages(c, config.NOTION_PARENT_PAGE_ID):
            if p["title"] in ARCHIVE_TITLES or p["title"].startswith(ARCHIVE_PREFIXES):
                c.delete(f"/blocks/{p['id']}")
                print(f"[-] 已归档页面: {p['title'][:40]}")

        # 2. database 正名
        c.patch(f"/databases/{DB_ID}", json={
            "title": [{"type": "text", "text": {"content": DB_TITLE}}],
        })
        print(f"[+] database 已改名: {DB_TITLE}")

        # 3. 行详情清理 + 接链接
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
        print(f"[+] 共 {len(rows)} 行待处理")

        fixed = 0
        for row in rows:
            props = row["properties"]
            vid = props.get("视频ID", {}).get("rich_text")
            vid = vid[0]["plain_text"] if vid else ""
            e = index.get(vid)
            if not e:
                print(f"  !! 无索引条目，跳过: {vid}")
                continue
            page_id = row["id"]
            blocks = c.get(f"/blocks/{page_id}/children?page_size=100").json().get("results", [])
            demo_block = next((b for b in blocks
                               if b["type"] == "paragraph" and "Demo 行" in
                               (b["paragraph"]["rich_text"][0]["plain_text"] if b["paragraph"]["rich_text"] else "")), None)
            if demo_block:
                c.delete(f"/blocks/{demo_block['id']}")
            has_link = any(b["type"] == "callout" and "打开完整笔记" in
                           (b["callout"]["rich_text"][0]["plain_text"] if b["callout"]["rich_text"] else "")
                           for b in blocks)
            if not has_link and e.get("notion_url"):
                c.patch(f"/blocks/{page_id}/children", json={"children": [{
                    "object": "block", "type": "callout",
                    "callout": {
                        "rich_text": [{"type": "text", "text": {
                            "content": "▶ 打开完整笔记（总结文档）",
                            "link": {"url": e["notion_url"]},
                        }}],
                        "icon": {"emoji": "📄"},
                    },
                }]})
                fixed += 1
        print(f"[+] 行详情链接补齐：{fixed} 行新增（其余已有或无链接可加）")


if __name__ == "__main__":
    main()
