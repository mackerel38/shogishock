"""Read-only baseline join, conservative v2 planning, offline diagnostic cards."""
import argparse
import json
from pathlib import Path

import yaml

from .obvious import escalation_reasons
from .report import HTML as PILOT_HTML
from .research import write_json


def plan_candidate(row, observed, total, diagnostic, cfg):
    advantage = row['best_eval'] * (1 if row['attacker_side'] == 'sente' else -1) if row['best_eval'] is not None else None
    reach = observed['reach_probability'] if observed else (0.0 if total else None)
    tol = cfg['neutralize_tolerance']
    neutral = diagnostic.get('obvious_reply_neutralizes') if diagnostic else None
    fraction = diagnostic.get(f'good_reply_fraction_{tol}') if diagnostic else None
    reasons = escalation_reasons(advantage, reach, neutral, fraction, cfg)
    if total < cfg['minimum_games_before_scan']:
        reasons.append('insufficient_reach_sample')
    # Even a large convenience sample is not automatically representative.
    reasons.append('sampling_design_not_validated')
    if neutral is None: reasons.append('obvious_reply_unresolved')
    if fraction is None: reasons.append('legal_fragility_unresolved')
    return {'candidate_id': row['candidate_id'], 'position_id': row['position_id'],
        'attacker_side': row['attacker_side'], 'parent_attacker_advantage': advantage,
        'parent_already_favorable': advantage >= cfg['parent_favorable_cp'] if advantage is not None else None,
        'games_reaching_position': observed['games_reaching_position'] if observed else 0,
        'total_games': total, 'reach_probability': reach,
        'population_reach_probability': None, 'sample_observed': observed is not None,
        'not_escalated_reason': reasons, 'escalated': False}


def run(config):
    cfg = yaml.safe_load(Path(config).read_text())
    out, baseline = Path(cfg['output']), Path(cfg['baseline'])
    load = lambda p: json.loads(p.read_text())
    reach = load(out / 'reach_positions.json')
    observed = {r['position_id']: r for r in reach}
    total = load(out / 'reach_summary.json')['accepted_games']
    reviewed = load(out / 'pilot_diagnostics.json')
    lookup = {r['candidate_id']: r for r in reviewed}
    rows = load(baseline / 'candidates.json')
    positions = {p['position_id']: p for p in load(baseline / 'positions.json')}
    plan = []
    for row in rows:
        r = lookup.get(row['candidate_id'], {})
        diagnostic = r.get('confirmation') or r.get('obvious_diagnostic')
        p = plan_candidate(row, observed.get(row['position_id']), total, diagnostic, cfg['selection'])
        plan.append(p)
        if r:
            r.update(p, move_history=positions[row['position_id']]['move_history'])
    write_json(out / 'candidate_plan.json', plan)
    join_summary = {'retained_candidates': len(plan), 'escalated': 0, 'accepted_games': total,
        'baseline_positions_observed': sum(pid in observed for pid in positions),
        'baseline_positions': len(positions),
        'review_candidates_observed': sum(r['sample_observed'] for r in reviewed),
        'review_candidates': len(reviewed),
        'observed_review_ids': [r['candidate_id'] for r in reviewed if r['sample_observed']],
        'decision': 'No new scan: convenience sample only; design broader sampling first.'}
    write_json(out / 'planning_summary.json', join_summary)
    board_js = PILOT_HTML[PILOT_HTML.index('const pieces='):PILOT_HTML.index('function plot(')]
    for side in ('sente', 'gote'):
        payload = json.dumps({'side': side, 'rows': [r for r in reviewed if r['attacker_side'] == side],
            'reach': [r for r in reach if r['side_to_move'] == side][:10]}, ensure_ascii=False).replace('<', '\\u003c')
        (out / f'report_{side}.html').write_text(HTML.replace('__DATA__', payload).replace('__BOARD__', board_js), encoding='utf-8')
    print(json.dumps(join_summary, ensure_ascii=False))


