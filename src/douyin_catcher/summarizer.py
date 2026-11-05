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

CORRECT_PROMPT = """你是转写校对助手。下面是一段语音转写（ASR）文本，其中可能存在错别字、
同音字错误、繁简漂移和专有名词识别错误。请纠正这些问题。
规则：
- 只纠正明显错误（同音字、专有名词、繁体转简体、标点），不要改写句式，不要增删内容；
- 结合视频标题和作者推断专有名词（技术术语、人名、产品名）；
- 直接输出纠正后的纯文本，不要任何解释或 Markdown。

视频标题：{title}
作者：{author}

转写文本：
{transcript}"""


def _extract_responses_text(data: dict) -> str:
    """从 Responses API 返回中提取文本（兼容 output[].content[].output_text）。"""
    text = data.get("output_text")
    if text:
        return str(text).strip()
    parts: list[str] = []
    for item in data.get("output") or []:
        if item.get("type") != "message":
            continue
        for block in item.get("content") or []:
            if block.get("type") == "output_text" and block.get("text"):
                parts.append(block["text"])
    return "\n".join(parts).strip()


async def _llm_text(prompt: str, api_key: str) -> str:
    """统一的 LLM 文本调用（兼容 chat/completions 与 responses 两种 API 风格）。"""
    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(timeout=180) as client:
        if config.LLM_API_STYLE == "responses":
            # Codex 风格反代仅支持 /v1/responses
            resp = await client.post(
                f"{config.LLM_BASE_URL}/responses",
                headers=headers,
                json={
                    "model": config.LLM_MODEL,
                    "input": prompt,
                    "temperature": 0.3,
                    "max_output_tokens": 2048,
                },
            )
            resp.raise_for_status()
            return _extract_responses_text(resp.json())
        resp = await client.post(
            f"{config.LLM_BASE_URL}/chat/completions",
            headers=headers,
            json={
                "model": config.LLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 2048,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()


async def correct_transcript(
    transcript: str, title: str = "", author: str = "", api_key: str | None = None
) -> str:
    """ASR 文本二次校对：纠正同音字/专有名词/繁简漂移。

    失败时原样返回，不阻塞主流程（与 Notion 上传同策略）。
    """
    api_key = api_key or config.LLM_API_KEY or config.SILICONFLOW_API_KEY
    if not api_key:
        return transcript
    prompt = CORRECT_PROMPT.format(title=title, author=author, transcript=transcript)
    try:
        corrected = await _llm_text(prompt, api_key)
    except Exception:  # ponytail: 校对是增强，不是依赖
        return transcript
    return corrected or transcript


async def summarize(
    title: str, author: str, transcript: str, api_key: str | None = None
) -> str:
    api_key = api_key or config.LLM_API_KEY or config.SILICONFLOW_API_KEY
    if not api_key:
        raise RuntimeError("缺少 LLM_API_KEY / SILICONFLOW_API_KEY")
    prompt = SUMMARY_PROMPT.format(title=title, author=author, transcript=transcript)
    return await _llm_text(prompt, api_key)
