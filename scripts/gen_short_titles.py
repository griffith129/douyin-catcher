"""为全部笔记生成 LLM 短标题（T1 预览，不改 Notion），写入 data/note_index.json。

用法：uv run python scripts/gen_short_titles.py
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from douyin_catcher.config import config  # noqa: E402
from douyin_catcher.short_title import generate_short_title  # noqa: E402

INDEX_FILE = Path("data/note_index.json")


async def main() -> None:
    index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    api_key = config.LLM_API_KEY or config.SILICONFLOW_API_KEY
    sem = asyncio.Semaphore(5)

    async def one(e: dict) -> None:
        async with sem:
            try:
                st = await generate_short_title(e["title"], e.get("preview", ""), api_key)
                e["short_title"] = st
                print(f"  {e['title'][:30]!r} → {st!r}")
            except Exception as exc:
                print(f"  FAIL {e['title'][:26]}: {exc}")

    await asyncio.gather(*(one(e) for e in index))
    INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    n = sum(1 for e in index if e.get("short_title"))
    print(f"[+] 短标题完成：{n}/{len(index)}")


if __name__ == "__main__":
    asyncio.run(main())
