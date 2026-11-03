import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """集中配置：一律从环境变量读取，.env 提供默认值。"""

    SILICONFLOW_API_KEY: str = os.getenv("SILICONFLOW_API_KEY", "")
    SILICONFLOW_BASE_URL: str = os.getenv(
        "SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"
    )
    ASR_MODEL: str = os.getenv("ASR_MODEL", "FunAudioLLM/SenseVoiceSmall")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "deepseek-ai/DeepSeek-V3")

    NOTES_DIR: str = os.getenv("NOTES_DIR", "notes")
    QUEUE_FILE: str = os.getenv("QUEUE_FILE", "data/queue.txt")
    DOWNLOAD_DIR: str = os.getenv("DOWNLOAD_DIR", "data/downloads")
    DATA_DIR: str = os.getenv("DATA_DIR", "data")

    HTTP_TIMEOUT: float = float(os.getenv("HTTP_TIMEOUT", "30"))
    DOWNLOAD_TIMEOUT: float = float(os.getenv("DOWNLOAD_TIMEOUT", "120"))
    USER_AGENT: str = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    )


config = Config()
