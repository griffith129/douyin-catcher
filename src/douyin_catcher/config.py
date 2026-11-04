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

    NOTES_DIR: str = os.getenv("NOTES_DIR", "notes")
    QUEUE_FILE: str = os.getenv("QUEUE_FILE", "data/queue.txt")
    DOWNLOAD_DIR: str = os.getenv("DOWNLOAD_DIR", "data/downloads")
    DATA_DIR: str = os.getenv("DATA_DIR", "data")

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
