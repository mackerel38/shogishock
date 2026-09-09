"""Research interpretation, fixed regression fixtures and classified KIF review."""
import copy
import hashlib
import html
import json
import random
from collections import defaultdict
from pathlib import Path

import shogi
import yaml

from .response_calibration import (OUT, SETS, PRIMARY, prepare, probabilities, evaluate,
                                   cached_features, shrink, event_metric)
from .response_cache import ResponseDiagnosticCache
from .human_policy import Policy, examples, describe
from .human_review import validate_kif
from .human_response import response_metrics
from .kif_export import ExportedKif, VariationNode, _add_branch, to_kif
from .research import identity, write_json, cp
from .report import HTML


def bootstrap(records, selected, weights):
    groups = defaultdict(lambda: {s: [] for s in PRIMARY})
    for r in records:
        old, new = probabilities(r,'existing',weights), probabilities(r,selected,weights)
        for j,s in enumerate(PRIMARY):
            if any(f['sets'][j] for f in r['features']):
                y = r['features'][r['label']]['sets'][j]
                a = sum(p*f['sets'][j] for p,f in zip(old,r['features']))
                b = sum(p*f['sets'][j] for p,f in zip(new,r['features']))
                groups[r['game']][s].append((b-y)**2-(a-y)**2)
    rng = random.Random(20260909)
    draws = {s:[] for s in PRIMARY}
    ids = sorted(groups)
    for _ in range(300):
        sample = rng.choices(ids,k=len(ids))
        for s in PRIMARY:
            values = [v for g in sample for v in groups[g][s]]
            if values: draws[s].append(sum(values)/len(values))
    result = {}
    for s in PRIMARY:
        values = sorted(draws[s])
        result[s] = {'valid_draws':len(values), 'delta_brier_interval95':
            [values[int(.025*len(values))], values[min(len(values)-1,int(.975*len(values)))]] if values else None}
    return result


