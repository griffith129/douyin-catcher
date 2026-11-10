"""Demo 体验层：两个功能扩展方案的可交互验证入口。

- /demo      方案对比 hub
- /demo/v1   方案1（1E+2B+2C+3B）：本地「笔记库」检索 + 批次报告
- /demo/v2   方案2（1A+2A+3F）：Notion database 体验入口
- /demo/api  demo 数据（索引/分类/批次/元信息）

只读模块，不改动 MVP 任何路径；数据文件不存在时返回空结构。
"""

import json
from pathlib import Path

from fastapi.responses import HTMLResponse

from .note_index import load_index
from .batch_report import list_batches

_INDEX_FILE = Path("data/note_index.json")
_TAXONOMY_FILE = Path("data/categories.json")
_BATCHES_FILE = Path("data/batches.json")
_META_FILE = Path("data/demo_meta.json")


def _demo_payload() -> dict:
    categories: dict = {}
    if _TAXONOMY_FILE.exists():
        categories = json.loads(_TAXONOMY_FILE.read_text(encoding="utf-8")).get("categories", {})
    meta: dict = {}
    if _META_FILE.exists():
        meta = json.loads(_META_FILE.read_text(encoding="utf-8"))
    return {
        "index": load_index(_INDEX_FILE),
        "categories": categories,
        "batches": list_batches(_BATCHES_FILE),
        "meta": meta,
    }


_CSS = """
:root{--bg:#f7f7f5;--card:#fff;--line:#e5e5e0;--ink:#1f1f1f;--muted:#777;
--accent:#2563eb;--accent-soft:#eff4ff;--green:#16a34a;--orange:#ea580c}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"PingFang SC","Microsoft YaHei",system-ui,sans-serif;background:var(--bg);color:var(--ink);line-height:1.6}
.wrap{max-width:1080px;margin:0 auto;padding:28px 20px 60px}
h1{font-size:22px;margin-bottom:4px}
.sub{color:var(--muted);font-size:13px;margin-bottom:20px}
.cards{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px;display:block;color:inherit;text-decoration:none;transition:.15s}
.card:hover{border-color:var(--accent);box-shadow:0 2px 12px rgba(37,99,235,.08)}
.card h2{font-size:16px;margin-bottom:8px}
.card p{font-size:13px;color:var(--muted)}
.tag{display:inline-block;font-size:11px;background:var(--accent-soft);color:var(--accent);border-radius:6px;padding:1px 8px;margin:2px 4px 2px 0}
.topbar{display:flex;align-items:center;gap:12px;margin-bottom:16px}
.topbar a{font-size:13px;color:var(--accent);text-decoration:none}
.toolbar{display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap}
input[type=search]{flex:1;min-width:220px;padding:9px 12px;border:1px solid var(--line);border-radius:8px;font-size:14px;background:#fff}
.layout{display:grid;grid-template-columns:220px 1fr;gap:16px;align-items:start}
.sidenav{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px;position:sticky;top:12px}
.cat{margin:2px 0}
.cat-head{display:flex;justify-content:space-between;align-items:center;padding:7px 8px;border-radius:7px;cursor:pointer;font-size:13px;font-weight:600}
.cat-head:hover{background:var(--accent-soft)}
.cat-head.active{background:var(--accent);color:#fff}
.cat-head .n{font-size:11px;font-weight:400;opacity:.75}
.subs{padding-left:10px;display:none}
.subs.open{display:block}
.sub-item{font-size:12px;color:var(--muted);padding:4px 8px;border-radius:6px;cursor:pointer}
.sub-item:hover{background:var(--accent-soft);color:var(--accent)}
.sub-item.active{color:var(--accent);font-weight:600}
.count{font-size:11px;color:var(--muted);margin:10px 8px 6px}
.list{display:flex;flex-direction:column;gap:10px}
.item{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.item h3{font-size:14px;margin-bottom:4px}
.item h3 a{color:var(--ink);text-decoration:none}
.item h3 a:hover{color:var(--accent)}
.meta-row{font-size:12px;color:var(--muted);display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.chip{font-size:11px;border-radius:5px;padding:1px 7px;background:var(--accent-soft);color:var(--accent)}
.chip.sub{background:#f0fdf4;color:var(--green)}
.chip.batch{background:#fff7ed;color:var(--orange)}
mark{background:#fde68a;padding:0 1px}
.preview{font-size:13px;color:#444;margin-top:8px;display:none;border-top:1px dashed var(--line);padding-top:8px}
.preview.open{display:block}
.toggle-btn{font-size:12px;color:var(--accent);background:none;border:none;cursor:pointer;padding:0;margin-top:6px}
.batch-card{background:var(--card);border:1px solid var(--line);border-radius:10px;margin-bottom:12px;overflow:hidden}
.batch-head{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;cursor:pointer}
.batch-head:hover{background:var(--accent-soft)}
.batch-head b{font-size:14px}
.batch-head .m{font-size:12px;color:var(--muted)}
.batch-body{display:none;border-top:1px solid var(--line);padding:10px 16px 14px}
.batch-body.open{display:block}
.cat-group{margin:8px 0 4px;font-size:13px;font-weight:600;color:var(--accent)}
.batch-item{display:flex;justify-content:space-between;gap:10px;font-size:13px;padding:4px 0;border-bottom:1px dashed var(--line)}
.batch-item:last-child{border-bottom:none}
.batch-item a{color:var(--ink);text-decoration:none}
.batch-item a:hover{color:var(--accent)}
.batch-item .links{white-space:nowrap;font-size:12px}
.batch-item .links a{color:var(--accent);margin-left:8px}
.empty{color:var(--muted);font-size:13px;padding:30px;text-align:center}
.link-list{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px;margin-bottom:14px}
.link-list h2{font-size:15px;margin-bottom:10px}
.link-list a{display:block;padding:9px 12px;border:1px solid var(--line);border-radius:8px;margin-bottom:8px;text-decoration:none;color:var(--ink);font-size:14px}
.link-list a:hover{border-color:var(--accent);color:var(--accent)}
.note{font-size:13px;color:var(--muted);margin-top:10px}
"""

