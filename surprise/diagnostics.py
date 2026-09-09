"""Stage A: read-only baseline, separate resumable diagnostics, limited 100k checks."""
import argparse
import hashlib
import json
import statistics
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

from .engine import Engine, CACHE_SCHEMA_VERSION
from .position import Position
from .research import cp, encode, select_review, write_json
from .obvious import obvious_replies, reply_features, reply_summary, escalation_reasons


def baseline_fingerprints(path):
    return {str(f.relative_to(path)): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in sorted(path.rglob('*')) if f.is_file() and f.name != 'analysis.md'}


def selection(rows, positions, count):
    chosen = {}
    for side in ('sente', 'gote'):
        group = [r for r in rows if r['attacker_side'] == side]
        # Predeclared purposive validation strata, not a random prevalence sample.
        for metric, reverse in [('pass_sensitivity', True), ('pass_relative_median', True),
                                 ('candidate_eval_loss', False), ('ply', False)][:count]:
            ordered = sorted(group, key=lambda r: ((-1 if reverse else 1) *
                             (positions[r['position_id']]['ply'] if metric == 'ply' else r[metric]), r['candidate_id']))
            r = next((r for r in ordered if r['candidate_id'] not in chosen), None)
            if r:
                chosen[r['candidate_id']] = metric
    return chosen


def diagnose_one(cfg, row, position, full=False):
    out = Path(cfg['output']) / ('confirm' if full else 'obvious')
    out.mkdir(parents=True, exist_ok=True)
    path = out / (row['candidate_id'] + '.json')
    nodes = cfg['diagnostic']['confirm_nodes' if full else 'nodes']
    parent = Position.from_sfen(position['sfen'])
    child = parent.apply_move(row['move'])
    features = {f['move']: f for f in obvious_replies(parent, row['move'])}
    moves = child.legal_moves() if full else list(features)
    witness = row['normal']['pv'][0] if row['normal']['pv'] else None
    if witness and witness not in moves:
        moves.append(witness)
    data = json.loads(path.read_text()) if path.exists() else {'candidate_id': row['candidate_id'], 'nodes': nodes, 'responses': []}
    if data['nodes'] != nodes:
        raise ValueError('changed diagnostic budget; use new output')
    done = {r['move'] for r in data['responses']}
    with Engine.from_config(cfg['engine_config']) as engine:
        root = data.get('root')
        if root is None:
            root = encode(engine.evaluate(child, nodes)) if full else row['normal']
            data['root'] = root
            write_json(path, data)
        for move in moves:
            if move in done:
                continue
            result = encode(engine.evaluate(child.apply_move(move), nodes))
            f = features.get(move) or reply_features(parent, row['move'], move)
            data['responses'].append(f | {'result': result})
            write_json(path, data)
    summary = reply_summary(data['responses'], root, row['attacker_side'], len(child.legal_moves()), cfg['diagnostic']['tolerances'])
    obvious = [r for r in data['responses'] if r['obvious']]
    tol = cfg['selection']['neutralize_tolerance']
    neutralizes = any(r[f'is_good_{tol}'] is True for r in obvious) if summary['numeric_comparable'] else None
    sign = 1 if row['attacker_side'] == 'sente' else -1
    best = min((r for r in obvious if r['engine_eval'] is not None), key=lambda r: sign * r['engine_eval'], default=None)
    data.update(summary, complete=len(data['responses']) == len(moves), obvious_reply_exists=bool(features),
                candidate_piece_capturable=any(f['reply_captures_candidate'] for f in features.values()),
                obvious_reply_neutralizes=neutralizes,
                obvious_reply_eval=best['engine_eval'] if best else None,
                obvious_reply_move=best['move'] if best else None,
                obvious_reply_gap_from_optimal=best['gap_from_optimal_estimate'] if best else None)
    for t in cfg['diagnostic']['tolerances']:
        data[f'obvious_reply_is_good_{t}'] = any(r[f'is_good_{t}'] is True for r in obvious) if summary['numeric_comparable'] else None
    write_json(path, data)
    return data


