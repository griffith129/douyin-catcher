"""测试：视频下载、音频提取、ASR、LLM 整理。"""

import json

import httpx
import respx

from douyin_catcher.asr import _transcribe_whisper, transcribe
from douyin_catcher.downloader import download_video
from douyin_catcher.summarizer import SUMMARY_PROMPT, correct_transcript, summarize

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


class TestWhisperTranscribe:
    async def test_whisper_passes_simplified_initial_prompt(self, tmp_path, monkeypatch):
        """faster-whisper 必须携带简体中文 initial_prompt。

        2026-11-05 真实故障：base 模型 language=zh 漂移输出繁体
        （大模型→大摩行、形式化→行事化、Rust→Ruex）。
        """
        import subprocess
        import sys
        import types

        captured = {}

        class FakeSeg:
            text = "你好世界"

        class FakeModel:
            def __init__(self, model, device=None, compute_type=None):
                captured["model"] = model

            def transcribe(self, path, language=None, vad_filter=None, initial_prompt=None):
                captured["lang"] = language
                captured["prompt"] = initial_prompt
                return iter([FakeSeg()]), None

        fake_mod = types.ModuleType("faster_whisper")
        fake_mod.WhisperModel = FakeModel
        monkeypatch.setitem(sys.modules, "faster_whisper", fake_mod)
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: None)

        out = _transcribe_whisper(tmp_path / "a.mp3")

        assert out == "你好世界"
        assert captured["lang"] == "zh"
        assert captured["prompt"] == "以下是普通话的句子。"


class TestCorrectTranscript:
    """ASR 文本 LLM 二次校对（纠正同音字/专有名词/繁简漂移）。"""

    @respx.mock
    async def test_fixes_asr_errors_via_llm(self, monkeypatch):
        from douyin_catcher.config import config as cfg

        monkeypatch.setattr(cfg, "LLM_BASE_URL", "http://127.0.0.1:7864/v1")
        monkeypatch.setattr(cfg, "LLM_API_STYLE", "responses", raising=False)
        monkeypatch.setattr(cfg, "LLM_MODEL", "cn:deepseek-v4-flash")
        route = respx.post("http://127.0.0.1:7864/v1/responses").mock(
            return_value=httpx.Response(
                200,
                json={"output_text": "我从一开始就反对让大模型之间搞对抗性代码审查。"},
            )
        )
        out = await correct_transcript(
            "我從一開始就反對讓大摩行之間搞對抗性代碼審查",
            title="别让大模型围着代码吵架了：TDD 与形式化验证",
            author="老周 AgentBuilder",
            api_key="sk-test",
        )
        assert out == "我从一开始就反对让大模型之间搞对抗性代码审查。"
        assert route.called

    @respx.mock
    async def test_falls_back_to_original_on_llm_error(self, monkeypatch):
        from douyin_catcher.config import config as cfg

        monkeypatch.setattr(cfg, "LLM_BASE_URL", "http://127.0.0.1:7864/v1")
        monkeypatch.setattr(cfg, "LLM_API_STYLE", "responses", raising=False)
        raw = "原始转写文本保持原样"
        respx.post("http://127.0.0.1:7864/v1/responses").mock(
            return_value=httpx.Response(500)
        )
        out = await correct_transcript(raw, title="T", api_key="sk-test")
        assert out == raw  # 校对失败不阻塞主流程，回退原文


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


class TestNoteSpec:
    """2B 路线：文档规范文件（docs/note_spec.md）拼入 LLM 提示词。"""

    async def _capture_request(self, monkeypatch, tmp_path):
        from douyin_catcher.config import config as cfg

        monkeypatch.setattr(cfg, "LLM_BASE_URL", "http://127.0.0.1:7864/v1")
        monkeypatch.setattr(cfg, "LLM_API_STYLE", "responses", raising=False)
        monkeypatch.setattr(cfg, "LLM_MODEL", "cn:deepseek-v4-flash")
        route = respx.post("http://127.0.0.1:7864/v1/responses").mock(
            return_value=httpx.Response(200, json={"output_text": "ok"})
        )
        await summarize(title="T", author="A", transcript="文", api_key="sk-test")
        import json as _json

        return _json.loads(route.calls.last.request.content)

    @respx.mock
    async def test_spec_file_injected_into_prompt(self, monkeypatch, tmp_path):
        from douyin_catcher.config import config as cfg

        spec_file = tmp_path / "note_spec.md"
        spec_file.write_text("SPEC_MARKER_文档规范内容", encoding="utf-8")
        monkeypatch.setattr(cfg, "NOTE_SPEC_FILE", str(spec_file), raising=False)
        body = await self._capture_request(monkeypatch, tmp_path)
        assert "SPEC_MARKER_文档规范内容" in body["input"]
        assert "一句话结论" in body["input"]  # 原有结构指令仍在

    @respx.mock
    async def test_missing_spec_file_falls_back_gracefully(self, monkeypatch, tmp_path):
        from douyin_catcher.config import config as cfg

        monkeypatch.setattr(cfg, "NOTE_SPEC_FILE", str(tmp_path / "nope.md"), raising=False)
        body = await self._capture_request(monkeypatch, tmp_path)
        assert "一句话结论" in body["input"]  # 规范缺失不报错，仍可整理

    @respx.mock
    async def test_max_output_tokens_raised_for_spec(self, monkeypatch, tmp_path):
        """新规范输出更长（精华版+逻辑链+ELI5），token 上限需 4096。"""
        from douyin_catcher.config import config as cfg

        monkeypatch.setattr(cfg, "NOTE_SPEC_FILE", "", raising=False)
        body = await self._capture_request(monkeypatch, tmp_path)
        assert body["max_output_tokens"] == 4096
