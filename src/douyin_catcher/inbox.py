"""方案A：从 douyin-chat-export 的开放 REST API 拉取对话消息，
提取抖音链接并去重入池（data/inbox_pool.json）。

douyin-chat-export：https://github.com/TeamBreakerr/douyin-chat-export
鉴权：Authorization: Bearer <api_token>（token 在其 data/panel_config.json）。
"""

import json
import re
import time
from pathlib import Path

import httpx

from .config import config

DOUYIN_LINK_RE = re.compile(
    r"https?://(?:v\.douyin\.com|www\.douyin\.com|www\.iesdouyin\.com)"
    r"/[^\s\"'\\<>，,。；;）)】\]]+"
)


def _headers(token: str | None) -> dict:
    return {"Authorization": f"Bearer {token}"} if token else {}


async def fetch_conversations(base_url: str, token: str | None = None) -> list[dict]:
    """列出 douyin-chat-export 中的会话。"""
    async with httpx.AsyncClient(timeout=30, trust_env=False) as client:
        resp = await client.get(
            f"{base_url.rstrip('/')}/api/conversations", headers=_headers(token)
        )
        resp.raise_for_status()
        data = resp.json()
    items = data.get("conversations") or data.get("items") or []
    return items if isinstance(items, list) else []


async def fetch_messages(
    base_url: str,
    conv_id: str,
    token: str | None = None,
    after_seq: int | None = None,
    page_size: int = 200,
) -> list[dict]:
    """分页拉取某会话的消息（after_seq 增量）。"""
    async with httpx.AsyncClient(timeout=30, trust_env=False) as client:
        all_msgs: list[dict] = []
        seq = after_seq
        while True:
            params: dict = {"page_size": str(page_size)}
            if seq is not None:
                params["after_seq"] = str(seq)
            resp = await client.get(
                f"{base_url.rstrip('/')}/api/conversations/{conv_id}/messages",
                headers=_headers(token),
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
            msgs = data.get("messages") or []
            if not msgs:
                break
            all_msgs.extend(msgs)
            last = int(msgs[-1].get("seq") or 0)
            if len(msgs) < page_size or last <= (seq or 0):
                break
            seq = last
    return all_msgs


def _iter_strings(obj) -> list[str]:
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_strings(v)


def _extract_from_message(msg: dict) -> list[str]:
    """递归扫描消息 JSON 里的抖音链接。"""
    urls: list[str] = []
    seen_text = ""
    content = msg.get("content")
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            content = {"text": content}
    for s in _iter_strings(content):
        seen_text += s + "\n"
    if msg.get("text_result"):
        seen_text += str(msg["text_result"]) + "\n"
    for m in DOUYIN_LINK_RE.finditer(seen_text):
        url = m.group(0).rstrip(".,;:")
        if url not in urls:
            urls.append(url)
    return urls


def extract_links(messages: list[dict]) -> list[dict]:
    """从消息列表中提取抖音链接，返回去重后的记录列表。"""
    seen: dict[str, dict] = {}
    for msg in messages:
        for url in _extract_from_message(msg):
            if url not in seen:
                seen[url] = {
                    "url": url,
                    "msg_id": msg.get("msg_id"),
                    "seq": msg.get("seq"),
                    "created_at_us": msg.get("created_at_us"),
                }
    return list(seen.values())


def load_pool(pool_file: str | Path) -> dict:
    path = Path(pool_file)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"links": {}, "last_seq": 0, "updated_at": ""}


def merge_into_pool(pool: dict, found: list[dict], status: str = "pending") -> int:
    """合并新链接进池（按 URL 去重），返回新增数量；状态默认 pending。"""
    added = 0
    for item in found:
        url = item["url"]
        if url not in pool["links"]:
            pool["links"][url] = {
                "status": status,
                "msg_id": item.get("msg_id"),
                "seq": item.get("seq"),
                "created_at_us": item.get("created_at_us"),
                "added_at": time.strftime("%Y-%m-%d %H:%M"),
            }
            added += 1
    return added


async def sync_inbox(
    pool_file: str | Path,
    base_url: str | None = None,
    conv_id: str | None = None,
    token: str | None = None,
) -> dict:
    """增量同步：拉取新消息 → 提取链接 → 合并入池 → 写回。返回统计。"""
    base_url = base_url or config.INBOX_API_BASE_URL
    conv_id = conv_id or config.INBOX_CONV_ID
    token = token or config.INBOX_API_TOKEN
    if not conv_id:
        raise RuntimeError("缺少 INBOX_CONV_ID（会话 ID）")
    pool = load_pool(pool_file)
    messages = await fetch_messages(
        base_url, conv_id, token=token, after_seq=pool.get("last_seq") or 0
    )
    found = extract_links(messages)
    added = merge_into_pool(pool, found)
    seqs = [int(m.get("seq") or 0) for m in messages]
    if seqs:
        pool["last_seq"] = max(int(pool.get("last_seq") or 0), max(seqs))
    pool["updated_at"] = time.strftime("%Y-%m-%d %H:%M")
    Path(pool_file).write_text(json.dumps(pool, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"added": added, "total": len(pool["links"]), "last_seq": pool["last_seq"]}
