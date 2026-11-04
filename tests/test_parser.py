"""测试：分享文本解析 —— 从抖音分享口令中提取链接、解析视频元数据。"""

import json
import pathlib

import httpx
import pytest
import respx

from douyin_catcher import parser
from douyin_catcher.parser import (
    extract_urls,
    extract_video_id,
    fetch_video_info,
    parse_share_text,
    _info_from_detail,
)


class TestExtractUrls:
    def test_extracts_url_from_share_text(self):
        text = "8.97 复制打开抖音，看看【XX的作品】知识分享 https://v.douyin.com/iAbCdEf/ "
        assert extract_urls(text) == ["https://v.douyin.com/iAbCdEf/"]

    def test_ignores_punctuation_suffix(self):
        text = "看看这个 https://v.douyin.com/abc123/，很好"
        assert extract_urls(text) == ["https://v.douyin.com/abc123/"]

    def test_returns_empty_when_no_url(self):
        assert extract_urls("没有任何链接") == []

    def test_keeps_full_order(self):
        text = "a https://v.douyin.com/one/ b https://www.douyin.com/video/123"
        assert extract_urls(text) == [
            "https://v.douyin.com/one/",
            "https://www.douyin.com/video/123",
        ]


class TestExtractVideoId:
    def test_from_video_path(self):
        url = "https://www.douyin.com/video/7412345678901234567"
        assert extract_video_id(url) == "7412345678901234567"

    def test_from_modal_id_query(self):
        url = "https://www.douyin.com/discover?modal_id=7412345678901234567"
        assert extract_video_id(url) == "7412345678901234567"

    def test_none_when_unrecognized(self):
        assert extract_video_id("https://www.douyin.com/user/abc") is None


DETAIL_DATA = {
    "status_code": 0,
    "aweme_detail": {
        "aweme_id": "7412345678901234567",
        "desc": "测试视频标题",
        "author": {"nickname": "测试作者"},
        "video": {
            "play_addr": {
                "uri": "v0d00fg10000abcdef",
                "url_list": [
                    "https://www.douyin.com/aweme/v1/play/?video_id=v0d00fg10000abcdef&ratio=1080p&line=0"
                ],
            }
        },
    },
}


class TestInfoFromDetail:
    def test_extracts_fields(self):
        info = _info_from_detail(DETAIL_DATA)
        assert info["aweme_id"] == "7412345678901234567"
        assert info["title"] == "测试视频标题"
        assert info["author"] == "测试作者"
        assert info["video_url"].startswith("https://")

    def test_replaces_playwm(self):
        data = {
            "aweme_detail": {
                "aweme_id": "1",
                "desc": "x",
                "author": {"nickname": "a"},
                "video": {
                    "play_addr": {"url_list": ["https://cdn.example.com/playwm/?x=1"]}
                },
            }
        }
        assert "playwm" not in _info_from_detail(data)["video_url"]

    def test_raises_when_detail_missing(self):
        with pytest.raises(ValueError):
            _info_from_detail({"status_code": 0})

    def test_raises_when_no_video_url(self):
        data = {
            "aweme_detail": {
                "aweme_id": "1",
                "desc": "x",
                "author": {"nickname": "a"},
                "video": {"play_addr": {"url_list": []}},
            }
        }
        info = _info_from_detail(data)
        assert info["video_url"] == ""


class TestFetchVideoInfo:
    async def test_delegates_to_browser(self, monkeypatch):
        async def fake_browser(aweme_id, timeout_s=30.0):
            return DETAIL_DATA

        monkeypatch.setattr(parser, "fetch_detail_via_browser", fake_browser)
        info = await fetch_video_info("7412345678901234567")
        assert info["title"] == "测试视频标题"

    async def test_raises_on_empty_detail(self, monkeypatch):
        async def fake_browser(aweme_id, timeout_s=30.0):
            return {"status_code": 0}

        monkeypatch.setattr(parser, "fetch_detail_via_browser", fake_browser)
        with pytest.raises(ValueError):
            await fetch_video_info("1")


class TestParseShareText:
    @respx.mock
    async def test_end_to_end_share_text(self, monkeypatch):
        respx.get("https://v.douyin.com/iAbCdEf/").mock(
            return_value=httpx.Response(
                302, headers={"Location": "https://www.douyin.com/video/7412345678901234567"}
            )
        )

        async def fake_browser(aweme_id, timeout_s=30.0):
            return DETAIL_DATA

        monkeypatch.setattr(parser, "fetch_detail_via_browser", fake_browser)
        info = await parse_share_text("看看 https://v.douyin.com/iAbCdEf/")
        assert info["aweme_id"] == "7412345678901234567"
        assert info["title"] == "测试视频标题"
