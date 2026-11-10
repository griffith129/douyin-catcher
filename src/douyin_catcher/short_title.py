"""短标题（T1）：LLM 生成限定字数、去抖音噪声的简洁标题。"""

import json
import re

from .config import config
from .enrich import _llm_text

MAX_LEN = 18

_PROMPT = """把下面的抖音视频标题改写成一个简洁的中文标题。

要求：
1. 最多 {max_len} 个字（含标点），一个短句说清视频核心主题
2. 删除所有不属于标题的噪声：#话题标签、@用户名、"三分钟带你搞"之类的推广语/钩子语、多余的副标题与表情
3. 基于标题与内容摘要概括，优先用内容确认的核心概念命名，不确定的信息不要编造
4. 只输出 JSON：{{"short_title": "..."}}，不要输出其他内容

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


async def generate_short_title(title: str, summary: str, api_key: str) -> str:
    raw = await _llm_text(build_short_title_prompt(title, summary), api_key)
    return parse_short_title(raw)
