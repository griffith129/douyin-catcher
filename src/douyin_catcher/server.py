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


class SyncBody(BaseModel):
    conv_ids: list[str] | None = None


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
        "conversations": pool.get("conversations", {}),
        "last_seq": pool.get("last_seq", 0),
        "updated_at": pool.get("updated_at", ""),
    }


@app.post("/inbox/sync")
async def inbox_sync(body: SyncBody | None = None):
    try:
        result = await sync_inbox(
            _pool_path(), conv_ids=body.conv_ids if body else None
        )
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
  body { font-family: system-ui, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 16px; color: #1a1a1a; }
  h1 { font-size: 20px; }
  .bar { display: flex; gap: 12px; align-items: center; margin: 16px 0; }
  button { padding: 6px 14px; cursor: pointer; }
  .conv { border: 1px solid #ddd; border-radius: 10px; margin: 12px 0; overflow: hidden; }
  .conv-head { display: flex; gap: 10px; align-items: center; padding: 12px 14px; background: #f7f7f8; cursor: pointer; user-select: none; }
  .conv-head:hover { background: #f0f0f2; }
  .conv-head input { width: 18px; height: 18px; }
  .caret { display: inline-block; transition: transform .15s; font-size: 12px; color: #666; }
  .conv.open .caret { transform: rotate(90deg); }
  .conv-name { font-weight: 700; font-size: 15px; flex: 1; }
  .conv-count { color: #888; font-size: 13px; }
  .conv-body { display: none; padding: 4px 12px 12px; }
  .conv.open .conv-body { display: block; }
  .item { display: flex; gap: 10px; padding: 9px 8px; border-bottom: 1px solid #f0f0f0; align-items: center; }
  .item:last-child { border-bottom: none; }
  .item input { width: 17px; height: 17px; }
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
<p class="muted">流程：① 点「从对话同步」拉取采集台里的对话框 → ② 勾选对话框展开 → ③ 勾选视频标题 → ④ 批量处理（转写+整理+自动进 Notion）</p>
<div class="bar">
  <button onclick="syncPool()">🔄 从对话同步</button>
  <button onclick="submitSelected()">▶️ 批量处理选中项</button>
  <span id="meta" class="muted"></span>
</div>
<div id="list"></div>
<script>
let links = {}, convs = {};

async function refresh() {
  const r = await fetch('/inbox/api'); const d = await r.json();
  links = d.links || {};
  convs = d.conversations || {};
  document.getElementById('meta').textContent =
    `共 ${Object.keys(links).length} 条 · ${Object.keys(convs).length} 个对话框 · 更新于 ${d.updated_at || '-'}`;
  render();
}

function esc(s) { return (s || '').replace(/</g, '&lt;'); }

function groupByConv() {
  const groups = {};
  for (const [url, it] of Object.entries(links)) {
    const cid = it.conv_id || '_legacy';
    (groups[cid] = groups[cid] || []).push([url, it]);
  }
  for (const cid of Object.keys(groups)) {
    groups[cid].sort((a, b) => (b[1].seq || 0) - (a[1].seq || 0));
  }
  // 对话框按其最新视频 seq 降序
  return Object.entries(groups).sort((a, b) =>
    (b[1][0]?.[1].seq || 0) - (a[1][0]?.[1].seq || 0));
}

function render() {
  const el = document.getElementById('list');
  const groups = groupByConv();
  if (!groups.length) {
    el.innerHTML = '<p class="muted">池子是空的——先点「从对话同步」，或直接 POST /link 投递。</p>';
    return;
  }
  el.innerHTML = groups.map(([cid, items]) => {
    const meta = convs[cid] || {};
    const name = cid === '_legacy' ? '（未分组 / 历史导入）' : (meta.name || cid);
    const shown = items.slice(0, 100);
    const rows = shown.map(([url, it]) => `
      <div class="item">
        <input type="checkbox" class="pick" data-url="${url}" ${it.status === 'pending' ? '' : 'disabled'}>
        <div class="url">
          <div class="title">${esc(it.title || '（标题待处理时补全）')}</div>
          <div class="muted">${esc(it.author || '')} · <a href="${url}" target="_blank">打开视频</a> · 收录于 ${it.added_at || '-'}</div>
        </div>
        <span class="status ${it.status}">${it.status}</span>
      </div>`).join('');
    const more = items.length > shown.length
      ? `<p class="muted" style="padding:0 8px">仅显示最近 100 条（该对话共 ${items.length} 条）。</p>` : '';
    return `
      <div class="conv" data-cid="${cid}">
        <div class="conv-head" onclick="toggleConv(this)">
          <input type="checkbox" class="pick-conv" onclick="event.stopPropagation(); toggleConvVideos(this)">
          <span class="caret">▶</span>
          <span class="conv-name">${esc(name)}</span>
          <span class="conv-count">${items.length} 条视频${meta.last_seq ? ` · seq ${meta.last_seq}` : ''}</span>
        </div>
        <div class="conv-body">${rows}${more}</div>
      </div>`;
  }).join('');
}

function toggleConv(head) {
  head.parentElement.classList.toggle('open');
}

function toggleConvVideos(box) {
  const conv = box.closest('.conv');
  conv.classList.add('open');
  conv.querySelectorAll('.pick:not(:disabled)').forEach(b => b.checked = box.checked);
}

async function syncPool() {
  const btn = event.target; btn.disabled = true; btn.textContent = '⏳ 同步中...';
  try {
    const r = await fetch('/inbox/sync', {method: 'POST'});
    const d = await r.json();
    if (!r.ok) { alert('同步失败: ' + (d.detail || '')); return; }
    alert(`同步完成：新增 ${d.added} 条 · 共 ${d.total} 条 · ${d.conversations} 个对话框`);
  } finally { btn.disabled = false; btn.textContent = '🔄 从对话同步'; }
  refresh();
}

async function submitSelected() {
  const urls = [...document.querySelectorAll('.pick:checked')].map(b => b.dataset.url);
  if (!urls.length) { alert('请先勾选要处理的视频'); return; }
  const r = await fetch('/inbox/select', {method: 'POST',
    headers: {'Content-Type': 'application/json'}, body: JSON.stringify({urls})});
  const d = await r.json();
  alert(`已入队 ${d.queued} 条，后台开始处理（转写 → 整理 → 自动进 Notion）`);
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
