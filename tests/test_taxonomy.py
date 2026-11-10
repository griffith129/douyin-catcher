"""taxonomy：3B 分类体系（清单持久化 + LLM 受限选择 + 提案去重）的单元测试。"""

import json

import pytest

from douyin_catcher.taxonomy import (
    Taxonomy,
    build_classify_prompt,
    classify_note,
    find_similar,
    load_taxonomy,
    save_taxonomy,
)

DEFAULT_CATEGORIES = {"AI Agent 与工作流": ["工作边界", "多智能体协作"], "编程与软件工程": ["TDD"]}


class TestTaxonomyPersistence:
    def test_load_missing_file_returns_empty(self, tmp_path):
        t = load_taxonomy(tmp_path / "no.json")
        assert t.categories == {}

    def test_save_and_load_roundtrip(self, tmp_path):
        p = tmp_path / "categories.json"
        save_taxonomy(Taxonomy(categories=DEFAULT_CATEGORIES), p)
        t = load_taxonomy(p)
        assert t.categories == DEFAULT_CATEGORIES


class TestFindSimilar:
    def test_exact_match_after_normalize(self):
        cats = ["AI Agent 与工作流", "编程"]
        assert find_similar("ai agent 与工作流", cats) == "AI Agent 与工作流"

    def test_substring_match(self):
        cats = ["AI Agent 与工作流"]
        assert find_similar("AI Agent", cats) == "AI Agent 与工作流"

    def test_no_match_returns_none(self):
        assert find_similar("量子物理", ["编程"]) is None


class TestBuildPrompt:
    def test_prompt_lists_categories(self):
        prompt = build_classify_prompt("标题", "摘要", DEFAULT_CATEGORIES)
        assert "AI Agent 与工作流" in prompt
        assert "标题" in prompt

    def test_prompt_allows_new_category_proposal(self):
        prompt = build_classify_prompt("标题", "摘要", DEFAULT_CATEGORIES)
        assert "新大类" in prompt


class TestClassifyNote:
    @pytest.mark.asyncio
    async def test_constrained_selection(self, monkeypatch):
        async def fake_llm(prompt, api_key):
            return '{"category": "AI Agent 与工作流", "subcategory": "工作边界", "new_category": null}'

        monkeypatch.setattr("douyin_catcher.taxonomy._llm_text", fake_llm)
        result = await classify_note("标题", "摘要", DEFAULT_CATEGORIES, api_key="k")
        assert result["category"] == "AI Agent 与工作流"
        assert result["subcategory"] == "工作边界"

    @pytest.mark.asyncio
    async def test_new_category_proposal_reused_if_similar(self, monkeypatch):
        """LLM 提案与现有大类相似时应被归并到现有类。"""
        async def fake_llm(prompt, api_key):
            return '{"category": "新大类", "subcategory": "x", "new_category": "AI Agent 工作流"}'

        monkeypatch.setattr("douyin_catcher.taxonomy._llm_text", fake_llm)
        result = await classify_note("标题", "摘要", DEFAULT_CATEGORIES, api_key="k")
        assert result["category"] == "AI Agent 与工作流"

    @pytest.mark.asyncio
    async def test_genuinely_new_category_returned_as_proposal(self, monkeypatch):
        async def fake_llm(prompt, api_key):
            return '{"category": "量子计算", "subcategory": "纠错", "new_category": "量子计算"}'

        monkeypatch.setattr("douyin_catcher.taxonomy._llm_text", fake_llm)
        result = await classify_note("标题", "摘要", DEFAULT_CATEGORIES, api_key="k")
        assert result["category"] == "量子计算"
        assert result["is_new_category"] is True

    @pytest.mark.asyncio
    async def test_malformed_llm_output_raises(self, monkeypatch):
        async def fake_llm(prompt, api_key):
            return "不是 JSON"

        monkeypatch.setattr("douyin_catcher.taxonomy._llm_text", fake_llm)
        with pytest.raises(ValueError):
            await classify_note("标题", "摘要", DEFAULT_CATEGORIES, api_key="k")
