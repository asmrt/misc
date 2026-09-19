"""IR(Workbook) → 単一HTMLビューア。

外部CDNに依存しない自己完結HTML1ファイルを生成する（配布・共有がそのままできる
＝「Tableauに依存せず」に直結する）。IRをJSONとして埋め込み、表示・検索は
すべてクライアントサイドのJavaScript（ライブラリ非使用）で行う。
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from .mask import apply_connection_mask
from .model import Workbook


def _workbook_to_dict(wb: Workbook) -> dict:
    return dataclasses.asdict(wb)


def render_html(wb: Workbook, mask_connections: bool = True) -> str:
    payload_wb = apply_connection_mask(wb) if mask_connections else wb
    data = _workbook_to_dict(payload_wb)
    data_json = json.dumps(data, ensure_ascii=False)
    title = Path(wb.source_path).stem or "workbook"
    return _TEMPLATE.replace("__TITLE__", _escape_html(title)).replace(
        "__DATA_JSON__", _escape_script(data_json)
    )


def write_viewer(wb: Workbook, out_path: str, mask_connections: bool = True) -> str:
    html = render_html(wb, mask_connections=mask_connections)
    Path(out_path).write_text(html, encoding="utf-8")
    return html


def _escape_html(s: str) -> str:
    return (
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def _escape_script(s: str) -> str:
    # </script> による早期終了を防ぐ
    return s.replace("</", "<\\/")


_TEMPLATE = r"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>__TITLE__ 仕様書ビューア</title>
<style>
:root{
  --bg:#f4f6f9; --surface:#ffffff; --ink:#1a2230; --ink-muted:#5b6472;
  --line:#d7dee6; --accent:#2563a8; --accent-soft:#e2edf8;
  --warn:#b4650e; --warn-soft:#f6e6d3; --mono-bg:#f0f3f7;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#10161f; --surface:#171f2a; --ink:#e7ecf3; --ink-muted:#9aa7b6;
    --line:#2c3744; --accent:#6fa8dc; --accent-soft:#1f3247;
    --warn:#e3a15c; --warn-soft:#3a2a18; --mono-bg:#1c2530;
  }
}
:root[data-theme="dark"]{
  --bg:#10161f; --surface:#171f2a; --ink:#e7ecf3; --ink-muted:#9aa7b6;
  --line:#2c3744; --accent:#6fa8dc; --accent-soft:#1f3247;
  --warn:#e3a15c; --warn-soft:#3a2a18; --mono-bg:#1c2530;
}
*{box-sizing:border-box;}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Hiragino Sans,"Noto Sans JP",sans-serif;}
a{color:var(--accent);}
.layout{display:flex;min-height:100vh;}
nav{width:230px;flex:none;background:var(--surface);border-right:1px solid var(--line);
  padding:16px 10px;position:sticky;top:0;height:100vh;overflow-y:auto;}
nav h1{font-size:14px;margin:4px 8px 14px;line-height:1.4;word-break:break-word;}
nav input{width:100%;padding:7px 9px;border:1px solid var(--line);border-radius:6px;
  background:var(--bg);color:var(--ink);font-size:13px;margin-bottom:10px;}
nav button{display:block;width:100%;text-align:left;padding:7px 9px;border:none;
  background:none;color:var(--ink);font-size:13px;border-radius:6px;cursor:pointer;}
nav button:hover{background:var(--accent-soft);}
nav button.active{background:var(--accent);color:#fff;}
main{flex:1;padding:26px 32px;max-width:980px;}
h2{font-size:20px;margin-top:0;}
.card{background:var(--surface);border:1px solid var(--line);border-radius:10px;
  padding:16px 18px;margin-bottom:14px;}
.card h3{margin:0 0 8px;font-size:15px;}
.meta{color:var(--ink-muted);font-size:12.5px;margin:2px 0;}
.pill{display:inline-block;font-size:11px;padding:2px 8px;border-radius:10px;
  background:var(--accent-soft);color:var(--accent);margin-right:6px;}
.pill.warn{background:var(--warn-soft);color:var(--warn);}
table{border-collapse:collapse;width:100%;font-size:12.5px;margin:8px 0;}
th,td{border:1px solid var(--line);padding:5px 8px;text-align:left;vertical-align:top;}
th{background:var(--mono-bg);}
pre{background:var(--mono-bg);padding:10px 12px;border-radius:8px;overflow-x:auto;
  font-size:12.5px;white-space:pre-wrap;word-break:break-word;}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;}
.field-link{cursor:pointer;text-decoration:underline dotted;}
.search-hit mark{background:var(--warn-soft);color:inherit;}
.dash-canvas{position:relative;width:100%;aspect-ratio:16/10;background:var(--mono-bg);
  border:1px solid var(--line);border-radius:8px;margin:10px 0;overflow:hidden;}
.dash-zone{position:absolute;border:1px solid var(--accent);background:var(--accent-soft);
  font-size:11px;color:var(--ink);padding:3px 5px;overflow:hidden;border-radius:3px;}
.dash-zone.leaf{background:var(--surface);}
[hidden]{display:none!important;}
</style>
</head>
<body>
<div class="layout">
  <nav>
    <h1>__TITLE__</h1>
    <input id="search" type="search" placeholder="全文検索…">
    <button data-view="overview" class="active">概要</button>
    <button data-view="datasources">データソース</button>
    <button data-view="calculations">計算フィールド</button>
    <button data-view="worksheets">ワークシート</button>
    <button data-view="dashboards">ダッシュボード</button>
    <button data-view="actions">アクション</button>
    <button data-view="parameters">パラメータ</button>
  </nav>
  <main id="main"></main>
</div>
<script id="wb-data" type="application/json">__DATA_JSON__</script>
<script>
const WB = JSON.parse(document.getElementById('wb-data').textContent);
const $main = document.getElementById('main');
const $search = document.getElementById('search');
const navButtons = [...document.querySelectorAll('nav button[data-view]')];

function h(s){return (s==null?'':String(s)).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}

function fieldIndex(){
  const idx = {};
  for (const dsName in WB.datasources){
    const ds = WB.datasources[dsName];
    for (const colName in ds.columns){
      idx[colName] = ds.columns[colName].caption || colName;
    }
  }
  return idx;
}
const FIELD_LABEL = fieldIndex();

function jumpToField(name){
  showView('calculations');
  setTimeout(()=>{
    const el = document.getElementById('calc-'+cssSafe(name));
    if(el){ el.scrollIntoView({behavior:'smooth', block:'center'}); el.classList.add('search-hit'); }
  }, 30);
}
function cssSafe(s){ return String(s).replace(/[^a-zA-Z0-9_-]/g,'_'); }
window.jumpToField = jumpToField;

function renderOverview(){
  const nDs = Object.keys(WB.datasources).length;
  const nWs = Object.keys(WB.worksheets).length;
  const nDb = Object.keys(WB.dashboards).length;
  let nCalc = 0;
  for (const dsName in WB.datasources){
    for (const c of Object.values(WB.datasources[dsName].columns)){ if(c.is_calculated) nCalc++; }
  }
  const nParam = Object.keys(WB.parameters).length;
  const nAction = WB.actions.length;
  let html = `<h2>概要</h2><div class="card">
    <table><tr><th>データソース</th><td>${nDs}</td></tr>
    <tr><th>ワークシート</th><td>${nWs}</td></tr>
    <tr><th>ダッシュボード</th><td>${nDb}</td></tr>
    <tr><th>計算フィールド</th><td>${nCalc}</td></tr>
    <tr><th>パラメータ</th><td>${nParam}</td></tr>
    <tr><th>アクション</th><td>${nAction}</td></tr>
    <tr><th>Tableauバージョン</th><td>${h(WB.tableau_version||'不明')}</td></tr>
    </table></div>`;
  if (WB.unparsed && WB.unparsed.length){
    html += `<h2>未対応要素</h2><div class="card"><p class="meta">本ツールが認識できなかったXML要素です。該当箇所は元のtwbを直接確認してください。</p>
      <table><tr><th>タグ</th><th>出現箇所</th><th>件数</th></tr>` +
      WB.unparsed.map(u=>`<tr><td><code>${h(u.tag)}</code></td><td>${h(u.path)}</td><td>${u.count}</td></tr>`).join('') +
      `</table></div>`;
  }
  $main.innerHTML = html;
}

function renderDatasources(){
  let html = '<h2>データソース</h2>';
  for (const dsName in WB.datasources){
    const ds = WB.datasources[dsName];
    const cols = Object.values(ds.columns).sort((a,b)=>(a.caption||a.name).localeCompare(b.caption||b.name,'ja'));
    html += `<div class="card"><h3>${h(ds.caption||ds.name)}</h3>
      <p class="meta">内部名: <code>${h(ds.name)}</code></p>`;
    if (ds.connections.length){
      html += `<table><tr><th>種別</th><th>サーバー</th><th>DB名</th></tr>` +
        ds.connections.map(c=>`<tr><td>${h(c.class_)}</td><td>${h(c.server||'')}</td><td>${h(c.dbname||'')}</td></tr>`).join('') +
        `</table>`;
    }
    html += `<table><tr><th>フィールド</th><th>型</th><th>役割</th><th>種別</th></tr>` +
      cols.map(c=>`<tr><td>${h(c.caption||c.name)}</td><td>${h(c.datatype||'')}</td><td>${h(c.role||'')}</td>
        <td>${c.is_calculated?'計算':(c.is_group?'グループ':'通常')}</td></tr>`).join('') +
      `</table></div>`;
  }
  $main.innerHTML = html || '<p>データソースはありません。</p>';
}

function renderCalculations(){
  let html = '<h2>計算フィールド</h2>';
  let any = false;
  for (const dsName in WB.datasources){
    const ds = WB.datasources[dsName];
    for (const col of Object.values(ds.columns)){
      if (!col.is_calculated) continue;
      any = true;
      const flags = [];
      if (col.uses_lod) flags.push('<span class="pill warn">LOD式</span>');
      if (col.uses_table_calc) flags.push('<span class="pill warn">表計算</span>');
      html += `<div class="card" id="calc-${cssSafe(col.name)}">
        <h3>${h(col.caption||col.name)} ${flags.join('')}</h3>
        <p class="meta">データソース: ${h(ds.caption||ds.name)}</p>
        <pre>${h(col.formula||'')}</pre>`;
      if (col.depends_on && col.depends_on.length){
        html += `<p class="meta">依存: ` + col.depends_on.map(d=>
          `<span class="field-link" onclick="jumpToField('${cssSafe(d)}')">${h(FIELD_LABEL[d]||d)}</span>`
        ).join(', ') + `</p>`;
      }
      if (col.referenced_by && col.referenced_by.length){
        html += `<p class="meta">参照元: ${h(col.referenced_by.join(', '))}</p>`;
      }
      html += `</div>`;
    }
  }
  $main.innerHTML = any ? html : '<h2>計算フィールド</h2><p>計算フィールドはありません。</p>';
}

function renderWorksheets(){
  let html = '<h2>ワークシート</h2>';
  const items = Object.values(WB.worksheets);
  for (const ws of items){
    html += `<div class="card"><h3>${h(ws.name)}</h3>
      <p class="meta">マーク: ${h(ws.mark_class||'不明')} / データソース: ${h((ws.datasources||[]).join(', ')||'不明')}</p>
      <p class="meta">列: <code>${h(ws.cols_raw||'(なし)')}</code></p>
      <p class="meta">行: <code>${h(ws.rows_raw||'(なし)')}</code></p>`;
    if (ws.encodings && ws.encodings.length){
      html += `<table><tr><th>チャネル</th><th>フィールド</th></tr>` +
        ws.encodings.map(e=>`<tr><td>${h(e.channel)}</td><td>${h(e.field_display)}</td></tr>`).join('') + `</table>`;
    }
    if (ws.filters && ws.filters.length){
      html += `<table><tr><th>フィルタ</th><th>種別</th><th>概要</th></tr>` +
        ws.filters.map(f=>`<tr><td>${h(f.field_display)}</td><td>${h(f.filter_class||'')}</td><td>${h(f.summary||'')}</td></tr>`).join('') + `</table>`;
    }
    html += `</div>`;
  }
  $main.innerHTML = items.length ? html : '<h2>ワークシート</h2><p>ワークシートはありません。</p>';
}

function zoneExtent(zones){
  let maxX=0, maxY=0;
  const walk = z => { maxX=Math.max(maxX, z.x+z.w); maxY=Math.max(maxY, z.y+z.h); (z.children||[]).forEach(walk); };
  zones.forEach(walk);
  return {maxX: maxX||1, maxY: maxY||1};
}
function leafZones(zones){
  // レイアウト用のコンテナゾーン(layout-basic/layout-flow等)は描画対象にせず、
  // 実際にコンテンツを持つ末端ゾーン（ワークシート・テキスト等）だけを平坦化して集める。
  // Tableauのゾーン座標は親からの相対ではなくダッシュボード全体に対する絶対座標なので、
  // オフセットを積み上げる必要はない。
  const out = [];
  const walk = z => {
    if (z.children && z.children.length){ z.children.forEach(walk); }
    else { out.push(z); }
  };
  zones.forEach(walk);
  return out;
}
function renderZones(zones, extent){
  return leafZones(zones).map(z=>{
    const left = (z.x/extent.maxX*100).toFixed(2);
    const top = (z.y/extent.maxY*100).toFixed(2);
    const w = (z.w/extent.maxX*100).toFixed(2);
    const hgt = (z.h/extent.maxY*100).toFixed(2);
    const label = z.worksheet_name || z.zone_type || '';
    return `<div class="dash-zone leaf" style="left:${left}%;top:${top}%;width:${w}%;height:${hgt}%;">${h(label)}</div>`;
  }).join('');
}

function renderDashboards(){
  let html = '<h2>ダッシュボード</h2>';
  const items = Object.values(WB.dashboards);
  for (const db of items){
    const extent = zoneExtent(db.zones||[]);
    html += `<div class="card"><h3>${h(db.name)}</h3>
      <p class="meta">サイズ: ${h(db.size_w||'自動')} × ${h(db.size_h||'自動')}</p>
      <div class="dash-canvas">${renderZones(db.zones||[], extent)}</div>
      </div>`;
  }
  $main.innerHTML = items.length ? html : '<h2>ダッシュボード</h2><p>ダッシュボードはありません。</p>';
}

function renderActions(){
  const items = WB.actions||[];
  let html = '<h2>アクション</h2>';
  if (items.length){
    html += `<table><tr><th>名前</th><th>種別</th><th>実行契機</th><th>ソース</th><th>ターゲット</th></tr>` +
      items.map(a=>`<tr><td>${h(a.name||'(無題)')}</td><td>${h(a.action_type)}</td><td>${h(a.activation||'')}</td>
        <td>${h((a.source_sheets||[]).join(', ')||'(全シート)')}</td><td>${h((a.target_sheets||[]).join(', '))}</td></tr>`).join('') +
      `</table>`;
  } else { html += '<p>アクションはありません。</p>'; }
  $main.innerHTML = html;
}

function renderParameters(){
  const items = Object.values(WB.parameters||{});
  let html = '<h2>パラメータ</h2>';
  if (items.length){
    html += `<table><tr><th>名前</th><th>型</th><th>現在値</th><th>使用箇所</th></tr>` +
      items.map(p=>`<tr><td>${h(p.caption||p.name)}</td><td>${h(p.datatype||'')}</td><td>${h(p.current_value||'')}</td>
        <td>${h((p.used_in||[]).join(', '))}</td></tr>`).join('') + `</table>`;
  } else { html += '<p>パラメータはありません。</p>'; }
  $main.innerHTML = html;
}

const VIEWS = {
  overview: renderOverview, datasources: renderDatasources, calculations: renderCalculations,
  worksheets: renderWorksheets, dashboards: renderDashboards, actions: renderActions,
  parameters: renderParameters,
};

function showView(name){
  navButtons.forEach(b=>b.classList.toggle('active', b.dataset.view===name));
  (VIEWS[name]||renderOverview)();
}
navButtons.forEach(b=>b.addEventListener('click', ()=>showView(b.dataset.view)));

$search.addEventListener('input', ()=>{
  const q = $search.value.trim().toLowerCase();
  if (!q){ return; }
  // 簡易全文検索: 計算フィールドの式・フィールド名・ワークシート名を横断
  const hits = [];
  for (const dsName in WB.datasources){
    for (const c of Object.values(WB.datasources[dsName].columns)){
      const hay = ((c.caption||'')+' '+c.name+' '+(c.formula||'')).toLowerCase();
      if (hay.includes(q)) hits.push({type:'field', name:c.caption||c.name});
    }
  }
  for (const ws of Object.values(WB.worksheets)){
    if (ws.name.toLowerCase().includes(q)) hits.push({type:'worksheet', name:ws.name});
  }
  showView('overview');
  const list = hits.slice(0,30).map(hit=>`<li>[${h(hit.type)}] ${h(hit.name)}</li>`).join('');
  $main.insertAdjacentHTML('beforeend', `<h2>検索結果: 「${h(q)}」</h2><div class="card"><ul>${list || '<li>該当なし</li>'}</ul></div>`);
});

showView('overview');
</script>
</body>
</html>
"""
