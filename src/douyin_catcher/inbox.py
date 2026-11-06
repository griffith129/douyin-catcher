"""方案A：从 douyin-chat-export 的开放 REST API 拉取对话消息，
提取抖音视频链接并去重入池（data/inbox_pool.json）。

两类来源：
- 分享卡片消息（msg_type=4）：raw_data.content_json 自带 itemId + aweme_title，
  直接得到"视频链接 + 标题"，无需额外解析；
- 文本消息：正则提取 v.douyin.com / douyin.com 链接（标题待处理时补全）。

douyin-chat-export：https://github.com/TeamBreakerr/douyin-chat-export
鉴权：Authorization: Bearer <api_token>（token 在其 data/panel_config.json）。
"""

import json
import re
import time
from pathlib import Path
from urllib.parse import quote

import httpx

from .config import config

DOUYIN_LINK_RE = re.compile(
    r"https?://(?:v\.douyin\.com|www\.douyin\.com|www\.iesdouyin\.com)"
    r"/[^\s\"'\\<>，,。；;）)】\]]+"
)
AWEME_ID_RE = re.compile(r"^\d{15,21}$")


def normalize_conv_id(conv_id: str) -> str:
    """剥掉从面板复制时可能带上的尖括号与空白。"""
    return (conv_id or "").strip().strip("<>").strip()


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
    items = data.get("items") or data.get("conversations") or []
    return items if isinstance(items, list) else []


async def fetch_messages(
    base_url: str,
    conv_id: str,
    token: str | None = None,
    after_seq: int | None = None,
    page_size: int = 500,
) -> list[dict]:
    """分页拉取某会话的全部新消息（after_seq 增量）。"""
    conv_id = normalize_conv_id(conv_id)
    base = f"{base_url.rstrip('/')}/api/conversations/{quote(conv_id, safe='')}/messages"
    async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
        all_msgs: list[dict] = []
        seq = after_seq
        while True:
            params: dict = {"page_size": str(page_size)}
            if seq is not None:
                params["after_seq"] = str(seq)
            resp = await client.get(base, headers=_headers(token), params=params)
            resp.raise_for_status()
            data = resp.json()
            # 真实 API 的列表键是 items；保留 messages 兜底
            msgs = data.get("items") or data.get("messages") or []
            if not msgs:
                break
            all_msgs.extend(msgs)
            last = int(msgs[-1].get("seq") or 0)
            if last <= (seq if seq is not None else -1) or not data.get("has_newer", True):
                break
            seq = last
    return all_msgs


def _share_records(msg: dict) -> list[dict]:
    """分享卡片消息 → itemId + 标题（raw_data.content_json）。

    真实结构（2026-11 抓包）：content_json 是再编码一次的 JSON 字符串，
    标题在 content_title，作者名在 content_name；兼容旧 aweme_title 字段。
    """
    try:
        raw = json.loads(msg.get("raw_data") or "{}")
    except (json.JSONDecodeError, TypeError):
        return []
    if raw.get("msg_type") != "share":
        return []
    cj_raw = raw.get("content_json") or "{}"
    if isinstance(cj_raw, str):
        try:
            cj = json.loads(cj_raw)
        except (json.JSONDecodeError, TypeError):
            return []
    elif isinstance(cj_raw, dict):
        cj = cj_raw
    else:
        return []
    media_type = cj.get("media_type")
    if media_type not in (None, "", "video"):  # 商品/直播卡片不要
        return []
    item_id = str(cj.get("itemId") or "")
    if not AWEME_ID_RE.match(item_id):
        return []
    return [
        {
            "url": f"https://www.douyin.com/video/{item_id}",
            "title": (cj.get("content_title") or cj.get("aweme_title") or "").strip(),
            "author": (cj.get("content_name") or "").strip(),
            "conv_id": msg.get("conv_id"),
            "msg_id": msg.get("msg_id"),
            "seq": msg.get("seq"),
            "timestamp": msg.get("timestamp"),
        }
    ]


def _text_records(msg: dict) -> list[dict]:
    """文本消息 → 正则提取抖音链接（标题未知，处理时补全）。"""
    texts = []
    content = msg.get("content")
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            content = {"text": content}

    def _walk(obj):
        if isinstance(obj, str):
            texts.append(obj)
        elif isinstance(obj, dict):
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for v in obj:
                _walk(v)

    _walk(content)
    if msg.get("voice_transcription"):
        texts.append(str(msg["voice_transcription"]))
    out = []
    for s in texts:
        for m in DOUYIN_LINK_RE.finditer(s):
            url = m.group(0).rstrip(".,;:")
            if not any(r["url"] == url for r in out):
                out.append(
                    {
                        "url": url,
                        "title": "",
                        "author": "",
                        "conv_id": msg.get("conv_id"),
                        "msg_id": msg.get("msg_id"),
                        "seq": msg.get("seq"),
                        "timestamp": msg.get("timestamp"),
                    }
                )
    return out


