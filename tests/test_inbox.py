"""测试：inbox 采集（douyin-chat-export REST 集成）+ 链接池合并。"""

import json

import httpx
import pytest
import respx

from douyin_catcher.inbox import (
    extract_links,
    fetch_conversations,
    fetch_messages,
    load_pool,
    merge_into_pool,
    sync_inbox,
)


def _share_msg(seq: int, item_id: str, title: str, ts: int = 1793839200) -> dict:
    """按 douyin-chat-export 真实结构构造分享卡片消息。

    真实字段（2026-11 抓包）：标题在 content_title，作者名在 content_name，
    content_json 是 raw_data 内层再编码一次的 JSON 字符串。
    """
    raw = {
        "server_id": f"srv_{item_id}",
        "content": "[分享]",
        "msg_type": "share",
        "awe_type": 800,
        "content_json": json.dumps(
            {
                "aweType": 800,
                "awemeType": 0,
                "itemId": item_id,
                "content_title": title,
                "content_name": "彻彻",
                "is_card": False,
                "scene_type": 0,
            },
            ensure_ascii=False,
        ),
    }
    return {
        "msg_id": f"srv_{item_id}",
        "seq": seq,
        "msg_type": 4,
        "content": "[分享]",
        "raw_data": json.dumps(raw, ensure_ascii=False),
        "timestamp": ts,
    }


MESSAGES = [
    _share_msg(101, "7703128487007112511", "经验进化-KDD26-港科大-逐步评价执行动作"),
    _share_msg(102, "7698402336053972827", "生成式AI与Agentic AI"),
    {
        "msg_id": "m3",
        "seq": 103,
        "msg_type": 1,
        "content": json.dumps({"text": "今天天气不错，没有链接"}),
        "raw_data": "",
        "timestamp": 1793839300,
    },
    {
        "msg_id": "m4",
        "seq": 104,
        "msg_type": 1,
        "content": json.dumps(
            {"text": "6.46 复制打开抖音 https://v.douyin.com/wr9uFGXibYY/ 看看"}
        ),
        "raw_data": "",
        "timestamp": 1793839400,
    },
    # 重复分享同一视频 → 去重
    _share_msg(105, "7703128487007112511", "经验进化-KDD26-港科大-逐步评价执行动作"),
]


class TestExtractLinks:
    def test_share_card_yields_url_title(self):
        found = extract_links(MESSAGES)
        by_url = {f["url"]: f for f in found}
        assert (
            "https://www.douyin.com/video/7703128487007112511" in by_url
        )
        item = by_url["https://www.douyin.com/video/7703128487007112511"]
        assert item["title"] == "经验进化-KDD26-港科大-逐步评价执行动作"
        assert item["author"] == "彻彻"
        assert item["msg_id"] == "srv_7703128487007112511"

    def test_text_link_without_title(self):
        found = extract_links(MESSAGES)
        by_url = {f["url"]: f for f in found}
        item = by_url.get("https://v.douyin.com/wr9uFGXibYY/")
        assert item is not None
        assert not item.get("title")

    def test_dedupes_same_video(self):
        found = extract_links(MESSAGES)
        ids = [f["url"] for f in found]
        assert len(ids) == len(set(ids))
        assert len(ids) == 3

    def test_ignores_non_video_share(self):
        msgs = [
            _share_msg(1, "12345", "x"),
        ]
        msgs[0]["raw_data"] = json.dumps(
            {
                "msg_type": "share",
                "content_json": json.dumps({"media_type": "goods", "itemId": "12345"}),
            }
        )
        found = extract_links(msgs)
        assert found == []

    def test_ignores_message_without_item_id(self):
        msgs = [_share_msg(1, "", "无视频")]
        assert extract_links(msgs) == []

    def test_real_capture_content_title_fields(self):
        """回归测试：真实抓包的分享卡片（aweType=800，无 aweme_title/media_type）。

        2026-11 真实数据标题在 content_title，作者在 content_name；
        旧实现读 aweme_title 导致 2115 条记录全部无标题。
        """
        cj = {
            "aweType": 800,
            "awemeType": 0,
            "content_name": "Yunana",
            "content_title": "10 Minutes",
            "cover_width": 576.0,
            "is_card": False,
            "itemId": "7459708493746949395",
            "msgHint": "",
            "scene_type": 0,
            "share_id": "23447832897_1793726982051_7459708493746949395",
        }
        raw = {
            "server_id": "7703998645226227249",
            "content": "[分享]",
            "msg_type": "share",
            "awe_type": 800,
            "is_self": False,
            "content_json": json.dumps(cj, ensure_ascii=False),
        }
        msg = {
            "msg_id": "srv_7703998645226227249",
            "conv_id": "0:1:23447832897:23447832897",
            "sender_uid": "23447832897",
            "content": "[分享]",
            "msg_type": 4,
            "seq": 3401,
            "raw_data": json.dumps(raw, ensure_ascii=False),
            "timestamp": 1793726963,
        }
        found = extract_links([msg])
        assert len(found) == 1
        rec = found[0]
        assert rec["url"] == "https://www.douyin.com/video/7459708493746949395"
        assert rec["title"] == "10 Minutes"
        assert rec["author"] == "Yunana"

    def test_non_video_awetype_skipped(self):
        """aweType 非 800（如图文/其他卡片）且无 itemId 的分享不入池。"""
        cj = {"aweType": 2000, "content_title": "直播间", "content_name": "x"}
        raw = {
            "msg_type": "share",
            "awe_type": 2000,
            "content_json": json.dumps(cj, ensure_ascii=False),
        }
        msg = {
            "msg_id": "s2",
            "seq": 2,
            "msg_type": 4,
            "content": "[分享]",
            "raw_data": json.dumps(raw, ensure_ascii=False),
        }
        assert extract_links([msg]) == []

    def test_ignores_non_douyin_urls(self):
        msgs = [
            {
                "msg_id": "x",
                "seq": 1,
                "msg_type": 1,
                "content": json.dumps({"text": "看 https://github.com/a/b"}),
                "raw_data": "",
            }
        ]
        assert extract_links(msgs) == []


