"""Render saved research data only: no API, model training, or engine calls."""
import html
import json
from pathlib import Path

from surprise.report import HTML

esc=lambda x:html.escape(str(x))
load=lambda p:json.loads(Path(p).read_text())
style=HTML.split('<style>',1)[1].split('</style>',1)[0]
board=HTML[HTML.index('const pieces='):HTML.index('function plot(')]
js="const esc=x=>String(x??'—').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c]));\n"+board+"\ndocument.querySelectorAll('[data-sfen]').forEach(e=>e.innerHTML=board(e.getAttribute('data-sfen')));"
out=Path('reports/human_e2e')
rows=load(out/'candidates.json');positions={p['position_id']:p for p in load(out/'positions.json')}
responses={r['candidate_id']:r for r in load(out/'human_responses.json')}
for side in ('sente','gote'):
    title=('Sente' if side=='sente' else 'Gote')+' Surprise / 小規模Human Policy実験'
    parts=[f'<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>{style}</style><main><h1>{title}</h1>',
        '<nav><a href="report_sente.html">先手</a> · <a href="report_gote.html">後手</a> · <a href="analysis.md">研究判断</a> · <a href="../human_policy_v2/calibration.html">予測校正</a></nav>',
        '<p class="notice">正＝先手有利。全て10kの探索推定値。P_good / human_gapは未検証の反実仮想Human Policyによる試算で、実測勝率ではありません。明白な取りへ低すぎる確率を置く反例を確認したため、大量scanには使用しません。</p>']
    for r in rows:
        if r['attacker_side']!=side or r['candidate_id'] not in responses:continue
        p=positions[r['position_id']];d=responses[r['candidate_id']]
        metrics=[('parent engine eval',r['best_eval']),('parent book eval（別の評価源）',p['parent_book_eval_sente']),
            ('candidate engine eval',r['candidate_eval']),('candidate eval loss',r['candidate_eval_loss']),
            ('reach sample',f"{r['reach_sample_count']}/612 = {r['reach_probability']:.3%}; {r['reach_distinct_players']} players"),
            ('ply / candidate capture / check',f"{p['ply']} / {r['is_capture']} / {r['is_check']}"),
            ('policy exact support',r['policy_exact_support']),('covered probability',r['covered_probability']),
            ('V_optimal（応手別探索の最良推定値）',r['V_optimal']),('E_human',round(r['E_human'],2)),
            ('human_eval_delta',round(r['human_eval_delta'],2)),('human_gap',round(r['human_gap'],2)),
            ('obvious reply neutralizes',r['obvious_reply_neutralizes']),('pass sensitivity（補助値）',r['pass_sensitivity'])]
        for t in ('50','100','200','300'):metrics.append((f'P_good {t}cp [lower, upper]',f"[{r['P_good'][t]['lower']:.4f}, {r['P_good'][t]['upper']:.4f}]"))
        parts.append(f'<article class="card" id="{r["candidate_id"]}"><h2>{esc(r["move"])} / {esc(r["selection_stratum"])}</h2><p><a href="../../exports/human_e2e/{side}_{r["candidate_id"]}.kif">ShogiHome KIF</a></p><div class="boards"><figure><figcaption>候補前</figcaption><div data-sfen="{esc(p["sfen"])}"></div></figure><figure><figcaption>候補後</figcaption><div data-sfen="{esc(r["resulting_sfen"])}"></div></figure></div>')
        parts.append('<table>'+''.join(f'<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>' for k,v in metrics)+'</table>')
        parts.append(f'<p>保留理由: {esc(", ".join(r["not_escalated_reason"]))}</p><p>履歴: <code>{esc(" ".join(p["move_history"]))}</code><br>candidate PV: <code>{esc(" ".join(r["normal"]["pv"]))}</code></p>')
        parts.append('<details><summary>全合法応手とHuman Policy確率・PV</summary><table><tr><th>応手</th><th>確率</th><th>評価</th><th>good 100cp</th><th>signal / PV</th></tr>')
        for x in d['responses']:
            parts.append(f'<tr><td>{x["move"]}</td><td>{x["human_probability"]:.4%}</td><td>{x["engine_eval"]}</td><td>{x["good_by_tolerance"]["100"]}</td><td>{esc(", ".join(x["signals"]))}<br>{esc(" ".join(x["result"]["pv"]))}</td></tr>')
        parts.append('</table></details></article>')
    parts.append('<p>KIF generated / branches validated / user visual review required.</p></main><script>'+js+'</script></html>')
    (out/f'report_{side}.html').write_text('\n'.join(parts),encoding='utf-8')

metrics=load('reports/human_policy_v2/policy_metrics.json')
parts=[f'<!doctype html><html lang="ja"><meta charset="utf-8"><title>Human Policy calibration</title><style>{style}</style><main><h1>Held-out reliability</h1><p>top-label calibration。P_goodという応手集合の校正ではなく、奇襲後の分布外局面へも保証されません。点は10個のconfidence binのうち非空のもの。横軸＝予測confidence、縦軸＝実際のtop1正答率、対角線＝一致。</p>']
for mode,d in metrics.items():
    parts.append(f'<section class="card"><h2>{mode} split</h2><p>games: {esc(d["games"])}</p>')
    for kind,color in [('popularity','#888'),('exact','#b95b29'),('hierarchical','#007e80')]:
        m=d['models'][kind]['test'];points=m['reliability']
        svg='<path d="M40 250L260 30" stroke="#aaa"/>'
        for b in points:
            if b['n']:svg+=f'<circle cx="{40+220*b["confidence"]}" cy="{250-220*b["accuracy"]}" r="{min(10,2+b["n"]**.5/3)}" fill="{color}"><title>n={b["n"]}, confidence={b["confidence"]:.3f}, accuracy={b["accuracy"]:.3f}</title></circle>'
        parts.append(f'<h3>{kind}: NLL {m["nll"]:.3f}, ECE {m["ece"]:.3f}</h3><svg width="300" viewBox="0 0 300 280">{svg}<text x="40" y="275">0</text><text x="250" y="275">1</text><text x="20" y="30">1</text></svg>')
    parts.append('</section>')
parts.append('</main></html>')
Path('reports/human_policy_v2/calibration.html').write_text('\n'.join(parts),encoding='utf-8')
print('Rendered per-side E2E boards and held-out reliability charts from saved data.')
