"""Bounded research runner. Existing engine/cache; frozen gate; no Human Policy."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import shogi
from surprise.engine import Engine
from surprise.obvious import reply_features
from surprise.position import Position
from surprise.research import cp, write_json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FROZEN = ROOT / 'reports/tactical_falsification/prototype.py'
assert hashlib.sha256(FROZEN.read_bytes()).hexdigest() == 'ab484b3318d5833c57ac0e8cbcccf0154239b2a74baf6c3754a4e27d16f78ed3'
assert hashlib.sha256((ROOT/'surprise/obvious.py').read_bytes()).hexdigest() == '290bdc28ed8eb9bcf11160fa84a93fc8961df22d36e6829cdf65cf8ad29c3f26'
spec = importlib.util.spec_from_file_location('frozen_gate', FROZEN)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def position(history):
    p = Position.startpos()
    for m in history:
        p = p.apply_move(m)
    return p


def features(parent, candidate, reply):
    child = parent.apply_move(candidate)
    r = reply_features(parent, candidate, reply)
    move = shogi.Move.from_usi(reply)
    victim = child.board.piece_at(move.to_square)
    can = any(m.to_square == move.to_square for m in child.apply_move(reply).board.legal_moves)
    free = bool(victim and victim.piece_type in (6,7,13,14) and not can)
    return r | {'free_major': free, 'can_be_recaptured': can,
                'victim_piece_type': victim.piece_type if victim else None,
                'strong': free or all(t in r['signals'] for t in ('recapture','material_recovery_proxy'))}


class Run:
    def __init__(self, engine):
        self.engine = engine
        self.path = HERE/'engine_evidence.json'
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {
            'requests': {}, 'new_engine_requests': 0, 'cache_hits': 0, 'new_100k_requests': 0,
            'engine_binary_sha256': engine.binary_sha256,
            'eval_sha256': engine.eval_sha256, 'config': 'config/default.yaml'}

    def query(self, p, nodes=10000, multipv=1):
        key = f'{p.sfen}|{nodes}|{multipv}'
        if key not in self.data['requests']:
            hit = self.engine.cache.get(self.engine._key(p, 'search', nodes, multipv)) is not None
            if not hit:
                assert self.data['new_engine_requests'] < 600, 'request cap'
                if nodes == 100000:
                    assert self.data['new_100k_requests'] < 12, '100k cap'
                self.data['new_engine_requests'] += 1
                self.data['new_100k_requests'] += int(nodes == 100000)
            else:
                self.data['cache_hits'] += 1
            results = self.engine.search(p, nodes, multipv)
            self.data['requests'][key] = {'sfen': p.sfen, 'nominal_nodes': nodes, 'multipv': multipv,
                'cache_hit': hit, 'results': [Engine._encode_result(x) for x in results]}
            write_json(self.path, self.data)
        return self.data['requests'][key]['results']


def evaluate_case(run, selection):
    history = selection['history'].split()
    parent = position(history)
    candidate = selection['candidate_move']
    child = parent.apply_move(candidate)
    rows = [features(parent, candidate, m) | {'result': run.query(child.apply_move(m))[0]}
            for m in child.legal_moves()]
    result = gate.classify(rows, selection['candidate_side'], child.legal_moves())
    sign = 1 if parent.turn == shogi.BLACK else -1
    reference = result.get('reference_eval')
    for r in rows:
        r['engine_eval'] = cp(r['result'])
        r['same_condition_gap'] = sign*(r['engine_eval']-reference) if reference is not None and r['engine_eval'] is not None else None
    cp_rows = [r for r in rows if r['engine_eval'] is not None]
    best = min(cp_rows, key=lambda r:sign*r['engine_eval']) if cp_rows else None
    return selection | {'position': parent.sfen, 'resulting_sfen': child.sfen,
        'parent_result': run.query(parent)[0], 'candidate_result':run.query(child)[0],
        'legal_reply_count':len(rows), 'responses':rows, 'final_gate_result':result,
        'engine_best_reply': best['move'] if best and reference is not None else None,
        'sensitivity':{f'gap_{t}_advantage_{a}':gate.classify(rows,selection['candidate_side'],child.legal_moves(),t,a)['decision']
                       for t in (50,100,200,300) for a in (300,500,1000)},
        'human_policy_reliability':'not evaluated; prior independent-validation NO unchanged'}


def main():
    selections = json.loads((HERE/'selections.json').read_text())
    # Validate all selected lines BEFORE starting the engine.
    for c in selections['cases']:
        child = position(c['history'].split()).apply_move(c['candidate_move'])
        for r in c['obvious_looking_replies']:
            child.apply_move(r)
    with Engine.from_config() as engine:
        run = Run(engine)
        if '--confirm' in sys.argv:
            targets = json.loads((HERE/'confirmation_plan.json').read_text())
            assert len(targets['positions']) <= 12
            out=[]
            for x in targets['positions']:
                c=next(c for c in selections['cases'] if c['id']==x['case_id'])
                history=c['history'].split()
                p=(position(history).apply_move(c['candidate_move']).apply_move(x['reply']) if 'reply' in x
                   else position(history[:x['prefix_length']]).apply_move(x['move']))
                out.append({'label':x['label'],'sfen':p.sfen,'result':run.query(p,100000)[0]})
                write_json(HERE/'confirmation_results.json',out)
                print(x['label'],out[-1]['result']['score'],flush=True)
            write_json(HERE/'confirmation_results.json',out)
            return
        # Minimal smoke doubles as first natural-history root.
        run.query(Position.startpos())
        cases = []
        audits = []
        audited = set()
        for c in selections['cases']:
            history = c['history'].split()
            trajectory=[]
            for i in range(len(history)+1):
                p=position(history[:i]); result=run.query(p)[0]
                trajectory.append({'ply':i,'history':history[:i],'sfen':p.sfen,'result':result})
            for i in range(len(history)):
                before,after=trajectory[i:i+2]
                tag=(before['sfen'],history[i])
                if tag in audited:
                    continue
                audited.add(tag)
                bv,av=cp(before['result']),cp(after['result'])
                if bv is not None and av is not None and abs(av-bv)>300:
                    p=Position.from_sfen(before['sfen']); best=before['result']['best_move']
                    if best in p.legal_moves():
                        alternative=run.query(p.apply_move(best))[0]
                        sign=1 if p.turn==shogi.BLACK else -1
                        gap=sign*(cp(alternative)-av) if cp(alternative) is not None else None
                        audits.append({'ply':i+1,'history':history[:i],'played':history[i],
                            'root_best':best,'played_result':after['result'],'alternative_result':alternative,
                            'same_condition_loss':gap,'root_swing':av-bv})
            case=evaluate_case(run,c);case['prefix_trajectory']=trajectory;cases.append(case)
            write_json(HERE/'results.json',{'cases':cases,'prefix_deviation_audits':audits})
            print(c['id'],case['final_gate_result'],flush=True)
        # Only the prespecified small alternative comparisons, never all candidate moves.
        comparisons=[]; alternative_count=0
        groups=[('natural_repair',selections['cases'][2]['history'].split()[:16],['P*8g','8h7g']),
                ('rook_seed',selections['cases'][2]['history'].split(),['2f2b+','2f2a+','7g3c+','P*8b']),
                ('pawn_drop_seed',selections['cases'][3]['history'].split(),['P*8b','P*2c','B*4e'])]
        for label,history,moves in groups:
            p=position(history);shortlist=run.query(p,multipv=3)
            extras=[x['best_move'] for x in shortlist[:2]]
            moves=list(dict.fromkeys(moves+extras))
            rows=[]
            for m in moves:
                if m not in p.legal_moves() or alternative_count>=12:
                    continue
                alternative_count+=1
                rows.append({'move':m,'result':run.query(p.apply_move(m))[0]})
            comparisons.append({'label':label,'history':history,'position':p.sfen,'shortlist':shortlist,'alternatives':rows})
        fixtures=json.loads((ROOT/'reports/tactical_falsification/fixtures.json').read_text())
        regressions=[]
        for f in fixtures['fixtures'][:3]:
            c=f['candidate'];p=Position.from_sfen(f['position']['sfen']);child=p.apply_move(c['move'])
            rows=[features(p,c['move'],r['move'])|{'result':r['result']} for r in f['evidence']['responses']]
            result=gate.classify(rows,c['attacker_side'],child.legal_moves())
            assert result['decision']=='reject'
            regressions.append({'candidate_id':c['candidate_id'],'result':result,'new_engine_calls':0})
        write_json(HERE/'results.json',{'cases':cases,'prefix_deviation_audits':audits,
            'bounded_alternatives':comparisons,'reject_regressions':regressions,
            'old_exchange_controls_safety_evidence':'withdrawn following human history review',
            'gate_changed':False,'human_policy_calls':0})
        print({k:v for k,v in run.data.items() if k!='requests'},flush=True)


if __name__=='__main__':
    main()
