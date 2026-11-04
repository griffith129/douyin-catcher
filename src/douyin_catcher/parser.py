"""分享口令/链接 → 视频元数据。

流程：正则提取 URL → 短链跟随重定向 → 提取 aweme_id →
无头浏览器加载视频页并拦截页面自身的签名 detail 响应 → 提取标题/作者/无水印地址。
（2025-11 起分享页 SSR 已不内嵌 videoInfoRes，浏览器渲染是当前可行路线。）
"""

import re

from .browser import fetch_detail_via_browser
from .config import config

URL_RE = re.compile(r"https?://[^\s，,。；;）)】\]]+")
VIDEO_ID_RE = re.compile(r"/(?:video|note|slides)/(\d{15,21})")
MODAL_ID_RE = re.compile(r"modal_id=(\d{15,21})")


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


def _info_from_detail(data: dict) -> dict:
    """从 detail 接口响应中提取统一形状的元数据。"""
    detail = data.get("aweme_detail") or {}
    if not detail:
        raise ValueError("视频不存在或已被删除（detail 返回空）")
    play_addr = (detail.get("video") or {}).get("play_addr") or {}
    url_list = play_addr.get("url_list") or []
    video_url = url_list[0].replace("playwm", "play") if url_list else ""
    return {
        "aweme_id": detail.get("aweme_id", ""),
        "title": (detail.get("desc") or "").strip(),
        "author": (detail.get("author") or {}).get("nickname", ""),
        "video_url": video_url,
    }


async def fetch_video_info(aweme_id: str) -> dict:
    """根据 aweme_id 拉取视频元数据（浏览器渲染路线）。"""
    data = await fetch_detail_via_browser(aweme_id, timeout_s=config.BROWSER_TIMEOUT)
    return _info_from_detail(data)


async def resolve_short_url(url: str) -> str:
    """跟随短链重定向，返回最终 URL。"""
    import httpx

    async with httpx.AsyncClient(
        timeout=config.HTTP_TIMEOUT,
        follow_redirects=False,
        headers={"User-Agent": config.USER_AGENT},
        trust_env=False,
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
