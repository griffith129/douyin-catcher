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

_UX = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>UX 优化 Demo · 8 案体验</title><style>__CSS__
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.opt{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.opt h3{font-size:14px;margin-bottom:4px}
.opt p{font-size:12px;color:var(--muted);margin-bottom:8px}
.opt a{font-size:13px;color:var(--accent);text-decoration:none;font-weight:600}
.badge{display:inline-block;font-size:10px;border-radius:5px;padding:0 6px;margin-left:6px;vertical-align:1px}
.b-notion{background:#f0fdf4;color:var(--green)} .b-web{background:var(--accent-soft);color:var(--accent)}
h2.sec{font-size:16px;margin:26px 0 10px}
</style></head><body>
<div class="wrap">
<div class="topbar"><h1>UX 优化 Demo · 8 案体验</h1><a href="/demo">← 返回</a></div>
<p class="sub">功能A：分类下大量视频的直观浏览（标签+摘要）。功能B：本次更新视图的快速导读（标题跳文档/标签/概述卡）。</p>

<h2 class="sec">功能 A · 分类内大量视频浏览</h2>
<div class="grid2">
<div class="opt"><h3>A1 分类画廊<span class="badge b-notion">Notion</span></h3>
<p>Gallery 视图：卡片直接显示 标题+标签+概述（概述/标签已回填为 property），小卡片高密度滚动。规模：数百篇内舒适。</p>
<a href="__DB__" target="_blank">打开 database → 切到「A1 分类画廊」视图</a></div>
<div class="opt"><h3>A2 分类清单<span class="badge b-notion">Notion</span></h3>
<p>List 视图按细类分组折叠：密度最高，展开某细类即见该类全部行（标题+标签+概述），适合类别多、每类几十篇。</p>
<a href="__DB__" target="_blank">打开 database → 切到「A2 分类清单」视图</a></div>
<div class="opt"><h3>A3 细类看板<span class="badge b-notion">Notion</span></h3>
<p>看板改按「细类」分列（不再是宽泛大类），列内卡片含标签+概述。解决原方案"一个分类 30+ 卡片难扫读"的痛点。</p>
<a href="__DB__" target="_blank">打开 database → 切到「A3 细类看板」视图</a></div>
<div class="opt"><h3>A4 分类阅读室<span class="badge b-web">本地 Web</span></h3>
<p>左栏大类/细类树 + 右侧密集列表：每行 标题+标签chips+两行摘要+元数据，即时搜索与细类过滤。信息密度与交互自由度最高。</p>
<a href="/demo/reading-room">进入阅读室 →</a></div>
</div>

<h2 class="sec">功能 B · 本次更新的快速导读</h2>
<div class="grid2">
<div class="opt"><h3>B1 更新详情表<span class="badge b-notion">Notion</span></h3>
<p>「本次更新」表格版：列为 标题(点击即打开总结文档)+标签+概述+日期。点击标题 → Notion 侧边 peek 直接预览文档全文。</p>
<a href="__DB__" target="_blank">打开 database → 切到「B1 本次更新·详情」视图</a></div>
<div class="opt"><h3>B2 更新画廊<span class="badge b-notion">Notion</span></h3>
<p>「本次更新」画廊版：每批视频一张卡（标题+标签+概述），点击卡片即打开文档。视觉扫读最直观。</p>
<a href="__DB__" target="_blank">打开 database → 切到「B2 本次更新·画廊」视图</a></div>
<div class="opt"><h3>B3 批次卡片墙<span class="badge b-web">本地 Web</span></h3>
<p>本次批次视频排成卡片墙：点击标题跳总结文档；点「视频概述」按钮 → 当前页弹出概述卡片（含全文摘要+标签+元数据）。</p>
<a href="/demo/batch-cards">进入卡片墙 →</a></div>
<div class="opt"><h3>B4 Toggle 更新日志<span class="badge b-notion">Notion</span></h3>
<p>更新日志页升级：每条视频一个折叠块（toggle），收起时只见标题链接，展开即显 概述+标签 的内联摘要卡。纯 Notion 原生。</p>
<a href="__LOG2__" target="_blank">打开更新日志 v2 →</a></div>
</div>

<h2 class="sec">第二轮 · 大类按钮浏览 + LLM 短标题</h2>
<div class="grid2">
<div class="opt"><h3>A5 大类按钮视图<span class="badge b-notion">Notion</span></h3>
<p>list 视图顶部有「分类」快速筛选按钮组，点按钮即过滤出该大类，行 = 标题+标签+概述。数据实时零维护。</p>
<a href="__DB__" target="_blank">打开 database → 切到「A5 大类按钮视图」</a></div>
<div class="opt"><h3>A6 分类聚合子页<span class="badge b-notion">Notion</span></h3>
<p>每个大类一个「分类 · X」子页，页内嵌该类专属列表视图（实时同步）。点分类 = 进入该类专属空间。</p>
<a href="__DB__" target="_blank">在父页面「抖音知识推送整理」下打开「分类 · ××」子页</a></div>
<div class="opt"><h3>A7 大类按钮手风琴<span class="badge b-web">本地 Web</span></h3>
<p>大类按钮横排 → 点击展开该类行（短标题+标签+摘要），点标题新窗口打开文档。完全按描述交互实现。</p>
<a href="/demo/cat-accordion">进入手风琴 →</a></div>
<div class="opt"><h3>T1 LLM 短标题对比<span class="badge b-web">本地 Web</span></h3>
<p>39 篇全量预览：新短标题（≤18字、去 #/@/钩子语）vs 原标题。确认后 database Name 将替换为短标题。</p>
<a href="/demo/titles">查看对比 →</a></div>
</div>

<div class="link-list" style="margin-top:22px"><h2>体验建议</h2>
<p class="note">想象视频量到 300 篇：A 组选一个你觉得"找视频最不累"的；B 组选一个"看完更新最快决定读哪篇"的。可组合（如 A4+B3）。</p></div>
</div></body></html>"""

_READING_ROOM = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>A4 · 分类阅读室</title><style>__CSS__
.app{display:grid;grid-template-columns:250px 1fr;height:100vh}
.side{background:var(--card);border-right:1px solid var(--line);overflow-y:auto;padding:14px 10px}
.side h1{font-size:15px;margin-bottom:2px}
.side .tip{font-size:11px;color:var(--muted);margin-bottom:10px}
.main{overflow-y:auto;padding:20px 24px}
.searchbar{position:sticky;top:0;background:var(--bg);padding-bottom:10px;z-index:2;display:flex;gap:10px}
.row{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin-bottom:10px}
.rtitle{font-size:15px;font-weight:600}
.rtitle a{color:var(--ink);text-decoration:none}
.rtitle a:hover{color:var(--accent)}
.rmeta{font-size:11px;color:var(--muted);margin:2px 0 6px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.rsum{font-size:13px;color:#444;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.rsum.open{-webkit-line-clamp:unset}
.tags{display:flex;gap:5px;flex-wrap:wrap;margin-top:6px}
.tag{font-size:11px;background:var(--accent-soft);color:var(--accent);border-radius:5px;padding:0 7px}
.more{font-size:12px;color:var(--accent);background:none;border:none;cursor:pointer;padding:0;margin-top:4px}
.crumb{font-size:12px;color:var(--muted);margin-bottom:8px}
</style></head><body>
<div class="app">
<div class="side"><h1>📚 分类阅读室</h1><div class="tip">A4 · 点大类→细类逐级下钻</div><div id="tree"></div></div>
<div class="main">
<div class="searchbar"><input id="q" type="search" placeholder="搜索标题 / 标签 / 摘要…" style="flex:1;padding:9px 12px;border:1px solid var(--line);border-radius:8px;font-size:14px;background:#fff" oninput="render()"></div>
<div class="crumb" id="crumb"></div>
<div id="list"></div>
</div></div>
<script>
let DATA=null, cat=null, sub=null;
const esc=s=>(s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function init(){
 DATA=await (await fetch('/demo/api')).json();
 let html=`<div class="cat"><div class="cat-head" data-c="" onclick="pickCat(this)"><span>全部</span><span class="n">${DATA.index.length}</span></div></div>`;
 for(const [c,subs] of Object.entries(DATA.categories)){
  const n=DATA.index.filter(e=>e.category===c).length;
  html+=`<div class="cat"><div class="cat-head" data-c="${esc(c)}" onclick="pickCat(this)"><span>${esc(c)}</span><span class="n">${n}</span></div>`;
  html+='<div class="subs" style="padding-left:10px;display:none">'+subs.map(s=>{
    const sn=DATA.index.filter(e=>e.category===c&&e.subcategory===s).length;
    return `<div class="sub-item" data-c="${esc(c)}" data-s="${esc(s)}" onclick="pickSub(this)" style="font-size:12px;color:var(--muted);padding:4px 8px;border-radius:6px;cursor:pointer">${esc(s)} <span style="opacity:.6">${sn}</span></div>`;}).join('')+'</div></div>';
 }
 document.getElementById('tree').innerHTML=html;
 render();
}
function pickCat(el){
 document.querySelectorAll('.cat-head').forEach(x=>x.classList.remove('active'));
 document.querySelectorAll('.sub-item').forEach(x=>x.classList.remove('active'));
 el.classList.add('active');cat=el.dataset.c;sub=null;
 document.querySelectorAll('.cat-head').forEach(h=>{
  const s=h.parentElement.querySelector('.subs');
  if(s) s.classList.toggle('open', h.dataset.c===cat);
 });
 render();
}
function pickSub(el){
 document.querySelectorAll('.sub-item').forEach(x=>{x.style.color='';x.style.fontWeight=''});
 el.style.color='var(--accent)';el.style.fontWeight='600';
 sub=(sub===el.dataset.s)?null:el.dataset.s;render();
}
function render(){
 const q=document.getElementById('q').value.trim().toLowerCase();
 let items=DATA.index.filter(e=>(!cat||e.category===cat)&&(!sub||e.subcategory===sub)&&
  (!q||(e.title+' '+(e.tags||[]).join(' ')+' '+(e.preview||'')).toLowerCase().includes(q)));
 items.sort((a,b)=>(b.tags||[]).length-(a.tags||[]).length||b.date.localeCompare(a.date));
 document.getElementById('crumb').textContent=[cat||'全部分类',sub].filter(Boolean).join(' › ')+` · ${items.length} 篇`;
 document.getElementById('list').innerHTML=items.map((e,i)=>`
  <div class="row"><div class="rtitle">${i+1}. <a href="${e.notion_url||e.source_url}" target="_blank">${esc(e.title)}</a></div>
  <div class="rmeta"><span class="chip">${esc(e.category)}</span><span class="chip sub">${esc(e.subcategory)}</span>
  <span>${esc(e.author)}</span><span>${esc(e.date)}</span>
  <a href="${e.source_url}" target="_blank" style="color:var(--accent)">来源↗</a></div>
  <div class="rsum" id="s${i}">${esc(e.preview||'')}</div>
  <div class="tags">${(e.tags||[]).map(t=>`<span class="tag">${esc(t)}</span>`).join('')}</div>
  <button class="more" onclick="const s=document.getElementById('s${i}');s.classList.toggle('open');this.textContent=s.classList.contains('open')?'收起 ▴':'展开摘要 ▾'">展开摘要 ▾</button>
  </div>`).join('')||'<div class="empty">没有匹配的笔记</div>';
}
init();
</script></body></html>"""

_BATCH_CARDS = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>B3 · 本次更新卡片墙</title><style>__CSS__
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}
.cardx{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;display:flex;flex-direction:column;gap:8px}
.cardx .t{font-size:14px;font-weight:600;line-height:1.45}
.cardx .t a{color:var(--ink);text-decoration:none}
.cardx .t a:hover{color:var(--accent)}
.cardx .m{font-size:11px;color:var(--muted)}
.cardx .tags{display:flex;gap:5px;flex-wrap:wrap}
.cardx .tag{font-size:11px;background:var(--accent-soft);color:var(--accent);border-radius:5px;padding:0 7px}
.btn{align-self:flex-start;font-size:12px;color:var(--accent);background:var(--accent-soft);border:none;border-radius:7px;padding:5px 12px;cursor:pointer}
.btn:hover{filter:brightness(.96)}
.modal-bg{display:none;position:fixed;inset:0;background:rgba(0,0,0,.35);z-index:9;align-items:center;justify-content:center}
.modal-bg.open{display:flex}
.modal{background:#fff;border-radius:14px;max-width:640px;width:92%;max-height:80vh;overflow-y:auto;padding:24px}
.modal h3{font-size:16px;margin-bottom:6px}
.modal .m{font-size:12px;color:var(--muted);margin-bottom:12px}
.modal .tags{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}
.modal .tag{font-size:12px;background:var(--accent-soft);color:var(--accent);border-radius:6px;padding:2px 9px}
.modal .body{font-size:14px;line-height:1.8;color:#333}
.closex{float:right;font-size:18px;color:var(--muted);cursor:pointer;border:none;background:none}
.batchbar{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}
.bbtn{font-size:13px;border:1px solid var(--line);background:#fff;border-radius:8px;padding:6px 14px;cursor:pointer}
.bbtn.active{background:var(--accent);color:#fff;border-color:var(--accent)}
</style></head><body>
<div class="wrap">
<div class="topbar"><h1>B3 · 本次更新卡片墙</h1><a href="/demo/ux">← 返回</a></div>
<p class="sub">点击标题 → 新窗口打开 Notion 总结文档；点「视频概述」→ 当前页弹出摘要卡片。</p>
<div class="batchbar" id="batchbar"></div>
<div class="cards" id="cards"></div></div>
<div class="modal-bg" id="mbg" onclick="if(event.target===this)this.classList.remove('open')">
<div class="modal" id="modal"></div></div>
<script>
let DATA=null, bid=null;
const esc=s=>(s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function init(){
 DATA=await (await fetch('/demo/api')).json();
 bid=DATA.batches[0]&&DATA.batches[0].batch_id;
 document.getElementById('batchbar').innerHTML=DATA.batches.map(b=>
  `<button class="bbtn${b.batch_id===bid?' active':''}" onclick="bid='${b.batch_id}';document.querySelectorAll('.bbtn').forEach(x=>x.classList.remove('active'));this.classList.add('active');render()">${b.batch_id}（${b.created_at}）</button>`).join('');
 render();
}
function byId(id){return DATA.index.find(e=>e.aweme_id===id)}
function render(){
 const b=DATA.batches.find(x=>x.batch_id===bid);
 document.getElementById('cards').innerHTML=(b?b.items:[]).map(it=>{
  const e=byId(it.aweme_id)||it;
  return `<div class="cardx"><div class="t"><a href="${it.notion_url||e.source_url||'#'}" target="_blank">${esc(it.title)}</a></div>
  <div class="m">${esc(e.category||'')} › ${esc(e.subcategory||'')} · ${esc(e.author||it.author||'')} · ${esc(e.date||'')}</div>
  <div class="tags">${(e.tags||[]).map(t=>`<span class="tag">${esc(t)}</span>`).join('')}</div>
  <button class="btn" onclick="showModal('${it.aweme_id}')">视频概述</button></div>`;
 }).join('')||'<div class="empty">该批次无视频</div>';
}
function showModal(id){
 const e=byId(id);if(!e)return;
 document.getElementById('modal').innerHTML=`
  <button class="closex" onclick="document.getElementById('mbg').classList.remove('open')">✕</button>
  <h3>${esc(e.title)}</h3>
  <div class="m">${esc(e.category)} › ${esc(e.subcategory)} · ${esc(e.author)} · ${esc(e.date)} ·
   <a href="${e.notion_url||e.source_url}" target="_blank" style="color:var(--accent)">打开完整笔记↗</a></div>
  <div class="tags">${(e.tags||[]).map(t=>`<span class="tag">${esc(t)}</span>`).join('')}</div>
  <div class="body">${esc(e.preview||'（无概述）')}…</div>`;
 document.getElementById('mbg').classList.add('open');
}
init();
</script></body></html>"""


_CAT_ACCORDION = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>A7 · 大类按钮手风琴 + 详情抽屉</title><style>__CSS__
.btnrow{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px}
.catbtn{font-size:14px;font-weight:600;border:1px solid var(--line);background:var(--card);border-radius:24px;padding:9px 20px;cursor:pointer;display:flex;gap:8px;align-items:center}
.catbtn .n{font-size:12px;font-weight:400;background:var(--accent-soft);color:var(--accent);border-radius:10px;padding:0 8px}
.catbtn.active{background:var(--accent);color:#fff;border-color:var(--accent)}
.catbtn.active .n{background:rgba(255,255,255,.25);color:#fff}
.panel{display:none;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:6px 18px 12px;margin-bottom:16px}
.panel.open{display:block}
.prow{display:grid;grid-template-columns:1fr 210px;gap:14px;padding:14px 4px;border-bottom:1px dashed var(--line);cursor:pointer;transition:background .12s}
.prow:last-child{border-bottom:none}
.prow:hover{background:var(--accent-soft)}
.prow.active{background:var(--accent-soft)}
.pt{font-size:15px;font-weight:600;line-height:1.5}
.pm{font-size:11px;color:var(--muted);margin:3px 0 6px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.ps{font-size:13px;color:#444;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.tags{display:flex;gap:5px;flex-wrap:wrap;align-content:start}
.tag{font-size:11px;background:var(--accent-soft);color:var(--accent);border-radius:5px;padding:0 7px}
.hint{font-size:12px;color:var(--muted);margin:4px 0 14px}
.overlay{position:fixed;inset:0;background:rgba(15,23,42,.25);opacity:0;pointer-events:none;transition:.2s;z-index:8}
.overlay.open{opacity:1;pointer-events:auto}
.drawer{position:fixed;top:0;right:-460px;width:440px;max-width:92vw;height:100vh;background:var(--card);box-shadow:-6px 0 24px rgba(0,0,0,.12);z-index:9;transition:right .25s ease;display:flex;flex-direction:column}
.drawer.open{right:0}
.dhead{padding:18px 20px 12px;border-bottom:1px solid var(--line);position:relative}
.dclose{position:absolute;top:14px;right:16px;width:32px;height:32px;border-radius:8px;border:1px solid var(--line);background:#fff;font-size:15px;cursor:pointer;color:var(--muted)}
.dclose:hover{color:var(--ink);border-color:var(--muted)}
.dt{font-size:17px;font-weight:700;line-height:1.5;padding-right:36px}
.dorig{font-size:12px;color:var(--muted);margin-top:5px;line-height:1.5;max-height:40px;overflow:hidden}
.dbody{flex:1;overflow-y:auto;padding:16px 20px 20px}
.dsec{margin-bottom:16px}
.dlabel{font-size:11px;color:var(--muted);margin-bottom:6px;font-weight:600;letter-spacing:.05em}
.chips{display:flex;gap:6px;flex-wrap:wrap}
.chip2{font-size:12px;border-radius:6px;padding:2px 10px;background:var(--accent-soft);color:var(--accent)}
.chip2.sub{background:#f0fdf4;color:var(--green)}
.dsummary{font-size:13px;line-height:1.85;color:#333;background:#fafaf8;border:1px dashed var(--line);border-radius:10px;padding:12px 14px;max-height:40vh;overflow-y:auto}
.dbtns{display:flex;gap:10px;margin-top:18px}
.dbtn{flex:1;text-align:center;font-size:14px;font-weight:600;border-radius:9px;padding:11px 0;text-decoration:none;cursor:pointer}
.dbtn.primary{background:var(--accent);color:#fff}
.dbtn.primary:hover{filter:brightness(1.05)}
.dbtn.ghost{border:1px solid var(--line);color:var(--ink);background:#fff}
.dbtn.ghost:hover{border-color:var(--accent);color:var(--accent)}
.empty{color:var(--muted);font-size:13px;padding:30px;text-align:center}
</style></head><body>
<div class="wrap" style="max-width:920px">
<div class="topbar"><h1>A7 · 大类按钮手风琴 + 详情抽屉</h1><a href="/demo/ux">← 返回</a></div>
<p class="hint">点击大类展开 → 点击任意视频行，右侧弹出详情抽屉（分类/标签/抖音链接/概述/Notion 跳转）；点击其他行自动切换；ESC 或 ✕ 关闭。</p>
<div class="btnrow" id="btnrow"></div>
<div id="panels"></div>
</div>
<div class="overlay" id="overlay" onclick="closeDrawer()"></div>
<div class="drawer" id="drawer">
  <div class="dhead">
    <button class="dclose" onclick="closeDrawer()" title="关闭">✕</button>
    <div class="dt" id="dTitle"></div>
    <div class="dorig" id="dOrig"></div>
  </div>
  <div class="dbody">
    <div class="dsec"><div class="dlabel">分类</div><div class="chips" id="dCat"></div></div>
    <div class="dsec"><div class="dlabel">标签</div><div class="chips" id="dTags"></div></div>
    <div class="dsec"><div class="dlabel">视频概述</div><div class="dsummary" id="dSum"></div></div>
    <div class="dbtns">
      <a class="dbtn ghost" id="dDouyin" target="_blank">▶ 抖音视频来源</a>
      <a class="dbtn primary" id="dNotion" target="_blank">打开 Notion 总结文档 ↗</a>
    </div>
  </div>
</div>
<script>
let DATA=null, active=null, curId=null;
const esc=s=>(s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function init(){
 DATA=await (await fetch('/demo/api')).json();
 const cats=Object.keys(DATA.categories).filter(c=>DATA.index.some(e=>e.category===c));
 document.getElementById('btnrow').innerHTML=cats.map(c=>{
  const n=DATA.index.filter(e=>e.category===c).length;
  return `<button class="catbtn" data-c="${esc(c)}" onclick="toggle(this)">${esc(c)}<span class="n">${n}</span></button>`;
 }).join('');
 document.addEventListener('keydown',e=>{if(e.key==='Escape')closeDrawer()});
}
function toggle(el){
 const c=el.dataset.c;
 active=(active===c)?null:c;render();
}
function render(){
 document.querySelectorAll('.catbtn').forEach(b=>b.classList.toggle('active',b.dataset.c===active));
 const items=DATA.index.filter(e=>e.category===active).sort((a,b)=>b.date.localeCompare(a.date));
 document.getElementById('panels').innerHTML=active?`<div class="panel open">${
  items.map(e=>`
  <div class="prow${e.aweme_id===curId?' active':''}" data-id="${esc(e.aweme_id)}" onclick="openDrawer('${esc(e.aweme_id)}')">
    <div>
      <div class="pt">${esc(e.short_title||e.title)}</div>
      <div class="pm"><span class="chip sub">${esc(e.subcategory)}</span><span>${esc(e.author)}</span><span>${esc(e.date)}</span></div>
      <div class="ps">${esc(e.preview||'')}</div>
    </div>
    <div class="tags">${(e.tags||[]).map(t=>`<span class="tag">${esc(t)}</span>`).join('')}</div>
  </div>`).join('')||'<div class="empty">该类暂无视频</div>'}</div>`:'';
 if(curId)fillDrawer(curId);
}
function byId(id){return DATA.index.find(e=>e.aweme_id===id)}
function openDrawer(id){
 curId=id;
 document.querySelectorAll('.prow').forEach(r=>r.classList.toggle('active',r.dataset.id===id));
 fillDrawer(id);
 document.getElementById('drawer').classList.add('open');
 document.getElementById('overlay').classList.add('open');
}
function fillDrawer(id){
 const e=byId(id);if(!e)return;
 document.getElementById('dTitle').textContent=e.short_title||e.title;
 document.getElementById('dOrig').textContent=e.short_title?('原标题：'+e.title):'';
 document.getElementById('dCat').innerHTML=
  `<span class="chip2">${esc(e.category)}</span><span class="chip2 sub">${esc(e.subcategory)}</span>`;
 document.getElementById('dTags').innerHTML=(e.tags||[]).map(t=>`<span class="tag">${esc(t)}</span>`).join('')||'<span class="pm">无</span>';
 document.getElementById('dSum').textContent=(e.preview||'（无概述）');
 const dn=document.getElementById('dNotion');dn.href=e.notion_url||e.source_url||'#';
 const dd=document.getElementById('dDouyin');dd.href=e.source_url||'#';
 dd.style.display=e.source_url?'':'none';
}
function closeDrawer(){
 curId=null;
 document.getElementById('drawer').classList.remove('open');
 document.getElementById('overlay').classList.remove('open');
 document.querySelectorAll('.prow').forEach(r=>r.classList.remove('active'));
}
init();
</script></body></html>"""

_TITLES = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>T1 · LLM 短标题前后对比</title><style>__CSS__
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
th{font-size:12px;color:var(--muted);text-align:left;padding:10px 12px;background:#fafaf8;border-bottom:1px solid var(--line)}
td{font-size:13px;padding:9px 12px;border-bottom:1px dashed var(--line);vertical-align:top}
tr:last-child td{border-bottom:none}
td.new{font-weight:600}
td.old{color:var(--muted);font-size:12px}
.len{font-size:11px;color:var(--muted)}
.ok{color:var(--green)} .warn{color:var(--orange)}
</style></head><body>
<div class="wrap">
<div class="topbar"><h1>T1 · LLM 短标题（39 篇全量预览）</h1><a href="/demo/ux">← 返回</a></div>
<p class="sub">新标题 ≤18 字，已去除 #话题 / @用户 / 推广钩子语。确认方案后：database Name 换为短标题，原标题存入「原标题」property，笔记 frontmatter 不动。</p>
<table><thead><tr><th style="width:30%">新短标题</th><th style="width:12%">字数</th><th>原标题</th></tr></thead>
<tbody id="tb"></tbody></table>
</div>
<script>
const esc=s=>(s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
(async()=>{
 const DATA=await (await fetch('/demo/api')).json();
 const seen=new Set();
 document.getElementById('tb').innerHTML=DATA.index.map(e=>{
  const st=e.short_title||'（未生成）';
  const dup=seen.has(st);seen.add(st);
  return `<tr><td class="new">${esc(st)}${dup?' <span class="warn">⚠同名</span>':''}</td>
  <td><span class="len ${st.length<=18?'ok':'warn'}">${st.length} 字</span></td>
  <td class="old">${esc(e.title)}</td></tr>`;
 }).join('');
})();
</script></body></html>"""


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

    @app.get("/demo/ux", response_class=HTMLResponse)
    async def demo_ux():
        meta = _demo_payload()["meta"]
        return (
            _UX.replace("__CSS__", _CSS)
            .replace("__DB__", meta.get("database_url", "https://www.notion.so"))
            .replace("__LOG2__", meta.get("log_url_v2", meta.get("log_url", "https://www.notion.so")))
        )

    @app.get("/demo/reading-room", response_class=HTMLResponse)
    async def demo_reading_room():
        return _READING_ROOM.replace("__CSS__", _CSS)

    @app.get("/demo/batch-cards", response_class=HTMLResponse)
    async def demo_batch_cards():
        return _BATCH_CARDS.replace("__CSS__", _CSS)

    @app.get("/demo/cat-accordion", response_class=HTMLResponse)
    async def demo_cat_accordion():
        return _CAT_ACCORDION.replace("__CSS__", _CSS)

    @app.get("/demo/titles", response_class=HTMLResponse)
    async def demo_titles():
        return _TITLES.replace("__CSS__", _CSS)