def run(config, metadata_only=False):
    cfg = yaml.safe_load(Path(config).read_text())
    baseline, out = Path(cfg['baseline']), Path(cfg['output'])
    if out.resolve() == baseline.resolve() or baseline.resolve() in out.resolve().parents:
        raise ValueError('diagnostics must be outside baseline')
    out.mkdir(parents=True, exist_ok=True)
    before = baseline_fingerprints(baseline)
    identity = {'baseline': before, 'config': cfg, 'cache_schema': CACHE_SCHEMA_VERSION}
    manifest = out / 'diagnostic_manifest.json'
    if manifest.exists() and json.loads(manifest.read_text()) != identity:
        raise ValueError('diagnostic fingerprint changed')
    write_json(manifest, identity)
    rows = json.loads((baseline / 'candidates.json').read_text())
    positions = {p['position_id']: p for p in json.loads((baseline / 'positions.json').read_text())}
    source = json.loads((baseline / 'manifest.json').read_text())
    if source['cache_schema'] != 5 or not source['complete']:
        raise ValueError('requires complete schema-5 baseline')
    selected = select_review(rows, cfg['diagnostic']['top_n'])
    enriched = []
    for r in selected:
        p = positions[r['position_id']]
        parent = Position.from_sfen(p['sfen'])
        first = r['normal']['pv'][0] if r['normal']['pv'] else None
        f = reply_features(parent, r['move'], first) if first else {}
        advantage = r['best_eval'] * (1 if r['attacker_side'] == 'sente' else -1) if r['best_eval'] is not None else None
        enriched.append(r | {'sfen': p['sfen'], 'ply': p['ply'], 'families': p['families'],
            'parent_attacker_advantage': advantage,
            'parent_already_favorable': advantage >= cfg['selection']['parent_favorable_cp'] if advantage is not None else None,
            'normal_first_reply': first, 'normal_first_reply_is_capture': f.get('is_capture'),
            'normal_first_reply_captures_candidate': f.get('reply_captures_candidate'),
            'normal_first_reply_is_obvious': f.get('obvious'), 'reach_probability': None})
    if not metadata_only:
        with Engine.from_config(cfg['engine_config']) as e:
            assert e.cache and e.binary_sha256 == source['engine_sha256'] and e.eval_sha256 == source['eval_sha256']
        with ThreadPoolExecutor(max_workers=cfg['diagnostic']['workers']) as pool:
            results = list(pool.map(lambda r: diagnose_one(cfg, r, positions[r['position_id']]), enriched))
        for r, diagnostic in zip(enriched, results):
            r['obvious_diagnostic'] = diagnostic
        chosen = selection(enriched, positions, cfg['diagnostic']['confirm_per_side'])
        confirm_rows = [r for r in enriched if r['candidate_id'] in chosen]
        with ThreadPoolExecutor(max_workers=cfg['diagnostic']['workers']) as pool:
            results = list(pool.map(lambda r: diagnose_one(cfg, r, positions[r['position_id']], True), confirm_rows))
        confirmations = dict(zip((r['candidate_id'] for r in confirm_rows), results))
        write_json(out / 'confirmation_selection.json', chosen)
        for r in enriched:
            r['confirmation'] = confirmations.get(r['candidate_id'])
            d = r['confirmation'] or r['obvious_diagnostic']
            r['not_escalated_reason'] = escalation_reasons(r['parent_attacker_advantage'], None,
                d['obvious_reply_neutralizes'], d[f"good_reply_fraction_{cfg['selection']['neutralize_tolerance']}"], cfg['selection'])
    write_json(out / 'pilot_diagnostics.json', enriched)
    summary = {}
    for side in ('sente', 'gote'):
        side_rows = [r for r in rows if r['attacker_side'] == side]
        summary[side] = {}
        for metric in ('pass_sensitivity', 'pass_relative_median', 'union'):
            ids = {r['candidate_id'] for r in sorted((r for r in side_rows if r.get(metric) is not None), key=lambda r: (-r[metric], r['candidate_id']))[:cfg['diagnostic']['top_n']]} if metric != 'union' else {r['candidate_id'] for r in enriched}
            g = [r for r in enriched if r['attacker_side'] == side and r['candidate_id'] in ids]
            counts = {field: sum(r[field] is True for r in g) for field in ('normal_first_reply_is_capture', 'normal_first_reply_captures_candidate', 'normal_first_reply_is_obvious', 'parent_already_favorable')}
            counts.update(n=len(g), distinct_parents=len({r['position_id'] for r in g}),
                ply_median=statistics.median(r['ply'] for r in g), ply_min=min(r['ply'] for r in g), ply_max=max(r['ply'] for r in g),
                ply_bins=dict(Counter('0-10' if r['ply'] <= 10 else '11-20' if r['ply'] <= 20 else '21-30' if r['ply'] <= 30 else '31-40' for r in g)),
                parent_advantage_median=statistics.median(r['parent_attacker_advantage'] for r in g),
                candidate_eval_median=statistics.median(r['candidate_eval'] for r in g),
                candidate_eval_loss_median=statistics.median(r['candidate_eval_loss'] for r in g),
                parent_threshold_counts={str(t): sum(r['parent_attacker_advantage'] >= t for r in g) for t in (100, 300, 500, 1000)})
            if not metadata_only:
                counts['obvious_reply_exists'] = sum(r['obvious_diagnostic']['obvious_reply_exists'] for r in g)
                counts['neutralizes_by_tolerance'] = {str(t): sum(r['obvious_diagnostic'][f'obvious_reply_is_good_{t}'] is True for r in g) for t in cfg['diagnostic']['tolerances']}
                counts['unknown_comparison'] = sum(not r['obvious_diagnostic']['numeric_comparable'] for r in g)
            summary[side][metric] = counts
    write_json(out / 'pilot_summary.json', summary)
    assert baseline_fingerprints(baseline) == before
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config/reach_pilot.yaml')
    parser.add_argument('--metadata-only', action='store_true')
    args = parser.parse_args()
    run(args.config, args.metadata_only)
