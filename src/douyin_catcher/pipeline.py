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
from .note import build_markdown, save_note
from .note_index import preview_from_md
from .notion import upload_note
from .parser import parse_share_text
from .summarizer import correct_transcript, summarize


async def _maybe_upload_to_notion(meta: dict, summary: str, transcript: str) -> str | None:
    """笔记收录进 Notion（1A）。未配置 token 时跳过，失败不阻塞主流程。"""
    if not (config.NOTION_TOKEN and config.NOTION_PARENT_PAGE_ID):
        return None
    try:
        md = build_markdown(meta, summary=summary, transcript=transcript)
        title = meta.get("title") or "抖音视频笔记"
        return await upload_note(title=title, md=md)
    except Exception as e:  # ponytail: Notion 故障不应丢掉本地笔记
        print(f"[notion] 上传失败，已保留本地笔记: {e}")
        return None


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


async def _maybe_enrich(meta: dict, preview: str) -> dict | None:
    """全自动收录（autotax）：短标题/分类/标签/概述 → 本地索引/批次 → Notion 插行。

    任何失败只记录日志，不影响 MVP 主流程（笔记已落盘）。
    """
    if not meta.get("aweme_id") or not preview:
        return None
    try:
        from .autotax import enrich_and_publish

        return await enrich_and_publish(meta, preview, api_key="")
    except Exception as e:  # ponytail: 收录失败不丢笔记，重跑脚本可补
        print(f"[autotax] 自动收录失败（笔记已保留）: {e}")
        return None


async def process_link(
    share_text: str,
    notes_dir: str | Path | None = None,
    work_dir: str | Path | None = None,
    skip_git: bool = False,
    meta_override: dict | None = None,
) -> Path:
    """端到端处理一条分享文本，返回生成的笔记路径。

    meta_override: 直接提供元数据（跳过抖音解析），用于测试或网络受限场景。
    """
    notes_dir = Path(notes_dir or config.NOTES_DIR)
    work_dir = Path(work_dir or config.DOWNLOAD_DIR)
    run_id = uuid.uuid4().hex[:8]
    run_work = work_dir / run_id
    run_work.mkdir(parents=True, exist_ok=True)

    meta = meta_override or await parse_share_text(share_text)
    if not meta.get("video_url"):
        raise ValueError("未取得视频下载地址（可能为图文或受限内容）")

    video_path = run_work / "video.mp4"
    await download_video(meta["video_url"], video_path)
    audio_path = extract_audio(video_path)
    transcript = await transcribe(audio_path)
    if not transcript:
        raise ValueError("ASR 结果为空")
    # LLM 二次校对：纠正同音字/专有名词/繁简漂移（失败自动回退原文）
    transcript = await correct_transcript(
        transcript, title=meta["title"], author=meta["author"]
    )

    summary = await summarize(title=meta["title"], author=meta["author"], transcript=transcript)
    note_path = save_note(meta, summary=summary, transcript=transcript, notes_dir=notes_dir)
    notion_url = await _maybe_upload_to_notion(meta, summary, transcript)
    if notion_url:
        print(f"[notion] 笔记已收录: {notion_url}")

    # 全自动收录：短标题/分类/标签/概述 → 本地索引/批次 → Notion 知识库插行（失败不影响主流程）
    meta["note_path"] = str(note_path)
    entry = await _maybe_enrich(meta, preview_from_md(note_path.read_text(encoding="utf-8")))
    if entry:
        print(f"[autotax] 已收录: {entry['category']} / {entry['subcategory']} ← {entry['short_title']}")

    shutil.rmtree(run_work, ignore_errors=True)

    if not skip_git:
        _git_commit(note_path, Path.cwd())
    return note_path


def run_pipeline_blocking(share_text: str) -> Path:
    return asyncio.run(process_link(share_text))
