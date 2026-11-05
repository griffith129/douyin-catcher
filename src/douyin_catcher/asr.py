"""语音转文字：硅基流动 SenseVoice（云端）或 faster-whisper（本地）。"""

from pathlib import Path

import httpx

from .audio import FFMPEG
from .config import config


async def _transcribe_siliconflow(audio_path: Path, api_key: str) -> str:
    url = f"{config.SILICONFLOW_BASE_URL}/audio/transcriptions"
    async with httpx.AsyncClient(timeout=300) as client:
        with audio_path.open("rb") as f:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (audio_path.name, f, "audio/mpeg")},
                data={"model": config.ASR_MODEL},
            )
    resp.raise_for_status()
    return resp.json().get("text", "").strip()


def _transcribe_whisper(audio_path: Path) -> str:
    import subprocess
    import tempfile

    from faster_whisper import WhisperModel

    # 先用 ffmpeg 转 16k wav，避免 PyAV 解码 mp3 的版本兼容问题
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = Path(tmp.name)
    subprocess.run(
        [FFMPEG, "-y", "-i", str(audio_path), "-ar", "16000", "-ac", "1", str(wav_path)],
        check=True, capture_output=True,
    )
    try:
        model = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")
        # initial_prompt 防止 zh 漂移输出繁体（2026-11-05 真实故障）
        segments, _ = model.transcribe(
            str(wav_path),
            language="zh",
            vad_filter=True,
            initial_prompt="以下是普通话的句子。",
        )
        return "".join(seg.text for seg in segments).strip()
    finally:
        wav_path.unlink(missing_ok=True)


async def transcribe(audio_path: str | Path, api_key: str | None = None) -> str:
    audio_path = Path(audio_path)
    if config.ASR_PROVIDER == "whisper":
        import asyncio

        return await asyncio.to_thread(_transcribe_whisper, audio_path)
    api_key = api_key or config.SILICONFLOW_API_KEY
    if not api_key:
        raise RuntimeError("缺少 SILICONFLOW_API_KEY（或设置 ASR_PROVIDER=whisper 走本地转写）")
    return await _transcribe_siliconflow(audio_path, api_key)
