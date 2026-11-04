"""无头浏览器渲染：加载抖音视频页，拦截页面自身发出的签名 detail 请求。

2025-11 起分享页 SSR 不再内嵌 videoInfoRes，且 detail 接口要求真实浏览器
铸造的 cookie（uifid 等），纯 httpx + 签名会被 ArgusSecurityPlugin 拒绝。
因此由真实浏览器完成全部签名与风控，我们只负责读取响应。
"""

import asyncio
import time

from playwright.sync_api import sync_playwright

_WEB_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
# 优先用本机已装浏览器（免下载 chromium 二进制）
_CHANNELS = ("msedge", "chrome")
_DETAIL_PATH = "/aweme/v1/web/aweme/detail/"


def _fetch_detail_sync(aweme_id: str, timeout_s: float) -> dict:
    with sync_playwright() as p:
        browser = None
        for channel in _CHANNELS:
            try:
                browser = p.chromium.launch(channel=channel, headless=True)
                break
            except Exception:
                continue
        if browser is None:
            # ponytail: 兜底需 playwright install chromium
            browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=_WEB_UA, locale="zh-CN")
        captured: dict = {}

        def _on_response(resp):
            if _DETAIL_PATH not in resp.url:
                return
            try:
                data = resp.json()
            except Exception:
                return
            detail = data.get("aweme_detail") or {}
            if detail.get("aweme_id") or detail.get("desc") or detail.get("video"):
                captured["data"] = data

        page.on("response", _on_response)
        try:
            page.goto(
                f"https://www.douyin.com/video/{aweme_id}",
                timeout=int(timeout_s * 1000),
                wait_until="domcontentloaded",
            )
            start = time.monotonic()
            while "data" not in captured and time.monotonic() - start < timeout_s:
                page.wait_for_timeout(500)
        finally:
            browser.close()
    return captured.get("data") or {}


async def fetch_detail_via_browser(aweme_id: str, timeout_s: float = 30.0) -> dict:
    """线程里跑阻塞实现，避免卡死事件循环。"""
    return await asyncio.to_thread(_fetch_detail_sync, aweme_id, timeout_s)
