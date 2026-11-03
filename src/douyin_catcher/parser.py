"""分享口令/链接 → 视频元数据。

流程：正则提取 URL → 短链跟随重定向 → 提取 aweme_id →
请求 iesdouyin 分享页，解析 window._ROUTER_DATA 拿标题/作者/无水印地址。
"""

import json
import re

import httpx

from .config import config

URL_RE = re.compile(r"https?://[^\s，,。；;）)】\]]+")
VIDEO_ID_RE = re.compile(r"/video/(\d{15,21})")
MODAL_ID_RE = re.compile(r"modal_id=(\d{15,21})")
ROUTER_DATA_RE = re.compile(r"window\._ROUTER_DATA\s*=\s*(\{.*?\})\s*;?\s*</script>", re.S)


def extract_urls(share_text: str) -> list[str]:
    """从分享口令中按顺序提取所有 URL（剔除中文标点尾部）。"""
    return URL_RE.findall(share_text or "")


def extract_video_id(url: str) -> str | None:
    """从抖音 URL 中提取视频 aweme_id。"""
    for pattern in (VIDEO_ID_RE, MODAL_ID_RE):
        m = pattern.search(url)
        if m:
            return m.group(1)
    return None


def _parse_router_data(html: str) -> dict:
    m = ROUTER_DATA_RE.search(html)
    if not m:
        raise ValueError("分享页中未找到 _ROUTER_DATA，接口可能已变化")
    return json.loads(m.group(1))


def _info_from_router_data(data: dict) -> dict:
    loader = data.get("loaderData", {})
    res = next(iter(loader.values()), {}).get("videoInfoRes", {})
    items = res.get("item_list") or []
    if not items:
        raise ValueError("视频不存在或已被删除")
    item = items[0]
    play_addr = item.get("video", {}).get("play_addr", {})
    url_list = play_addr.get("url_list") or []
    video_url = url_list[0].replace("playwm", "play") if url_list else ""
    return {
        "aweme_id": item.get("aweme_id", ""),
        "title": (item.get("desc") or "").strip(),
        "author": (item.get("author") or {}).get("nickname", ""),
        "video_url": video_url,
    }


async def fetch_video_info(aweme_id: str) -> dict:
    """根据 aweme_id 拉取视频元数据。"""
    url = f"https://www.iesdouyin.com/share/video/{aweme_id}"
    async with httpx.AsyncClient(
        timeout=config.HTTP_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": config.USER_AGENT},
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    return _info_from_router_data(_parse_router_data(resp.text))


async def resolve_short_url(url: str) -> str:
    """跟随短链重定向，返回最终 URL。"""
    async with httpx.AsyncClient(
        timeout=config.HTTP_TIMEOUT,
        follow_redirects=False,
        headers={"User-Agent": config.USER_AGENT},
    ) as client:
        resp = await client.get(url)
    if resp.is_redirect or resp.is_server_error and "Location" in resp.headers:
        return resp.headers["Location"]
    if resp.status_code == 200:
        return str(resp.url)
    raise ValueError(f"短链解析失败: HTTP {resp.status_code}")


async def parse_share_text(share_text: str) -> dict:
    """分享口令 → 视频元数据（主入口）。"""
    for url in extract_urls(share_text):
        vid = extract_video_id(url)
        if vid is None:
            final = await resolve_short_url(url)
            vid = extract_video_id(final)
        if vid:
            return await fetch_video_info(vid)
    raise ValueError("分享文本中未找到抖音视频链接")
