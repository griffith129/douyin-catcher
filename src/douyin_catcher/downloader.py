"""无水印视频下载。

抖音 CDN 流可能中途停滞（httpx.ReadTimeout），因此：
- 读超时独立设置（小于总超时，快速感知停滞）；
- 失败后断点续传重试（Range 请求）；
- 服务器不支持 Range（返回 200 而非 206）时从头重写。
"""

from pathlib import Path

import httpx

from .config import config

# 触发重试的网络类异常（不含 4xx/5xx——HTTP 错误重试没有意义）
_RETRYABLE = (
    httpx.ReadTimeout,
    httpx.ConnectTimeout,
    httpx.ReadError,
    httpx.RemoteProtocolError,
)

_READ_TIMEOUT = 30.0  # 单次 read 停滞 30s 即判定流断开，快速进入重试


def _headers(partial: int) -> dict:
    h = {
        "User-Agent": config.USER_AGENT,
        "Referer": "https://www.douyin.com/",
    }
    if partial:
        h["Range"] = f"bytes={partial}-"
    return h


async def _attempt(url: str, dest: Path) -> None:
    partial = dest.stat().st_size if dest.exists() else 0
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(config.DOWNLOAD_TIMEOUT, read=_READ_TIMEOUT),
        follow_redirects=True,
        trust_env=False,  # 国内 CDN 直连，绕过环境代理
        headers=_headers(partial),
    ) as client:
        async with client.stream("GET", url) as resp:
            resume = partial > 0 and resp.status_code == 206  # 服务器确认断点续传
            resp.raise_for_status()
            mode = "ab" if resume else "wb"
            with dest.open(mode) as f:
                async for chunk in resp.aiter_bytes(65536):
                    f.write(chunk)


async def download_video(url: str, dest: str | Path, retries: int = 3) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    last_exc: Exception | None = None
    for _ in range(retries + 1):
        try:
            await _attempt(url, dest)
            return dest
        except _RETRYABLE as exc:
            last_exc = exc
    raise last_exc  # type: ignore[misc]
