"""FastAPI 接收服务：POST /link 入队，后台 worker 消费。"""

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import config
from .parser import extract_urls
from .pipeline import process_link
from .queue import LinkQueue

logger = logging.getLogger("douyin_catcher")

_queue: LinkQueue | None = None


def get_queue() -> LinkQueue:
    global _queue
    if _queue is None:
        _queue = LinkQueue(config.QUEUE_FILE)
    return _queue


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_worker_loop())
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="douyin-catcher", lifespan=lifespan)


class LinkBody(BaseModel):
    text: str


@app.post("/link")
async def receive_link(body: LinkBody):
    if not extract_urls(body.text):
        raise HTTPException(status_code=400, detail="分享文本中没有链接")
    queued = get_queue().push(body.text)
    return {"ok": True, "queued": queued}


@app.get("/health")
async def health():
    return {"ok": True}


async def _worker_loop():
    while True:
        url = await asyncio.to_thread(get_queue().pop)
        if url is None:
            await asyncio.sleep(3)
            continue
        logger.info("处理链接: %s", url)
        try:
            note = await process_link(url)
            logger.info("完成: %s", note)
        except Exception:
            logger.exception("处理失败: %s", url)
