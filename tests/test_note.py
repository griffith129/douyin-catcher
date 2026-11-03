"""测试：笔记生成 —— frontmatter、文件名清洗、落盘。"""

import pathlib

from douyin_catcher.note import build_markdown, safe_filename, save_note

META = {
    "aweme_id": "7412345678901234567",
    "title": "一分钟讲清/卡尔曼滤波",
    "author": "知识博主",
    "video_url": "https://example.com/video",
}


def test_safe_filename():
    assert safe_filename('a/b\\c:d*e?"<>|') == "abcde"
    assert len(safe_filename("很长" * 100)) <= 60


def test_build_markdown_contains_frontmatter_and_sections():
    md = build_markdown(META, summary="## 核心要点\n- 要点1", transcript="大家好")
    assert md.startswith("---\n")
    assert "aweme_id: '7412345678901234567'" in md
    assert "author: 知识博主" in md
    assert "## 核心要点" in md
    assert "## 原文文案" in md
    assert "大家好" in md


def test_save_note_writes_file(tmp_path: pathlib.Path):
    path = save_note(META, summary="# 总结", transcript="文案", notes_dir=tmp_path)
    assert path.exists()
    assert path.suffix == ".md"
    assert "7412345678901234567" in path.name
    content = path.read_text(encoding="utf-8")
    assert "# 总结" in content


def test_save_note_same_id_overwrites(tmp_path):
    save_note(META, summary="v1", transcript="t", notes_dir=tmp_path)
    path = save_note(META, summary="v2", transcript="t", notes_dir=tmp_path)
    assert "v2" in path.read_text(encoding="utf-8")
    assert len(list(tmp_path.glob("*.md"))) == 1
