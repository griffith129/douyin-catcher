"""单测配置隔离：无论 .env 如何，测试一律使用可 mock 的默认后端。"""

import pytest

from douyin_catcher import config as cfg


@pytest.fixture(autouse=True)
def _test_config(monkeypatch):
    monkeypatch.setattr(cfg.config, "ASR_PROVIDER", "siliconflow")
    monkeypatch.setattr(cfg.config, "LLM_BASE_URL", "https://api.siliconflow.cn/v1")
    monkeypatch.setattr(cfg.config, "LLM_API_STYLE", "chat", raising=False)
    monkeypatch.setattr(cfg.config, "LLM_MODEL", "deepseek-ai/DeepSeek-V3")
    monkeypatch.setattr(cfg.config, "LLM_API_KEY", "")
    monkeypatch.setattr(cfg.config, "SILICONFLOW_API_KEY", "")