def run():
    cfg = yaml.safe_load(Path('config/human_pilot.yaml').read_text())
    data = examples(cfg)
    splits = json.loads((Path(cfg['raw_dir'])/'splits_v2.json').read_text())
    metrics = json.loads((OUT/'metrics.json').read_text())
    decision = json.loads((OUT/'decision.json').read_text())
    uncertainty = {}
    victim_slices = {}
    for mode in ('time','player','game'):
        train_ids = set(splits[mode]['train']);test_ids = set(splits[mode]['test'])
        model = Policy(data,[r for r in data['rows'] if r['game'] in train_ids],5)
        with ResponseDiagnosticCache('data/response_calibration.sqlite3') as cache:
            records = prepare(model,data,[r for r in data['rows'] if r['game'] in test_ids],cache)
        uncertainty[mode] = bootstrap(records,metrics[mode]['selected'],metrics[mode]['weights'])
        victim_slices[mode] = {}
        for label, types in [('pawn',[shogi.PAWN]),('bishop',[shogi.BISHOP,shogi.PROM_BISHOP]),
                             ('rook',[shogi.ROOK,shogi.PROM_ROOK])]:
            victim_slices[mode][label] = {}
            for name in ('existing',metrics[mode]['selected']):
                obs = []
                for r in records:
                    mask = [f['victim_piece_type'] in types for f in r['features']]
                    if not any(mask):continue
                    q = probabilities(r,name,metrics[mode]['weights'])
                    obs.append((sum(p for p,flag in zip(q,mask) if flag),int(mask[r['label']]),r['game']))
                victim_slices[mode][label][name] = event_metric(obs)
    write_json(OUT/'bootstrap.json',{'scope':'paired game clusters, descriptive reused-test intervals; player dependence remains','splits':uncertainty})
    write_json(OUT/'victim_slices.json',{'scope':'descriptive slices of already-defined victim type; not used for model selection','splits':victim_slices})
    train_ids = set(splits['time']['train'])
    model = Policy(data,[r for r in data['rows'] if r['game'] in train_ids],5)
    oldrows = {r['candidate_id']:r for r in json.loads(Path('reports/human_e2e/candidates.json').read_text())}
    oldresponses = {r['candidate_id']:r for r in json.loads(Path('reports/human_e2e/human_responses.json').read_text())}
    manual = json.loads(Path('reports/response_set_review/review_manifest.json').read_text())
    cases = []
    for case in manual['cases']:
        cid = case['candidate_id'];old = oldrows[cid]
        p = describe(old['resulting_sfen']);pid = identity(old['resulting_sfen'])
        history = case['move_history']+[case['candidate_move']]
        with ResponseDiagnosticCache('data/response_calibration.sqlite3') as cache:
            fs = cached_features(cache,p['sfen'],history)
        record = {'features':fs, 'existing':model.predict(p,pid,' '.join(history),'hierarchical',2,1),
                  **{f'shrink{k}':shrink(model,p,pid,' '.join(history),k) for k in (2,5,10)}}
        q = probabilities(record,metrics['time']['selected'],metrics['time']['weights'])
        support = sum(model.exact.get(pid,{}).values())
        responses = copy.deepcopy(oldresponses[cid]['responses'])
        indices = {f['move']:i for i,f in enumerate(fs)}
        for r in responses:
            i = indices[r['move']]
            r.update(human_probability=q[i], previous_probability=record['existing'][i],
                     response_sets=[s for s,flag in zip(SETS,fs[i]['sets']) if flag],
                     response_features=fs[i])
        # Previous full-legal 10k evaluations only, never a fresh engine invocation.
        trial = response_metrics(responses,old['V_optimal'],old['attacker_side'],[50,100,200,300]) if decision['exploratory_reweight_allowed'] else None
        result = {**case, 'selected_policy':metrics['time']['selected'], 'policy_exact_support':support,
            'low_support':support<2, 'abstain':True, 'needs_human_review':True,
            'response_set_calibration_status':'exploratory_only', 'true_human_P_good_bounds':[0,1],
            'bound_warning':'[0,1] expresses no validated human-probability claim; arithmetic model-mass bounds are different',
            'parent_eval':old['best_eval'],'candidate_eval':old['candidate_eval'],
            'reach_probability':old['reach_probability'],'obvious_reply_neutralizes':old['obvious_reply_neutralizes'],
            'previous_model_P_good':old['P_good'],'model_reweight':trial,
            'responses':responses,'resulting_sfen':old['resulting_sfen'],
            'variant_capture_mass':{name:sum(a*f['sets'][0] for a,f in zip(probabilities(record,name,metrics['time']['weights']),fs))
                                    for name in metrics['time']['test']},
            'event_mass':{s:{'old':sum(a*f['sets'][j] for a,f in zip(record['existing'],fs)),
                               'new':sum(a*f['sets'][j] for a,f in zip(q,fs))} for j,s in enumerate(SETS)}}
        warnings = []
        node = VariationNode(move=case['candidate_move'],comment=[
            f"[{case['classification']}; NOT an accepted surprise]",case['classification_reason'],
            f"parent_eval={old['best_eval']} candidate_eval={old['candidate_eval']} (positive=sente)",
            f"reach={old['reach_probability']} exact_support={support} low_support={support<2}",
            'abstain=true; calibration=exploratory_only; needs_human_review=true',
            'true human P_good unvalidated: [0,1]; not a model-coverage interval',
            f"obvious_reply_neutralizes={old['obvious_reply_neutralizes']}",
            ('MODEL ONLY: P_good='+str({t:v['value'] for t,v in trial['P_good'].items()})) if trial else 'No new E2E metrics: exploratory gate did not pass',
            (f"MODEL ONLY: E_human={trial['E_human']:.2f}; human_gap={trial['human_gap']:.2f}; coverage={trial['covered_probability']:.6f}") if trial else 'Prediction-only diagnostic',
            'parent_engine_best_pv: '+' '.join(old['best']['pv'])])
        board = shogi.Board(old['resulting_sfen'])
        for r in sorted(responses,key=lambda r:-r['human_probability']):
            _add_branch(node,[r['move']]+r['result']['pv'],[
                'response_sets: '+', '.join(r['response_sets']),
                f"Human Policy old={r['previous_probability']:.6f} new={r['human_probability']:.6f}",
                f"cached 10k engine_eval={cp(r['result'])}; obvious={r['obvious']}",
                'good replies: '+str(r['good_by_tolerance']),
                'features: '+str({k:v for k,v in r['response_features'].items() if k not in ('x','sets')})],warnings,board)
        _add_branch(node,old['normal']['pv'],['[engine PV after candidate; previous 10k]'],warnings,board)
        exported = ExportedKif(cid,case['parent_sfen'],case['move_history'],node,warnings)
        text = to_kif(exported,title='Response calibration review — abstain')
        result['kif_validation'] = validate_kif(text)
        assert not warnings
        path = Path('exports/response_calibration')/case['classification']/f"{old['attacker_side']}_{cid}.kif"
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
        result['export_kif'] = str(path)
        cases.append(result)
    for classification in ('actual_candidate','diagnostic_counterexample','control'):
        (OUT/classification).mkdir(parents=True,exist_ok=True)
        write_json(OUT/classification/'manifest.json',{'classification':classification,'cases':[c['candidate_id'] for c in cases if c['classification']==classification]})
    write_json(OUT/'review.json',{'actual_candidate_count':0,'diagnostic_count':1,'control_count':2,'cases':cases})
    render(metrics,cases)
    inputs = ['surprise/calibration_review.py','surprise/human_policy.py','surprise/obvious.py',
        'surprise/response_cache.py','surprise/kif_export.py','surprise/human_response.py',
        'reports/response_calibration/metrics.json','reports/response_calibration/decision.json',
        'reports/response_set_review/review_manifest.json','reports/human_e2e/candidates.json',
        'reports/human_e2e/human_responses.json']
    write_json(OUT/'review_provenance.json',{'sha256':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in inputs},
        'new_engine_calls':0,'old_legal_responses_reweighted':sum(len(c['responses']) for c in cases),
        'gui_visual_review':'required; not performed'})


