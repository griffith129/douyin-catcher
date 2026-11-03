"""全流程编排：链接 → 元数据 → 下载 → 音频 → ASR → LLM → 笔记 → git。"""

import asyncio
import shutil
import subprocess
import uuid
from pathlib import Path

from .asr import transcribe
from .audio import extract_audio
from .config import config
from .downloader import download_video
from .note import save_note
from .parser import parse_share_text
from .summarizer import summarize


def _git_commit(note_path: Path, repo_dir: Path) -> str | None:
    """在仓库目录提交新笔记；失败不阻塞主流程。"""
    try:
        subprocess.run(["git", "add", str(note_path)], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"notes: add {note_path.stem}"],
            cwd=repo_dir, check=True, capture_output=True,
        )
        return "committed"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


async def process_link(
    share_text: str,
    notes_dir: str | Path | None = None,
    work_dir: str | Path | None = None,
    skip_git: bool = False,
) -> Path:
    """端到端处理一条分享文本，返回生成的笔记路径。"""
    notes_dir = Path(notes_dir or config.NOTES_DIR)
    work_dir = Path(work_dir or config.DOWNLOAD_DIR)
    run_id = uuid.uuid4().hex[:8]
    run_work = work_dir / run_id
    run_work.mkdir(parents=True, exist_ok=True)

    meta = await parse_share_text(share_text)
    if not meta.get("video_url"):
        raise ValueError("未取得视频下载地址（可能为图文或受限内容）")

    video_path = run_work / "video.mp4"
    await download_video(meta["video_url"], video_path)
    audio_path = extract_audio(video_path)
    transcript = await transcribe(audio_path)
    if not transcript:
        raise ValueError("ASR 结果为空")

    summary = await summarize(title=meta["title"], author=meta["author"], transcript=transcript)
    note_path = save_note(meta, summary=summary, transcript=transcript, notes_dir=notes_dir)

    shutil.rmtree(run_work, ignore_errors=True)

    if not skip_git:
        _git_commit(note_path, Path.cwd())
    return note_path


def run_pipeline_blocking(share_text: str) -> Path:
    return asyncio.run(process_link(share_text))
