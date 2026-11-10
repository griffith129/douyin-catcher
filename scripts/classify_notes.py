"""对 notes/ 全部笔记跑真实 LLM 分类（3B 流程），产出：
- data/categories.json（大类→细类清单，含新提案大类自动入库）
- data/note_index.json（索引 + 每篇分类结果）

用法：uv run python scripts/classify_notes.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from douyin_catcher.config import config  # noqa: E402
from douyin_catcher.note_index import build_index, load_index, parse_frontmatter, save_index  # noqa: E402
from douyin_catcher.taxonomy import (  # noqa: E402
    classify_note,
    load_taxonomy,
    save_taxonomy,
    Taxonomy,
)

NOTES_DIR = Path("notes")
TAXONOMY_FILE = Path("data/categories.json")
INDEX_FILE = Path("data/note_index.json")
RESULT_FILE = Path("data/classify_results.json")

# 3B 初始大类（宽泛主题，LLM 可提案新大类）
SEED_CATEGORIES = {
    "AI Agent 与工作流": ["工作边界", "多智能体协作", "工具调用", "记忆与上下文"],
    "大模型与推理技术": ["模型架构", "推理优化", "评测与基准"],
    "编程与软件工程": ["开发方法论", "工具链", "代码质量"],
    "求职与职业发展": ["面试准备", "简历与作品集"],
    "认知与思维方法": ["思维模型", "学习方法"],
}


async def main() -> None:
    taxonomy = load_taxonomy(TAXONOMY_FILE)
    if not taxonomy.categories:
        taxonomy = Taxonomy(categories=dict(SEED_CATEGORIES))
        save_taxonomy(taxonomy, TAXONOMY_FILE)
        print(f"[+] 初始大类清单已写入 {TAXONOMY_FILE}（{len(SEED_CATEGORIES)} 大类）")

    entries = load_index(INDEX_FILE) or build_index(NOTES_DIR)
    print(f"[+] 共 {len(entries)} 篇笔记待分类")

    api_key = config.LLM_API_KEY or config.SILICONFLOW_API_KEY
    results: dict[str, dict] = {}
    if RESULT_FILE.exists():
        import json

        results = json.loads(RESULT_FILE.read_text(encoding="utf-8"))

    new_cats = []
    for i, e in enumerate(entries, 1):
        if e["aweme_id"] in results:
            continue
        md = (NOTES_DIR / e["file"]).read_text(encoding="utf-8")
        summary = e["preview"]
        try:
            r = await classify_note(e["title"], summary, taxonomy.categories, api_key)
        except Exception as exc:  # 单篇失败不阻塞整体
            print(f"  [{i}/{len(entries)}] FAIL {e['title'][:30]}: {exc}")
            continue
        results[e["aweme_id"]] = r
        if r["is_new_category"]:
            new_cats.append(r["category"])
            taxonomy.categories[r["category"]] = [r["subcategory"]]
            save_taxonomy(taxonomy, TAXONOMY_FILE)
            print(f"  ★ 新大类提案入库: {r['category']}")
        print(f"  [{i}/{len(entries)}] {e['title'][:28]} → {r['category']} / {r['subcategory']}")

    # 把分类结果合并进索引
    for e in entries:
        r = results.get(e["aweme_id"])
        if r:
            e["category"] = r["category"]
            e["subcategory"] = r["subcategory"]
    save_taxonomy(taxonomy, TAXONOMY_FILE)
    save_index(entries, INDEX_FILE)
    RESULT_FILE.write_text(
        __import__("json").dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[+] 完成：{len(results)} 篇已分类，大类共 {len(taxonomy.categories)} 个")
    if new_cats:
        print(f"[+] 新增大类: {', '.join(sorted(set(new_cats)))}")


if __name__ == "__main__":
    asyncio.run(main())
