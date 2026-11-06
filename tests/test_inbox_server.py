"""测试：Web 选择台端点（/inbox 系列的方案B交互层）。"""

import json

import httpx
import respx
from fastapi.testclient import TestClient

from douyin_catcher import server as server_mod
from douyin_catcher.config import config
from douyin_catcher.server import app

client = TestClient(app)


def _seed_pool(tmp_path, monkeypatch, links: dict):
    pool_file = tmp_path / "inbox_pool.json"
    pool_file.write_text(
        json.dumps({"links": links, "last_seq": 10, "updated_at": ""}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "INBOX_POOL_FILE", str(pool_file), raising=False)
    return pool_file


URL1 = "https://v.douyin.com/wr9uFGXibYY/"
URL2 = "https://www.douyin.com/video/7698402336053972827"


class TestInboxApi:
    def test_lists_pool_items(self, tmp_path, monkeypatch):
        _seed_pool(tmp_path, monkeypatch, {URL1: {"status": "pending", "seq": 1}})
        r = client.get("/inbox/api")
        assert r.status_code == 200
        body = r.json()
        assert URL1 in body["links"]
        assert body["links"][URL1]["status"] == "pending"

    def test_api_returns_conversations(self, tmp_path, monkeypatch):
        _seed_pool(tmp_path, monkeypatch, {})
        pool_file = tmp_path / "inbox_pool.json"
        pool = json.loads(pool_file.read_text(encoding="utf-8"))
        pool["conversations"] = {"0:1:c1:c1": {"name": "彻彻", "last_seq": 3429}}
        pool_file.write_text(json.dumps(pool, ensure_ascii=False), encoding="utf-8")
        r = client.get("/inbox/api")
        assert r.status_code == 200
        convs = r.json()["conversations"]
        assert convs["0:1:c1:c1"]["name"] == "彻彻"

    def test_inbox_page_served(self, tmp_path, monkeypatch):
        _seed_pool(tmp_path, monkeypatch, {})
        r = client.get("/inbox")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        assert "选择台" in r.text


class TestInboxSelect:
    def test_select_enqueues_and_marks(self, tmp_path, monkeypatch):
        pool_file = _seed_pool(
            tmp_path, monkeypatch,
            {URL1: {"status": "pending", "seq": 1}, URL2: {"status": "pending", "seq": 2}},
        )
        q_file = tmp_path / "q.txt"
        monkeypatch.setattr(config, "QUEUE_FILE", str(q_file), raising=False)
        monkeypatch.setattr(server_mod, "_queue", None)
        r = client.post("/inbox/select", json={"urls": [URL1]})
        assert r.status_code == 200
        body = r.json()
        assert body["queued"] == 1
        # 队列里有该链接
        assert URL1 in q_file.read_text(encoding="utf-8")
        # 池中状态更新
        pool = json.loads(pool_file.read_text(encoding="utf-8"))
        assert pool["links"][URL1]["status"] == "queued"
        assert pool["links"][URL2]["status"] == "pending"

    def test_select_empty_returns_zero(self, tmp_path, monkeypatch):
        _seed_pool(tmp_path, monkeypatch, {URL1: {"status": "pending"}})
        r = client.post("/inbox/select", json={"urls": []})
        assert r.status_code == 200
        assert r.json()["queued"] == 0


class TestInboxSync:
    @respx.mock
    def test_sync_pulls_from_service(self, tmp_path, monkeypatch):
        _seed_pool(tmp_path, monkeypatch, {})
        pool_file = str(tmp_path / "inbox_pool.json")
        monkeypatch.setattr(config, "INBOX_POOL_FILE", pool_file, raising=False)
        monkeypatch.setattr(config, "INBOX_API_BASE_URL", "http://127.0.0.1:8000", raising=False)
        monkeypatch.setattr(config, "INBOX_CONV_ID", "c1", raising=False)
        monkeypatch.setattr(config, "INBOX_API_TOKEN", "tk", raising=False)
        respx.get("http://127.0.0.1:8000/api/conversations").mock(
            return_value=httpx.Response(
                200, json={"items": [{"conv_id": "c1", "name": "彻彻"}]}
            )
        )
        msg = {
            "msg_id": "m1", "seq": 11, "msg_type": 7,
            "content": json.dumps({"text": "分享 https://v.douyin.com/abcNew123/"}),
        }
        respx.get(url__startswith="http://127.0.0.1:8000/api/conversations/c1/messages").mock(
            return_value=httpx.Response(200, json={"messages": [msg], "total": 1})
        )
        r = client.post("/inbox/sync")
        assert r.status_code == 200
        body = r.json()
        assert body["added"] == 1
        pool = json.loads(open(pool_file, encoding="utf-8").read())
        assert "https://v.douyin.com/abcNew123/" in pool["links"]
        assert pool["links"]["https://v.douyin.com/abcNew123/"]["conv_id"] == "c1"

    @respx.mock
    def test_sync_with_selected_conv_ids(self, tmp_path, monkeypatch):
        """POST /inbox/sync 带 conv_ids 时只同步指定会话。"""
        _seed_pool(tmp_path, monkeypatch, {})
        pool_file = str(tmp_path / "inbox_pool.json")
        monkeypatch.setattr(config, "INBOX_POOL_FILE", pool_file, raising=False)
        monkeypatch.setattr(config, "INBOX_API_BASE_URL", "http://127.0.0.1:8000", raising=False)
        monkeypatch.setattr(config, "INBOX_API_TOKEN", "tk", raising=False)
        monkeypatch.setattr(config, "INBOX_CONV_ID", "", raising=False)
        respx.get("http://127.0.0.1:8000/api/conversations").mock(
            return_value=httpx.Response(
                200, json={"items": [{"conv_id": "c2", "name": "阿明"}]}
            )
        )
        route = respx.get(
            url__startswith="http://127.0.0.1:8000/api/conversations/c2/messages"
        ).mock(return_value=httpx.Response(200, json={"items": [], "has_newer": False}))
        r = client.post("/inbox/sync", json={"conv_ids": ["c2"]})
        assert r.status_code == 200
        assert route.called
        pool = json.loads(open(pool_file, encoding="utf-8").read())
        assert list(pool["conversations"]) == ["c2"]