def render(metrics,cases):
    esc = lambda x: html.escape(str(x))
    style = HTML.split('<style>',1)[1].split('</style>',1)[0]
    board_js = HTML[HTML.index('const pieces='):HTML.index('function plot(')]
    js = "const esc=x=>String(x??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c]));\n"+board_js+"\ndocument.querySelectorAll('[data-sfen]').forEach(e=>e.innerHTML=board(e.getAttribute('data-sfen')));"
    parts = [f'<!doctype html><meta charset="utf-8"><title>Response calibration review</title><style>{style}</style><main><h1>集合校正：探索的再評価</h1><p>actual_candidate 0 / diagnostic 1 / control 2。全件abstain。旧test再利用であり独立最終評価ではありません。正＝先手有利。新engine計算なし。</p>']
    for mode,d in metrics.items():
        parts.append(f'<h2>{esc(mode)}: selected {esc(d["selected"])}</h2><table><tr><th>model</th><th>NLL</th><th>Brier</th><th>primary set Brier</th></tr>')
        for name,m in d['test'].items():
            parts.append(f'<tr><td>{esc(name)}</td><td>{m["overall"]["nll"]:.4f}</td><td>{m["overall"]["brier"]:.4f}</td><td>{m["primary_mean_brier"]:.4f}</td></tr>')
        parts.append('</table>')
        for event in SETS:
            parts.append(f'<h3>{esc(event)}</h3><table><tr><th>model</th><th>n</th><th>observed</th><th>predicted</th><th>Brier</th><th>ECE</th></tr>')
            svg = '<path d="M30 230L230 30" stroke="#aaa"/>'
            for name,color in [('existing','#777'),(d['selected'],'#008878')]:
                m = d['test'][name]['sets'][event]
                parts.append(f'<tr><td>{esc(name)}</td><td>{m["sample_count"]}</td><td>{m["observed_probability"]:.3%}</td><td>{m["predicted_probability"]:.3%}</td><td>{m["brier"]:.4f}</td><td>{m["ece"]:.4f}</td></tr>')
                for b in m['calibration_bins']:
                    if b['n']:svg+=f'<circle cx="{30+200*b["predicted"]}" cy="{230-200*b["observed"]}" r="4" fill="{color}"><title>{name} n={b["n"]}</title></circle>'
            parts.append('</table><p>横＝予測mass、縦＝実測率。灰＝旧、緑＝選択モデル。</p><svg width="260" viewBox="0 0 260 260">'+svg+'</svg>')
    for c in cases:
        parts.append(f'<article><h2>{esc(c["classification"])}: {esc(c["candidate_move"])}</h2><p>{esc(c["classification_reason"])}</p><a href="../../{esc(c["export_kif"])}">ShogiHome KIF</a><div class="boards"><div data-sfen="{esc(c["parent_sfen"])}"></div><div data-sfen="{esc(c["resulting_sfen"])}"></div></div><p>support={c["policy_exact_support"]}; abstain=true; parent={c["parent_eval"]}; candidate={c["candidate_eval"]}; reach={c["reach_probability"]:.3%}</p><p>model reweight: {esc(c["model_reweight"])}</p><table><tr><th>reply</th><th>old</th><th>new</th><th>sets</th><th>engine</th></tr>')
        for r in sorted(c['responses'],key=lambda r:-r['human_probability']):
            parts.append(f'<tr><td>{r["move"]}</td><td>{r["previous_probability"]:.3%}</td><td>{r["human_probability"]:.3%}</td><td>{esc(r["response_sets"])}</td><td>{cp(r["result"])}</td></tr>')
        parts.append('</table></article>')
    parts.append('<p>KIF generated / branches validated / user visual review required.</p></main><script>'+js+'</script>')
    (OUT/'review.html').write_text('\n'.join(parts))


if __name__ == '__main__':
    run()
