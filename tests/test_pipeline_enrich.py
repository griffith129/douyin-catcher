"""pipeline 的 autotax 接线：失败吞掉，不影响 MVP 主流程。"""

import textwrap

import pytest

from douyin_catcher import pipeline


class TestMaybeEnrich:
    @pytest.mark.asyncio
    async def test_passes_through_result(self, tmp_path, monkeypatch):
        captured = {}

        async def fake_enrich(meta, preview, api_key):
            captured["meta"] = meta
            return {"short_title": "t"}

        monkeypatch.setattr("douyin_catcher.autotax.enrich_and_publish", fake_enrich)
        r = await pipeline._maybe_enrich(
            {"aweme_id": "1", "title": "t", "author": "a", "source_url": "u"},
            "精华内容",
        )
        assert r == {"short_title": "t"}
        assert captured["meta"]["source_url"] == "u"

    @pytest.mark.asyncio
    async def test_failure_swallowed(self, monkeypatch):
        async def boom(meta, preview, api_key):
            raise RuntimeError("LLM 挂了")

        monkeypatch.setattr("douyin_catcher.autotax.enrich_and_publish", boom)
        r = await pipeline._maybe_enrich(
            {"aweme_id": "1", "title": "t", "author": "a", "source_url": "u"},
            "精华内容",
        )
        assert r is None  # 主流程不受影响

    @pytest.mark.asyncio
    async def test_merges_missing_fields_from_note_frontmatter(self, tmp_path, monkeypatch):
        """parser 提供的 meta 缺 source_url/captured_at 时，从笔记 frontmatter 补全。"""
        captured = {}

        async def fake_enrich(meta, preview, api_key):
            captured["meta"] = meta
            return {"short_title": "t"}

        monkeypatch.setattr("douyin_catcher.autotax.enrich_and_publish", fake_enrich)
        note = tmp_path / "n.md"
        note.write_text(textwrap.dedent("""\
            ---
            aweme_id: '7706039103401753066'
            title: 标题
            author: 作者
            source_url: https://www.douyin.com/video/7706039103401753066
            captured_at: 2026-11-10 09:30
            ---

            # 内容
            """), encoding="utf-8")
        await pipeline._maybe_enrich(
            {"aweme_id": "7706039103401753066", "title": "标题", "author": "作者",
             "source_url": "", "note_path": str(note)},
            "精华内容",
        )
        m = captured["meta"]
        assert m["source_url"] == "https://www.douyin.com/video/7706039103401753066"
        assert m["captured_at"] == "2026-11-10 09:30"

    @pytest.mark.asyncio
    async def test_existing_meta_fields_not_overwritten(self, tmp_path, monkeypatch):
        captured = {}

        async def fake_enrich(meta, preview, api_key):
            captured["meta"] = meta
            return {}

        monkeypatch.setattr("douyin_catcher.autotax.enrich_and_publish", fake_enrich)
        await pipeline._maybe_enrich(
            {"aweme_id": "1", "title": "t", "author": "a", "source_url": "https://keep",
             "note_path": str(tmp_path / "missing.md")},
            "精华内容",
        )
        assert captured["meta"]["source_url"] == "https://keep"  # 笔记文件不存在也不覆盖
