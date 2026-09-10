"""Frozen bounded benchmark; no reference moves inserted below the root."""
import hashlib
import json
import sys
from pathlib import Path

import shogi
from surprise.engine import Engine
from surprise.position import Position
from surprise.research import PIECE_VALUES, cp, identity, write_json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'reports/tactical_falsification_v2'))
from experiment import features, gate, position

HISTORY='7g7f 3c3d 2g2f 8c8d 2f2e 8d8e 6i7h 4a3b 2e2d 2c2d 2h2d 8e8f 8g8f 8b8f 2d3d 2b8h+ 7i8h P*2h 3i2h B*4e'.split()


def salience(p,m):
    move=shogi.Move.from_usi(m);victim=p.board.piece_at(move.to_square)
    child=p.apply_move(m)
    return {'capture':bool(victim),'victim_value':PIECE_VALUES[victim.piece_type] if victim else 0,
            'promotion':move.promotion,'check':child.is_check(),
            'score':(PIECE_VALUES[victim.piece_type] if victim else 0)+300*move.promotion+200*child.is_check()}


def order(result):
    v=cp(result)
    if v is not None:return (1,v)
    s=result['score'];mate=s.get('mate_distance')
    if s.get('score_type')=='mate' and mate:return (2 if mate>0 else 0,0)
    return (-1,0)


class BudgetStop(Exception):pass


class Memo:
    def __init__(self,engine):
        self.engine=engine;self.path=HERE/'engine_evidence.json'
        self.data=json.loads(self.path.read_text()) if self.path.exists() else {'requests':{},'new_requests':0,'cache_hits':0,'new100k':0,
            'binary_sha256':engine.binary_sha256,'eval_sha256':engine.eval_sha256}

    def query(self,p,nodes=10000,multipv=1):
        key=f'{p.sfen}|{nodes}|{multipv}'
        if key not in self.data['requests']:
            hit=self.engine.cache.get(self.engine._key(p,'search',nodes,multipv)) is not None
            if not hit and (self.data['new_requests']>=1000 or nodes==100000 and self.data['new100k']>=8):raise BudgetStop()
            rs=[Engine._encode_result(x) for x in self.engine.search(p,nodes,multipv)]
            self.data['new_requests']+=int(not hit);self.data['cache_hits']+=int(hit)
            self.data['new100k']+=int(not hit and nodes==100000)
            self.data['requests'][key]={'sfen':p.sfen,'nodes':nodes,'multipv':multipv,'cache_hit':hit,'results':rs}
            write_json(self.path,self.data)
        return self.data['requests'][key]['results']


def redundant(p,m,legal):
    move=shogi.Move.from_usi(m)
    piece=p.board.piece_at(move.from_square) if move.from_square is not None else None
    return not move.promotion and m+'+' in legal and piece and piece.piece_type in (1,6,7)


def root_selection(p,rows):
    ranked=sorted(rows,key=lambda r:(order(r['result']),r['move']),reverse=True)
    chosen=ranked[:3]
    for r in ranked[3:]:
        m=shogi.Move.from_usi(r['move']);piece=p.board.piece_at(m.from_square) if m.from_square is not None else None
        if piece and piece.piece_type==shogi.ROOK and not r['salience']['capture'] and m.to_square//9>m.from_square//9:
            after=p.apply_move(r['move'])
            if not after.board.is_attacked_by(shogi.WHITE,m.to_square):
                chosen.append(r);break
    if len(chosen)<4 and len(ranked)>3:chosen.append(ranked[3])
    return chosen


def evaluate_candidate(memo,p,m):
    child=p.apply_move(m);rows=[];complete=True
    try:
        for r in child.legal_moves():
            rows.append(features(p,m,r)|{'salience':salience(child,r),'result':memo.query(child.apply_move(r))[0]})
    except BudgetStop:complete=False
    verdict=gate.classify(rows,'gote',child.legal_moves())
    reference=verdict.get('reference_eval')
    for r in rows:
        r['gap']=reference-cp(r['result']) if reference is not None and cp(r['result']) is not None else None
        r['natural_proxy']=bool(r['obvious'] or r['salience']['capture'] or r['salience']['check'])
    best=sorted([r for r in rows if r['gap']==0],key=lambda r:r['move'])[:1]
    errors=sorted([r for r in rows if r['natural_proxy'] and r['gap'] is not None and r['gap']>=300],
                  key=lambda r:(-r['salience']['score'],r['move']))[:2]
    flag=verdict['decision']=='not_falsified' and bool(errors) and complete
    return {'move':m,'result':memo.query(child)[0],'gate':verdict,'complete':complete,'responses':rows,
            'displayed_replies':[r['move'] for r in best+errors],'trap_flag':flag,
            'max_natural_gap':max((r['gap'] for r in errors),default=0),
            'sensitivity':{f'{t}/{a}':gate.classify(rows,'gote',child.legal_moves(),t,a)['decision'] for t in (50,100,200,300) for a in (300,500,1000)}}


