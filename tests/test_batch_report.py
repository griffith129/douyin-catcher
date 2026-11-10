"""batch_report：2B 批次报告（本地）的单元测试。"""

import json

from douyin_catcher.batch_report import list_batches, record_batch, record_item_into_daily_batch


class TestBatchReport:
    def test_record_and_list(self, tmp_path):
        f = tmp_path / "batches.json"
        record_batch(
            f,
            items=[
                {"aweme_id": "1", "title": "视频一", "category": "AI", "notion_url": "u1"},
                {"aweme_id": "2", "title": "视频二", "category": "编程", "notion_url": "u2"},
            ],
        )
        batches = list_batches(f)
        assert len(batches) == 1
        assert batches[0]["batch_id"] == "batch-001"
        assert len(batches[0]["items"]) == 2
        assert batches[0]["items"][0]["category"] == "AI"

    def test_batch_ids_increment(self, tmp_path):
        f = tmp_path / "batches.json"
        record_batch(f, items=[])
        record_batch(f, items=[])
        ids = [b["batch_id"] for b in list_batches(f)]
        assert sorted(ids) == ["batch-001", "batch-002"]

    def test_batches_sorted_newest_first(self, tmp_path):
        f = tmp_path / "batches.json"
        record_batch(f, items=[])
        record_batch(f, items=[])
        batches = list_batches(f)
        assert batches[0]["batch_id"] == "batch-002"

    def test_record_has_timestamp(self, tmp_path):
        f = tmp_path / "batches.json"
        record_batch(f, items=[])
        b = list_batches(f)[0]
        assert "created_at" in b and b["created_at"]


class TestDailyBatch:
    def test_same_day_items_merge_into_one_batch(self, tmp_path, monkeypatch):
        import douyin_catcher.batch_report as br

        monkeypatch.setattr(br, "_today", lambda: "2026-11-10")
        f = tmp_path / "batches.json"
        b1 = record_item_into_daily_batch(f, {"aweme_id": "1", "title": "a", "category": "c"})
        b2 = record_item_into_daily_batch(f, {"aweme_id": "2", "title": "b", "category": "c"})
        assert b1 == b2
        batches = list_batches(f)
        assert len(batches) == 1
        assert len(batches[0]["items"]) == 2

    def test_new_day_gets_new_batch(self, tmp_path, monkeypatch):
        import douyin_catcher.batch_report as br

        f = tmp_path / "batches.json"
        monkeypatch.setattr(br, "_today", lambda: "2026-11-10")
        record_item_into_daily_batch(f, {"aweme_id": "1", "title": "a", "category": "c"})
        monkeypatch.setattr(br, "_today", lambda: "2026-11-11")
        b2 = record_item_into_daily_batch(f, {"aweme_id": "2", "title": "b", "category": "c"})
        batches = list_batches(f)
        assert len(batches) == 2
        assert b2 == batches[0]["batch_id"]  # 最新在前

    def test_batch_id_stable_numbering(self, tmp_path, monkeypatch):
        import douyin_catcher.batch_report as br

        monkeypatch.setattr(br, "_today", lambda: "2026-11-10")
        f = tmp_path / "batches.json"
        record_batch(f, items=[])  # 手动批次占 batch-001
        bid = record_item_into_daily_batch(f, {"aweme_id": "1", "title": "a", "category": "c"})
        assert bid == "batch-002"
