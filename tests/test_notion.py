"""测试：Notion 1A 收录 —— md 转 blocks 与子页面创建。"""

import json

import httpx
import pytest
import respx

from douyin_catcher.notion import md_to_blocks, upload_note


class TestMdToBlocks:
    def test_headings_and_bullets(self):
        md = "## 一句话结论\n这是结论。\n\n## 核心要点\n- 要点一\n- 要点二\n\n普通段落"
        blocks = md_to_blocks(md)
        types = [b["type"] for b in blocks]
        assert types == [
            "heading_2",
            "paragraph",
            "heading_2",
            "bulleted_list_item",
            "bulleted_list_item",
            "paragraph",
        ]

    def test_block_content(self):
        blocks = md_to_blocks("# 标题\n- 项目")
        assert blocks[0]["type"] == "heading_1"
        assert blocks[0]["heading_1"]["rich_text"][0]["text"]["content"] == "标题"
        assert blocks[1]["bulleted_list_item"]["rich_text"][0]["text"]["content"] == "项目"

    def test_strips_frontmatter(self):
        md = "---\naweme_id: 123\n---\n\n## 一句话结论\n正文"
        blocks = md_to_blocks(md)
        types = [b["type"] for b in blocks]
        assert types == ["heading_2", "paragraph"]

    def test_long_text_chunked_under_2000(self):
        blocks = md_to_blocks("字" * 3000)
        rich = blocks[0]["paragraph"]["rich_text"]
        assert sum(len(r["text"]["content"]) for r in rich) == 3000
        assert all(len(r["text"]["content"]) <= 2000 for r in rich)


class TestUploadNote:
    @respx.mock
    async def test_creates_subpage(self):
        route = respx.post("https://api.notion.com/v1/pages").mock(
            return_value=httpx.Response(
                200, json={"id": "page-1", "url": "https://notion.so/page-1"}
            )
        )
        url = await upload_note(
            title="测试笔记", md="# 标题\n内容", parent_page_id="parent-1", token="ntn_test"
        )
        assert url == "https://notion.so/page-1"
        assert route.called
        body = json.loads(route.calls.last.request.content)
        assert body["parent"]["page_id"] == "parent-1"
        assert body["properties"]["title"]["title"][0]["text"]["content"] == "测试笔记"
        assert body["children"][0]["type"] == "heading_1"

    @respx.mock
    async def test_appends_blocks_over_100(self):
        create_route = respx.post("https://api.notion.com/v1/pages").mock(
            return_value=httpx.Response(
                200, json={"id": "page-1", "url": "https://notion.so/page-1"}
            )
        )
        append_route = respx.patch("https://api.notion.com/v1/blocks/page-1/children").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        md = "\n".join(f"- 第{i}条" for i in range(150))
        await upload_note(title="长笔记", md=md, parent_page_id="parent-1", token="ntn_test")
        assert create_route.called
        assert append_route.called
        body = json.loads(append_route.calls.last.request.content)
        assert 0 < len(body["children"]) <= 100

    @respx.mock
    async def test_raises_on_http_error(self):
        respx.post("https://api.notion.com/v1/pages").mock(
            return_value=httpx.Response(401, json={"message": "unauthorized"})
        )
        with pytest.raises(httpx.HTTPStatusError):
            await upload_note(
                title="x", md="内容", parent_page_id="parent-1", token="ntn_bad"
            )

    async def test_raises_when_unconfigured(self, monkeypatch):
        from douyin_catcher.config import config as cfg

        monkeypatch.setattr(cfg, "NOTION_TOKEN", "", raising=False)
        monkeypatch.setattr(cfg, "NOTION_PARENT_PAGE_ID", "", raising=False)
        with pytest.raises(RuntimeError):
            await upload_note(title="x", md="内容")
