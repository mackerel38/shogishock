"""Portable, offline research reports; all plotted scores are sente perspective."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .research import select_review, select_diverse, write_json


def render_reports(out):
    out = Path(out)
    rows = json.loads((out / "candidates.json").read_text())
    positions = json.loads((out / "positions.json").read_text())
    manifest = json.loads((out / "manifest.json").read_text())
    deep = json.loads((out / "deep.json").read_text()) if (out / "deep.json").exists() else {}
    audit = {a["candidate_id"]: a for a in json.loads((out / "audit.json").read_text())} if (out / "audit.json").exists() else {}
    summaries = {}
    for side in ("sente", "gote"):
        group = [r for r in rows if r["attacker_side"] == side]
        group_positions = {p["position_id"]: p for p in positions if p["side_to_move"] == side}
        valid = [r for r in group if r["pass_sensitivity"] is not None]
        summary = {"positions": len(group_positions), "candidates": len(group),
                   "cp_pass_pairs": len(valid), "checks": sum(r["is_check"] for r in group),
                   "captures": sum(r["is_capture"] for r in group),
                   "missing_numeric_pass": len(group) - len(valid),
                   "tags": dict(Counter(t for r in group for t in r["tags"])),
                   "rankings": {}}
        for metric in ("pass_sensitivity", "pass_relative_median"):
            top = sorted((r for r in group if r[metric] is not None), key=lambda r: (-r[metric], r["candidate_id"]))[:30]
            summary["rankings"][metric] = {
                "n": len(top), "captures": sum(r["is_capture"] for r in top),
                "quiet": sum(not r["is_capture"] and not r["is_check"] for r in top),
                "distinct_parents": len(set(r["position_id"] for r in top)),
                "adverse_500": sum(r["candidate_eval"] <= -500 if side == "sente" else r["candidate_eval"] >= 500 for r in top),
                "ids": [r["candidate_id"] for r in top]}
        summaries[side] = summary
        payload = json.dumps({"side": side, "rows": group, "positions": group_positions,
                              "summary": summary, "manifest": manifest, "deep": deep, "audit": audit}, ensure_ascii=False)
        payload = payload.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
        (out / f"report_{side}.html").write_text(HTML.replace("__PAYLOAD__", payload), encoding="utf-8")
    write_json(out / "summary.json", summaries)
    review = select_review(rows, manifest["config"]["research"]["review_per_side"])
    write_json(out / "review_candidates.json", review)
    write_json(out / "diverse_review.json", select_diverse(rows))


HTML = r'''<!doctype html>
<html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ShogiShock · Pass pilot</title>
<style>
:root{color-scheme:light;--ink:#172b35;--muted:#50636c;--accent:#007e80;--paper:#f3f5f4}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.6 system-ui,sans-serif}
main{max-width:1360px;margin:auto;padding:26px}header{border-top:5px solid var(--accent);padding:18px 0}h1{font-size:34px;line-height:1.2;margin:12px 0}h2{font-size:21px}a{color:#007077}p{max-width:1000px}.muted{color:var(--muted)}
.stats,.controls,.boards,.plots{display:flex;gap:16px;flex-wrap:wrap}.stats div{background:white;padding:14px 24px;border-radius:8px}.stats strong{display:block;font-size:27px}.controls{position:sticky;top:0;background:#f3f5f4ed;padding:14px 0;z-index:2;align-items:center}select,input,button{padding:8px;border:1px solid #9aaeb2;border-radius:5px;background:white;color:var(--ink)}button{cursor:pointer}label{display:flex;gap:8px;align-items:center}
.plot{flex:1;min-width:300px;background:white;border:1px solid #d6dfdf;padding:12px;border-radius:10px}.plot svg{width:100%;height:auto}.plot circle:hover{r:6;fill:#be4520}.card{background:white;padding:22px;margin:20px 0;border:1px solid #d6dfdf;border-radius:10px;scroll-margin-top:95px}.card:target{border:3px solid var(--accent)}.boards figure{margin:0;flex:1;max-width:350px;min-width:235px}.boards svg{width:100%}.boards figcaption{font-weight:600}.metrics{flex:1;min-width:285px}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}td,th{padding:4px 9px;text-align:left;border-bottom:1px solid #edf0ef}td:last-child{text-align:right}.tag{font-size:12px;padding:3px 8px;background:#e8f1f1;border-radius:10px;display:inline-block;margin-right:6px}code{overflow-wrap:anywhere;white-space:pre-wrap}details{margin-top:14px}summary{cursor:pointer;color:#006e70}.notice{background:#fff2d8;padding:12px 18px;border-left:4px solid #cb953a}.pv{display:grid;grid-template-columns:110px 1fr;gap:6px}footer{margin:30px 0}.selected{outline:2px solid #b65024}@media(max-width:650px){main{padding:12px}h1{font-size:26px}.controls{position:static}.boards figure{max-width:100%}.card{padding:12px}}
</style>
<main><header><span class="muted">SHOGISHOCK / RESEARCH PILOT 01</span><h1 id="title"></h1>
<nav><a href="report_sente.html">Sente Surprise</a> · <a href="report_gote.html">Gote Surprise</a> · <a href="analysis.md">実験考察</a> · <a href="candidates.json">全候補JSON</a></nav>
<p>評価値は常に <b>正＝先手有利、負＝後手有利</b>。passは非合法な「何もしない」を用いた反実仮想です。人間が誤る確率や奇襲の新規性は、まだ測定していません。</p>
<p class="notice" id="notice"></p><div class="stats" id="stats"></div></header>
<section class="plots"><div class="plot"><h2>Raw pass sensitivity</h2><div id="raw"></div></div><div class="plot"><h2>Relative pass sensitivity</h2><div id="relative"></div></div></section>
<p class="muted">全CPペアを描画。青＝非駒取り、橙＝駒取り。点をクリックすると候補詳細へ移動します。詰み／欠測は数値化せず、カードに残します。relative＝同一元局面の中央値との差。</p>
<div class="controls"><label>並べ替え <select id="sort"><option value="pass_sensitivity">raw pass</option><option value="pass_relative_median">relative pass</option><option value="candidate_eval">engine eval（先手視点・降順）</option><option value="candidate_eval_loss">理論コスト</option></select></label>
<label>表示 <select id="filter"><option value="all">すべて</option><option value="diverse">各元局面から1件</option><option value="quiet">王手・駒取り以外</option><option value="check">王手（pass不能を含む）</option><option value="adverse">奇襲側に500cp以上不利</option><option value="deep">深掘り済み</option><option value="audit">全合法応手の診断済み</option></select></label>
<label>検索 <input id="query" placeholder="USI / ID / 戦型"></label><span id="count"></span></div>
<div id="picked"></div><div id="cards"></div><button id="more">次の30件</button><footer class="muted">engine cache・候補checkpointを保存。候補を評価値で除外しません。one-shotも正式な成果ですが、現段階の分類は未確定です。</footer></main>
<script id="data" type="application/json">__PAYLOAD__</script>
<script>
const D=JSON.parse(document.getElementById('data').textContent), $=id=>document.getElementById(id);
const esc=x=>String(x??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=x=>x===null||x===undefined?'—':typeof x==='number'?(Number.isInteger(x)?x.toLocaleString():x.toFixed(2)):esc(x);
const score=r=>!r?'—':(r.score.bound==='upperbound'?'≤ ':r.score.bound==='lowerbound'?'≥ ':'')+(r.score.score_type==='cp'?fmt(r.score.score_cp):r.score.score_type==='mate'?'mate '+r.score.mate_distance:'unknown');
const pieces={P:'歩',L:'香',N:'桂',S:'銀',G:'金',B:'角',R:'飛',K:'玉','+P':'と','+L':'杏','+N':'圭','+S':'全','+B':'馬','+R':'龍'};
function board(sfen,move){
 const [layout,turn,hands]=sfen.split(' ');let cells='', y=0, last=move?move.slice(-2):'';if(move?.endsWith('+'))last=move.slice(-3,-1);
 for(const row of layout.split('/')){let x=0,prom='';for(const ch of row){if(ch==='+'){prom='+';continue}if(/[1-9]/.test(ch)){x+=Number(ch);continue}
 const cx=35+x*32,cy=55+y*32,key=prom+ch.toUpperCase(),white=ch===ch.toLowerCase();
 if(String(9-x)+'abcdefghi'[y]===last)cells+=`<rect x="${cx-16}" y="${cy-16}" width="32" height="32" fill="#ffda8b"/>`;
 cells+=`<text x="${cx}" y="${cy+7}" text-anchor="middle" font-size="22" fill="${prom?'#a33025':'#172b35'}" ${white?`transform="rotate(180 ${cx} ${cy})"`:''}>${pieces[key]}</text>`;prom='';x++}y++}
 let grid='';for(let i=0;i<=9;i++){grid+=`<path d="M${19+i*32} 39V327 M19 ${39+i*32}H307" stroke="#8d805f" stroke-width=".7"/>`;if(i<9)grid+=`<text x="${35+i*32}" y="33" text-anchor="middle" font-size="10">${9-i}</text><text x="318" y="${59+i*32}" font-size="10">${'一二三四五六七八九'[i]}</text>`}
 let hand=['',''];let n='';for(const ch of hands){if(/[0-9]/.test(ch)){n+=ch;continue}if(ch==='-')continue;hand[ch===ch.toUpperCase()?0:1]+=pieces[ch.toUpperCase()]+(n||'')+' ';n=''}
 return `<svg role="img" aria-label="将棋盤 ${esc(sfen)}" viewBox="0 0 340 358"><rect width="340" height="358" rx="6" fill="#f5e7c9"/><text x="19" y="18" font-size="12">後手 持駒：${hand[1]||'なし'}</text>${grid}${cells}<text x="19" y="349" font-size="12">先手 持駒：${hand[0]||'なし'} / ${turn==='b'?'先手':'後手'}番</text></svg>`;
}
function plot(id,metric){
 const rows=D.rows.filter(r=>Number.isFinite(r.candidate_eval)&&Number.isFinite(r[metric]));if(!rows.length){$(id).textContent='CPペアなし';return}
 const xs=rows.map(r=>r.candidate_eval),ys=rows.map(r=>r[metric]);let xmin=Math.min(...xs),xmax=Math.max(...xs),ymin=Math.min(...ys),ymax=Math.max(...ys);if(xmin===xmax)xmax++;if(ymin===ymax)ymax++;
 const x=v=>65+(v-xmin)/(xmax-xmin)*475,y=v=>270-(v-ymin)/(ymax-ymin)*225;let svg='';
 for(let i=0;i<5;i++){const xv=xmin+(xmax-xmin)*i/4,yv=ymin+(ymax-ymin)*i/4;svg+=`<path d="M65 ${y(yv)}H540" stroke="#e6ecec"/><text x="60" y="${y(yv)+4}" text-anchor="end" font-size="11">${Math.round(yv)}</text><text x="${x(xv)}" y="290" text-anchor="middle" font-size="11">${Math.round(xv)}</text>`}
 for(const r of rows)svg+=`<a href="#${r.candidate_id}" data-pick="${r.candidate_id}"><circle cx="${x(r.candidate_eval)}" cy="${y(r[metric])}" r="3" opacity=".55" fill="${r.is_capture?'#b95b29':'#007e80'}"><title>${r.move} eval=${r.candidate_eval} ${metric}=${r[metric]}</title></circle></a>`;
 $(id).innerHTML=`<svg viewBox="0 0 580 325" role="img" aria-label="候補評価と${metric}の散布図">${svg}<text x="300" y="315" text-anchor="middle" font-size="12">candidate engine eval / cp（先手視点）</text><text x="65" y="20" font-size="12">${metric} / cp</text></svg>`;
}
const ranked={};for(const field of ['pass_sensitivity','pass_relative_median']){ranked[field]={};D.rows.filter(r=>r[field]!==null).sort((a,b)=>b[field]-a[field]||a.candidate_id.localeCompare(b.candidate_id)).forEach((r,i)=>ranked[field][r.candidate_id]=i+1)}
function card(r,selected=false){
 const p=D.positions[r.position_id],metrics=[['best eval',score(r.best)],['candidate / normal eval',score(r.normal)],['candidate eval loss',fmt(r.candidate_eval_loss)],['pass eval',score(r.passed)],['pass_eval_delta',fmt(r.pass_eval_delta)],['pass_sensitivity',fmt(r.pass_sensitivity)],['pass_relative_median',fmt(r.pass_relative_median)],['pass_percentile',fmt(r.pass_percentile)],['pass_zscore',fmt(r.pass_zscore)],['ply',p.ply],['is_check / is_capture',`${r.is_check} / ${r.is_capture}`],['position / move frequency',`${r.position_frequency} / ${r.candidate_move_frequency}`],['resulting position frequency',r.resulting_position_frequency]];
 let deep='';for(const [nodes,d] of Object.entries(D.deep[r.candidate_id]||{}))deep+=`<tr><td>${fmt(Number(nodes))}</td><td>${score(d.normal)}</td><td>${score(d.passed)}</td><td>${fmt(d.pass_sensitivity)}</td></tr><tr><td colspan="4"><small>normal PV: ${esc(d.normal.pv.join(' '))}<br>pass PV: ${esc(d.passed?.pv.join(' '))}</small></td></tr>`;
 return `<article class="card ${selected?'selected':''}" id="${selected?'selected-':''}${r.candidate_id}"><h2>Raw #${ranked.pass_sensitivity[r.candidate_id]||'—'} · Relative #${ranked.pass_relative_median[r.candidate_id]||'—'}　${esc(r.move)}</h2><p><span class="tag">${esc(p.families.join(' / '))}</span>${r.tags.map(t=>`<span class="tag">${t}</span>`).join('')}<span class="tag">${r.surprise_type}</span></p>
 <div class="boards"><figure><figcaption>候補前</figcaption>${board(p.sfen)}</figure><figure><figcaption>候補後：${esc(r.move)}</figcaption>${board(r.resulting_sfen,r.move)}</figure><div class="metrics"><table>${metrics.map(([k,v])=>`<tr><td>${k}</td><td>${v}</td></tr>`).join('')}</table></div></div>
 ${!r.pass_applicable?`<p class="notice">pass_applicable=false: ${esc(r.pass_reason)}</p>`:''}
 <details ${selected?'open':''}><summary>SFEN・手順・PV・出現手順・深掘り</summary><p>ID: <code>${r.candidate_id}</code><br>SFEN: <code>${esc(p.sfen)}</code><br>候補後: <code>${esc(r.resulting_sfen)}</code></p><div class="pv"><b>move history</b><code>${esc(p.move_history.join(' '))||'startpos'}</code><b>best PV</b><code>${esc(r.best.pv.join(' '))}</code><b>candidate PV</b><code>${esc([r.move,...r.normal.pv].join(' '))}</code><b>pass PV</b><code>${esc(r.passed?.pv.join(' '))}</code></div><p class="muted">candidate PVは候補手から、pass PVは仮想pass後から開始。PV末尾（最大8ply）の駒損proxy: ${r.pv_material_loss}。タグは証明ではありません。</p><p>出典: ${esc(p.source)} / ${esc(p.frequency_semantics)}</p><details><summary>alternative move orders (${p.alternative_move_orders.length})</summary>${p.alternative_move_orders.map(m=>`<p><code>${esc(m.join(' '))||'startpos'}</code></p>`).join('')}</details>${deep?`<h3>探索量比較（relativeの深掘り再計算は未実施）</h3><table><tr><th>nodes</th><th>normal</th><th>pass</th><th>sensitivity</th></tr>${deep}</table>`:''}${auditTable(r)}</details></article>`;
}
function auditTable(r){const a=D.audit[r.candidate_id];if(!a)return '';const rows=a.responses.slice().sort((x,y)=>D.side==='sente'?(x.engine_eval??Infinity)-(y.engine_eval??Infinity):(y.engine_eval??-Infinity)-(x.engine_eval??-Infinity));return `<h3>合法応手による反証診断</h3><p>${a.nodes_budget} nodes / 全${a.legal_reply_count}応手。十分良い応手数（50/100/200/300cp）: ${[50,100,200,300].map(t=>a.good_response_counts[t].count).join(' / ')}。確率ではなく、P_goodは未測定です。</p><table><tr><th>応手</th><th>engine eval</th><th>PV</th></tr>${rows.map(x=>`<tr><td>${esc(x.move)}</td><td>${score(x.result)}</td><td><code>${esc(x.result.pv.join(' '))}</code></td></tr>`).join('')}</table>`}
let limit=30;
function render(){const field=$('sort').value,q=$('query').value.toLowerCase(),filter=$('filter').value;let rows=D.rows.filter(r=>{const p=D.positions[r.position_id];return (!q||(r.move+' '+r.candidate_id+' '+p.families.join(' ')).toLowerCase().includes(q))&&(filter==='all'||filter==='diverse'||filter==='quiet'&&!r.is_check&&!r.is_capture||filter==='check'&&r.is_check||filter==='deep'&&D.deep[r.candidate_id]||filter==='audit'&&D.audit[r.candidate_id]||filter==='adverse'&&r.candidate_eval!==null&&(D.side==='sente'?r.candidate_eval<=-500:r.candidate_eval>=500))});rows.sort((a,b)=>(b[field]??-Infinity)-(a[field]??-Infinity)||a.candidate_id.localeCompare(b.candidate_id));if(filter==='diverse'){const seen=new Set();rows=rows.filter(r=>{if(seen.has(r.position_id))return false;seen.add(r.position_id);return true})}$('count').textContent=`${rows.length}件 / 表示${Math.min(limit,rows.length)}件`;$('cards').innerHTML=rows.slice(0,limit).map(r=>card(r)).join('');$('more').hidden=rows.length<=limit;}
function pick(id){const r=D.rows.find(r=>r.candidate_id===id);if(!r)return;$('picked').innerHTML=card(r,true);$('picked').scrollIntoView({behavior:'smooth',block:'start'});}
document.addEventListener('click',e=>{const a=e.target.closest('[data-pick]');if(a){e.preventDefault();history.replaceState(null,'','#'+a.dataset.pick);pick(a.dataset.pick)}});
window.addEventListener('hashchange',()=>pick(location.hash.slice(1)));
for(const id of ['sort','filter','query'])$(id).addEventListener('input',()=>{limit=30;render()});$('more').onclick=()=>{limit+=30;render()};
$('title').textContent=(D.side==='sente'?'Sente':'Gote')+' Surprise / Pass探索';document.title=$('title').textContent;
$('notice').textContent=`${D.manifest.complete?'走査完了':'部分結果'}。10k等の浅い探索には誤差があります。種局面は研究用作成手順です。頻度は収録手順内の回数で、人間棋譜頻度ではありません。探索量 normal=${D.manifest.config.search.shallow_nodes}, pass=${D.manifest.config.search.pass_nodes} nodes。`;
$('stats').innerHTML=[['種局面',D.summary.positions],['全合法手候補',D.summary.candidates],['CP passペア',D.summary.cp_pass_pairs],['王手候補',D.summary.checks]].map(([k,v])=>`<div>${k}<strong>${fmt(v)}</strong></div>`).join('');
plot('raw','pass_sensitivity');plot('relative','pass_relative_median');render();if(location.hash)pick(location.hash.slice(1));
</script></html>'''
