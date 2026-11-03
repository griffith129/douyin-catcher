"""Markdown 笔记生成与落盘。"""

import re
from datetime import datetime
from pathlib import Path

import yaml


def safe_filename(name: str, max_len: int = 60) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\s]+', "", name or "untitled")
    return cleaned[:max_len] or "untitled"


def build_markdown(meta: dict, summary: str, transcript: str) -> str:
    front = {
        "aweme_id": meta["aweme_id"],
        "title": meta.get("title", ""),
        "author": meta.get("author", ""),
        "source_url": f"https://www.douyin.com/video/{meta['aweme_id']}",
        "captured_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "tags": ["douyin", "知识收藏"],
    }
    body = (
        f"---\n{yaml.safe_dump(front, allow_unicode=True, sort_keys=False)}---\n\n"
        f"# {meta.get('title') or '抖音视频笔记'}\n\n"
        f"{summary.strip()}\n\n"
        f"## 原文文案\n\n{transcript.strip()}\n"
    )
    return body


def save_note(meta: dict, summary: str, transcript: str, notes_dir: str | Path) -> Path:
    notes = Path(notes_dir)
    notes.mkdir(parents=True, exist_ok=True)
    date_prefix = datetime.now().strftime("%Y-%m-%d")
    filename = f"{date_prefix}-{safe_filename(meta.get('title', ''))}-{meta['aweme_id']}.md"
    path = notes / filename
    path.write_text(build_markdown(meta, summary, transcript), encoding="utf-8")
    return path
