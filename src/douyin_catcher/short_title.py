"""短标题（T1 v2）：LLM 生成限定字数、去噪、**保留特征字段**的简洁标题。

核心思想（用户 2026-11-10 定案）：短标题必须最大限度保留原标题中的
专有名词/数字/核心概念，确保不同视频的标题可区分，防止同质化。
"""

import json
import re

from .config import config
from .enrich import _llm_text

MAX_LEN = 18

_PROMPT = """把下面的抖音视频标题改写成一个简洁的中文标题。

要求：
1. 最多 {max_len} 个字（含标点），一个短句说清视频核心主题
2. 删除所有不属于标题的噪声：#话题标签、@用户名、"三分钟带你搞"之类的推广语/钩子语、多余的副标题与表情
3. **最大限度保留原标题中的特征字段**：专有名词（产品名/模型名/框架名/课程名/公司名）、数字（如"七项""4大场景"）、核心技术概念（如 KV Cache、RL、Runtime）。这些是视频的身份特征，丢失会导致标题同质化、无法区分
4. 改写后的标题必须能与同主题的其他视频明确区分——如果原标题的特征字段足以定位视频，优先原样保留这些字段，只删噪声、重排语序
5. 基于标题与内容摘要概括；内容中出现但原标题没有的关键概念也可以补入，但不得编造原标题没有的产品/模型名
6. 只输出 JSON：{{"short_title": "..."}}，不要输出其他内容

原标题：{title}
内容摘要：{summary}"""


def build_short_title_prompt(title: str, summary: str) -> str:
    return _PROMPT.format(max_len=MAX_LEN, title=title, summary=summary[:600])


def parse_short_title(raw: str) -> str:
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        raise ValueError(f"短标题输出无法解析: {raw[:200]}")
    data = json.loads(m.group(0))
    title = str(data.get("short_title", "")).strip().strip('"“”')
    if not title:
        raise ValueError("短标题为空")
    if len(title) > MAX_LEN:
        title = title[:MAX_LEN]
    return title


def make_unique(titles: list[str]) -> list[str]:
    """同名短标题追加（2）/（3）后缀，保证库内可区分（允许超上限 ≤3 字）。"""
    seen: dict[str, int] = {}
    out = []
    for t in titles:
        n = seen.get(t, 0)
        seen[t] = n + 1
        out.append(t if n == 0 else f"{t}（{n + 1}）")
    return out


async def generate_short_title(title: str, summary: str, api_key: str) -> str:
    raw = await _llm_text(build_short_title_prompt(title, summary), api_key)
    return parse_short_title(raw)
