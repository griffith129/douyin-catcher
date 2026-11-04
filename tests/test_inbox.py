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


MESSAGES = [
    {
        "msg_id": "m1",
        "seq": 101,
        "msg_type": 7,
        "content": json.dumps(
            {"text": "6.46 复制打开抖音，看看【学姐的作品】经验进化 https://v.douyin.com/wr9uFGXibYY/ 12/01"}
        ),
        "created_at_us": "1730000000000000",
    },
    {
        "msg_id": "m2",
        "seq": 102,
        "msg_type": 43,
        "content": json.dumps(
            {
                "share": {
                    "desc": "生成式AI与Agentic AI",
                    "url": "https://www.douyin.com/video/7698402336053972827",
                }
            }
        ),
        "created_at_us": "1730000100000000",
    },
    {
        "msg_id": "m3",
        "seq": 103,
        "msg_type": 7,
        "content": json.dumps({"text": "今天天气不错，没有链接"}),
        "created_at_us": "1730000200000000",
    },
    {
        "msg_id": "m4",
        "seq": 104,
        "msg_type": 7,
        "content": json.dumps(
            {"text": "再看这条 https://v.douyin.com/wr9uFGXibYY/ 重复分享"}
        ),
        "created_at_us": "1730000300000000",
    },
]


class TestExtractLinks:
    def test_extracts_text_and_share_links(self):
        found = extract_links(MESSAGES)
        urls = {f["url"] for f in found}
        assert "https://v.douyin.com/wr9uFGXibYY/" in urls
        assert "https://www.douyin.com/video/7698402336053972827" in urls

    def test_dedupes_same_link(self):
        found = extract_links(MESSAGES)
        v_links = [f for f in found if f["url"] == "https://v.douyin.com/wr9uFGXibYY/"]
        assert len(v_links) == 1

    def test_carries_msg_meta(self):
        found = extract_links(MESSAGES)
        share = [f for f in found if f["url"] == "https://www.douyin.com/video/7698402336053972827"][0]
        assert share["msg_id"] == "m2"
        assert share["seq"] == 102

    def test_ignores_non_douyin_urls(self):
        msgs = [{"msg_id": "x", "seq": 1, "content": json.dumps({"text": "看 https://github.com/a/b"})}]
        assert extract_links(msgs) == []


class TestPool:
    def test_merge_and_persist(self, tmp_path):
        pool_file = tmp_path / "inbox_pool.json"
        found = extract_links(MESSAGES)
        pool = load_pool(pool_file)
        added = merge_into_pool(pool, found)
        assert added == 2
        pool_file.write_text(json.dumps(pool, ensure_ascii=False), encoding="utf-8")
        # 重复合并不再新增
        pool2 = load_pool(pool_file)
        assert merge_into_pool(pool2, found) == 0

    def test_merge_marks_status(self, tmp_path):
        pool_file = tmp_path / "inbox_pool.json"
        pool = load_pool(pool_file)
        merge_into_pool(pool, extract_links(MESSAGES)[:1])
        item = list(pool["links"].values())[0]
        assert item["status"] == "pending"


class TestFetchAPI:
    @respx.mock
    async def test_fetch_conversations(self):
        respx.get("http://127.0.0.1:8000/api/conversations").mock(
            return_value=httpx.Response(200, json={"conversations": [{"conv_id": "c1", "name": "自己"}]})
        )
        convs = await fetch_conversations("http://127.0.0.1:8000", token="tk")
        assert convs[0]["conv_id"] == "c1"

    @respx.mock
    async def test_fetch_messages_after_seq(self):
        route = respx.get(url__startswith="http://127.0.0.1:8000/api/conversations/c1/messages").mock(
            return_value=httpx.Response(200, json={"messages": MESSAGES, "total": 4})
        )
        msgs = await fetch_messages("http://127.0.0.1:8000", "c1", token="tk", after_seq=100)
        assert len(msgs) == 4
        assert "after_seq=100" in str(route.calls.last.request.url)


class TestSyncInbox:
    @respx.mock
    async def test_full_sync_flow(self, tmp_path):
        pool_file = tmp_path / "inbox_pool.json"
        respx.get(url__startswith="http://127.0.0.1:8000/api/conversations/c1/messages").mock(
            return_value=httpx.Response(200, json={"messages": MESSAGES, "total": 4})
        )
        result = await sync_inbox(
            pool_file, base_url="http://127.0.0.1:8000", conv_id="c1", token="tk"
        )
        assert result["added"] == 2
        pool = load_pool(pool_file)
        assert len(pool["links"]) == 2
        assert pool["last_seq"] == 104

    @respx.mock
    async def test_sync_incremental_skips_old(self, tmp_path):
        pool_file = tmp_path / "inbox_pool.json"
        route = respx.get(url__startswith="http://127.0.0.1:8000/api/conversations/c1/messages").mock(
            return_value=httpx.Response(200, json={"messages": MESSAGES, "total": 4})
        )
        await sync_inbox(pool_file, base_url="http://127.0.0.1:8000", conv_id="c1", token="tk")
        await sync_inbox(pool_file, base_url="http://127.0.0.1:8000", conv_id="c1", token="tk")
        # 第二次从 last_seq 之后拉
        assert "after_seq=104" in str(route.calls[-1].request.url)
