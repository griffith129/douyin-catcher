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


class TestUxPages:
    def test_ux_hub_lists_all_options(self, tmp_path, monkeypatch):
        _seed_demo_data(tmp_path, monkeypatch)
        r = client.get("/demo/ux")
        assert r.status_code == 200
        for marker in ("分类画廊", "分类清单", "细类看板", "阅读室", "本次更新", "卡片墙", "toggle"):
            assert marker in r.text

    def test_reading_room(self, tmp_path, monkeypatch):
        _seed_demo_data(tmp_path, monkeypatch)
        r = client.get("/demo/reading-room")
        assert r.status_code == 200
        assert "/demo/api" in r.text

    def test_batch_cards(self, tmp_path, monkeypatch):
        _seed_demo_data(tmp_path, monkeypatch)
        r = client.get("/demo/batch-cards")
        assert r.status_code == 200
        assert "/demo/api" in r.text

    def test_cat_accordion(self, tmp_path, monkeypatch):
        _seed_demo_data(tmp_path, monkeypatch)
        r = client.get("/demo/cat-accordion")
        assert r.status_code == 200
        assert "/kb/api?desktop=1" in r.text  # 手风琴与 /kb 共用模板，同样桌面端直开

    def test_titles_preview(self, tmp_path, monkeypatch):
        _seed_demo_data(tmp_path, monkeypatch)
        r = client.get("/demo/titles")
        assert r.status_code == 200
        assert "short_title" in r.text.replace(" ", "") or "短标题" in r.text


class TestKnowledgeBasePage:
    """正式功能：知识库手风琴 + 抽屉（数据由 pipeline 自动更新）。"""

    def test_kb_page(self, tmp_path, monkeypatch):
        _seed_demo_data(tmp_path, monkeypatch)
        r = client.get("/kb")
        assert r.status_code == 200
        assert "/kb/api?desktop=1" in r.text  # 数据源 = 索引/分类/批次（autotax 自动追加，桌面端直开）

    def test_kb_page_same_as_accordion(self, tmp_path, monkeypatch):
        _seed_demo_data(tmp_path, monkeypatch)
        assert client.get("/kb").text == client.get("/demo/cat-accordion").text

    def test_kb_api_matches_demo_api(self, tmp_path, monkeypatch):
        _seed_demo_data(tmp_path, monkeypatch)
        assert client.get("/kb/api").json() == client.get("/demo/api").json()


class TestNotionDesktopUrls:
    """功能：知识库「打开 Notion 总结文档」直接在 Notion 桌面端打开（notion:// 协议）。"""

    def test_helper_converts_notion_url(self):
        assert (
            demo_mod.to_notion_desktop_url("https://www.notion.so/Page-Title-abc123")
            == "notion://www.notion.so/Page-Title-abc123"
        )

    def test_helper_converts_app_notion_domain(self):
        """生产数据存在 app.notion.com/p/<标题>-<页面ID> 形态，提取 ID 转桌面端深链。"""
        assert (
            demo_mod.to_notion_desktop_url(
                "https://app.notion.com/p/100-4148b2bb783381908b16e43710427947"
            )
            == "notion://www.notion.so/4148b2bb783381908b16e43710427947"
        )
        # 无标题前缀的纯 ID 形态
        assert (
            demo_mod.to_notion_desktop_url(
                "https://app.notion.com/p/4148b2bb783381908b16e43710427947"
            )
            == "notion://www.notion.so/4148b2bb783381908b16e43710427947"
        )

    def test_helper_keeps_non_notion_urls(self):
        assert demo_mod.to_notion_desktop_url("https://example.com/x") == "https://example.com/x"
        assert demo_mod.to_notion_desktop_url("") == ""
        assert demo_mod.to_notion_desktop_url("u1") == "u1"

    def test_helper_keeps_douyin_source(self):
        assert demo_mod.to_notion_desktop_url("https://www.douyin.com/video/1") == (
            "https://www.douyin.com/video/1"
        )

    def test_kb_api_desktop_param_rewrites_notion_urls(self, tmp_path, monkeypatch):
        _seed_demo_data(tmp_path, monkeypatch)
        # 种子数据里的 notion_url 是 Notion 页面形态才好验证转换
        (tmp_path / "note_index.json").write_text(
            json.dumps(
                [
                    {
                        "aweme_id": "111", "title": "视频一", "author": "甲", "date": "2026-11-06",
                        "source_url": "https://www.douyin.com/video/1", "file": "a.md", "preview": "x",
                        "category": "AI Agent 与工作流", "subcategory": "工具调用",
                        "notion_url": "https://www.notion.so/Note-One-abc",
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        body = client.get("/kb/api", params={"desktop": "1"}).json()
        assert body["index"][0]["notion_url"] == "notion://www.notion.so/Note-One-abc"
        # 抖音来源不受影响
        assert body["index"][0]["source_url"] == "https://www.douyin.com/video/1"

    def test_kb_api_default_unchanged(self, tmp_path, monkeypatch):
        _seed_demo_data(tmp_path, monkeypatch)
        assert client.get("/kb/api").json() == client.get("/demo/api").json()

    def test_kb_page_uses_desktop_api(self, tmp_path, monkeypatch):
        _seed_demo_data(tmp_path, monkeypatch)
        r = client.get("/kb")
        assert r.status_code == 200
        assert "/kb/api?desktop=1" in r.text


class TestAntdUi:
    """2C 改造：kb/inbox 页面基于 antd UMD 真组件（本地 static，离线可用）。"""

    def test_static_antd_files_served(self):
        for path in (
            "/static/antd/antd.min.js",
            "/static/antd/react.production.min.js",
            "/static/antd/react-dom.production.min.js",
            "/static/antd/dayjs.min.js",
            "/static/antd/reset.min.css",
        ):
            assert client.get(path).status_code == 200, path

    def test_kb_page_uses_antd(self, tmp_path, monkeypatch):
        _seed_demo_data(tmp_path, monkeypatch)
        html = client.get("/kb").text
        assert "/static/antd/antd.min.js" in html
        assert "/static/antd/react.production.min.js" in html
        assert "/static/antd/react-dom.production.min.js" in html
        assert "/static/antd/dayjs.min.js" in html
        assert "/static/antd/reset.min.css" in html
        assert 'id="root"' in html
        # 导航 / 数据展示 / 布局 / 按钮 / 反馈：各至少一个 antd 组件
        assert "Breadcrumb" in html   # 导航
        assert "Table" in html        # 数据展示
        assert "Tag" in html          # 数据展示
        assert "Descriptions" in html # 数据展示（抽屉详情）
        assert "Empty" in html        # 数据展示（空态）
        assert "Button" in html       # 按钮
        assert "Drawer" in html       # 反馈（详情抽屉）
