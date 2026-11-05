"""FastAPI 接收服务：POST /link 入队，/inbox 选择台，后台 worker 消费。"""

import asyncio
import contextlib
import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .config import config
from .inbox import load_pool, sync_inbox
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


def _pool_path() -> Path:
    return Path(config.INBOX_POOL_FILE)


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


class SelectBody(BaseModel):
    urls: list[str]


@app.post("/link")
async def receive_link(body: LinkBody):
    if not extract_urls(body.text):
        raise HTTPException(status_code=400, detail="分享文本中没有链接")
    queued = get_queue().push(body.text)
    return {"ok": True, "queued": queued}


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/inbox/api")
async def inbox_api():
    pool = load_pool(_pool_path())
    return {
        "links": pool.get("links", {}),
        "last_seq": pool.get("last_seq", 0),
        "updated_at": pool.get("updated_at", ""),
    }


@app.post("/inbox/sync")
async def inbox_sync():
    try:
        result = await sync_inbox(_pool_path())
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"采集服务不可达: {e}")
    return result


@app.post("/inbox/select")
async def inbox_select(body: SelectBody):
    pool = load_pool(_pool_path())
    queued = 0
    for url in body.urls:
        item = pool["links"].get(url)
        if not item or item.get("status") != "pending":
            continue
        if get_queue().push(url):
            item["status"] = "queued"
            item["queued_at"] = time.strftime("%Y-%m-%d %H:%M")
            queued += 1
    if queued:
        pool["updated_at"] = time.strftime("%Y-%m-%d %H:%M")
        _pool_path().write_text(json.dumps(pool, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "queued": queued}


_INBOX_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>douyin-catcher 视频选择台</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 860px; margin: 40px auto; padding: 0 16px; color: #1a1a1a; }
  h1 { font-size: 20px; }
  .bar { display: flex; gap: 12px; align-items: center; margin: 16px 0; }
  button { padding: 6px 14px; cursor: pointer; }
  .item { display: flex; gap: 10px; padding: 10px 12px; border: 1px solid #ddd; border-radius: 8px; margin: 8px 0; align-items: center; }
  .item input { width: 18px; height: 18px; }
  .url { word-break: break-all; flex: 1; font-size: 14px; }
  .title { font-size: 14px; font-weight: 600; margin-bottom: 2px; }
  .status { font-size: 12px; padding: 2px 8px; border-radius: 10px; background: #eee; }
  .status.pending { background: #fff3cd; }
  .status.queued { background: #d4edda; }
  .muted { color: #888; font-size: 13px; }
</style>
</head>
<body>
<h1>📥 抖音视频选择台</h1>
<div class="bar">
  <button onclick="syncPool()">🔄 从对话同步</button>
  <button onclick="toggleAll()">全选/反选</button>
  <button onclick="submitSelected()">▶️ 批量处理选中项</button>
  <span id="meta" class="muted"></span>
</div>
<div id="list"></div>
<script>
let links = {};
async function refresh() {
  const r = await fetch('/inbox/api'); const d = await r.json();
  links = d.links || {};
  document.getElementById('meta').textContent =
    `共 ${Object.keys(links).length} 条 · 池子更新于 ${d.updated_at || '-'} · last_seq ${d.last_seq}`;
  render();
}
function render() {
  const el = document.getElementById('list');
  const entries = Object.entries(links).sort((a, b) => (b[1].seq || 0) - (a[1].seq || 0));
  const shown = entries.slice(0, 100);
  el.innerHTML = shown.length ? shown.map(([url, it]) => `
    <div class="item">
      <input type="checkbox" class="pick" data-url="${url}" ${it.status === 'pending' ? '' : 'disabled'}>
      <div class="url">
        <div class="title">${(it.title || '（标题待处理时补全）').replace(/</g, '&lt;')}</div>
        <div class="muted"><a href="${url}" target="_blank">${url}</a> · 消息 seq ${it.seq ?? '-'} · 收录于 ${it.added_at || '-'}</div>
      </div>
      <span class="status ${it.status}">${it.status}</span>
    </div>`).join('')
    : '<p class="muted">池子是空的——先点「从对话同步」，或直接 POST /link 投递。</p>';
  if (entries.length > shown.length) {
    el.insertAdjacentHTML('beforeend', `<p class="muted">仅显示最近 100 条（共 ${entries.length} 条已入池，历史仍在池中可用）。</p>`);
  }
}
function toggleAll() {
  const boxes = [...document.querySelectorAll('.pick:not(:disabled)')];
  const allOn = boxes.length && boxes.every(b => b.checked);
  boxes.forEach(b => b.checked = !allOn);
}
async function syncPool() {
  const r = await fetch('/inbox/sync', {method: 'POST'});
  const d = await r.json();
  if (!r.ok) { alert('同步失败: ' + (d.detail || '')); return; }
  alert(`同步完成：新增 ${d.added} 条（共 ${d.total} 条）`);
  refresh();
}
async function submitSelected() {
  const urls = [...document.querySelectorAll('.pick:checked')].map(b => b.dataset.url);
  if (!urls.length) { alert('请先勾选要处理的视频'); return; }
  const r = await fetch('/inbox/select', {method: 'POST',
    headers: {'Content-Type': 'application/json'}, body: JSON.stringify({urls})});
  const d = await r.json();
  alert(`已入队 ${d.queued} 条，后台开始处理`);
  refresh();
}
refresh();
</script>
</body>
</html>"""


@app.get("/inbox", response_class=HTMLResponse)
async def inbox_page():
    return HTMLResponse(_INBOX_PAGE)


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
