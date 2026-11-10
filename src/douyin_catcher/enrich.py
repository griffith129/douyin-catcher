"""enrich：笔记的「概述」与「标签」生成逻辑（UX demo 数据层）。"""

import json
import re

import httpx

from .config import config

_LLM_TIMEOUT = 120


def summarize_preview(preview: str, limit: int = 200) -> str:
    """取精华版首段前 limit 字符作概述，在句号处截断避免半句。"""
    text = re.sub(r"\s+", "", preview)
    if len(text) <= limit:
        return text
    cut = text[:limit]
    # 在截断范围内回退到最后一个句号（中英文），避免半句
    m = None
    for m in re.finditer(r"[。！？.!?]", cut):
        pass
    if m and m.end() >= limit // 2:
        return cut[: m.end()]
    return cut


def build_tag_prompt(title: str, summary: str) -> str:
    return f"""从下面的视频学习笔记中提取 3-5 个检索用标签。

要求：
- 每个标签 2-6 个字，是具体可搜索的主题词（如：KV Cache、上下文压缩、多智能体）
- 覆盖视频的核心技术点/主题，不要使用"AI""视频""学习"这类过泛的词
- 只输出 JSON 数组，如 ["标签1", "标签2"]，不要输出其他内容

视频标题：{title}
笔记摘要：{summary[:600]}"""


def parse_tags(raw: str) -> list[str]:
    """解析 LLM 输出的 JSON 数组，容错提取。"""
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if not m:
        raise ValueError(f"标签输出无法解析: {raw[:200]}")
    tags = json.loads(m.group(0))
    out = []
    for t in tags:
        s = str(t).strip().strip("#")
        if s and s not in out:
            out.append(s[:12])
    return out[:5]


async def _llm_text(prompt: str, api_key: str) -> str:
    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(timeout=_LLM_TIMEOUT) as client:
        if config.LLM_API_STYLE == "responses":
            resp = await client.post(
                f"{config.LLM_BASE_URL}/responses",
                headers=headers,
                json={"model": config.LLM_MODEL, "input": prompt, "max_output_tokens": 512},
            )
            data = resp.json()
            return "".join(c.get("text", "") for c in data["output"][0]["content"])
        resp = await client.post(
            f"{config.LLM_BASE_URL}/chat/completions",
            headers=headers,
            json={
                "model": config.LLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 512,
            },
        )
        return resp.json()["choices"][0]["message"]["content"]


async def extract_tags(title: str, summary: str, api_key: str) -> list[str]:
    raw = await _llm_text(build_tag_prompt(title, summary), api_key)
    return parse_tags(raw)
