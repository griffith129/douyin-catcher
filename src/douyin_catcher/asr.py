"""硅基流动 SenseVoice 语音转文字。"""

from pathlib import Path

import httpx

from .config import config


async def transcribe(audio_path: str | Path, api_key: str | None = None) -> str:
    api_key = api_key or config.SILICONFLOW_API_KEY
    if not api_key:
        raise RuntimeError("缺少 SILICONFLOW_API_KEY")
    url = f"{config.SILICONFLOW_BASE_URL}/audio/transcriptions"
    async with httpx.AsyncClient(timeout=300) as client:
        with Path(audio_path).open("rb") as f:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (Path(audio_path).name, f, "audio/mpeg")},
                data={"model": config.ASR_MODEL},
            )
    resp.raise_for_status()
    return resp.json().get("text", "").strip()