_HUB = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>功能扩展 Demo 体验</title><style>__CSS__</style></head><body>
<div class="wrap">
<h1>功能扩展 Demo 体验</h1>
<p class="sub">两个方案的完整实现 demo，请分别体验后选择。数据：39 篇真实笔记 · 7 大类（含 LLM 自动新建 2 类）</p>
<div class="cards">
<a class="card" href="/demo/v1">
<h2>方案 1 · 本地工作台体验</h2>
<div><span class="tag">1E Notion库+本地索引双轨</span><span class="tag">2B 本地批次报告</span><span class="tag">2C Notion 更新日志</span><span class="tag">3B 受限分类</span></div>
<p>在浏览器里直接搜索/按分类树筛选全部笔记，回看历次更新批次；Notion 侧配更新日志页。适合"选择台为工作中心"的用法。</p>
</a>
<a class="card" href="/demo/v2">
<h2>方案 2 · Notion 内体验</h2>
<div><span class="tag">1A Database 化</span><span class="tag">2A 批次视图</span><span class="tag">3F 分类联动</span></div>
<p>全部体验在 Notion 内完成：知识库 database（39 行已分类）、「本次更新」筛选视图、「分类看板」分组视图。适合"Notion 为唯一入口"的用法。</p>
</a>
</div>
</div></body></html>"""

_V1 = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>方案1 · 本地笔记库</title><style>__CSS__</style></head><body>
<div class="wrap">
<div class="topbar"><h1>方案 1 · 本地笔记库（1E + 2B）</h1><a href="/demo">← 返回</a><a href="/demo/v2">看方案2 →</a></div>
<p class="sub">搜索与分类筛选拉取本地索引（实时）；点击笔记标题可跳 Notion 或抖音来源。底部队列回看历次批次（2B）。</p>
<div class="toolbar"><input id="q" type="search" placeholder="搜索标题 / 作者 / 笔记内容…" oninput="render()"></div>
<div class="layout">
<div class="sidenav" id="cats"></div>
<div><div class="count" id="count"></div><div class="list" id="list"></div></div>
</div>
<div style="margin-top:28px"><h1 style="font-size:18px">批次报告（2B）</h1>
<p class="sub">每次从选择台批量整理后生成一个批次，点击展开查看该批视频及其分类。</p>
<div id="batches"></div></div>
</div>
<script>
let DATA=null, cat=null, sub=null;
const esc=s=>s.replace(/[&<>"]/g,c=>{{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]});
const hl=(s,q)=>{{if(!q)return esc(s);const i=s.toLowerCase().indexOf(q.toLowerCase());if(i<0)return esc(s);
return esc(s.slice(0,i))+'<mark>'+esc(s.slice(i,i+q.length))+'</mark>'+esc(s.slice(i+q.length));}};
async function init(){{
 DATA=await (await fetch('/demo/api')).json();
 const tree=document.getElementById('cats');
 let html='<div class="cat"><div class="cat-head" data-c="" onclick="pickCat(this)"><span>全部</span><span class="n">'+DATA.index.length+'</span></div></div>';
 for(const [c,subs] of Object.entries(DATA.categories)){{
  const n=DATA.index.filter(e=>e.category===c).length;
  html+=`<div class="cat"><div class="cat-head" data-c="${{esc(c)}}" onclick="pickCat(this)"><span>${{esc(c)}}</span><span class="n">${{n}}</span></div>`;
  html+='<div class="subs">'+subs.map(s=>`<div class="sub-item" data-c="${{esc(c)}}" data-s="${{esc(s)}}" onclick="pickSub(this)">${{esc(s)}}</div>`).join('')+'</div></div>';
 }}
 tree.innerHTML=html;
 render();
}}
function pickCat(el){{
 document.querySelectorAll('.cat-head').forEach(x=>x.classList.remove('active'));
 document.querySelectorAll('.sub-item').forEach(x=>x.classList.remove('active'));
 if(cat===el.dataset.c){{cat=null;render();return;}}
 el.classList.add('active');cat=el.dataset.c;sub=null;
 document.querySelectorAll('.cat-head').forEach(h=>{{if(h.dataset.c===cat){{const s=h.parentElement.querySelector('.subs');if(s)s.classList.add('open');}}else{{const s=h.parentElement.querySelector('.subs');if(s)s.classList.remove('open');}}}});
 render();}}
function pickSub(el){{
 document.querySelectorAll('.sub-item').forEach(x=>x.classList.remove('active'));
 el.classList.add('active');sub=(sub===el.dataset.s)?null:el.dataset.s;render();}}
function render(){{
 const q=document.getElementById('q').value.trim();
 let items=DATA.index.filter(e=>
  (!cat||e.category===cat)&&(!sub||e.subcategory===sub)&&
  (!q||(e.title+e.author+(e.preview||'')).toLowerCase().includes(q.toLowerCase())));
 document.getElementById('count').textContent=`共 ${{items.length}} 篇`+(q?`（匹配"${{q}}"）`:'');
 document.getElementById('list').innerHTML=items.map(e=>`
  <div class="item"><h3><a href="${{e.notion_url||e.source_url}}" target="_blank">${{hl(e.title,q)}}</a></h3>
  <div class="meta-row"><span class="chip">${{esc(e.category||'未分类')}}</span>
  <span class="chip sub">${{esc(e.subcategory||'-')}}</span>
  <span>${{hl(e.author||'',q)}}</span><span>${{esc(e.date)}}</span>
  <a href="${{e.source_url}}" target="_blank" style="color:var(--accent);font-size:12px">抖音来源↗</a></div>
  <button class="toggle-btn" onclick="this.nextElementSibling.classList.toggle('open')">笔记预览 ▾</button>
  <div class="preview">${{hl(e.preview||'（无预览）',q)}}…</div></div>`).join('')
  ||'<div class="empty">没有匹配的笔记</div>';}}
function renderBatches(){{
 document.getElementById('batches').innerHTML=DATA.batches.map(b=>{{
  const groups={{}};b.items.forEach(i=>{{(groups[i.category||'未分类']=groups[i.category||'未分类']||[]).push(i)}});
  return `<div class="batch-card"><div class="batch-head" onclick="this.nextElementSibling.classList.toggle('open')">
  <b>${{esc(b.batch_id)}}</b><span class="m">${{esc(b.created_at)}} · ${{b.items.length}} 篇 · 点击展开</span></div>
  <div class="batch-body">${{Object.keys(groups).sort().map(c=>`<div class="cat-group">${{esc(c)}}（${{groups[c].length}}）</div>`+
   groups[c].map(i=>`<div class="batch-item"><a href="${{i.notion_url||'#'}}" target="_blank">${{esc(i.title)}}</a>
   <span class="links"><a href="${{i.notion_url||'#'}}" target="_blank">Notion↗</a></span></div>`).join('')).join('')}}</div></div>`;
 }}).join('')||'<div class="empty">暂无批次记录</div>';}}
init();document.addEventListener('DOMContentLoaded',()=>setTimeout(renderBatches,300));
</script></body></html>"""

