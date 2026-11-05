"""测试：视频下载、音频提取、ASR、LLM 整理。"""

import json

import httpx
import respx

from douyin_catcher.asr import transcribe
from douyin_catcher.downloader import download_video
from douyin_catcher.summarizer import SUMMARY_PROMPT, summarize

import pytest


class TestDownloadVideo:
    @respx.mock
    async def test_streams_to_file(self, tmp_path):
        payload = b"fake-video-bytes-0123456789"
        route = respx.get("https://cdn.example.com/video.mp4").mock(
            return_value=httpx.Response(200, content=payload)
        )
        dest = tmp_path / "v.mp4"
        await download_video("https://cdn.example.com/video.mp4", dest)
        assert dest.read_bytes() == payload
        # 抖音 CDN 要求 Referer，缺失会被 403
        req = route.calls.last.request
        assert req.headers.get("Referer") == "https://www.douyin.com/"

    @respx.mock
    async def test_raises_on_http_error(self, tmp_path):
        respx.get("https://cdn.example.com/404.mp4").mock(
            return_value=httpx.Response(404)
        )
        with pytest.raises(httpx.HTTPStatusError):
            await download_video("https://cdn.example.com/404.mp4", tmp_path / "x.mp4")

    @respx.mock
    async def test_retries_on_read_timeout(self, tmp_path):
        """CDN 流中途停滞触发 ReadTimeout 时自动重试（真实故障：2026-11-05 E2E）。"""
        payload = b"fake-video-bytes-0123456789"
        route = respx.get("https://cdn.example.com/video.mp4").mock(
            side_effect=[httpx.ReadTimeout("stalled"), httpx.Response(200, content=payload)]
        )
        dest = tmp_path / "v.mp4"
        await download_video("https://cdn.example.com/video.mp4", dest)
        assert dest.read_bytes() == payload
        assert route.call_count == 2

    @respx.mock
    async def test_resumes_with_range_header(self, tmp_path):
        """已有部分文件时，重试携带 Range 断点续传，206 内容追加写入。"""
        partial = b"fake-video-"
        rest = b"bytes-0123456789"
        dest = tmp_path / "v.mp4"
        dest.write_bytes(partial)
        route = respx.get("https://cdn.example.com/video.mp4").mock(
            side_effect=[httpx.ReadTimeout("stalled"), httpx.Response(206, content=rest)]
        )
        await download_video("https://cdn.example.com/video.mp4", dest)
        assert dest.read_bytes() == partial + rest
        assert route.calls.last.request.headers.get("Range") == f"bytes={len(partial)}-"

    @respx.mock
    async def test_range_ignored_restarts_fresh(self, tmp_path):
        """服务器不支持 Range（返回 200）时，从头重写而非追加。"""
        payload = b"full-video-content"
        dest = tmp_path / "v.mp4"
        dest.write_bytes(b"stale-partial")
        respx.get("https://cdn.example.com/video.mp4").mock(
            side_effect=[httpx.ReadTimeout("stalled"), httpx.Response(200, content=payload)]
        )
        await download_video("https://cdn.example.com/video.mp4", dest)
        assert dest.read_bytes() == payload

    @respx.mock
    async def test_raises_after_exhausting_retries(self, tmp_path):
        respx.get("https://cdn.example.com/video.mp4").mock(
            side_effect=httpx.ReadTimeout("always stalled")
        )
        with pytest.raises(httpx.ReadTimeout):
            await download_video("https://cdn.example.com/video.mp4", tmp_path / "v.mp4", retries=2)


class TestTranscribe:
    @respx.mock
    async def test_returns_text(self, tmp_path):
        audio = tmp_path / "a.mp3"
        audio.write_bytes(b"fake-audio")
        route = respx.post("https://api.siliconflow.cn/v1/audio/transcriptions").mock(
            return_value=httpx.Response(200, json={"text": "大家好，今天讲卡尔曼滤波。"})
        )
        text = await transcribe(audio, api_key="sk-test")
        assert text == "大家好，今天讲卡尔曼滤波。"
        assert route.called

    @respx.mock
    async def test_raises_on_error(self, tmp_path):
        audio = tmp_path / "a.mp3"
        audio.write_bytes(b"x")
        respx.post("https://api.siliconflow.cn/v1/audio/transcriptions").mock(
            return_value=httpx.Response(401, json={"message": "bad key"})
        )
        with pytest.raises(httpx.HTTPStatusError):
            await transcribe(audio, api_key="sk-bad")


class TestSummarize:
    @respx.mock
    async def test_returns_llm_content(self):
        respx.post("https://api.siliconflow.cn/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={"choices": [{"message": {"content": "## 一句话结论\n讲得不错"}}]},
            )
        )
        out = await summarize(
            title="T", author="A", transcript="文案", api_key="sk-test"
        )
        assert "一句话结论" in out

    @respx.mock
    async def test_responses_api_style(self, monkeypatch):
        """LLM_API_STYLE=responses 时走 /responses 端点（Codex 风格）。"""
        from douyin_catcher.config import config as cfg
        from douyin_catcher import summarizer

        monkeypatch.setattr(cfg, "LLM_BASE_URL", "http://127.0.0.1:7864/v1")
        monkeypatch.setattr(cfg, "LLM_API_STYLE", "responses", raising=False)
        monkeypatch.setattr(cfg, "LLM_MODEL", "cn:deepseek-v4-flash")
        route = respx.post("http://127.0.0.1:7864/v1/responses").mock(
            return_value=httpx.Response(
                200,
                json={
                    "status": "completed",
                    "output": [
                        {
                            "type": "message",
                            "content": [
                                {"type": "output_text", "text": "## 一句话结论\nresponses 风格"}
                            ],
                        }
                    ],
                },
            )
        )
        out = await summarize(
            title="T", author="A", transcript="文案", api_key="sk-test"
        )
        assert "一句话结论" in out
        assert route.called

    def test_prompt_mentions_required_sections(self):
        for section in ("一句话结论", "核心要点", "关键细节", "原文没有讲清的问题"):
            assert section in SUMMARY_PROMPT
