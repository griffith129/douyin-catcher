"""autotax：pipeline 全自动集成（单次 LLM 分析 + 本地更新 + Notion 插行）。"""

import json

import pytest
import respx
from httpx import Response

from douyin_catcher import autotax
from douyin_catcher.autotax import analyze_note, enrich_and_publish
from douyin_catcher.config import config
from douyin_catcher.taxonomy import Taxonomy, load_taxonomy, save_taxonomy

CATS = {"AI Agent 与工作流": ["工作边界", "工具调用"], "编程与软件工程": ["TDD"]}

GOOD_LLM = json.dumps({
    "short_title": "Agent的四层工作边界",
    "category": "AI Agent 与工作流",
    "subcategory": "工作边界",
    "new_category": None,
    "tags": ["工作边界", "上下文"],
}, ensure_ascii=False)

META = {
    "aweme_id": "999", "title": "原标题 #AI #Agent @某人",
    "author": "作者甲", "source_url": "https://www.douyin.com/video/999",
    "captured_at": "2026-11-10 12:00", "note_path": "notes/x.md",
    "notion_page_url": "https://notion.so/note-page-999",  # MVP 上传的总结文档子页面
}


def _seed(tmp_path, monkeypatch, categories=CATS):
    monkeypatch.setattr(autotax, "_TAXONOMY_FILE", tmp_path / "categories.json")
    monkeypatch.setattr(autotax, "_INDEX_FILE", tmp_path / "note_index.json")
    monkeypatch.setattr(autotax, "_BATCHES_FILE", tmp_path / "batches.json")
    save_taxonomy(Taxonomy(dict(categories)), tmp_path / "categories.json")
    monkeypatch.setattr(config, "NOTION_TOKEN", "ntn_test", raising=False)


def _mock_llm(monkeypatch, payload=GOOD_LLM):
    async def fake_llm(prompt, api_key):
        return payload

    monkeypatch.setattr("douyin_catcher.autotax._llm_text", fake_llm)


class TestAnalyzeNote:
    @pytest.mark.asyncio
    async def test_parses_combined_output(self, monkeypatch):
        _mock_llm(monkeypatch)
        r = await analyze_note("标题", "摘要", CATS, "k")
        assert r["short_title"] == "Agent的四层工作边界"
        assert r["category"] == "AI Agent 与工作流"
        assert r["tags"] == ["工作边界", "上下文"]
        assert r["is_new_category"] is False

    @pytest.mark.asyncio
    async def test_similar_new_category_merged(self, monkeypatch):
        _mock_llm(monkeypatch, GOOD_LLM.replace('"category": "AI Agent 与工作流"', '"category": "AI Agent工作流"'))
        r = await analyze_note("标题", "摘要", CATS, "k")
        assert r["category"] == "AI Agent 与工作流"

    @pytest.mark.asyncio
    async def test_prompt_contains_categories_and_distinctive_rule(self, monkeypatch):
        captured = {}

        async def fake_llm(prompt, api_key):
            captured["p"] = prompt
            return GOOD_LLM

        monkeypatch.setattr("douyin_catcher.autotax._llm_text", fake_llm)
        await analyze_note("标题", "摘要", CATS, "k")
        assert "AI Agent 与工作流" in captured["p"]
        assert "专有名词" in captured["p"]

    @pytest.mark.asyncio
    async def test_malformed_raises(self, monkeypatch):
        _mock_llm(monkeypatch, "不是 JSON")
        with pytest.raises(ValueError):
            await analyze_note("标题", "摘要", CATS, "k")


