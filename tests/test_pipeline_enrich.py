"""pipeline 的 autotax 接线：失败吞掉，不影响 MVP 主流程。"""

import pytest

from douyin_catcher import pipeline


class TestMaybeEnrich:
    @pytest.mark.asyncio
    async def test_passes_through_result(self, monkeypatch):
        async def fake_enrich(meta, preview, api_key):
            return {"short_title": "t"}

        monkeypatch.setattr("douyin_catcher.autotax.enrich_and_publish", fake_enrich)
        r = await pipeline._maybe_enrich(
            {"aweme_id": "1", "title": "t", "author": "a", "source_url": "u"},
            "精华内容",
        )
        assert r == {"short_title": "t"}

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
