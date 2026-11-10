"""short_title：LLM 短标题生成与解析的单元测试（v2：特征保留 + 同名去重）。"""

import pytest

from douyin_catcher.short_title import (
    MAX_LEN,
    build_short_title_prompt,
    generate_short_title,
    make_unique,
    parse_short_title,
)


class TestBuildPrompt:
    def test_contains_limit_and_title(self):
        p = build_short_title_prompt("原标题很长 #话题 @用户", "摘要")
        assert str(MAX_LEN) in p and "原标题很长" in p

    def test_mentions_noise_removal(self):
        assert "话题标签" in build_short_title_prompt("t", "s")

    def test_requires_distinctive_fields(self):
        """v2 核心：prompt 必须要求保留特征字段、防止同质化。"""
        p = build_short_title_prompt("t", "s")
        assert "专有名词" in p and "数字" in p
        assert "区分" in p


class TestMakeUnique:
    def test_first_occurrence_unchanged(self):
        assert make_unique(["A", "B"]) == ["A", "B"]

    def test_duplicate_gets_suffix(self):
        assert make_unique(["A", "A"]) == ["A", "A（2）"]

    def test_triple_duplicate(self):
        assert make_unique(["A", "A", "A"]) == ["A", "A（2）", "A（3）"]

    def test_non_adjacent_duplicates(self):
        assert make_unique(["A", "B", "A"]) == ["A", "B", "A（2）"]


class TestParse:
    def test_plain_json(self):
        assert parse_short_title('{"short_title": "KV Cache 原理"}') == "KV Cache 原理"

    def test_json_with_prose(self):
        assert parse_short_title('结果：{"short_title": "TDD 实践"} 完') == "TDD 实践"

    def test_strip_quotes(self):
        assert parse_short_title('{"short_title": "《测试》"}') == "《测试》"

    def test_hard_cut_over_limit(self):
        out = parse_short_title('{"short_title": "' + "长" * 30 + '"}')
        assert len(out) == MAX_LEN

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            parse_short_title('{"short_title": ""}')

    def test_malformed_raises(self):
        with pytest.raises(ValueError):
            parse_short_title("无 JSON")


@pytest.mark.asyncio
async def test_generate_end_to_end(monkeypatch):
    async def fake_llm(prompt, api_key):
        return '{"short_title": "Agent 工作边界四层模型"}'

    monkeypatch.setattr("douyin_catcher.short_title._llm_text", fake_llm)
    out = await generate_short_title("长原标题 #AI #Agent @某人", "摘要", "k")
    assert out == "Agent 工作边界四层模型"
