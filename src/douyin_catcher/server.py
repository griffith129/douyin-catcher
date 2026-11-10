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
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import config
from .demo import register as register_demo
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
register_demo(app)  # /demo 体验层（只读，不影响 MVP 路由）

# antd UMD 静态资源（本地化，页面离线可用）
_STATIC_DIR = Path(__file__).parent / "static"
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


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
<link rel="stylesheet" href="/static/antd/reset.min.css">
<script src="/static/antd/react.production.min.js"></script>
<script src="/static/antd/react-dom.production.min.js"></script>
<script src="/static/antd/dayjs.min.js"></script>
<script src="/static/antd/antd.min.js"></script>
<style>
  body { background: #f5f5f5; }
  .page { max-width: 980px; margin: 0 auto; padding: 28px 20px 60px; }
  .title-mark { background: #ffe9a8; padding: 0 1px; }
</style>
</head>
<body>
<div id="root"></div>
<script>
const h = React.createElement;
const { ConfigProvider, Button, Input, Tag, CheckableTag, Checkbox, Collapse, List,
        Badge, Space, Typography, message, Empty } = antd;
const zhCN = (antd.locales && antd.locales.zh_CN) || undefined;
const { Title, Text } = Typography;

const STATUS_COLOR = { pending: 'gold', queued: 'green', done: 'default', failed: 'red' };

function esc(s) { return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;'); }
function hl(s, query) {
  s = esc(s);
  if (!query) return s;
  const i = s.toLowerCase().indexOf(query.toLowerCase());
  if (i < 0) return s;
  return s.slice(0, i) + '<mark class="title-mark">' + s.slice(i, i + query.length) + '</mark>' + s.slice(i + query.length);
}

function App() {
  const [links, setLinks] = React.useState({});
  const [convs, setConvs] = React.useState({});
  const [metaText, setMetaText] = React.useState('');
  const [selected, setSelected] = React.useState(new Set());
  const [query, setQuery] = React.useState('');
  const [onlyPending, setOnlyPending] = React.useState(false);
  const [searchOpen, setSearchOpen] = React.useState(false);
  const [syncing, setSyncing] = React.useState(false);
  const [openKeys, setOpenKeys] = React.useState([]);
  const selectedRef = React.useRef(selected);
  selectedRef.current = selected;

  async function refresh() {
    const r = await fetch('/inbox/api'); const d = await r.json();
    const lk = d.links || {};
    setLinks(lk);
    setConvs(d.conversations || {});
    setMetaText(`共 ${Object.keys(lk).length} 条 · ${Object.keys(d.conversations || {}).length} 个对话框 · 更新于 ${d.updated_at || '-'}`);
  }

  function pickOne(url, checked) {
    const next = new Set(selectedRef.current);
    checked ? next.add(url) : next.delete(url);
    setSelected(next);
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
      (b[1][0] && b[1][0][1].seq || 0) - (a[1][0] && a[1][0][1].seq || 0));
  }

  function rowMatches(it, cname) {
    if (onlyPending && it.status !== 'pending') return false;
    if (!query) return true;
    const q = query.toLowerCase();
    return (it.title || '').toLowerCase().includes(q)
        || (it.author || '').toLowerCase().includes(q)
        || (cname || '').toLowerCase().includes(q);
  }

  function toggleConvVideos(cid, matched, checked) {
    const next = new Set(selectedRef.current);
    matched.forEach(([url, it]) => {
      if (it.status === 'pending') checked ? next.add(url) : next.delete(url);
    });
    setSelected(next);
    setOpenKeys(keys => keys.includes(cid) ? keys : [...keys, cid]);
  }

  async function syncPool() {
    setSyncing(true);
    try {
      const r = await fetch('/inbox/sync', { method: 'POST' });
      const d = await r.json();
      if (!r.ok) { message.error('同步失败: ' + (d.detail || '')); return; }
      message.success(`同步完成：新增 ${d.added} 条 · 共 ${d.total} 条 · ${d.conversations} 个对话框`);
    } finally { setSyncing(false); }
    refresh();
  }

  async function submitSelected() {
    if (!selected.size) { message.warning('请先勾选要处理的视频'); return; }
    const r = await fetch('/inbox/select', { method: 'POST',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ urls: [...selected] }) });
    const d = await r.json();
    message.success(`已入队 ${d.queued} 条，后台开始处理（转写 → 整理 → 自动进 Notion）`);
    setSelected(new Set());
    refresh();
  }

  React.useEffect(() => { refresh(); }, []);

  const groups = groupByConv();
  const convItems = [];
  let totalMatch = 0;
  const autoOpen = [];
  for (const [cid, items] of groups) {
    const cm = convs[cid] || {};
    const cname = cid === '_legacy' ? '（未分组 / 历史导入）' : (cm.name || cid);
    const matched = items.filter(([, it]) => rowMatches(it, cname));
    totalMatch += matched.length;
    const convNameHit = query && cname.toLowerCase().includes(query.toLowerCase());
    if (!(matched.length > 0 || (convNameHit && !onlyPending))) continue;
    autoOpen.push(cid);
    const shown = matched.slice(0, 100);
    const matchTip = query ? ` · 匹配 ${matched.length}/${items.length}` : '';
    const allPicked = shown.filter(([, it]) => it.status === 'pending').every(([url]) => selected.has(url)) && shown.some(([, it]) => it.status === 'pending');
    convItems.push({
      key: cid,
      label: h(Space, { size: 10 },
        h(Checkbox, {
          checked: allPicked,
          disabled: !shown.some(([, it]) => it.status === 'pending'),
          onClick: e => e.stopPropagation(),
          onChange: e => toggleConvVideos(cid, matched, e.target.checked),
        }),
        h('span', { style: { fontWeight: 700, fontSize: 15 },
          dangerouslySetInnerHTML: { __html: hl(cname, query) } }),
        h(Text, { type: 'secondary', style: { fontSize: 12 } },
          `${items.length} 条视频${matchTip}${cm.last_seq ? ` · seq ${cm.last_seq}` : ''}`)
      ),
      children: h(React.Fragment, null,
        h(List, {
          size: 'small', dataSource: shown,
          locale: { emptyText: '没有匹配的视频——调整搜索词或筛选条件' },
          renderItem: ([url, it]) => h(List.Item, {
            key: url,
            actions: [h(Tag, { color: STATUS_COLOR[it.status] || 'default', style: { margin: 0 } }, it.status)],
          },
            h('div', { style: { display: 'flex', gap: 10, alignItems: 'flex-start', minWidth: 0 } },
              h(Checkbox, {
                checked: selected.has(url),
                disabled: it.status !== 'pending',
                onChange: e => pickOne(url, e.target.checked),
              }),
              h('div', { style: { minWidth: 0 } },
                h('div', { style: { fontSize: 14, fontWeight: 600 },
                  dangerouslySetInnerHTML: { __html: hl(it.title || '（标题待处理时补全）', query) } }),
                h(Text, { type: 'secondary', style: { fontSize: 12 } },
                  h('span', { dangerouslySetInnerHTML: { __html: hl(it.author || '', query) } }),
                  ' · ',
                  h('a', { href: url, target: '_blank', style: { color: '#1677ff' } }, '打开视频'),
                  it.added_at ? ` · ${it.added_at}` : '')
              )
            ))
        }),
        matched.length > shown.length
          ? h(Text, { type: 'secondary', style: { fontSize: 12, paddingLeft: 8 } },
              `仅显示前 100 条匹配（该对话共 ${matched.length} 条匹配）。`)
          : null
      ),
    });
  }

  const activeKeys = query ? autoOpen : openKeys;

  return h('div', { className: 'page' },
    h(Title, { level: 4, style: { marginTop: 0 } }, '📥 抖音视频选择台'),
    h(Alert_flow),
    h(Space, { wrap: true, style: { margin: '14px 0' } },
      h(Button, { type: 'primary', loading: syncing, onClick: syncPool }, '🔄 从对话同步'),
      h(Button, { type: searchOpen ? 'default' : 'text', onClick: () => {
        setSearchOpen(v => !v); if (searchOpen) { setQuery(''); setOnlyPending(false); }
      } }, '🔍 搜索'),
      h(Badge, { count: selected.size, color: '#1677ff' },
        h(Button, { type: 'primary', ghost: true, onClick: submitSelected }, '▶️ 批量处理选中项')),
      h(Text, { type: 'secondary', style: { fontSize: 12 } }, metaText)
    ),
    searchOpen && h('div', { style: { border: '1px solid #d9d9d9', borderRadius: 10, padding: '12px 14px', marginBottom: 14, background: '#fafafa' } },
      h(Input, {
        placeholder: '搜索视频标题 / 作者 / 对话框名…（在全部已同步对话框内过滤）',
        allowClear: true, value: query, autoFocus: true,
        onChange: e => setQuery(e.target.value.trim()), style: { marginBottom: 10 },
      }),
      h(Space, { wrap: true, size: 12 },
        h(CheckableTag, { checked: onlyPending, onChange: v => setOnlyPending(v) }, '仅待处理'),
        h(Text, { type: 'secondary', style: { fontSize: 12 } }, '搜索范围：已同步的全部对话框'),
        h(Text, { type: 'secondary', style: { fontSize: 12 } },
          searchOpen ? `匹配 ${totalMatch} / ${Object.keys(links).length} 条` : '')
      )
    ),
    convItems.length
      ? h(Collapse, {
          items: convItems, activeKey: activeKeys,
          onChange: keys => setOpenKeys(Array.isArray(keys) ? keys : [keys]),
          style: { background: '#fff' },
        })
      : h(Empty, { description: '池子是空的——先点「从对话同步」，或直接 POST /link 投递' })
  );
}

// 流程说明（antd Alert 展示）
function Alert_flow() {
  return h('div', {
    style: { background: '#e6f4ff', border: '1px solid #91caff', borderRadius: 8, padding: '8px 12px', fontSize: 13, color: '#1677ff' },
  }, '流程：① 「从对话同步」拉取采集台对话框 → ② 勾选对话框并展开 → ③ 勾选视频标题 → ④ 批量处理（转写+整理+自动进 Notion）');
}

ReactDOM.createRoot(document.getElementById('root')).render(
  h(ConfigProvider, { locale: zhCN }, h(App))
);
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