class Graph:
    def __init__(self):self.nodes={};self.edges={}
    def node(self,p,history,flags):
        key=identity(p.sfen)
        item=self.nodes.setdefault(key,{'id':key,'sfen':' '.join(p.sfen.split()[:3])+' 1','ply':len(history),
            'side_to_move':'sente' if p.turn==0 else 'gote','histories':[],'path_naturalness':[], 'status':'analysis_node'})
        item['ply']=min(item['ply'],len(history))
        if history not in item['histories']:item['histories'].append(history.copy())
        entry={'history':history.copy(),'flags':flags.copy()}
        if entry not in item['path_naturalness']:item['path_naturalness'].append(entry)
        return key
    def add(self,p,history,m,flags,role,result=None,**extras):
        a=self.node(p,history,flags);b=self.node(p.apply_move(m),history+[m],flags)
        key=(a,m)
        item=self.edges.setdefault(key,{'from':a,'to':b,'move':m,'actor':'opponent' if p.turn==0 else 'us',
            'roles':[],'engine_eval':cp(result) if result else None,'score':result['score'] if result else None})
        if role not in item['roles']:item['roles'].append(role)
        item.update(extras)
        return p.apply_move(m),history+[m]


def assemble(evidence):
    graph=Graph();root=position(HISTORY);root_id=graph.node(root,[],['previously_exposed_root','prefix_horizon_warning'])
    for b in evidence['branches']:
        flags=['previously_exposed_root','prefix_horizon_warning']
        if b['root_loss'] is not None and b['root_loss']>300:flags.append('opponent_root_deviation_over300')
        if b['root_loss'] is not None and b['root_loss']>600:flags.append('large_prior_deviation')
        p,h=graph.add(root,[],b['opponent_move'],flags,'natural_reply',b['root_result'],eval_loss=b['root_loss'],naturalness_evidence=b['plausibility'])
        if cp(b['root_result']) is not None and abs(cp(b['root_result']))>1000:flags=flags+['parent_absolute_eval_over1000']
        for c in b['candidates']:
            pc,hc=graph.add(p,h,c['move'],flags,'candidate',c['result'],eval_loss=c['candidate_initial_cost_cp'],
                gate=c['gate'],selected=c['move']==b['our_response'],trap_effect={'mechanical_flag':c['trap_flag'],'gap':c['max_natural_gap']})
            for m in c['displayed_replies']:
                r=next(r for r in c['responses'] if r['move']==m)
                pf=flags+(['opponent_error_over300'] if r['gap'] and r['gap']>=300 else [])
                pr,hr=graph.add(pc,hc,m,pf,'best_reply' if r['gap']==0 else 'natural_reply',r['result'],
                    eval_loss=r['gap'],naturalness_evidence=r['salience']|{'signals':r['signals'],'heuristic_only':True})
                continuation=c.get('continuations',{}).get(m)
                if continuation:
                    graph.add(pr,hr,continuation['move'],pf,'normal_move' if r['gap']==0 else 'punishment',continuation['result'],
                              trap_effect={'conditional_loss_before_continuation':r['gap']})
    return {'root':root_id,'root_history':HISTORY,'attacker_side':'gote','nodes':list(graph.nodes.values()),'edges':list(graph.edges.values()),
            'branches':evidence['branches'],'source_checkpoint':'d58a9b3bef8e909d67fd452578277860cdfacb11',
            'production_gate':'INCONCLUSIVE; not enabled','independent_rediscovery':False,'new_external_opening_search':False}


