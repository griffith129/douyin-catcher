"""用 ffmpeg（imageio-ffmpeg 自带二进制）从视频提取音频。"""

import subprocess
from pathlib import Path

import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def extract_audio(video_path: str | Path, audio_path: str | Path | None = None) -> Path:
    video_path = Path(video_path)
    audio_path = Path(audio_path) if audio_path else video_path.with_suffix(".mp3")
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        FFMPEG,
        "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "libmp3lame",
        "-b:a", "64k",
        "-ar", "16000",
        "-ac", "1",
        str(audio_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg 提取音频失败: {proc.stderr[-500:]}")
    return audio_path
