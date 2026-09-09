"""Render sealed measurements only; no acquisition, fit or evaluation."""
import html
import json
from pathlib import Path

from surprise.frozen_policy import verify_freeze, sha
from surprise.response_calibration import SETS

root=Path('reports/independent_policy_validation')
verify_freeze()
seal=json.loads((root/'measurement_seal.json').read_text())
assert sha(root/'metrics.json')==seal['metrics_sha256']
metrics=json.loads((root/'metrics.json').read_text())
summary=json.loads((root/'dataset_summary.json').read_text())
old=json.loads(Path('reports/response_calibration/metrics.json').read_text())
esc=lambda x:html.escape(str(x))
fmt=lambda x:'NA' if x is None else f'{x:.4f}'
parts=['<!doctype html><html lang="ja"><meta charset="utf-8"><title>Independent policy validation</title>',
       '<style>body{font-family:system-ui;max-width:1150px;margin:2em auto;padding:1em}table{border-collapse:collapse}td,th{padding:.5em;border:1px solid #ccc}section{margin:2em 0}pre{white-space:pre-wrap}</style>',
       '<h1>凍結モデルの独立確認</h1><p>再fit・再選択・新candidate scanなし。既知アカウント非重複の便宜標本。新標本での結果を見てモデルを修正しません。</p>',
       '<p><a href="analysis.md">研究判断</a> · <a href="SAMPLING_PLAN.md">取得前計画</a> · <a href="metrics.json">全指標JSON</a></p>',
       '<h2>Dataset</h2><pre>'+esc(json.dumps(summary,ensure_ascii=False,indent=2))+'</pre>']
comparison={}
for mode,d in metrics.items():
    comparison[mode]={'prior_exploratory_sample_scope':'old full sample included correspondence; not paired with confirmation',
                      'sets':{}}
    parts.append(f'<section><h2>{mode} frozen snapshot: {esc(d["frozen_selected"])}</h2><p>inherited relative gate={d["inherited_relative_gate"]}; candidate promotion remains disabled</p>')
    parts.append('<table><tr><th>model</th><th>NLL</th><th>multiclass Brier</th><th>top1/3/5</th><th>top ECE</th></tr>')
    for name in ('old','new'):
        m=d[name]['overall']
        parts.append(f'<tr><td>{name}</td><td>{fmt(m.get("nll"))}</td><td>{fmt(m.get("brier"))}</td><td>{" / ".join(fmt(m.get(k)) for k in ("top1","top3","top5"))}</td><td>{fmt(m.get("ece"))}</td></tr>')
    parts.append('</table>')
    for event in SETS:
        previous=old[mode]['test'][old[mode]['selected']]['sets'][event]
        comparison[mode]['sets'][event]={'old_exploratory_selected':previous,'independent_old_model':d['old']['sets'][event],
                                        'independent_frozen_selected':d['new']['sets'][event]}
        parts.append(f'<h3>{event}</h3><table><tr><th>model</th><th>opportunities / games / players / movers</th><th>observed</th><th>predicted</th><th>Brier</th><th>ECE</th></tr>')
        svg='<path d="M30 230L230 30" stroke="#aaa"/>'
        for name,color in [('old','#777'),('new','#008878')]:
            m=d[name]['sets'][event]
            counts=' / '.join(str(m[k]) for k in ('opportunity_count','distinct_games','distinct_players_both_sides','distinct_actual_movers'))
            parts.append(f'<tr><td>{name}</td><td>{counts}</td><td>{fmt(m.get("observed_probability"))}</td><td>{fmt(m.get("predicted_probability"))}</td><td>{fmt(m.get("brier"))}</td><td>{fmt(m.get("ece"))}</td></tr>')
            for b in m.get('calibration_bins',[]):
                if b['n']:svg+=f'<circle cx="{30+200*b["predicted"]}" cy="{230-200*b["observed"]}" r="4" fill="{color}"><title>{name}: n={b["n"]}</title></circle>'
        parts.append('</table><p>横＝予測、縦＝実測。灰＝旧モデル、緑＝凍結補正モデル。</p><svg width="260" viewBox="0 0 260 260">'+svg+'</svg>')
    parts.append('</section>')
parts.append('</html>')
(root/'report.html').write_text('\n'.join(parts))
(root/'exploratory_comparison.json').write_text(json.dumps(comparison,ensure_ascii=False,indent=2)+'\n')
print('Rendered sealed metrics and old exploratory comparison; no model calls.')
