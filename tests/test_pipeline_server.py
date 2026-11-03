"""测试：全流程编排与 HTTP 服务。"""

import json

import httpx
import respx
from fastapi.testclient import TestClient

from douyin_catcher import pipeline
from douyin_catcher.server import app

ROUTER_DATA = {
    "loaderData": {
        "video_(id)/page": {
            "videoInfoRes": {
                "item_list": [
                    {
                        "aweme_id": "1112223334445556667",
                        "desc": "管线测试视频",
                        "author": {"nickname": "作者A"},
                        "video": {"play_addr": {"uri": "v0d00x", "url_list": [
                            "https://www.douyin.com/aweme/v1/play/?video_id=v0d00x&playwm"]}},
                    }
                ]
            }
        }
    }
}


def _mock_upstream():
    respx.get("https://v.douyin.com/test1/").mock(
        return_value=httpx.Response(302, headers={"Location": "https://www.douyin.com/video/1112223334445556667"})
    )
    respx.get("https://www.iesdouyin.com/share/video/1112223334445556667").mock(
        return_value=httpx.Response(200, text="<script>window._ROUTER_DATA = " + json.dumps(ROUTER_DATA) + ";</script>")
    )
    respx.get(url__startswith="https://www.douyin.com/aweme/v1/play/").mock(
        return_value=httpx.Response(200, content=b"fakevideo")
    )
    respx.post("https://api.siliconflow.cn/v1/audio/transcriptions").mock(
        return_value=httpx.Response(200, json={"text": "这是文字稿。"})
    )
    respx.post("https://api.siliconflow.cn/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": "## 一句话结论\nOK"}}]})
    )


class TestPipeline:
    @respx.mock
    async def test_process_link_full_flow(self, tmp_path, monkeypatch):
        _mock_upstream()
        monkeypatch.setattr(pipeline.config, "SILICONFLOW_API_KEY", "sk-test")
        # 单元隔离：跳过真实 ffmpeg，生成占位音频文件
        def fake_extract(video, audio=None):
            from pathlib import Path
            audio = Path(video).with_suffix(".mp3")
            audio.write_bytes(b"fake-audio")
            return audio
        monkeypatch.setattr(pipeline, "extract_audio", fake_extract)
        note_path = await pipeline.process_link(
            "看看 https://v.douyin.com/test1/",
            notes_dir=tmp_path / "notes",
            work_dir=tmp_path / "work",
            skip_git=True,
        )
        assert note_path.exists()
        text = note_path.read_text(encoding="utf-8")
        assert "一句话结论" in text
        assert "这是文字稿。" in text
        assert "aweme_id: '1112223334445556667'" in text

    async def test_process_link_rejects_bad_text(self, tmp_path):
        import pytest
        with pytest.raises(ValueError):
            await pipeline.process_link("没有链接", notes_dir=tmp_path, work_dir=tmp_path)


class TestServer:
    @respx.mock
    def test_post_link_enqueues(self, tmp_path, monkeypatch):
        _mock_upstream()
        monkeypatch.setenv("QUEUE_FILE", str(tmp_path / "q.txt"))
        from douyin_catcher import server as server_mod
        monkeypatch.setattr(server_mod, "get_queue", lambda: __import__("douyin_catcher.queue", fromlist=["LinkQueue"]).LinkQueue(tmp_path / "q.txt"))
        client = TestClient(app)
        r = client.post("/link", json={"text": "8.97 打开抖音 https://v.douyin.com/test1/"})
        assert r.status_code == 200
        body = r.json()
        assert body["queued"] is True
        # 重复提交去重
        r2 = client.post("/link", json={"text": "again https://v.douyin.com/test1/"})
        assert r2.json()["queued"] is False

    def test_post_link_rejects_no_url(self, tmp_path, monkeypatch):
        monkeypatch.setattr("douyin_catcher.server.get_queue", lambda: __import__("douyin_catcher.queue", fromlist=["LinkQueue"]).LinkQueue(tmp_path / "q2.txt"))
        client = TestClient(app)
        r = client.post("/link", json={"text": "没有链接"})
        assert r.status_code == 400
