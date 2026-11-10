"""enrich 模块：概述截断与标签提取的单元测试。"""

import pytest

from douyin_catcher.enrich import build_tag_prompt, extract_tags, parse_tags, summarize_preview


class TestSummarizePreview:
    def test_short_text_unchanged(self):
        assert summarize_preview("短的概述。") == "短的概述。"

    def test_long_text_truncated_at_sentence(self):
        text = "第一句。" * 60 + "结尾"
        out = summarize_preview(text, limit=200)
        assert len(out) <= 200
        assert out.endswith("。")

    def test_no_sentence_falls_back_to_hard_cut(self):
        text = "a" * 300
        assert summarize_preview(text, limit=200) == "a" * 200

    def test_whitespace_removed(self):
        assert summarize_preview("hello \n world", limit=100) == "helloworld"


class TestTagPrompt:
    def test_contains_title_and_rules(self):
        p = build_tag_prompt("标题", "摘要内容")
        assert "标题" in p and "JSON" in p

    def test_rejects_generic_tags(self):
        assert "过泛" in build_tag_prompt("t", "s")


class TestParseTags:
    def test_plain_json(self):
        assert parse_tags('["KV Cache", "上下文压缩"]') == ["KV Cache", "上下文压缩"]

    def test_json_in_prose(self):
        assert parse_tags('结果如下：["TDD"] 完毕') == ["TDD"]

    def test_dedup_and_strip_hash(self):
        assert parse_tags('["#TDD", "TDD", "测试"]') == ["TDD", "测试"]

    def test_max_five(self):
        raw = '["a","b","c","d","e","f"]'
        assert len(parse_tags(raw)) == 5

    def test_malformed_raises(self):
        with pytest.raises(ValueError):
            parse_tags("没有数组")


@pytest.mark.asyncio
async def test_extract_tags_via_llm(monkeypatch):
    async def fake_llm(prompt, api_key):
        return '["TDD", "形式化验证"]'

    monkeypatch.setattr("douyin_catcher.enrich._llm_text", fake_llm)
    assert await extract_tags("t", "s", "k") == ["TDD", "形式化验证"]
