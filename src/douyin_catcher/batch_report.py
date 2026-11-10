"""2B 批次报告：记录每次批量整理的视频集合，支持回看历史批次。"""

import json
from datetime import datetime
from pathlib import Path


def record_batch(path: str | Path, items: list[dict]) -> str:
    """追加一个批次（batch_id 自增），返回批次号。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    batches = []
    if p.exists():
        batches = json.loads(p.read_text(encoding="utf-8"))
    batch_id = f"batch-{len(batches) + 1:03d}"
    batches.append(
        {
            "batch_id": batch_id,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "items": items,
        }
    )
    p.write_text(json.dumps(batches, ensure_ascii=False, indent=2), encoding="utf-8")
    return batch_id


def list_batches(path: str | Path) -> list[dict]:
    """返回全部批次，最新在前。"""
    p = Path(path)
    if not p.exists():
        return []
    batches = json.loads(p.read_text(encoding="utf-8"))
    return list(reversed(batches))


def _today() -> str:
    from datetime import datetime

    return datetime.now().strftime("%Y-%m-%d")


def record_item_into_daily_batch(path: str | Path, item: dict) -> str:
    """pipeline 自动收录用：同一天的条目聚合进同一个批次，返回批次号。

    与 record_batch（一次批量选择 = 一个批次）并存，互不干扰。
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    batches = []
    if p.exists():
        batches = json.loads(p.read_text(encoding="utf-8"))
    today = _today()
    for b in reversed(batches):
        if b.get("created_at", "").startswith(today) and b.get("daily"):
            b["items"].append(item)
            p.write_text(json.dumps(batches, ensure_ascii=False, indent=2), encoding="utf-8")
            return b["batch_id"]
    batch_id = f"batch-{len(batches) + 1:03d}"
    batches.append({
        "batch_id": batch_id,
        "created_at": f"{today} {datetime.now().strftime('%H:%M:%S')}",
        "daily": True,
        "items": [item],
    })
    p.write_text(json.dumps(batches, ensure_ascii=False, indent=2), encoding="utf-8")
    return batch_id
