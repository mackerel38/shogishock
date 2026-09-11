"""Exposed coverage benchmark, frozen plan; no production or policy changes."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import shogi
from surprise.engine import Engine
from surprise.position import Position
from surprise.obvious import reply_features
from surprise.research import cp, identity, write_json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'reports/trap_tree_benchmark'))
from explore import HISTORY, position, redundant, salience, features, gate

ROOT_MOVES = ['3d2d', '3d3e', '3d3f']
LEVELS = [100000, 1000000, 5000000, 20000000, 80000000]


def load(name):
    return json.loads((HERE / name).read_text())


def save(name, obj):
    write_json(HERE / name, obj)


class Memo:
    def __init__(self, engine):
        self.engine = engine
        path = HERE / 'engine_evidence.json'
        self.data = load(path.name) if path.exists() else {
            'requests': {}, 'binary_sha256': engine.binary_sha256,
            'eval_sha256': engine.eval_sha256, 'threads': engine.threads,
            'hash_mb': engine.hash_mb, 'plan_sha256': hashlib.sha256((HERE/'PLAN.md').read_bytes()).hexdigest()}

    def query(self, p, nodes=10000):
        key = f'{p.sfen}|{nodes}|1'
        if key not in self.data['requests']:
            hit = self.engine.cache.get(self.engine._key(p, 'search', nodes, 1)) is not None
            result = Engine._encode_result(self.engine.search(p, nodes, 1)[0])
            self.data['requests'][key] = {'sfen': p.sfen, 'nodes': nodes,
                                        'cache_hit': hit, 'result': result}
            save('engine_evidence.json', self.data)
        return self.data['requests'][key]['result']


def motive(p, usi, parent=None, candidate=None):
    m = shogi.Move.from_usi(usi)
    after = p.apply_move(usi)
    b, a, side = p.board, after.board, p.turn
    mover = b.piece_at(m.from_square) if m.from_square is not None else None
    victim = b.piece_at(m.to_square)
    tags = []
    detail = {}
    if victim:
        tags.append('grab_material')
    if m.promotion:
        tags.append('promotion')
    if mover and mover.piece_type in (6, 7, 13, 14) and (victim or m.promotion):
        tags.append('counterattack')
    if after.is_check():
        tags.append('check')
    if m.drop_piece_type == shogi.PAWN:
        tags.append('pawn_drop_setup')
    if mover and mover.piece_type not in (1, 8):
        attacked = b.is_attacked_by(1-side, m.from_square)
        defended = b.is_attacked_by(side, m.from_square)
        detail.update(source_attacked=attacked, source_defended=defended,
                      destination_attacked=a.is_attacked_by(1-side, m.to_square))
        if attacked:
            tags.append('escape_attacked_piece')
        if not defended:
            tags.append('save_hanging_piece')
        forward = (m.to_square//9 - m.from_square//9) * (1 if side else -1) > 0
        home = m.from_square//9 >= 6 if side == 0 else m.from_square//9 <= 2
        if mover.piece_type in (4, 5) and home and forward and not victim and not m.promotion:
            tags.append('development')
    targets, reinforced = [], []
    for sq in range(81):
        piece = b.piece_at(sq)
        if not piece or piece.piece_type == 1 or sq == m.to_square:
            continue
        if piece.color != side and a.is_attacked_by(side, sq) and not b.is_attacked_by(side, sq):
            targets.append(sq)
        if piece.color == side and sq != m.from_square and a.is_attacked_by(side, sq) and not b.is_attacked_by(side, sq):
            reinforced.append(sq)
    if targets:
        tags.append('piece_attack')
    if reinforced:
        tags.append('reinforce_piece')
    if targets and 'development' in tags:
        tags.append('develop_with_tempo')
    king = next(s for s in range(81) if (q := b.piece_at(s)) and q.color == side and q.piece_type == 8)
    neighbors = [s for s in range(81) if max(abs(s//9-king//9), abs(s%9-king%9)) == 1]
    new_defense = [s for s in neighbors if a.is_attacked_by(side,s) and not b.is_attacked_by(side,s)]
    if new_defense:
        tags.append('protect_king')
    if any(b.piece_at(s) is None for s in new_defense):
        tags.append('block_invasion')
    detail.update(new_enemy_targets=targets, new_friendly_defense=reinforced, new_king_neighbor_defense=new_defense)
    if parent is not None:
        f = reply_features(parent, candidate, usi)
        tags.extend(f['signals'])
        detail['history_features'] = f
    return {'human_motivation_tags': sorted(set(tags)), 'motive_geometry': detail,
            'heuristic_only': True, 'salience': salience(p, usi)}


def rank_value(result, side):
    v = cp(result)
    if v is not None:
        return (1, v if side == 0 else -v)
    md = result['score'].get('mate_distance')
    if result['score'].get('score_type') == 'mate' and md:
        winning = (md > 0) == (side == 0)
        return (2 if winning else 0, -abs(md) if winning else abs(md))
    return (-1, 0)


def coverage(memo, history, old_selected, is_reply):
    assert len(history) <= 30
    p = position(history)
    parent = position(history[:-1]) if is_reply else None
    legal = p.legal_moves()
    rows = []
    for m in legal:
        f = motive(p, m, parent, history[-1] if is_reply else None)
        rows.append({'move': m, **f, 'result': memo.query(p.apply_move(m)),
                     'redundant_nonpromotion': bool(redundant(p,m,legal))})
    ranked = sorted(rows, key=lambda r: (rank_value(r['result'],p.turn),r['move']), reverse=True)
    for i,r in enumerate(ranked):
        r['engine_rank'] = i+1
        r['engine_top'] = i < 8
        r['human_motivated'] = bool(r['human_motivation_tags']) and not r['redundant_nonpromotion']
        r['in_union'] = r['engine_top'] or r['human_motivated']
        r['old_selected'] = r['move'] in old_selected
    return {'id': identity(p.sfen), 'history': history, 'sfen': p.sfen, 'absolute_ply':len(history),
            'side_to_move': 'sente' if p.turn == 0 else 'gote',
            'legal_reply_count' if is_reply else 'legal_candidate_count': len(legal),
            'human_motivated_reply_count' if is_reply else 'motif_candidate_count': sum(r['human_motivated'] for r in rows),
            'engine_top_reply_count' if is_reply else 'engine_top_candidate_count': 8,
            'union_reply_count' if is_reply else 'union_candidate_count':sum(r['in_union'] for r in rows),
            'human_motivated_but_missed_by_old_rule':[r['move'] for r in ranked if r['human_motivated'] and not r['old_selected']],
            'old_rule_scope':'previous displayed/selected slate, NOT previous all-legal screening',
            'rows': ranked}


def screen(memo):
    old = json.loads((ROOT/'reports/trap_tree_benchmark/evidence.json').read_text())
    cand, replies = [], []
    for root_move in ROOT_MOVES:
        b = next(b for b in old['branches'] if b['opponent_move'] == root_move)
        cand.append(coverage(memo,HISTORY+[root_move],[c['move'] for c in b['candidates']],False))
        save('candidate_coverage.json',cand)
        c = next((c for c in b['candidates'] if c['move']=='4e6g+'),None)
        replies.append(coverage(memo,HISTORY+[root_move,'4e6g+'],c['displayed_replies'] if c else [],True))
        save('reply_coverage.json',replies)
        print('screened',root_move,cand[-1]['union_candidate_count'],replies[-1]['union_reply_count'],flush=True)


def transition(old, new, side):
    changes, moves, pv2 = {}, {}, {}
    for m in new:
        a,b=old[m],new[m]
        if cp(a) is not None and cp(b) is not None:
            changes[m]=abs(cp(a)-cp(b))<=100
        else:
            changes[m]=a['score']==b['score'] and b['score']['score_type']=='mate'
        moves[m]=a.get('best_move')==b.get('best_move')
        pv2[m]=a.get('pv',[])[:2]==b.get('pv',[])[:2]
    best_old=max(old,key=lambda m:rank_value(old[m],side))
    best_new=max(new,key=lambda m:rank_value(new[m],side))
    order_ok=best_old==best_new or (cp(new[best_old]) is not None and cp(new[best_new]) is not None and
               abs(cp(new[best_old])-cp(new[best_new]))<=100 and cp(old[best_old]) is not None and
               cp(old[best_new]) is not None and abs(cp(old[best_old])-cp(old[best_new]))<=100)
    return {'stable':all(changes.values()) and all(moves.values()) and order_ok,
            'score_stable':changes,'first_move_stable':moves,'pv_first2_stable':pv2,
            'ordering_stable_with_100cp_ties':order_ok,'best_old':best_old,'best_new':best_new}


def deep(memo):
    out=load('deep_checks.json') if (HERE/'deep_checks.json').exists() else {'groups':[],'mate_hypotheses':[]}
    for kind,items in [('candidate',load('candidate_coverage.json')),('reply',load('reply_coverage.json'))]:
        for item in items:
            p=position(item['history'])
            selected={r['move'] for r in item['rows'] if r['engine_top']}
            if kind=='candidate':
                selected.update(set(p.legal_moves()) & {'P*2c','4e6g+','8f8h+'})
            else:
                for r in item['rows']:
                    m=shogi.Move.from_usi(r['move']);piece=p.board.piece_at(m.from_square) if m.from_square is not None else None
                    if r['salience']['capture'] or r['salience']['promotion'] or (piece and piece.piece_type==5 and r['human_motivated']):
                        selected.add(r['move'])
                selected.update(set(p.legal_moves()) & {'7h7i','7h8g','2d2a+'})
            gid=kind+'_'+item['history'][20]
            group=next((g for g in out['groups'] if g['id']==gid),None)
            if group is None:
                group={'id':gid,'history':item['history'],'sfen':p.sfen,'moves':sorted(selected),
                       'reference_scope':'best of preselected explicitly evaluated children, not proven global optimum','levels':[]}
                out['groups'].append(group)
            if group.get('stable'):
                continue
            for n in LEVELS:
                if any(x['nodes']==n for x in group['levels']):continue
                current={m:memo.query(p.apply_move(m),n) for m in group['moves']}
                row={'nodes':n,'results':current}
                if group['levels']:row['transition']=transition(group['levels'][-1]['results'],current,p.turn)
                group['levels'].append(row)
                group['stable']=len(group['levels'])>=3 and all(x.get('transition',{}).get('stable',False) for x in group['levels'][-2:])
                save('deep_checks.json',out)
                print(gid,n,'stable',group['stable'],flush=True)
                if group['stable']:break
    save('deep_checks.json',out)


def mate_checks(memo):
    out=load('deep_checks.json') if (HERE/'deep_checks.json').exists() else {'groups':[],'mate_hypotheses':[]}
    for rm in ['3d3e','3d2d']:
        for suffix in [[],['8f8h+']]:
            history=HISTORY+[rm,'4e6g+','7h7i']+suffix
            key=rm+('_after_rook' if suffix else '_before_rook')
            item=next((x for x in out['mate_hypotheses'] if x['id']==key),None)
            if item is None:
                item={'id':key,'history':history,'sfen':position(history).sfen,'levels':[],
                      'human_claim':'gote forced mate approximately within19 after R8h+; unconfirmed',
                      'proof_type':'ordinary full-legal search; not dedicated tsume solver'}
                out['mate_hypotheses'].append(item)
            for n in LEVELS:
                if any(x['nodes']==n for x in item['levels']):continue
                r=memo.query(position(history),n)
                p=position(history)
                for m in r.get('pv',[]):p=p.apply_move(m)
                item['levels'].append({'nodes':n,'result':r,'pv_terminal_checkmate':p.board.is_checkmate()})
                save('deep_checks.json',out)
                print('mate',key,n,r['score'],'terminal',p.board.is_checkmate(),flush=True)
                if len(item['levels'])>=3 and all(x['result']['score']['score_type']=='mate' and x['result']['score']==r['score'] and
                      x['result'].get('best_move')==r.get('best_move') for x in item['levels'][-3:]) and p.board.is_checkmate():break


def regressions():
    fixtures=json.loads((ROOT/'reports/tactical_falsification/fixtures.json').read_text())
    out=[]
    for f in fixtures['fixtures'][:3]:
        c=f['candidate'];p=Position.from_sfen(f['position']['sfen'])
        rows=[features(p,c['move'],r['move'])|{'result':r['result']} for r in f['evidence']['responses']]
        result=gate.classify(rows,c['attacker_side'],p.apply_move(c['move']).legal_moves())
        assert result['decision']=='reject'
        out.append({'id':c['candidate_id'],'verdict':result,'new_engine_calls':0})
    save('regressions.json',out)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['screen','deep','mate','regressions'])
    args=parser.parse_args()
    if args.stage=='regressions':regressions()
    else:
        with Engine.from_config() as engine:
            memo=Memo(engine)
            {'screen':screen,'deep':deep,'mate':mate_checks}[args.stage](memo)
