"""Selective OR / exhaustive AND proof attempt. Failure is inconclusive."""
import hashlib
import importlib.util
import json
from pathlib import Path

import shogi
spec=importlib.util.spec_from_file_location('coverage_experiment',Path(__file__).with_name('experiment.py'))
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)


def key(board):return ' '.join(board.sfen().split()[:3])


class Limit(Exception):pass


class Proof:
    def __init__(self,hints):
        self.hints=hints;self.visited=0;self.proven={};self.failed=set();self.stack=set()

    def search(self,b,remaining):
        k=key(b);state=(k,remaining)
        if k in self.stack:return None
        if state in self.proven:return state
        if state in self.failed:return None
        self.visited+=1
        if self.visited%10000==0:print('proof states',self.visited,flush=True)
        if self.visited>100000:raise Limit()
        moves=list(b.legal_moves)
        if not moves:
            if b.turn==0 and b.is_check():
                self.proven[state]={'sfen':b.sfen(),'remaining':remaining,'terminal':True,'children':{}}
                return state
            return None
        if remaining==0:return None
        self.stack.add(k)
        try:
            if b.turn==1:
                options=[]
                for m in moves:
                    hinted=m.usi() in self.hints.get(k,[])
                    b.push(m);checking=b.is_check();b.pop()
                    if hinted or checking:options.append((not hinted,m.usi(),m))
                for _,_,m in sorted(options):
                    b.push(m);child=self.search(b,remaining-1);b.pop()
                    if child is not None:
                        self.proven[state]={'sfen':b.sfen(),'remaining':remaining,'terminal':False,'children':{m.usi():child}}
                        return state
            else:
                ordered=sorted(moves,key=lambda m:(m.usi() not in self.hints.get(k,[]),m.usi()))
                children={}
                for m in ordered:
                    b.push(m);child=self.search(b,remaining-1);b.pop()
                    if child is None:break
                    children[m.usi()]=child
                if len(children)==len(moves):
                    self.proven[state]={'sfen':b.sfen(),'remaining':remaining,'terminal':False,'children':children}
                    return state
            self.failed.add(state)
            return None
        finally:self.stack.remove(k)


def verify(root,nodes,ancestors=None):
    ancestors=set() if ancestors is None else ancestors
    n=nodes[root];b=shogi.Board(n['sfen']);k=key(b)
    assert k not in ancestors,'repeated position in alleged proof'
    legal={m.usi() for m in b.legal_moves}
    if n['terminal']:
        assert b.turn==0 and b.is_check() and not legal
        return 0
    assert n['remaining']>0
    assert set(n['children'])<=legal
    assert len(n['children'])==1 if b.turn==1 else set(n['children'])==legal
    distances=[]
    for move,c in n['children'].items():
        b.push(shogi.Move.from_usi(move))
        assert key(b)==key(shogi.Board(nodes[c]['sfen']))
        assert nodes[c]['remaining']==n['remaining']-1
        distances.append(1+verify(c,nodes,ancestors|{k}));b.pop()
    return max(distances)


def main():
    snapshot=e.HERE/'mate_proof_hints.json'
    if snapshot.exists():
        frozen=json.loads(snapshot.read_text());hints=frozen['hints'];source_hash=frozen['source_sha256']
    else:
        raw=(e.HERE/'engine_evidence.json').read_bytes();data=json.loads(raw);hints={}
        for q in data['requests'].values():
            b=shogi.Board(q['sfen'])
            for usi in q['result'].get('pv',[]):
                hints.setdefault(key(b),set()).add(usi);b.push(shogi.Move.from_usi(usi))
        hints={k:sorted(v) for k,v in hints.items()};source_hash=hashlib.sha256(raw).hexdigest()
        e.save(snapshot.name,{'source_sha256':source_hash,'hints':hints})
    output={'hint_source_sha256':source_hash,'hint_positions':len(hints),
            'new_engine_calls':0,'root_limit_including_rook_move':19,'cases':[]}
    for rm in ['3d3e','3d2d']:
        history=e.HISTORY+[rm,'4e6g+','7h7i','8f8h+'];p=e.position(history);solver=Proof(hints)
        cut=False
        try:root=solver.search(p.board,18)
        except Limit:root=None;cut=True
        verified=False;distance=None;verification_error=None
        if root is not None:
            try:distance=verify(root,solver.proven);verified=True
            except AssertionError as ex:verification_error=str(ex)
        row={'root_reply':rm,'history':history,'sfen':p.sfen,'visited_states':solver.visited,
             'cutoff':cut,'certified':verified,'mate_distance_after_rook':distance,
             'decision':'certified_upper_bound' if verified else 'INCONCLUSIVE',
             'verification_error':verification_error,'proven_substates':len(solver.proven),
             'reason_if_unconfirmed':'selective attacker search or resource limit, NOT a no-mate proof'}
        if verified:
            # Tuple keys serialized as separate IDs, with only reachable certificate nodes.
            reachable={}
            def collect(state):
                ident=hashlib.sha256(str(state).encode()).hexdigest()[:24]
                if ident in reachable:return ident
                node=solver.proven[state];reachable[ident]={k:v for k,v in node.items() if k!='children'}
                reachable[ident]['children']={m:collect(c) for m,c in node['children'].items()}
                return ident
            certroot=collect(root)
            e.save('mate_certificate_'+rm+'.json',{'root':certroot,'nodes':reachable})
        output['cases'].append(row);e.save('mate_proof_checks.json',output)
        print(row,flush=True)


if __name__=='__main__':main()
