"""Dependency-free probability baselines, grouped held-out tests, calibration."""
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import random
import sqlite3

import shogi
import yaml

from .human_data import digest
from .research import identity, write_json


def action_class(board, move):
    m=shogi.Move.from_usi(move)
    piece=board.piece_at(m.from_square) if m.from_square is not None else None
    victim=board.piece_at(m.to_square)
    retreat=bool(piece and (m.to_square//9-m.from_square//9)*(1 if board.turn==0 else -1)>0)
    pawn_contact=bool(piece and victim and piece.piece_type==shogi.PAWN and victim.piece_type==shogi.PAWN)
    return ':'.join(map(str,[piece.piece_type if piece else m.drop_piece_type,
        int(piece is None),int(victim is not None),int(m.promotion),int(pawn_contact),int(retreat)]))


def describe(sfen):
    board=shogi.Board(sfen)
    moves=sorted(m.usi() for m in board.legal_moves)
    return {'sfen':sfen,'moves':moves,'classes':[action_class(board,m) for m in moves],'side':board.turn}


def examples(cfg):
    path=Path(cfg['raw_dir'])/'policy_examples.json'
    if path.exists():return json.loads(path.read_text())
    db=sqlite3.connect(cfg['database'])
    games={k:json.loads(v) for k,v in db.execute('SELECT game_key,payload FROM games WHERE accepted=1')}
    positions={p:describe(s) for p,s in db.execute('SELECT position_id,sfen FROM positions')}
    rows=[]
    for key,ply,pid,move in db.execute('SELECT game_key,ply,position_id,move FROM occurrences WHERE move IS NOT NULL ORDER BY game_key,ply'):
        g=games[key]
        assert move in positions[pid]['moves']
        rows.append({'game':key,'ply':ply,'pid':pid,'move':move,
            'prefix':' '.join(g['moves'][:ply])})
    db.close()
    result={'games':{k:{'players':list(v['player_ids'].values()),'date':v['created_at_ms']} for k,v in games.items()},'positions':positions,'rows':rows}
    write_json(path,result)
    return result


def group_for(key,seed):
    value=int(digest(seed+key)[:8],16)/2**32
    return 'train' if value<.6 else 'validation' if value<.8 else 'test'


def split_games(games,mode,seed):
    # Independent domain from focal sampling and participant-cap ordering.
    seed = seed + ':heldout-v2:' + mode + ':'
    groups={k:[] for k in ('train','validation','test','purged')}
    if mode=='time':
        ordered=sorted(games,key=lambda k:(games[k]['date'],k))
        a=games[ordered[int(len(ordered)*.6)]]['date'];b=games[ordered[int(len(ordered)*.8)]]['date']
    for key,g in games.items():
        if mode=='game': bucket=group_for(key,seed)
        elif mode=='time':bucket='train' if g['date']<a else 'validation' if g['date']<b else 'test'
        else:
            bins={group_for(p,seed) for p in g['players']}
            bucket=next(iter(bins)) if len(bins)==1 else 'purged'
        groups[bucket].append(key)
    assert not set(groups['train'])&set(groups['test'])
    if mode=='player':
        ps={k:{p for g in groups[k] for p in games[g]['players']} for k in ('train','validation','test')}
        assert not(ps['train']&ps['test'] or ps['train']&ps['validation'] or ps['validation']&ps['test'])
    return groups


def normalize(values):
    s=sum(values)
    return [v/s for v in values]


class Policy:
    def __init__(self,data,train,alpha=5):
        self.positions=data['positions'];self.alpha=alpha
        self.pop=defaultdict(Counter);self.exact=defaultdict(Counter);self.prefix=defaultdict(Counter)
        self.chosen=Counter();self.available=Counter()
        for r in train:
            p=self.positions[r['pid']];idx=p['moves'].index(r['move'])
            self.pop[p['side']][r['move']]+=1;self.exact[r['pid']][r['move']]+=1;self.prefix[r['prefix']][r['move']]+=1
            self.chosen[p['classes'][idx]]+=1;self.available.update(p['classes'])

    def predict(self,p,pid,prefix,kind='hierarchical',threshold=5,temperature=1):
        moves=p['moves'];n=len(moves)
        if not n:return []
        popularity=normalize([self.pop[p['side']][m]+.5 for m in moves])
        if kind=='uniform':probs=[1/n]*n
        elif kind=='popularity':probs=popularity
        else:
            counts=self.prefix.get(prefix,{}) if kind=='prefix' else self.exact.get(pid,{})
            support=sum(counts.values())
            fallback=normalize([(self.chosen[c]+1)/(self.available[c]+20) for c in p['classes']])
            fallback=[.5*a+.5*b for a,b in zip(fallback,popularity)]
            if kind=='behavior':probs=fallback
            elif kind=='hierarchical' and support<threshold:probs=fallback
            else:
                prior=fallback if kind=='hierarchical' else popularity
                probs=normalize([counts.get(m,0)+self.alpha*q for m,q in zip(moves,prior)])
        if temperature!=1:probs=normalize([q**(1/temperature) for q in probs])
        assert abs(sum(probs)-1)<1e-8 and all(q>0 for q in probs)
        return probs


def metric(records):
    if not records:return {'n':0}
    result={'n':len(records)}
    for key in ('nll','brier','top1','top3','top5'):
        result[key]=sum(r[key] for r in records)/len(records)
    bins=[]
    for i in range(10):
        g=[r for r in records if min(9,int(r['confidence']*10))==i]
        bins.append({'lower':i/10,'upper':(i+1)/10,'n':len(g),
            'confidence':sum(r['confidence'] for r in g)/len(g) if g else None,
            'accuracy':sum(r['top1'] for r in g)/len(g) if g else None})
    result['reliability']=bins
    result['ece']=sum(b['n']*abs(b['confidence']-b['accuracy']) for b in bins if b['n'])/len(records)
    result['distinct_games']=len({r['game'] for r in records})
    return result


def evaluate(model,data,rows,kind,threshold=5,temperature=1):
    records=[];cache={}
    for r in rows:
        p=data['positions'][r['pid']]
        key=(r['pid'],r['prefix'] if kind=='prefix' else '')
        if key not in cache:cache[key]=model.predict(p,r['pid'],r['prefix'],kind,threshold,temperature)
        probs=cache[key];i=p['moves'].index(r['move'])
        ordered=sorted(range(len(probs)),key=lambda j:(-probs[j],p['moves'][j]))
        support=sum(model.exact.get(r['pid'],{}).values())
        records.append({'game':r['game'],'ply':r['ply'],'pid':r['pid'],'support':support,
            'nll':-math.log(probs[i]),'brier':sum(q*q for q in probs)-2*probs[i]+1,
            'top1':int(ordered[0]==i),'top3':int(i in ordered[:3]),'top5':int(i in ordered[:5]),
            'confidence':max(probs)})
    return records


def bootstrap_delta(selected,baseline):
    groups=defaultdict(list)
    for a,b in zip(selected,baseline):
        assert (a['game'],a['pid'],a['ply'])==(b['game'],b['pid'],b['ply'])
        groups[a['game']].append(a['nll']-b['nll'])
    ids=sorted(groups);rng=random.Random(20260909);values=[]
    for _ in range(300):
        sample=[v for key in rng.choices(ids,k=len(ids)) for v in groups[key]]
        values.append(sum(sample)/len(sample))
    values.sort()
    return {'delta_nll':sum(a['nll']-b['nll'] for a,b in zip(selected,baseline))/len(selected),
        'bootstrap_game_interval95':[values[7],values[292]],'scope':'game-cluster bootstrap; residual player dependence remains'}


def run(config,report_output='reports/human_policy_v2'):
    cfg=yaml.safe_load(Path(config).read_text());out=Path(report_output);out.mkdir(parents=True,exist_ok=True);data=examples(cfg)
    result={};snapshots={}
    for mode in ('game','time','player'):
        split=split_games(data['games'],mode,cfg['seed']);sets={k:set(v) for k,v in split.items()}
        subsets={k:[r for r in data['rows'] if r['game'] in ids] for k,ids in sets.items() if k!='purged'}
        if not all(subsets.values()):
            result[mode]={'status':'insufficient_split','games':{k:len(v) for k,v in split.items()}};continue
        model=Policy(data,subsets['train'],cfg['policy']['smoothing']);models={};predictions={}
        for kind in ('uniform','popularity','prefix','exact','behavior','hierarchical'):
            candidates=[]
            for threshold in cfg['policy']['exact_thresholds'] if kind=='hierarchical' else [5]:
                for temp in [1] if kind=='uniform' else [.75,1,1.25,1.5]:
                    val=evaluate(model,data,subsets['validation'],kind,threshold,temp)
                    candidates.append((metric(val)['nll'],threshold,temp))
            _,threshold,temp=min(candidates)
            rec=evaluate(model,data,subsets['test'],kind,threshold,temp);predictions[kind]=rec
            models[kind]={'threshold':threshold,'temperature':temp,'validation_nll':min(candidates)[0],
                'test':metric(rec),
                'exact_supported':metric([r for r in rec if r['support']>=threshold]),
                'fallback':metric([r for r in rec if r['support']<threshold]),
                'unseen_exact':metric([r for r in rec if r['support']==0]),
                'ply_bands':{name:metric([r for r in rec if lo<=r['ply']<=hi]) for name,lo,hi in [('0-4',0,4),('5-12',5,12),('13-24',13,24)]}}
        chosen=min(('prefix','exact','hierarchical'),key=lambda k:models[k]['validation_nll'])
        selected=models[chosen];delta=bootstrap_delta(predictions[chosen],predictions['popularity'])
        enough=len(split['validation'])>=cfg['policy']['validation_min_games'] and len(split['test'])>=cfg['policy']['test_min_games']
        gate=enough and delta['delta_nll']<=-cfg['policy']['nll_improvement_min'] and selected['test']['ece']<=cfg['policy']['ece_max']
        result[mode]={'games':{k:len(v) for k,v in split.items()},'models':models,'selected_on_validation':chosen,
            'selected_minus_popularity':delta,'small_e2e_gate':gate,
            'train_test_player_overlap':len({p for g in split['train'] for p in data['games'][g]['players']}&{p for g in split['test'] for p in data['games'][g]['players']})}
        snapshots[mode]=split
        write_json(out/'policy_metrics.json',result)
        print(mode,chosen,json.dumps({'games':result[mode]['games'],'nll':selected['test']['nll'],'ece':selected['test']['ece'],'gate':gate}),flush=True)
    write_json(Path(cfg['raw_dir'])/'splits_v2.json',snapshots)
    gate=all(result.get(mode,{}).get('small_e2e_gate',False) for mode in ('time','player'))
    write_json(out/'policy_decision.json',{'small_e2e_allowed':gate,'large_scan_allowed':False,
        'reason':'bounded engineering/research trial only; no response-set/OOD calibration guarantee' if gate else 'held-out support/performance/calibration checkpoint not passed',
        'splits_config_sha256':digest(json.dumps(cfg['policy'],sort_keys=True))})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',default='config/human_pilot.yaml')
    parser.add_argument('--report-output',default='reports/human_policy_v2')
    args=parser.parse_args();run(args.config,args.report_output)
