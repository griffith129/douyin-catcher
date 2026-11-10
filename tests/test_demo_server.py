"""测试：/demo 体验路由（方案1/方案2 两个 demo 的入口与数据 API）。"""

import json

from fastapi.testclient import TestClient

from douyin_catcher import demo as demo_mod
from douyin_catcher.server import app

client = TestClient(app)


def _seed_demo_data(tmp_path, monkeypatch):
    index = [
        {
            "aweme_id": "111", "title": "视频一", "author": "甲", "date": "2026-11-06",
            "source_url": "u1", "file": "a.md", "preview": "精华内容一",
            "category": "AI Agent 与工作流", "subcategory": "工具调用", "notion_url": "n1",
        },
        {
            "aweme_id": "222", "title": "视频二", "author": "乙", "date": "2026-11-07",
            "source_url": "u2", "file": "b.md", "preview": "精华内容二",
            "category": "编程与软件工程", "subcategory": "TDD", "notion_url": "",
        },
    ]
    categories = {"categories": {"AI Agent 与工作流": ["工具调用"], "编程与软件工程": ["TDD"]}}
    batches = [
        {"batch_id": "batch-001", "created_at": "2026-11-10 12:00:00",
         "items": [{"aweme_id": "111", "title": "视频一", "category": "AI Agent 与工作流", "notion_url": "n1"}]}
    ]
    meta = {"database_url": "https://notion.so/db", "log_url": "https://notion.so/log", "batch": "demo-2026-11-10"}
    monkeypatch.setattr(demo_mod, "_INDEX_FILE", tmp_path / "note_index.json", raising=False)
    monkeypatch.setattr(demo_mod, "_TAXONOMY_FILE", tmp_path / "categories.json", raising=False)
    monkeypatch.setattr(demo_mod, "_BATCHES_FILE", tmp_path / "batches.json", raising=False)
    monkeypatch.setattr(demo_mod, "_META_FILE", tmp_path / "demo_meta.json", raising=False)
    (tmp_path / "note_index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "categories.json").write_text(json.dumps(categories, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "batches.json").write_text(json.dumps(batches, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "demo_meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")


class TestDemoApi:
    def test_returns_full_payload(self, tmp_path, monkeypatch):
        _seed_demo_data(tmp_path, monkeypatch)
        r = client.get("/demo/api")
        assert r.status_code == 200
        body = r.json()
        assert len(body["index"]) == 2
        assert body["index"][0]["category"] == "AI Agent 与工作流"
        assert "AI Agent 与工作流" in body["categories"]
        assert body["batches"][0]["batch_id"] == "batch-001"
        assert body["meta"]["database_url"]

    def test_empty_data_ok(self, tmp_path, monkeypatch):
        monkeypatch.setattr(demo_mod, "_INDEX_FILE", tmp_path / "no.json", raising=False)
        monkeypatch.setattr(demo_mod, "_TAXONOMY_FILE", tmp_path / "no.json", raising=False)
        monkeypatch.setattr(demo_mod, "_BATCHES_FILE", tmp_path / "no.json", raising=False)
        monkeypatch.setattr(demo_mod, "_META_FILE", tmp_path / "no.json", raising=False)
        r = client.get("/demo/api")
        assert r.status_code == 200
        assert r.json() == {"index": [], "categories": {}, "batches": [], "meta": {}}


class TestDemoPages:
    def test_hub_lists_both_plans(self, tmp_path, monkeypatch):
        _seed_demo_data(tmp_path, monkeypatch)
        r = client.get("/demo")
        assert r.status_code == 200
        assert "/demo/v1" in r.text and "/demo/v2" in r.text

    def test_v1_page_is_local_experience(self, tmp_path, monkeypatch):
        _seed_demo_data(tmp_path, monkeypatch)
        r = client.get("/demo/v1")
        assert r.status_code == 200
        assert "搜索" in r.text and "批次" in r.text

    def test_v2_page_links_notion(self, tmp_path, monkeypatch):
        _seed_demo_data(tmp_path, monkeypatch)
        r = client.get("/demo/v2")
        assert r.status_code == 200
        assert "notion.so/db" in r.text