HTML = r'''<!doctype html><html lang="ja"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>ShogiShock / v2診断</title>
<style>body{font:15px/1.65 system-ui;background:#f4f6f5;color:#183039;margin:20px auto;max-width:1280px;padding:12px}a{color:#00777d}article,section{background:white;border:1px solid #cad7d5;border-radius:8px;padding:18px;margin:18px 0}article:target{border:3px solid #00777d}.boards,.plots{display:flex;flex-wrap:wrap;gap:16px}.boards figure{width:275px;margin:0}.boards svg,.plot svg{width:100%}.plot{width:570px}table{border-collapse:collapse;width:100%}td,th{padding:5px;border-bottom:1px solid #ddd;text-align:left}code{overflow-wrap:anywhere}.notice{background:#fff1d7;padding:15px}details{margin:14px 0}h1{font-size:28px}select{padding:8px}pre{white-space:pre-wrap}</style>
<h1 id="title"></h1><nav><a href="report_sente.html">Sente Surprise</a> · <a href="report_gote.html">Gote Surprise</a> · <a href="analysis.md">考察</a> · <a href="SOURCES.md">データ出典・利用条件</a></nav>
<p class="notice">旧pilotのraw / relative各上位30の和集合を再診断。新しいscanではありません。全評価値は正＝先手有利。passは即時対応要求のcheap featureであり、奇襲強度ではありません。reachは非ランダムな19対局内の観測値で、母集団の到達確率は不明です。</p>
<div class="plots" id="plots"></div><p>横軸は各図のラベル、縦軸はいずれもraw pass sensitivity。橙＝10kで明白な良応手あり、青＝未成立。点から候補カードへ移動。</p>
<label>並べ替え <select id="sort"><option value="pass_sensitivity">raw pass</option><option value="pass_relative_median">relative pass</option><option value="ply">ply</option></select></label>
<div id="cards"></div><h2>実棋譜で観測された局面（参考・新scan未実施）</h2><div id="reach"></div>
<script id="data" type="application/json">__DATA__</script><script>
const D=JSON.parse(document.getElementById('data').textContent),$=id=>document.getElementById(id);
const esc=x=>String(x??'未確定').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const score=r=>!r?'未解析':r.score.score_type==='cp'?`${r.score.bound} ${r.score.score_cp}`:r.score.score_type==='mate'?`mate ${r.score.mate_distance}`:'unknown';
__BOARD__
function chart(field,label){const xs=D.rows.map(r=>r[field]),ys=D.rows.map(r=>r.pass_sensitivity);let lo=Math.min(...xs),hi=Math.max(...xs),a=Math.min(...ys),b=Math.max(...ys);if(lo===hi)hi++;if(a===b)b++;
const x=v=>60+(v-lo)/(hi-lo)*450,y=v=>240-(v-a)/(b-a)*200;
let s='';for(let i=0;i<5;i++){let vx=lo+(hi-lo)*i/4,vy=a+(b-a)*i/4;s+=`<path d="M60 ${y(vy)}H510" stroke="#ddd"/><text x="3" y="${y(vy)+4}" font-size="11">${Math.round(vy)}</text><text x="${x(vx)}" y="263" font-size="11" text-anchor="middle">${Math.round(vx)}</text>`}
for(const r of D.rows)s+=`<a href="#${esc(r.candidate_id)}"><circle cx="${x(r[field])}" cy="${y(r.pass_sensitivity)}" r="4" fill="${r.obvious_diagnostic.obvious_reply_neutralizes?'#c66b22':'#007e80'}"><title>${esc(r.move)} ${label}=${r[field]}</title></circle></a>`;
return `<section class="plot"><h2>${esc(label)} × raw pass</h2><svg viewBox="0 0 560 300">${s}<text x="280" y="290" text-anchor="middle">${esc(label)}</text></svg></section>`}
function card(r){const d=r.confirmation||r.obvious_diagnostic,sh=r.obvious_diagnostic;
d.responses.forEach(x=>x.tags=x.signals);
const values=[['parent engine eval',r.best_eval],['parent attacker advantage（派生量）',r.parent_attacker_advantage],['candidate engine eval',r.candidate_eval],['candidate eval loss',r.candidate_eval_loss],['pass eval',score(r.passed)],['raw / relative pass',`${r.pass_sensitivity} / ${r.pass_relative_median}`],['ply / check / capture',`${r.ply} / ${r.is_check} / ${r.is_capture}`],['candidate piece capturable',d.candidate_piece_capturable],['normal first reply',r.normal_first_reply],['first reply captures candidate',r.normal_first_reply_captures_candidate],['sample reach',`${r.games_reaching_position} / ${r.total_games} = ${(r.reach_probability*100).toFixed(1)}%（母集団不明）`],['obvious reply (10k)',`${sh.obvious_reply_move} / eval ${sh.obvious_reply_eval} / gap ${sh.obvious_reply_gap_from_optimal}`],['neutralizes (10k, tolerance 100)',sh.obvious_reply_neutralizes],['表示診断のbudget',d.nodes],['obvious reply / eval',`${d.obvious_reply_move} / ${d.obvious_reply_eval}`],['gap from optimal estimate',d.obvious_reply_gap_from_optimal],['neutralizes (表示budget)',d.obvious_reply_neutralizes],['root estimate',score(d.root)],['legal replies / evaluated',`${d.legal_reply_count} / ${d.responses.length}`],...[50,100,200,300].map(t=>[`good replies ${t}cp: count / fraction`,`${d['good_reply_count_'+t]??'未確定'} / ${d['good_reply_fraction_'+t]??'未確定'}`])];
return `<article id="${esc(r.candidate_id)}"><h2>${esc(r.move)} · ${esc(r.candidate_id)}</h2><div class="boards"><figure><figcaption>候補前</figcaption>${board(r.sfen)}</figure><figure><figcaption>候補後</figcaption>${board(r.resulting_sfen,r.move)}</figure></div><table>${values.map(([k,v])=>`<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join('')}</table><p>昇格保留理由: ${esc(r.not_escalated_reason.join(', '))}</p><p>partial countは解析済み応手内のみ。fractionは全合法応手のCP比較が可能な場合だけ。詰み・bound混在は未確定。Human Policy / P_goodではありません。</p><details><summary>SFEN・手順・PV・全診断応手</summary><p>SFEN: <code>${esc(r.sfen)}</code><br>履歴: <code>${esc(r.move_history.join(' '))}</code><br>best PV: ${esc(r.best.pv.join(' '))}<br>candidate PV: ${esc(r.normal.pv.join(' '))}<br>pass PV: ${esc(r.passed?.pv.join(' '))}</p><table><tr><th>応手・属性</th><th>評価</th><th>gap</th><th>PV</th></tr>${d.responses.map(x=>`<tr><td>${esc(x.move)} ${esc(x.tags?.join(', '))}</td><td>${esc(score(x.result))}</td><td>${esc(x.gap_from_optimal_estimate)}</td><td>${esc(x.result.pv.join(' '))}</td></tr>`).join('')}</table></details></article>`}
function render(){const f=$('sort').value;$('cards').innerHTML=D.rows.slice().sort((a,b)=>b[f]-a[f]).map(card).join('')}
$('title').textContent=(D.side==='sente'?'Sente':'Gote')+' Surprise / pilot反証診断 ('+D.rows.length+'候補)';
$('plots').innerHTML=chart('best_eval','parent engine eval（先手視点）')+chart('ply','ply');
$('sort').addEventListener('change',render);render();
$('reach').innerHTML=D.reach.map(r=>`<section><p>sample reach ${r.games_reaching_position}/${r.total_games} (${(r.reach_probability*100).toFixed(1)}%) / ply ${r.min_ply}–${r.max_ply} / parent eval未解析</p><div class="boards"><figure>${board(r.sfen)}</figure></div><p>実着手回数: ${esc(JSON.stringify(r.move_distribution))}</p></section>`).join('');
</script></html>'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config/reach_pilot.yaml')
    run(parser.parse_args().config)
