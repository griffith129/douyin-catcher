"""server 启动辅助（uvicorn 不在测试依赖里，放这里避免 import 开销）。"""

import uvicorn


def run_server(host: str = "0.0.0.0", port: int = 8787) -> None:
    uvicorn.run("douyin_catcher.server:app", host=host, port=port)
