"""笔记索引：扫描 notes/*.md 的 frontmatter 构建本地检索索引。

这是 1E 方案的本地一翼：Notion database 负责人工浏览，本地索引负责
选择台侧的快速搜索/筛选。索引以 JSON 落盘，可整体重建。
"""

import json
import re
from pathlib import Path

import yaml


def parse_frontmatter(md: str) -> dict:
    """解析笔记 YAML frontmatter，无 frontmatter 返回空 dict。"""
    stripped = md.lstrip()
    if not stripped.startswith("---"):
        return {}
    parts = stripped.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        data = yaml.safe_load(parts[1]) or {}
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError:
        return {}


def _preview(md: str, limit: int = 300) -> str:
    """提取「精华版」小节首段作为预览。"""
    body = md.split("---", 2)[2] if md.startswith("---") else md
    m = re.search(r"##\s*精华版\s*\n+(.+)", body)
    text = m.group(1).strip() if m else body.strip()
    return text[:limit]


def build_index(notes_dir: str | Path) -> list[dict]:
    """扫描目录下全部 .md，返回按日期降序的索引条目列表。"""
    entries: list[dict] = []
    for f in sorted(Path(notes_dir).glob("*.md")):
        md = f.read_text(encoding="utf-8")
        meta = parse_frontmatter(md)
        entries.append(
            {
                "aweme_id": str(meta.get("aweme_id", "") or f.stem),
                "title": str(meta.get("title", "") or f.stem),
                "author": str(meta.get("author", "") or ""),
                "date": str(meta.get("captured_at", "") or "")[:10],
                "source_url": str(meta.get("source_url", "") or ""),
                "file": f.name,
                "preview": _preview(md),
            }
        )
    entries.sort(key=lambda e: e["date"], reverse=True)
    return entries


def save_index(entries: list[dict], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_index(path: str | Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))