class TestEnrichAndPublish:
    @pytest.mark.asyncio
    async def test_happy_path_local_and_notion(self, tmp_path, monkeypatch):
        _seed(tmp_path, monkeypatch)
        monkeypatch.setattr(config, "NOTION_DB_ID", "db123", raising=False)
        _mock_llm(monkeypatch)
        with respx.mock:
            route = respx.post("https://api.notion.com/v1/pages").mock(
                return_value=Response(200, json={"url": "https://notion.so/row1"})
            )
            entry = await enrich_and_publish(META, "这是精华版内容，讲工作边界。", "k")
        # 本地
        assert entry["category"] == "AI Agent 与工作流"
        assert entry["short_title"] == "Agent的四层工作边界"
        assert entry["batch_id"]
        assert entry["notion_url"] == META["notion_page_url"]  # 总结文档 = MVP 子页面
        assert entry["row_url"] == "https://notion.so/row1"  # 知识库行
        index = json.loads((tmp_path / "note_index.json").read_text(encoding="utf-8"))
        assert len(index) == 1 and index[0]["notion_url"] == META["notion_page_url"]
        assert index[0]["row_url"] == "https://notion.so/row1"
        batches = json.loads((tmp_path / "batches.json").read_text(encoding="utf-8"))
        assert batches[0]["daily"] is True and len(batches[0]["items"]) == 1
        assert batches[0]["items"][0]["notion_url"] == META["notion_page_url"]
        # Notion 请求体
        body = json.loads(route.calls.last.request.content)
        props = body["properties"]
        assert props["Name"]["title"][0]["text"]["content"] == "Agent的四层工作边界"
        assert props["分类"]["select"]["name"] == "AI Agent 与工作流"
        assert props["视频ID"]["rich_text"][0]["text"]["content"] == "999"
        assert props["原标题"]["rich_text"][0]["text"]["content"].startswith("原标题")
        assert props["标签"]["multi_select"][0]["name"] == "工作边界"
        assert props["批次"]["select"]["name"] == entry["batch_id"]
        # 行详情首个 callout = 概述；第二个 callout = 跳转总结文档链接
        assert body["children"][0]["callout"]["rich_text"][0]["text"]["content"].startswith("📌")
        link = body["children"][1]["callout"]["rich_text"][0]["text"]
        assert link["content"] == "▶ 打开完整笔记（总结文档）"
        assert link["link"]["url"] == META["notion_page_url"]

    @pytest.mark.asyncio
    async def test_short_title_dedup_against_index(self, tmp_path, monkeypatch):
        _seed(tmp_path, monkeypatch)
        monkeypatch.setattr(config, "NOTION_DB_ID", "", raising=False)
        _mock_llm(monkeypatch)
        (tmp_path / "note_index.json").write_text(json.dumps(
            [{"aweme_id": "1", "short_title": "Agent的四层工作边界"}], ensure_ascii=False), encoding="utf-8")
        entry = await enrich_and_publish(META, "摘要内容。", "k")
        assert entry["short_title"] == "Agent的四层工作边界（2）"

    @pytest.mark.asyncio
    async def test_new_category_persisted(self, tmp_path, monkeypatch):
        _seed(tmp_path, monkeypatch)
        monkeypatch.setattr(config, "NOTION_DB_ID", "", raising=False)
        _mock_llm(monkeypatch, GOOD_LLM
                  .replace('"category": "AI Agent 与工作流"', '"category": "物理AI"')
                  .replace('"subcategory": "工作边界"', '"subcategory": "仿真训练"')
                  .replace('"new_category": null', '"new_category": "物理AI"'))
        entry = await enrich_and_publish(META, "摘要。", "k")
        assert entry["category"] == "物理AI" and entry["is_new_category"] is True
        t = load_taxonomy(tmp_path / "categories.json")
        assert "物理AI" in t.categories

    @pytest.mark.asyncio
    async def test_no_db_id_skips_notion(self, tmp_path, monkeypatch):
        _seed(tmp_path, monkeypatch)
        monkeypatch.setattr(config, "NOTION_DB_ID", "", raising=False)
        _mock_llm(monkeypatch)
        with respx.mock:
            entry = await enrich_and_publish(META, "摘要。", "k")
            assert entry["notion_url"] == META["notion_page_url"]  # 总结文档来自 meta
            assert entry["row_url"] == ""  # 未插行
            assert not respx.calls  # 未发出任何 HTTP 请求

    @pytest.mark.asyncio
    async def test_date_falls_back_to_today(self, tmp_path, monkeypatch):
        _seed(tmp_path, monkeypatch)
        monkeypatch.setattr(config, "NOTION_DB_ID", "", raising=False)
        _mock_llm(monkeypatch)
        meta = {k: v for k, v in META.items() if k != "captured_at"}
        entry = await enrich_and_publish(meta, "摘要。", "k")
        assert entry["date"]  # 不应为 None

    @pytest.mark.asyncio
    async def test_notion_failure_keeps_local(self, tmp_path, monkeypatch):
        _seed(tmp_path, monkeypatch)
        monkeypatch.setattr(config, "NOTION_DB_ID", "db123", raising=False)
        _mock_llm(monkeypatch)
        with respx.mock:
            respx.post("https://api.notion.com/v1/pages").mock(return_value=Response(500))
            with pytest.raises(Exception):
                await enrich_and_publish(META, "摘要。", "k")
        index = json.loads((tmp_path / "note_index.json").read_text(encoding="utf-8"))
        assert len(index) == 1  # 本地先行，未丢失
