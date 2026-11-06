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
  .bar { display: flex; gap: 12px; align-items: center; margin: 16px 0; flex-wrap: wrap; }
  button { padding: 6px 14px; cursor: pointer; }
  #searchPanel { display: none; border: 1px solid #ddd; border-radius: 10px; padding: 12px 14px; margin-bottom: 14px; background: #fafafa; }
  #searchPanel.open { display: block; }
  #searchInput { width: 100%; box-sizing: border-box; padding: 8px 10px; border: 1px solid #ccc; border-radius: 8px; font-size: 14px; }
  .chips { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; align-items: center; }
  .chip { cursor: pointer; font-size: 13px; padding: 4px 14px; border-radius: 14px; border: 1px solid #ccc; background: #fff; user-select: none; }
  .chip.on { background: #e8f0fe; border-color: #378ADD; color: #185FA5; }
  .conv { border: 1px solid #ddd; border-radius: 10px; margin: 12px 0; overflow: hidden; }
  .conv.hide { display: none; }
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
  .item.hide { display: none; }
  .item input { width: 17px; height: 17px; }
  .url { word-break: break-all; flex: 1; font-size: 14px; min-width: 0; }
  .title { font-size: 14px; font-weight: 600; margin-bottom: 2px; }
  .title mark { background: #ffe9a8; padding: 0 1px; }
  .status { font-size: 12px; padding: 2px 8px; border-radius: 10px; background: #eee; white-space: nowrap; }
  .status.pending { background: #fff3cd; }
  .status.queued { background: #d4edda; }
  .muted { color: #888; font-size: 13px; }
</style>
</head>
<body>
<h1>📥 抖音视频选择台</h1>
<p class="muted">流程：① 「从对话同步」拉取采集台对话框 → ② 勾选对话框并展开 → ③ 勾选视频标题 → ④ 批量处理（转写+整理+自动进 Notion）</p>
<div class="bar">
  <button onclick="syncPool()">🔄 从对话同步</button>
  <button id="searchToggle" onclick="toggleSearch()">🔍 搜索</button>
  <button onclick="submitSelected()">▶️ 批量处理选中项 (<span id="selN">0</span>)</button>
  <span id="meta" class="muted"></span>
</div>
<div id="searchPanel">
  <input id="searchInput" placeholder="搜索视频标题 / 作者 / 对话框名…（在全部已同步对话框内过滤）" oninput="render()">
  <div class="chips">
    <span class="chip" id="chipPending" onclick="toggleChip(this)">仅待处理</span>
    <span class="muted">搜索范围：已同步的全部对话框</span>
    <span class="muted" id="matchInfo"></span>
    <span style="flex:1"></span>
    <span class="chip" onclick="clearSearch()">✕ 清空并收起</span>
  </div>
</div>
<div id="list"></div>
<script>
let links = {}, convs = {};
const selected = new Set();   // 跨渲染保留勾选
let query = '', onlyPending = false, searchOpen = false;

async function refresh() {
  const r = await fetch('/inbox/api'); const d = await r.json();
  links = d.links || {};
  convs = d.conversations || {};
  document.getElementById('meta').textContent =
    `共 ${Object.keys(links).length} 条 · ${Object.keys(convs).length} 个对话框 · 更新于 ${d.updated_at || '-'}`;
  render();
}

function esc(s) { return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;'); }
function hl(s) {
  s = esc(s);
  if (!query) return s;
  const i = s.toLowerCase().indexOf(query.toLowerCase());
  if (i < 0) return s;
  return s.slice(0, i) + '<mark>' + s.slice(i, i + query.length) + '</mark>' + s.slice(i + query.length);
}

function groupByConv() {
  const groups = {};
  for (const [url, it] of Object.entries(links)) {
    const cid = it.conv_id || '_legacy';
    (groups[cid] = groups[cid] || []).push([url, it]);
  }
  for (const cid of Object.keys(groups))
    groups[cid].sort((a, b) => (b[1].seq || 0) - (a[1].seq || 0));
  return Object.entries(groups).sort((a, b) =>
    (b[1][0]?.[1].seq || 0) - (a[1][0]?.[1].seq || 0));
}

function rowMatches(it, cid, cname) {
  if (onlyPending && it.status !== 'pending') return false;
  if (!query) return true;
  const q = query.toLowerCase();
  return (it.title || '').toLowerCase().includes(q)
      || (it.author || '').toLowerCase().includes(q)
      || (cname || '').toLowerCase().includes(q);
}

function render() {
  query = document.getElementById('searchInput').value.trim();
  const el = document.getElementById('list');
  const groups = groupByConv();
  if (!groups.length) {
    el.innerHTML = '<p class="muted">池子是空的——先点「从对话同步」，或直接 POST /link 投递。</p>';
    return;
  }
  let totalMatch = 0, html = '';
  for (const [cid, items] of groups) {
    const meta = convs[cid] || {};
    const name = cid === '_legacy' ? '（未分组 / 历史导入）' : (meta.name || cid);
    const matched = items.filter(([, it]) => rowMatches(it, cid, name));
    totalMatch += matched.length;
    const convNameHit = query && name.toLowerCase().includes(query.toLowerCase());
    const showConv = matched.length > 0 || (convNameHit && !onlyPending);
    if (!showConv) continue;
    const shown = matched.slice(0, 100);
    const rows = shown.map(([url, it]) => `
      <div class="item">
        <input type="checkbox" class="pick" data-url="${url}" ${selected.has(url) ? 'checked' : ''} ${it.status === 'pending' ? '' : 'disabled'} onchange="pickOne(this)">
        <div class="url">
          <div class="title">${hl(it.title || '（标题待处理时补全）')}</div>
          <div class="muted">${hl(it.author || '')} · <a href="${url}" target="_blank">打开视频</a> · ${it.added_at || ''}</div>
        </div>
        <span class="status ${it.status}">${it.status}</span>
      </div>`).join('');
    const more = matched.length > shown.length
      ? `<p class="muted" style="padding:0 8px">仅显示前 100 条匹配（该对话共 ${matched.length} 条匹配）。</p>` : '';
    const matchTip = query ? ` · 匹配 ${matched.length}/${items.length}` : '';
    html += `
      <div class="conv ${query ? 'open' : ''}" data-cid="${cid}">
        <div class="conv-head" onclick="toggleConv(this)">
          <input type="checkbox" class="pick-conv" onclick="event.stopPropagation(); toggleConvVideos(this)">
          <span class="caret">▶</span>
          <span class="conv-name">${hl(name)}</span>
          <span class="conv-count">${items.length} 条视频${matchTip}${meta.last_seq ? ` · seq ${meta.last_seq}` : ''}</span>
        </div>
        <div class="conv-body">${rows}${more}</div>
      </div>`;
  }
  el.innerHTML = html || '<p class="muted">没有匹配的视频——调整搜索词或筛选条件。</p>';
  document.getElementById('matchInfo').textContent =
    searchOpen ? `匹配 ${totalMatch} / ${Object.keys(links).length} 条` : '';
  document.getElementById('selN').textContent = selected.size;
}

function toggleConv(head) { head.parentElement.classList.toggle('open'); }

function toggleConvVideos(box) {
  const conv = box.closest('.conv');
  conv.classList.add('open');
  conv.querySelectorAll('.pick:not(:disabled)').forEach(b => {
    b.checked = box.checked;
    box.checked ? selected.add(b.dataset.url) : selected.delete(b.dataset.url);
  });
  updateSelN();
}

function pickOne(cb) { cb.checked ? selected.add(cb.dataset.url) : selected.delete(cb.dataset.url); updateSelN(); }
function updateSelN() { document.getElementById('selN').textContent = selected.size; }

function toggleSearch() {
  searchOpen = !searchOpen;
  document.getElementById('searchPanel').classList.toggle('open', searchOpen);
  document.getElementById('searchToggle').style.background = searchOpen ? '#e8f0fe' : '';
  if (!searchOpen) clearSearch(true);
  else document.getElementById('searchInput').focus();
}

function toggleChip(el) {
  el.classList.toggle('on');
  onlyPending = el.classList.contains('on');
  render();
}

function clearSearch(keepOpen) {
  query = ''; onlyPending = false;
  document.getElementById('searchInput').value = '';
  document.getElementById('chipPending').classList.remove('on');
  if (!keepOpen) { searchOpen = false; document.getElementById('searchPanel').classList.remove('open'); document.getElementById('searchToggle').style.background = ''; }
  render();
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
  if (!selected.size) { alert('请先勾选要处理的视频'); return; }
  const r = await fetch('/inbox/select', {method: 'POST',
    headers: {'Content-Type': 'application/json'}, body: JSON.stringify({urls: [...selected]})});
  const d = await r.json();
  alert(`已入队 ${d.queued} 条，后台开始处理（转写 → 整理 → 自动进 Notion）`);
  selected.clear(); updateSelN();
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