def extract_links(messages: list[dict]) -> list[dict]:
    """从消息列表中提取抖音视频，按 URL 去重。"""
    seen: dict[str, dict] = {}
    for msg in messages:
        for rec in _share_records(msg) or _text_records(msg):
            url = rec["url"]
            if url not in seen:
                seen[url] = rec
    return list(seen.values())


def load_pool(pool_file: str | Path) -> dict:
    path = Path(pool_file)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"links": {}, "conversations": {}, "last_seq": 0, "updated_at": ""}


def merge_into_pool(
    pool: dict,
    found: list[dict],
    status: str = "pending",
    conv_name: str = "",
) -> int:
    """合并新视频进池（按 URL 去重），返回新增数量。

    conv_id 来自每条记录自身；conv_name 由调用方（当前会话名）补充。
    """
    added = 0
    for item in found:
        url = item["url"]
        if url not in pool["links"]:
            pool["links"][url] = {
                "status": status,
                "title": item.get("title", ""),
                "author": item.get("author", ""),
                "conv_id": item.get("conv_id"),
                "conv_name": conv_name,
                "msg_id": item.get("msg_id"),
                "seq": item.get("seq"),
                "timestamp": item.get("timestamp"),
                "added_at": time.strftime("%Y-%m-%d %H:%M"),
            }
            added += 1
    return added


async def sync_inbox(
    pool_file: str | Path,
    base_url: str | None = None,
    conv_id: str | None = None,
    token: str | None = None,
    conv_ids: list[str] | None = None,
) -> dict:
    """多会话增量同步：每个会话独立记录 last_seq，按会话分组入池。

    conv_ids 为空时同步采集服务中的全部会话；conv_id 为旧版单会话参数。
    池结构：{"links": {...}, "conversations": {conv_id: {"name", "last_seq"}}}。
    """
    base_url = base_url or config.INBOX_API_BASE_URL
    token = token or config.INBOX_API_TOKEN
    if conv_id:
        conv_ids = [conv_id]
    pool = load_pool(pool_file)
    pool.setdefault("conversations", {})
    convs_meta = {
        normalize_conv_id(c.get("conv_id") or ""): c
        for c in await fetch_conversations(base_url, token)
        if c.get("conv_id")
    }
    if not conv_ids:
        conv_ids = list(convs_meta)
    if not conv_ids:
        raise RuntimeError("采集服务中没有任何会话")

    # 旧版单会话池迁移：seed 配置会话并把无 conv_id 的存量链接归入
    if not pool["conversations"] and pool.get("last_seq"):
        legacy = normalize_conv_id(config.INBOX_CONV_ID)
        if legacy:
            pool["conversations"][legacy] = {
                "name": (convs_meta.get(legacy) or {}).get("name") or legacy,
                "last_seq": int(pool["last_seq"]),
            }
            for it in pool["links"].values():
                if not it.get("conv_id"):
                    it["conv_id"] = legacy

    added = 0
    for cid in conv_ids:
        cid = normalize_conv_id(cid)
        if not cid:
            continue
        state = pool["conversations"].setdefault(
            cid,
            {"name": (convs_meta.get(cid) or {}).get("name") or cid, "last_seq": 0},
        )
        if (convs_meta.get(cid) or {}).get("name"):
            state["name"] = convs_meta[cid]["name"]
        messages = await fetch_messages(
            base_url, cid, token=token, after_seq=state.get("last_seq") or 0
        )
        found = extract_links(messages)
        for rec in found:  # 消息缺 conv_id 字段时按当前会话补全
            if not rec.get("conv_id"):
                rec["conv_id"] = cid
        added += merge_into_pool(pool, found, conv_name=state["name"])
        seqs = [int(m.get("seq") or 0) for m in messages]
        if seqs:
            state["last_seq"] = max(int(state.get("last_seq") or 0), max(seqs))

    pool["last_seq"] = max(
        (int(s.get("last_seq") or 0) for s in pool["conversations"].values()), default=0
    )
    pool["updated_at"] = time.strftime("%Y-%m-%d %H:%M")
    Path(pool_file).write_text(
        json.dumps(pool, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {
        "added": added,
        "total": len(pool["links"]),
        "last_seq": pool["last_seq"],
        "conversations": len(pool["conversations"]),
    }