def main():
    if '--offline' in sys.argv:
        write_json(HERE/'tree.json',assemble(json.loads((HERE/'evidence.json').read_text())));return
    with Engine.from_config() as engine:
        memo=Memo(engine)
        if '--confirm' in sys.argv:
            plan=json.loads((HERE/'confirmation_plan.json').read_text());out=[]
            for r in plan['positions']:
                out.append(r|{'result':memo.query(Position.from_sfen(r['sfen']),100000)[0]})
                write_json(HERE/'confirmation.json',out)
            return
        root=position(HISTORY)
        root_rows=[{'move':m,'salience':salience(root,m),'result':memo.query(root.apply_move(m))[0]} for m in root.legal_moves()]
        chosen=root_selection(root,root_rows);best=max((cp(r['result']) for r in root_rows if cp(r['result']) is not None),default=None)
        evidence={'root_history':HISTORY,'root_sfen':root.sfen,'root_replies':root_rows,'branches':[]}
        write_json(HERE/'evidence.json',evidence)
        print('root branches',[r['move'] for r in chosen],flush=True)
        for r in chosen:
            p=root.apply_move(r['move']);shortlist=memo.query(p,multipv=3);legal=p.legal_moves()
            moves=[shortlist[0]['best_move']];scores={m:salience(p,m) for m in legal}
            forcing=sorted([m for m in legal if m not in moves and not redundant(p,m,legal) and scores[m]['score']>0],key=lambda m:(-scores[m]['score'],m))
            if forcing:moves.append(forcing[0])
            elif len(shortlist)>1:moves.append(shortlist[1]['best_move'])
            b={'opponent_move':r['move'],'root_result':r['result'],'root_loss':best-cp(r['result']) if best is not None and cp(r['result']) is not None else None,
               'plausibility':{'engine_rank':1+sorted(root_rows,key=lambda z:(order(z['result']),z['move']),reverse=True).index(r),'salience':r['salience'],
                              'rationale':'top3 engine or best remaining safe rook retreat; human plausibility unmeasured'},
               'shortlist':shortlist,'candidates':[]}
            for m in moves:
                c=evaluate_candidate(memo,p,m);b['candidates'].append(c)
                print(r['move'],m,c['gate'],c['max_natural_gap'],flush=True)
            ref=min((cp(c['result']) for c in b['candidates'] if cp(c['result']) is not None),default=None)
            for c in b['candidates']:
                c['candidate_initial_cost_cp']=max(0,cp(c['result'])-ref) if cp(c['result']) is not None and ref is not None else None
                c['cost_reference_scope']='best of tested explicit candidate children at10k; bounded, not proven global optimum'
            viable=[c for c in b['candidates'] if c['gate']['decision']=='not_falsified']
            flagged=[c for c in viable if c['trap_flag']]
            selected=min(flagged,key=lambda c:(-c['max_natural_gap'],c['candidate_initial_cost_cp'] or 0,c['move'])) if flagged else min(viable or b['candidates'],key=lambda c:(c['candidate_initial_cost_cp'] if c['candidate_initial_cost_cp'] is not None else 1e9,c['move']))
            b['our_response']=selected['move']
            b['branch_status']='trap_branch' if flagged else 'normal_branch' if viable else 'opponent_refutes' if all(c['gate']['decision']=='reject' for c in b['candidates']) else 'needs_review'
            b['status_scope']='mechanical provisional; human naturalness and final Astra interpretation separate'
            for c in b['candidates']:
                c['continuations']={}
                for m in c['displayed_replies']:
                    rr=next(x for x in c['responses'] if x['move']==m);pc=p.apply_move(c['move']).apply_move(m);continuation=rr['result'].get('best_move')
                    if continuation in pc.legal_moves():
                        c['continuations'][m]={'move':continuation,'result':memo.query(pc.apply_move(continuation))[0]}
            evidence['branches'].append(b);write_json(HERE/'evidence.json',evidence);write_json(HERE/'tree.json',assemble(evidence))
        fixtures=json.loads((ROOT/'reports/tactical_falsification/fixtures.json').read_text());regressions=[]
        for f in fixtures['fixtures'][:3]:
            c=f['candidate'];p=Position.from_sfen(f['position']['sfen'])
            rows=[features(p,c['move'],r['move'])|{'result':r['result']} for r in f['evidence']['responses']]
            result=gate.classify(rows,c['attacker_side'],p.apply_move(c['move']).legal_moves());assert result['decision']=='reject'
            regressions.append({'id':c['candidate_id'],'gate':result})
        evidence['regressions']=regressions;write_json(HERE/'evidence.json',evidence);write_json(HERE/'tree.json',assemble(evidence))
        print('done',memo.data['new_requests'],memo.data['cache_hits'],flush=True)


if __name__=='__main__':main()
