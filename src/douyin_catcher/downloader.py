"""无水印视频下载。"""

from pathlib import Path

import httpx

from .config import config


async def download_video(url: str, dest: str | Path) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(
        timeout=config.DOWNLOAD_TIMEOUT,
        follow_redirects=True,
        trust_env=False,  # 国内 CDN 直连，绕过环境代理
        headers={"User-Agent": config.USER_AGENT, "Referer": "https://www.douyin.com/"},
    ) as client:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            with dest.open("wb") as f:
                async for chunk in resp.aiter_bytes(65536):
                    f.write(chunk)
    return dest
