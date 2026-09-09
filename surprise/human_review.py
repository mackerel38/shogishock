"""Human prediction review and seed annotation; explicitly not a candidate scan."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

import shogi
import shogi.KIF
import yaml

from .human_policy import examples, Policy, evaluate, metric
from .kif_export import ExportedKif, VariationNode, _add_branch, to_kif
from .position import Position
from .research import identity, write_json


def validate_kif(text):
    board=shogi.Board();states={};last=None;count=0;branches=0
    for line in text.splitlines():
        branch=re.match(r'変化：(\d+)手',line)
        if branch:
            number=int(branch[1]);sfen,last=states[number];board=shogi.Board(sfen);branches+=1;continue
        numbered=re.match(r'\s*(\d+)\s+',line)
        if not numbered:continue
        assert int(numbered[1])==board.move_number, line
        states[board.move_number]=(board.sfen(),last)
        usi,last,_=shogi.KIF.Parser.parse_move_str(line,last)
        assert usi is not None,line
        move=shogi.Move.from_usi(usi)
        assert board.is_legal(move),line
        board.push(move);count+=1
    return {'legal_move_lines':count,'variation_headers':branches}


def run(config):
    cfg=yaml.safe_load(Path(config).read_text());out=Path('reports/human_policy_v2')
    data=examples(cfg);splits=json.loads((Path(cfg['raw_dir'])/'splits_v2.json').read_text())
    metrics=json.loads((out/'policy_metrics.json').read_text())
    reach={r['position_id']:r for r in json.loads((Path(cfg['output'])/'reach_positions.json').read_text())}
    seeds=json.loads(Path('reports/terashock_seed_audit/positions.json').read_text())
    seed_ids={r['position_id'] for r in seeds if r['ply']<=12}
    join={}
    for limit in (12,16,20):
        group=[r for r in seeds if r['ply']<=limit]
        observed=[r for r in group if r['position_id'] in reach]
        supported=[r for r in observed if reach[r['position_id']]['sample_count']>=10 and reach[r['position_id']]['distinct_players_reaching']>=10]
        join[str(limit)]={'book_positions':len(group),'human_observed_positions':len(observed),
            'supported_games10_players10':len(supported),
            'sample_games':len(data['games']),'population_reach_unknown_for_unobserved':True}
    write_json(out/'seed_reach_join_summary.json',join)
    train=[r for r in data['rows'] if r['game'] in set(splits['time']['train'])]
    test=[r for r in data['rows'] if r['game'] in set(splits['time']['test'])]
    model=Policy(data,train,cfg['policy']['smoothing'])
    kind=metrics['time']['selected_on_validation'];choice=metrics['time']['models'][kind]
    rec=evaluate(model,data,test,kind,choice['threshold'],choice['temperature'])
    behavior={}
    for name,index in [('capture',2),('promotion',3),('pawn_contact_capture',4),('retreat',5)]:
        observations=[]
        for r in test:
            p=data['positions'][r['pid']];classes=[c.split(':') for c in p['classes']]
            if not any(c[index]=='1' for c in classes):continue
            q=model.predict(p,r['pid'],r['prefix'],kind,choice['threshold'],choice['temperature'])
            probability=sum(prob for prob,c in zip(q,classes) if c[index]=='1')
            observed=int(classes[p['moves'].index(r['move'])][index]=='1')
            observations.append((probability,observed))
        bins=[]
        for i in range(10):
            g=[(p,y) for p,y in observations if min(9,int(10*p))==i]
            if g:bins.append({'bin':i,'n':len(g),'predicted':sum(p for p,y in g)/len(g),'observed':sum(y for p,y in g)/len(g)})
        n=len(observations)
        behavior[name]={'opportunities':n,'chosen':sum(y for p,y in observations),
            'mean_predicted_probability':sum(p for p,y in observations)/n if n else None,
            'observed_rate':sum(y for p,y in observations)/n if n else None,
            'binary_brier':sum((p-y)**2 for p,y in observations)/n if n else None,
            'event_ece':sum(b['n']*abs(b['predicted']-b['observed']) for b in bins)/n if n else None,
            'reliability':bins}
    write_json(out/'behavior_calibration.json',{'scope':'post-hoc falsification on fixed time test; conditional on event move available; not causal effects','events':behavior})
    write_json(out/'book_policy_slices.json',{'time_test_book12':metric([r for r in rec if r['pid'] in seed_ids]),
        'time_test_outside_book12':metric([r for r in rec if r['pid'] not in seed_ids])})
    by_game={}
    for r in test:by_game.setdefault(r['game'],{})[r['ply']]=r
    candidates=[]
    for r in test:
        following=by_game[r['game']].get(r['ply']+1)
        if not following or r['pid'] not in seed_ids or r['ply']>11 or reach[r['pid']]['sample_count']<10:continue
        p=data['positions'][following['pid']]
        q=model.predict(p,following['pid'],following['prefix'],kind,choice['threshold'],choice['temperature'])
        ordered=sorted(zip(p['moves'],q),key=lambda x:(-x[1],x[0]))
        if ordered[0][0]==following['move']:continue
        candidates.append({'parent':r,'reply':following,'prediction':ordered,'confidence':ordered[0][1]})
    selected=[]
    for side in (0,1):
        seen=set()
        for r in sorted(candidates,key=lambda r:-r['confidence']):
            if data['positions'][r['parent']['pid']]['side']!=side or r['parent']['pid'] in seen:continue
            selected.append(r);seen.add(r['parent']['pid'])
            if len(seen)==3:break
    directory=Path('exports/human_policy_review_v2');directory.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for index,r in enumerate(selected):
        parent=r['parent'];reply=r['reply'];p=data['positions'][parent['pid']];h=reach[parent['pid']]
        cid=parent['pid']+'_'+parent['move'].replace('*','-')
        side='sente' if p['side']==0 else 'gote'
        candidate=VariationNode(move=parent['move'],comment=['[held-out prediction review; NOT a discovered surprise]',
            'time split: train only; validation-selected model; this example was selected post-hoc for review',
            f"reach sample: {h['games_reaching_position']}/{h['total_games']}; players={h['distinct_players_reaching']}",
            'parent_eval / candidate_eval / P_good / human_gap: not measured in this prediction-only review',
            f"actual held-out response: {reply['move']}"])
        child=Position.from_sfen(p['sfen']).apply_move(parent['move'])
        warnings=[];probs=dict(r['prediction'])
        _add_branch(candidate,[reply['move']],[f"[observed human response] human_probability: {probs[reply['move']]:.6f}"],warnings,child.board)
        for rank,(move,prob) in enumerate(r['prediction'][:5],1):
            _add_branch(candidate,[move],[f'[Human Policy top {rank}]',f'human_probability: {prob:.6f}'],warnings,child.board)
        kif=to_kif(ExportedKif(cid,p['sfen'],parent['prefix'].split(),candidate,warnings),title='Human Policy held-out review, not E2E')
        validation=validate_kif(kif);assert not warnings
        file=directory/f'{side}_{cid}.kif';file.write_text(kif,encoding='utf-8')
        manifest.append({'side':side,'file':str(file),'candidate_id':cid,'sfen':p['sfen'],'candidate_move':parent['move'],
            'actual_reply':reply['move'],'predicted_reply':r['prediction'][0][0],
            'predicted_confidence':r['confidence'],'probability_of_actual':probs[reply['move']],
            'reach_probability':h['reach_probability'],'sample_count':h['sample_count'],
            'validation':validation,'GUI_status':'user visual review required'})
    write_json(out/'kif_review_manifest.json',manifest)
    decision=json.loads((out/'policy_decision.json').read_text())
    write_json(out/'prediction_review_status.json',{'status':'prediction_review_only',
        'small_e2e_gate':decision['small_e2e_allowed'],
        'new_parent_positions_evaluated':0,'new_candidates_examined':0,
        'obvious_reply_rejects':None,'redundant_nonpromotion_rejects':None,
        'P_good':None,'human_gap':None,'new_engine_requests':0,
        'review_kif_count':len(manifest),'review_kif_purpose':'held-out prediction review only, not new surprise candidates'})
    print(json.dumps({'seed_join':join,'review_kifs':len(manifest)},ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',default='config/human_pilot.yaml')
    run(p.parse_args().config)
