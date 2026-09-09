"""Offline fixed-fixture research only; no engine or policy invocation."""
import hashlib
import json
import sys
from pathlib import Path

import shogi
from surprise.obvious import reply_features
from surprise.position import Position
from surprise.research import cp

CASES = [
    ('human_e2e', '5c46af1026197c8aeb70_3a3b', 'reject'),
    ('pass_pilot', '0a33fbe73571830519e4_2b6f', 'reject'),
    ('pass_pilot', '5ecc3699847f6446b58a_8h4d', 'reject'),
    ('pass_pilot', 'a77ad58c704df8bb27bf_7g3c+', 'not_falsified'),
    ('pass_pilot', 'b1d901d7811d5a04a762_3c7g+', 'not_falsified'),
]


def classify(rows, side, legal, tolerance=100, advantage=300):
    sign = 1 if side == 'sente' else -1
    if len(rows) != len(legal) or {r['move'] for r in rows} != set(legal):
        return {'decision': 'needs_verification', 'reason': 'incomplete_or_duplicate_responses'}
    values = []
    for r in rows:
        score = r['result']['score']
        v = cp(r['result'])
        if v is not None:
            values.append(v)
        elif not (score.get('bound') == 'exact' and score.get('score_type') == 'mate'
                  and isinstance(score.get('mate_distance'), int)
                  and sign * score['mate_distance'] > 0):
            return {'decision': 'needs_verification', 'reason': 'non_comparable_score'}
    if not values:
        return {'decision': 'needs_verification', 'reason': 'no_cp_reference'}
    reference = min(values, key=lambda v: sign * v)
    witnesses = [r['move'] for r in rows if r['strong'] and cp(r['result']) is not None
                 and sign * (cp(r['result']) - reference) <= tolerance
                 and -sign * cp(r['result']) >= advantage]
    return {'decision': 'reject' if witnesses else 'not_falsified',
            'reason': 'strong_adequate_punishing_reply' if witnesses else 'conjunction_not_met',
            'reference_eval': reference, 'witnesses': witnesses}


def run():
    root = Path(__file__).resolve().parents[2]
    hashes = {}
    snapshots = []
    frozen = json.loads(Path(__file__).with_name('fixtures.json').read_text()) if '--fixtures' in sys.argv else None
    def read(rel):
        raw = (root / rel).read_bytes()
        hashes[rel] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)
    output = []
    for source, cid, expected in CASES:
        if frozen:
            snapshot = next(x for x in frozen['fixtures'] if x['candidate']['candidate_id'] == cid)
            c, p, evidence, budget = (snapshot[k] for k in ('candidate', 'position', 'evidence', 'budget'))
            hashes.update(frozen['source_sha256'])
        else:
            c = next(x for x in read(f'reports/{source}/candidates.json') if x['candidate_id'] == cid)
            p = next(x for x in read(f'reports/{source}/positions.json') if x['position_id'] == c['position_id'])
        if not frozen and source == 'human_e2e':
            evidence = next(x for x in read('reports/human_e2e/human_responses.json') if x['candidate_id'] == cid)
            budget = 10000
        elif not frozen:
            evidence = read(f'reports/reach_pilot/confirm/{cid}.json')
            budget = evidence['nodes']
        snapshots.append({'candidate': {k: c[k] for k in ('candidate_id', 'position_id', 'move', 'attacker_side', 'best_eval', 'candidate_eval')},
                          'position': {k: p[k] for k in ('sfen', 'move_history')}, 'budget': budget,
                          'evidence': {'responses': [{'move': r['move'], 'result': {'score': r['result']['score'], 'pv': r['result'].get('pv', [])}} for r in evidence['responses']]}})
        parent = Position.from_sfen(p['sfen'])
        child = parent.apply_move(c['move'])
        rows = []
        for old in evidence['responses']:
            move = old['move']
            f = reply_features(parent, c['move'], move)
            m = shogi.Move.from_usi(move)
            victim = child.board.piece_at(m.to_square)
            after = child.apply_move(move)
            recapturable = any(x.to_square == m.to_square for x in after.board.legal_moves)
            free_major = bool(victim and victim.piece_type in (6, 7, 13, 14) and not recapturable)
            strong = free_major or all(t in f['signals'] for t in ('recapture', 'material_recovery_proxy'))
            rows.append({**f, 'strong': strong, 'free_major': free_major,
                         'victim_piece_type': victim.piece_type if victim else None,
                         'can_be_recaptured': recapturable, 'result': old['result']})
        outcome = classify(rows, c['attacker_side'], child.legal_moves())
        assert outcome['decision'] == expected, (cid, outcome)
        sign = 1 if c['attacker_side'] == 'sente' else -1
        replies = []
        for r in rows:
            if not r['obvious'] and not r['strong']:
                continue
            v = cp(r['result'])
            replies.append({k: v0 for k, v0 in r.items() if k != 'result'} | {
                'engine_eval': v, 'score': r['result']['score'], 'pv': r['result'].get('pv', []),
                'gap': sign * (v-outcome['reference_eval']) if v is not None else None})
        output.append({
            'candidate_id': cid, 'position': p['sfen'], 'move_history': p['move_history'],
            'move_being_examined': c['move'], 'attacker_side': c['attacker_side'],
            'purpose': 'diagnostic_counterexample' if expected == 'reject' else 'control',
            'surprise_move_decision': outcome['decision'], 'decision_reason': outcome['reason'],
            'obvious_replies': replies,
            'engine_evidence': {'parent_eval': c['best_eval'], 'candidate_root_eval': c['candidate_eval'],
                                'nominal_reply_nodes': budget, 'legal_reply_count': len(rows), **outcome},
            'human_policy_reliability': 'not assessed or used; independent-validation restriction remains',
            'human_review_point': 'Verify the free capture and absence of compensation' if expected == 'reject'
                else 'Compare alternative recaptures; not_falsified is not approval as a surprise',
            'sensitivity': {f'gap_{t}_advantage_{a}': classify(rows, c['attacker_side'], child.legal_moves(), t, a)['decision']
                            for t in (50, 100, 200, 300) for a in (300, 500, 1000)},
        })
    result = {'cases': output, 'source_sha256': hashes, 'new_engine_calls': 0, 'new_policy_calls': 0}
    if not frozen:
        Path(__file__).with_name('fixtures.json').write_text(json.dumps({'fixtures': snapshots, 'source_sha256': hashes}, indent=2)+'\n')
    Path(__file__).with_name('results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print([(x['candidate_id'], x['surprise_move_decision']) for x in output])


if __name__ == '__main__':
    run()
