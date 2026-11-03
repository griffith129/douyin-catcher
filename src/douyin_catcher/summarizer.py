"""LLM 整理：把视频文案整理成结构化学习笔记。"""

import httpx

from .config import config

SUMMARY_PROMPT = """你是知识整理助手。下面是一条抖音知识类视频的文字稿。
请把它整理成 Markdown 学习笔记，必须包含以下小节（按此顺序）：
## 一句话结论
## 核心要点
（3-6 条，每条一句话）
## 关键细节
（值得记住的事实、数据、例子；没有则写"无"）
## 原文没有讲清的问题
（列出视频未展开但值得追问的点；没有则写"无"）

要求：忠实于文字稿，不要编造；语言简洁；直接输出 Markdown，不要额外寒暄。

视频标题：{title}
作者：{author}

文字稿：
{transcript}"""


async def summarize(
    title: str, author: str, transcript: str, api_key: str | None = None
) -> str:
    api_key = api_key or config.LLM_API_KEY or config.SILICONFLOW_API_KEY
    if not api_key:
        raise RuntimeError("缺少 LLM_API_KEY / SILICONFLOW_API_KEY")
    url = f"{config.LLM_BASE_URL}/chat/completions"
    payload = {
        "model": config.LLM_MODEL,
        "messages": [
            {
                "role": "user",
                "content": SUMMARY_PROMPT.format(
                    title=title, author=author, transcript=transcript
                ),
            }
        ],
        "temperature": 0.3,
        "max_tokens": 2048,
    }
    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()