_V2 = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>方案2 · Notion 内体验</title><style>__CSS__</style></head><body>
<div class="wrap">
<div class="topbar"><h1>方案 2 · Notion 内体验（1A + 2A）</h1><a href="/demo">← 返回</a><a href="/demo/v1">看方案1 →</a></div>
<p class="sub">全部功能在 Notion 内完成：打开下面的链接逐一体验。database 已含 39 行真实分类数据（批次 demo-2026-11-10）。</p>
<div class="link-list">
<h2>体验入口</h2>
<a href="__DB__" target="_blank">📚 抖音知识库（Demo）— database 主视图：试试顶部分类/批次下拉筛选、按列排序、右上角搜索</a>
<a href="__DB__" target="_blank">🆕 「本次更新」视图 — database 顶栏切换到该视图（2A）：只看最近一批入库的视频</a>
<a href="__DB__" target="_blank">🗂 「分类看板」视图 — database 顶栏切换到该视图：按大类分列的看板（分类浏览 b）</a>
<a href="__LOG__" target="_blank">📜 更新日志（Demo）— 父页面下的日志页：按批次→大类分组列出视频（方案1 的 2C，此处供对比）</a>
</div>
<div class="link-list">
<h2>体验要点（对比方案1时关注）</h2>
<p class="note">① 检索手感：Notion 右上角搜索 vs 本地方案1的即时搜索框<br>
② 分类浏览：看板分组拖拽 vs 本地方案1的分类树点选<br>
③ 更新回看：「本次更新」视图 vs 本地方案1的批次报告卡片<br>
④ 分类元数据（分类/细类/批次/作者/日期）都是 property，未来可任意加视图、图表、自动化</p>
</div>
</div></body></html>"""


def register(app):
    @app.get("/demo/api")
    async def demo_api():
        return _demo_payload()

    @app.get("/demo", response_class=HTMLResponse)
    async def demo_hub():
        return _HUB.replace("__CSS__", _CSS)

    @app.get("/demo/v1", response_class=HTMLResponse)
    async def demo_v1():
        return _V1.replace("__CSS__", _CSS)

    @app.get("/demo/v2", response_class=HTMLResponse)
    async def demo_v2():
        meta = _demo_payload()["meta"]
        return (
            _V2.replace("__CSS__", _CSS)
            .replace("__DB__", meta.get("database_url", "https://www.notion.so"))
            .replace("__LOG__", meta.get("log_url", "https://www.notion.so"))
        )
