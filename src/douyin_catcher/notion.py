"""Notion 1A：官方 API 直连，把笔记收录为指定页面下的子页面。

用法：在 .env 配置 NOTION_TOKEN（integration secret，ntn_ 开头）和
NOTION_PARENT_PAGE_ID（目标页面 ID，可从 Notion 链接中提取），pipeline
落盘笔记后自动建子页面上传；未配置则跳过，不影响主流程。
"""

import httpx

from .config import config

_API = "https://api.notion.com/v1"
_HEADERS = {"Notion-Version": "2022-06-28", "Content-Type": "application/json"}
_RICH_TEXT_LIMIT = 2000
_BLOCKS_PER_REQUEST = 100


def _rich_text(text: str) -> list[dict]:
    """切分超长文本为多个 rich_text 元素（单元素上限 2000 字符）。"""
    out = []
    for i in range(0, len(text), _RICH_TEXT_LIMIT):
        out.append({"type": "text", "text": {"content": text[i : i + _RICH_TEXT_LIMIT]}})
    return out or [{"type": "text", "text": {"content": ""}}]


def _strip_frontmatter(md: str) -> str:
    if md.startswith("---"):
        parts = md.split("---", 2)
        if len(parts) >= 3:
            return parts[2].lstrip("\n")
    return md


def md_to_blocks(md: str) -> list[dict]:
    """把简化的 Markdown 行转换为 Notion blocks。"""
    blocks: list[dict] = []
    for raw in _strip_frontmatter(md).splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("### "):
            kind, text = "heading_3", line[4:]
        elif line.startswith("## "):
            kind, text = "heading_2", line[3:]
        elif line.startswith("# "):
            kind, text = "heading_1", line[2:]
        elif line.startswith("- ") or line.startswith("* "):
            kind, text = "bulleted_list_item", line[2:]
        else:
            kind, text = "paragraph", line
        blocks.append({"object": "block", "type": kind, kind: {"rich_text": _rich_text(text)}})
    return blocks


def extract_page_id(link: str) -> str:
    """从 Notion 链接或裸 ID 中提取页面 ID（去掉连字符与查询串）。"""
    import re

    cleaned = link.split("?")[0].rstrip("/")
    m = re.search(r"([0-9a-fA-F]{32}|[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})$", cleaned)
    return (m.group(1).replace("-", "") if m else cleaned.replace("-", ""))


async def upload_note(
    title: str,
    md: str,
    parent_page_id: str | None = None,
    token: str | None = None,
) -> str:
    """在指定页面下创建子页面并写入 blocks，返回子页面 URL。"""
    token = token or config.NOTION_TOKEN
    parent = parent_page_id or config.NOTION_PARENT_PAGE_ID
    if not token:
        raise RuntimeError("缺少 NOTION_TOKEN")
    if not parent:
        raise RuntimeError("缺少 NOTION_PARENT_PAGE_ID")
    blocks = md_to_blocks(md)
    payload = {
        "parent": {"page_id": parent},
        "properties": {"title": {"title": [{"text": {"content": title}}]}},
        "children": blocks[:_BLOCKS_PER_REQUEST],
    }
    headers = {**_HEADERS, "Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(f"{_API}/pages", headers=headers, json=payload)
        resp.raise_for_status()
        page = resp.json()
        # 超出首请求上限的 blocks 分批追加
        for i in range(_BLOCKS_PER_REQUEST, len(blocks), _BLOCKS_PER_REQUEST):
            append = await client.patch(
                f"{_API}/blocks/{page['id']}/children",
                headers=headers,
                json={"children": blocks[i : i + _BLOCKS_PER_REQUEST]},
            )
            append.raise_for_status()
        return page.get("url", "")
