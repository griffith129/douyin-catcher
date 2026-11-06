import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """集中配置：一律从环境变量读取，.env 提供默认值。"""

    SILICONFLOW_API_KEY: str = os.getenv("SILICONFLOW_API_KEY", "")
    SILICONFLOW_BASE_URL: str = os.getenv(
        "SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"
    )
    ASR_PROVIDER: str = os.getenv("ASR_PROVIDER", "siliconflow")  # siliconflow | whisper
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")
    ASR_MODEL: str = os.getenv("ASR_MODEL", "FunAudioLLM/SenseVoiceSmall")

    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")  # 缺省回退 SILICONFLOW_API_KEY
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.siliconflow.cn/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "deepseek-ai/DeepSeek-V3")
    LLM_API_STYLE: str = os.getenv("LLM_API_STYLE", "chat")  # chat | responses
    NOTE_SPEC_FILE: str = os.getenv("NOTE_SPEC_FILE", "docs/note_spec.md")  # 文档规范提示词，空 = 不用

    NOTES_DIR: str = os.getenv("NOTES_DIR", "notes")
    QUEUE_FILE: str = os.getenv("QUEUE_FILE", "data/queue.txt")
    DOWNLOAD_DIR: str = os.getenv("DOWNLOAD_DIR", "data/downloads")
    DATA_DIR: str = os.getenv("DATA_DIR", "data")

    NOTION_TOKEN: str = os.getenv("NOTION_TOKEN", "")  # integration secret（ntn_ 开头）
    NOTION_PARENT_PAGE_ID: str = os.getenv("NOTION_PARENT_PAGE_ID", "")

    INBOX_API_BASE_URL: str = os.getenv("INBOX_API_BASE_URL", "http://127.0.0.1:8000")
    INBOX_API_TOKEN: str = os.getenv("INBOX_API_TOKEN", "")
    INBOX_CONV_ID: str = os.getenv("INBOX_CONV_ID", "")
    INBOX_POOL_FILE: str = os.getenv("INBOX_POOL_FILE", "data/inbox_pool.json")

    HTTP_TIMEOUT: float = float(os.getenv("HTTP_TIMEOUT", "30"))
    DOWNLOAD_TIMEOUT: float = float(os.getenv("DOWNLOAD_TIMEOUT", "120"))
    BROWSER_TIMEOUT: float = float(os.getenv("BROWSER_TIMEOUT", "30"))
    USER_AGENT: str = os.getenv(
        "USER_AGENT",
        # 关键：抖音仅对 Android UA 的分享页做 SSR（内嵌 videoInfoRes）
        "Mozilla/5.0 (Linux; Android 14; Pixel 8) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36",
    )


config = Config()
