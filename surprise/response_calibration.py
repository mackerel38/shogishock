"""Bounded, exploratory response-set calibration; no engine or acquisition calls."""
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import shogi
import yaml

from .human_policy import Policy, examples, normalize, metric
from .obvious import reply_features
from .position import Position
from .research import PIECE_VALUES, write_json
from .response_cache import ResponseDiagnosticCache

OUT = Path('reports/response_calibration')
SETS = ('capture_any', 'captures_candidate', 'recapture', 'material_recovery',
        'pawn_contact_capture', 'high_value_capture', 'promotion')
PRIMARY = SETS[:4]
SCHEMA = 'response-calibration-v1'


def features(sfen, history):
    """History is required to distinguish taking the last mover and recapture."""
    board = shogi.Board(sfen)
    parent = shogi.Board()
    for move in history[:-1]:
        parent.push_usi(move)
    if history:
        check = shogi.Board(parent.sfen())
        check.push_usi(history[-1])
        assert check.sfen().split()[:3] == sfen.split()[:3]
    rows = []
    for usi in sorted(m.usi() for m in board.legal_moves):
        move = shogi.Move.from_usi(usi)
        victim = board.piece_at(move.to_square)
        mover = board.piece_at(move.from_square) if move.from_square is not None else None
        capture = victim is not None
        obvious = reply_features(Position(board=parent), history[-1], usi) if history and capture else {'signals': []}
        recapturable = False
        if capture:
            after = shogi.Board(sfen)
            after.push(move)
            recapturable = any(m.to_square == move.to_square for m in after.legal_moves)
        vv = PIECE_VALUES[victim.piece_type] if victim else 0
        mv = PIECE_VALUES[mover.piece_type] if mover else 0
        recovery = capture and (not recapturable or vv > mv)
        flags = [capture, 'captures_candidate' in obvious['signals'], 'recapture' in obvious['signals'],
                 recovery, bool(victim and mover and victim.piece_type == mover.piece_type == shogi.PAWN),
                 bool(victim and victim.piece_type in (shogi.BISHOP, shogi.ROOK, shogi.PROM_BISHOP, shogi.PROM_ROOK)),
                 move.promotion]
        if history and capture:
            assert recovery == ('material_recovery_proxy' in obvious['signals'])
        gain = vv - (mv if recapturable else 0) if capture else 0
        rows.append({'move': usi, 'sets': [int(v) for v in flags],
                     'victim_piece_type': victim.piece_type if victim else None,
                     'victim_value': vv, 'mover_piece_type': mover.piece_type if mover else move.drop_piece_type,
                     'material_gain_proxy': gain, 'can_be_recaptured': recapturable,
                     'candidate_was_just_exposed': None,
                     'x': [float(v) for v in flags] + [vv/1000, max(0, gain)/1000, float(recapturable)]})
    return rows


def cached_features(cache, sfen, history):
    # One payload contains every legal response; sentinel is unambiguous and schema-specific.
    return cache.get_or_compute(sfen=sfen, move_history=history,
        candidate_move=history[-1] if history else '', reply_move='ALL_LEGAL',
        feature_schema=SCHEMA, compute=lambda: features(sfen, history))


def shrink(model, p, pid, prefix, k):
    fallback = model.predict(p, pid, prefix, 'behavior')
    counts = model.exact.get(pid, {})
    return normalize([counts.get(m, 0) + k*q for m, q in zip(p['moves'], fallback)])


def tilt(q, fs, weights):
    if not weights:
        return q
    logits = [math.log(p) + sum(w*x for w, x in zip(weights, f['x'])) for p, f in zip(q, fs)]
    peak = max(logits)
    return normalize([math.exp(v-peak) for v in logits])


def fit(records, dimensions):
    weights = [0.0]*10
    for _ in range(80):
        grad = [0.0]*10
        for r in records:
            q = tilt(r['shrink5'], r['features'], weights)
            for j in dimensions:
                grad[j] += sum(p*f['x'][j] for p, f in zip(q, r['features'])) - r['features'][r['label']]['x'][j]
        for j in dimensions:
            weights[j] -= .5*(grad[j]/len(records) + .01*weights[j])
    return weights


def event_metric(obs):
    if not obs:
        return {'sample_count': 0, 'distinct_games': 0}
    bins = []
    for i in range(10):
        group = [(p, y) for p, y, _ in obs if min(9, int(p*10)) == i]
        bins.append({'bin': i, 'n': len(group),
            'predicted': sum(p for p, y in group)/len(group) if group else None,
            'observed': sum(y for p, y in group)/len(group) if group else None})
    n = len(obs)
    return {'sample_count': n, 'distinct_games': len({g for _, _, g in obs}),
        'chosen': sum(y for p, y, _ in obs), 'observed_probability': sum(y for p,y,_ in obs)/n,
        'predicted_probability': sum(p for p,y,_ in obs)/n,
        'brier': sum((p-y)**2 for p,y,_ in obs)/n,
        'ece': sum(b['n']*abs(b['predicted']-b['observed']) for b in bins if b['n'])/n,
        'calibration_bins': bins}


def probabilities(record, name, weights):
    if name in ('existing', 'shrink2', 'shrink5', 'shrink10'):
        return record[name]
    return tilt(record['shrink5'], record['features'], weights[name])