class TestPool:
    def test_merge_and_persist(self, tmp_path):
        pool_file = tmp_path / "inbox_pool.json"
        found = extract_links(MESSAGES)
        pool = load_pool(pool_file)
        added = merge_into_pool(pool, found)
        assert added == 3
        pool_file.write_text(json.dumps(pool, ensure_ascii=False), encoding="utf-8")
        # 重复合并不再新增
        pool2 = load_pool(pool_file)
        assert merge_into_pool(pool2, found) == 0

    def test_merge_keeps_title(self, tmp_path):
        pool_file = tmp_path / "inbox_pool.json"
        pool = load_pool(pool_file)
        merge_into_pool(pool, extract_links(MESSAGES)[:1])
        item = list(pool["links"].values())[0]
        assert item["status"] == "pending"
        assert item.get("title")


class TestFetchAPI:
    @respx.mock
    async def test_fetch_conversations(self):
        respx.get("http://127.0.0.1:8000/api/conversations").mock(
            return_value=httpx.Response(
                200,
                json={"items": [{"conv_id": "0:1:1:1", "name": "彻彻"}]},
            )
        )
        convs = await fetch_conversations("http://127.0.0.1:8000", token="tk")
        assert convs[0]["conv_id"] == "0:1:1:1"

    @respx.mock
    async def test_fetch_messages_uses_items_key_and_after_seq(self):
        route = respx.get(
            url__startswith="http://127.0.0.1:8000/api/conversations/c1/messages"
        ).mock(
            return_value=httpx.Response(
                200, json={"items": MESSAGES, "total": 5, "has_newer": False}
            )
        )
        msgs = await fetch_messages("http://127.0.0.1:8000", "c1", token="tk", after_seq=0)
        assert len(msgs) == 5
        assert "after_seq=0" in str(route.calls.last.request.url)

    @respx.mock
    async def test_conv_id_brackets_stripped(self):
        """conv_id 带尖括号时自动剥掉（用户从面板复制的常见错误）。"""
        route = respx.get(
            url__startswith="http://127.0.0.1:8000/api/conversations/0%3A1%3A1%3A1/messages"
        ).mock(
            return_value=httpx.Response(200, json={"items": [], "total": 0})
        )
        await fetch_messages("http://127.0.0.1:8000", "<0:1:1:1>", token="tk")
        assert route.called


class TestSyncInbox:
    @respx.mock
    async def test_full_sync_flow(self, tmp_path):
        pool_file = tmp_path / "inbox_pool.json"
        respx.get(
            url__startswith="http://127.0.0.1:8000/api/conversations/c1/messages"
        ).mock(
            return_value=httpx.Response(
                200, json={"items": MESSAGES, "total": 5, "has_newer": False}
            )
        )
        result = await sync_inbox(
            pool_file, base_url="http://127.0.0.1:8000", conv_id="c1", token="tk"
        )
        assert result["added"] == 3
        pool = load_pool(pool_file)
        assert len(pool["links"]) == 3
        assert pool["last_seq"] == 105

    @respx.mock
    async def test_sync_incremental_skips_old(self, tmp_path):
        pool_file = tmp_path / "inbox_pool.json"
        route = respx.get(
            url__startswith="http://127.0.0.1:8000/api/conversations/c1/messages"
        ).mock(
            return_value=httpx.Response(
                200, json={"items": MESSAGES, "total": 5, "has_newer": False}
            )
        )
        await sync_inbox(pool_file, base_url="http://127.0.0.1:8000", conv_id="c1", token="tk")
        await sync_inbox(pool_file, base_url="http://127.0.0.1:8000", conv_id="c1", token="tk")
        assert "after_seq=105" in str(route.calls[-1].request.url)
