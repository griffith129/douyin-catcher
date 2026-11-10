"""note_index：扫描 notes/*.md 构建《笔记索引》的单元测试。"""

import textwrap
from pathlib import Path

from douyin_catcher.note_index import (
    build_index,
    load_index,
    parse_frontmatter,
    save_index,
)


def _write_note(path: Path, aweme_id: str, title: str, author: str, captured: str):
    md = textwrap.dedent(
        f"""
        ---
        aweme_id: '{aweme_id}'
        title: {title}
        author: {author}
        source_url: https://www.douyin.com/video/{aweme_id}
        captured_at: {captured}
        tags:
        - douyin
        ---

        # {title}

        ## 精华版

        这是精华版内容。
        """
    )
    path.write_text(md, encoding="utf-8")


class TestParseFrontmatter:
    def test_parses_basic_fields(self, tmp_path):
        f = tmp_path / "note.md"
        _write_note(f, "111", "标题一", "作者甲", "2026-11-06 17:20")
        meta = parse_frontmatter(f.read_text(encoding="utf-8"))
        assert meta["aweme_id"] == "111"
        assert meta["title"] == "标题一"
        assert meta["author"] == "作者甲"
        assert meta["source_url"] == "https://www.douyin.com/video/111"

    def test_missing_frontmatter_returns_empty(self):
        assert parse_frontmatter("没有 frontmatter 的内容") == {}


class TestBuildIndex:
    def test_scans_notes_dir(self, tmp_path):
        _write_note(tmp_path / "a.md", "111", "视频一", "作者甲", "2026-11-06 10:00")
        _write_note(tmp_path / "b.md", "222", "视频二", "作者乙", "2026-11-07 11:00")
        (tmp_path / "ignore.txt").write_text("not a note", encoding="utf-8")
        entries = build_index(tmp_path)
        assert len(entries) == 2
        by_id = {e["aweme_id"]: e for e in entries}
        assert by_id["111"]["title"] == "视频一"
        assert by_id["222"]["file"].endswith("b.md")

    def test_entry_has_preview_from_jinghua(self, tmp_path):
        _write_note(tmp_path / "a.md", "111", "视频一", "作者甲", "2026-11-06 10:00")
        entries = build_index(tmp_path)
        assert "精华版内容" in entries[0]["preview"]

    def test_entries_sorted_by_date_desc(self, tmp_path):
        _write_note(tmp_path / "a.md", "111", "旧视频", "甲", "2026-11-01 10:00")
        _write_note(tmp_path / "b.md", "222", "新视频", "乙", "2026-11-07 11:00")
        entries = build_index(tmp_path)
        assert entries[0]["title"] == "新视频"


class TestIndexPersistence:
    def test_save_and_load_roundtrip(self, tmp_path):
        entries = [{"aweme_id": "111", "title": "t", "category": "AI", "preview": "p",
                    "author": "a", "date": "2026-11-06", "source_url": "u", "file": "f"}]
        out = tmp_path / "note_index.json"
        save_index(entries, out)
        loaded = load_index(out)
        assert loaded == entries