def evaluate(records, name, weights):
    scored = []
    events = defaultdict(list)
    for r in records:
        q = probabilities(r, name, weights)
        order = sorted(range(len(q)), key=lambda j: (-q[j], r['features'][j]['move']))
        i = r['label']
        scored.append({'game': r['game'], 'support': r['support'], 'nll': -math.log(q[i]),
            'brier': sum(p*p for p in q)-2*q[i]+1, 'confidence': max(q),
            'top1': int(order[0] == i), 'top3': int(i in order[:3]), 'top5': int(i in order[:5])})
        for j, event in enumerate(SETS):
            if any(f['sets'][j] for f in r['features']):
                events[event].append((sum(p*f['sets'][j] for p,f in zip(q,r['features'])), r['features'][i]['sets'][j], r['game']))
    result = {'overall': metric(scored), 'sets': {e: event_metric(events[e]) for e in SETS},
        'exact_supported': metric([r for r in scored if r['support'] >= 2]),
        'fallback': metric([r for r in scored if r['support'] < 2]),
        'support_zero': metric([r for r in scored if r['support'] == 0]),
        'support_one': metric([r for r in scored if r['support'] == 1]),
        'low_support_fraction': sum(r['support'] < 2 for r in scored)/len(scored)}
    result['primary_mean_brier'] = sum(result['sets'][s]['brier'] for s in PRIMARY)/len(PRIMARY)
    return result


def prepare(model, data, rows, cache):
    records = []
    local = {}
    for row in rows:
        p = data['positions'][row['pid']]
        key = (row['pid'], row['prefix'])
        if key not in local:
            fs = cached_features(cache, p['sfen'], row['prefix'].split())
            assert [f['move'] for f in fs] == p['moves']
            local[key] = {'features': fs, 'existing': model.predict(p,row['pid'],row['prefix'],'hierarchical',2,1),
                **{f'shrink{k}': shrink(model,p,row['pid'],row['prefix'],k) for k in (2,5,10)},
                'support': sum(model.exact.get(row['pid'],{}).values())}
        records.append({**local[key], 'game': row['game'], 'label': p['moves'].index(row['move'])})
    return records


def run():
    cfg = yaml.safe_load(Path('config/human_pilot.yaml').read_text())
    data = examples(cfg)
    splits = json.loads((Path(cfg['raw_dir'])/'splits_v2.json').read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    results = {}
    for mode in ('time','player','game'):
        split = splits[mode]
        groups = {k:set(v) for k,v in split.items()}
        train = [r for r in data['rows'] if r['game'] in groups['train']]
        model = Policy(data, train, 5)
        calibration = {g for g in groups['validation'] if int(hashlib.sha256(('response-calibration-v1:'+g).encode()).hexdigest()[:8],16)%2 == 0}
        selection = groups['validation'] - calibration
        assert calibration and selection and not calibration & selection
        subsets = {'calibration': calibration, 'selection': selection, 'test': groups['test']}
        with ResponseDiagnosticCache('data/response_calibration.sqlite3') as cache:
            records = {k: prepare(model,data,[r for r in data['rows'] if r['game'] in ids],cache) for k,ids in subsets.items()}
        print(mode, 'features ready', flush=True)
        weights = {'capture_tilt': fit(records['calibration'], [0]), 'differentiated_tilt': fit(records['calibration'], range(10))}
        names = ['existing','shrink2','shrink5','shrink10','capture_tilt','differentiated_tilt']
        val = {n: evaluate(records['selection'], n, weights) for n in names}
        eligible = [n for n in names if val[n]['overall']['nll'] <= val['existing']['overall']['nll']+.02]
        selected = min(eligible, key=lambda n: (val[n]['primary_mean_brier'], n))
        test = {n: evaluate(records['test'], n, weights) for n in names}
        old, new = test['existing'], test[selected]
        gate = (new['primary_mean_brier'] < old['primary_mean_brier'] and new['overall']['nll'] <= old['overall']['nll']+.02
                and all(new['sets'][s]['brier'] <= old['sets'][s]['brier']+.01 for s in PRIMARY))
        results[mode] = {'games': {k:len(v) for k,v in subsets.items()}, 'train_games':len(groups['train']),
            'selected': selected, 'weights': weights, 'selection': val, 'test': test, 'exploratory_gate': gate,
            'independent_final_evaluation':False, 'abstain_fraction':1.0,
            'response_set_calibration_status':'exploratory_only'}
        write_json(OUT/'metrics.json',results)
        print(mode, selected, 'gate', gate, 'NLL',old['overall']['nll'],new['overall']['nll'],flush=True)
    decision = {'exploratory_reweight_allowed': all(results[m]['exploratory_gate'] for m in ('time','player')),
        'large_scan_allowed':False, 'actual_candidate_count':0, 'independent_final_evaluation':False,
        'reason':'reused tests; low support and response-set calibration uncertainty require abstention'}
    write_json(OUT/'decision.json',decision)
    files = ['surprise/response_calibration.py','reports/response_calibration/PLAN.md',
             'config/human_pilot.yaml',str(Path(cfg['raw_dir'])/'splits_v2.json'),str(Path(cfg['raw_dir'])/'policy_examples.json')]
    write_json(OUT/'provenance.json',{'sha256':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in files},
        'engine_calls':0,'new_games':0,'source_checkpoint':'c37ae1c925bad3c6c87a68375866ca7f6766a1fb'})


if __name__ == '__main__':
    run()
