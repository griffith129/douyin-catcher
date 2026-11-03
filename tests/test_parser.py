"""测试：分享文本解析 —— 从抖音分享口令中提取链接、解析视频元数据。"""

import json
import pathlib

import httpx
import pytest
import respx

from douyin_catcher.parser import (
    extract_urls,
    extract_video_id,
    fetch_video_info,
    parse_share_text,
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


ROUTER_DATA = {
    "loaderData": {
        "video_(id)/page": {
            "videoInfoRes": {
                "item_list": [
                    {
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
                    }
                ]
            }
        }
    }
}


class TestFetchVideoInfo:
    @respx.mock
    async def test_parse_router_data(self, tmp_path: pathlib.Path):
        html = "<html><script>window._ROUTER_DATA = " + json.dumps(ROUTER_DATA) + ";</script></html>"
        respx.get("https://www.iesdouyin.com/share/video/7412345678901234567").mock(
            return_value=httpx.Response(200, text=html)
        )
        info = await fetch_video_info("7412345678901234567")
        assert info["aweme_id"] == "7412345678901234567"
        assert info["title"] == "测试视频标题"
        assert info["author"] == "测试作者"
        # playwm -> play 得到无水印地址
        assert info["video_url"].startswith("https://")

    @respx.mock
    async def test_raises_when_no_item(self):
        empty = {"loaderData": {"video_(id)/page": {"videoInfoRes": {"item_list": []}}}}
        html = "<script>window._ROUTER_DATA = " + json.dumps(empty) + ";</script>"
        respx.get("https://www.iesdouyin.com/share/video/1").mock(
            return_value=httpx.Response(200, text=html)
        )
        with pytest.raises(ValueError):
            await fetch_video_info("1")


class TestParseShareText:
    @respx.mock
    async def test_end_to_end_share_text(self):
        respx.get("https://v.douyin.com/iAbCdEf/").mock(
            return_value=httpx.Response(
                302, headers={"Location": "https://www.douyin.com/video/7412345678901234567"}
            )
        )
        html = "<script>window._ROUTER_DATA = " + json.dumps(ROUTER_DATA) + ";</script>"
        respx.get("https://www.iesdouyin.com/share/video/7412345678901234567").mock(
            return_value=httpx.Response(200, text=html)
        )
        info = await parse_share_text("看看 https://v.douyin.com/iAbCdEf/")
        assert info["aweme_id"] == "7412345678901234567"
        assert info["title"] == "测试视频标题"
