"""At most four book parents, six full reply evaluations; gated human experiment."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

import yaml

from .engine import Engine, CACHE_SCHEMA_VERSION
from .human_policy import examples, Policy, describe
from .human_response import response_metrics
from .human_review import validate_kif
from .kif_export import export_candidate
from .obvious import obvious_replies, reply_features, reply_summary
from .position import Position
from .promotion import annotate_pairs
from .research import cp, encode, evaluate_candidate, relative_metrics, write_json


def analyze_parent(position,cfg,out):
    e=cfg['experiment'];path=out/'checkpoints'/(position['position_id']+'.json')
    data=json.loads(path.read_text()) if path.exists() else {'position':position,'rows':[]}
    done={r['move'] for r in data['rows']};p=Position.from_sfen(position['sfen'])
    legacy=yaml.safe_load(Path(e['engine_config']).read_text())
    legacy['search'].update(shallow_nodes=e['nodes'],pass_nodes=e['nodes'])
    with Engine.from_config(e['engine_config']) as engine:
        assert engine.cache
        best=data.get('best') or encode(engine.evaluate(p,e['nodes']));data['best']=best
        parent_advantage=cp(best)*(1 if position['side_to_move']=='sente' else -1) if cp(best) is not None else None
        data['parent_attacker_advantage']=parent_advantage
        if parent_advantage is None or parent_advantage>=e['parent_favorable_cp']:
            data['parent_not_escalated_reason']='parent_eval_unknown' if parent_advantage is None else 'parent_already_favorable'
            write_json(path,data);return data
        for move in p.legal_moves():
            if move in done:continue
            r=evaluate_candidate(engine,position,move,best,legacy)
            child=p.apply_move(move);features={f['move']:f for f in obvious_replies(p,move)}
            moves=list(features)
            if r['normal']['pv'] and r['normal']['pv'][0] not in moves:moves.append(r['normal']['pv'][0])
            replies=[]
            for reply in moves:
                replies.append((features.get(reply) or reply_features(p,move,reply))|{'result':encode(engine.evaluate(child.apply_move(reply),e['nodes']))})
            summary=reply_summary(replies,r['normal'],r['attacker_side'],len(child.legal_moves()),e['tolerances'])
            neutral=any(x['obvious'] and x['is_good_100'] for x in replies) if summary['numeric_comparable'] else None
            r.update(parent_attacker_advantage=parent_advantage,parent_already_favorable=False,
                parent_book_eval_sente=position['parent_book_eval_sente'],reach_probability=position['reach_probability'],
                reach_sample_count=position['sample_count'],reach_distinct_players=position['distinct_players_reaching'],
                obvious_reply_exists=bool(features),obvious_reply_neutralizes=neutral,
                candidate_piece_capturable=any(f['reply_captures_candidate'] for f in features.values()),
                obvious_diagnostic=summary|{'responses':replies},
                not_escalated_reason=['obvious_reply_neutralizes'] if neutral else ['obvious_reply_unresolved'] if neutral is None else [])
            data['rows'].append(r);write_json(path,data)
    annotate_pairs(p,data['rows'],e['nonpromotion_loss_cp']);relative_metrics(data['rows'])
    write_json(path,data);return data


def run(config):
    cfg=yaml.safe_load(Path(config).read_text());e=cfg['experiment'];out=Path('reports/human_e2e')
    seed_cfg=yaml.safe_load(Path('config/terashock_seed.yaml').read_text())
    if e['max_positions_per_side']>2 or e['max_candidates_per_side']>3 or e['nodes']>100000:
        raise ValueError('bounded E2E budget exceeded')
    decision=json.loads(Path('reports/human_policy_v2/policy_decision.json').read_text())
    if not decision['small_e2e_allowed']:raise ValueError('held-out checkpoint not passed; no scan')
    out.mkdir(parents=True,exist_ok=True);(out/'checkpoints').mkdir(exist_ok=True)
    reach={r['position_id']:r for r in json.loads((Path(cfg['output'])/'reach_positions.json').read_text())}
    seeds=json.loads(Path('reports/terashock_seed_audit/positions.json').read_text())
    eligible=[r for r in seeds if 3<=r['ply']<=seed_cfg['primary_max_ply'] and r['position_id'] in reach
        and reach[r['position_id']]['sample_count']>=e['min_games_support']
        and reach[r['position_id']]['distinct_players_reaching']>=e['min_players_support']
        and r['book_score_numeric'] and abs(r['parent_book_eval_sente'])<seed_cfg['parent_book_abs_eval_low_priority_cp']]
    positions=[]
    for side in ('sente','gote'):
        group=sorted((r for r in eligible if r['side_to_move']==side),key=lambda r:(-reach[r['position_id']]['reach_probability'],r['ply'],r['position_id']))[:e['max_positions_per_side']]
        for r in group:
            h=reach[r['position_id']]
            positions.append(r|{k:v for k,v in h.items() if k not in ('sfen','move_history','side_to_move')}|{'source':'BOOK-700T-Shock + independent human annotation'})
    with Engine.from_config(e['engine_config']) as engine:
        assert engine.cache
        fingerprint={'binary_sha256':engine.binary_sha256,'eval_sha256':engine.eval_sha256,
            'engine_config':yaml.safe_load(Path(e['engine_config']).read_text())}
    manifest={'config':cfg,'engine':fingerprint,'seed_config':seed_cfg,'seed_manifest':json.loads(Path('reports/terashock_seed_audit/manifest.json').read_text()),
        'policy_decision':decision,'cache_schema':CACHE_SCHEMA_VERSION,'positions':[p['position_id'] for p in positions],
        'scope':'local exploratory experiment only; book redistribution not approved'}
    path=out/'manifest.json'
    if path.exists() and json.loads(path.read_text())!=manifest:raise ValueError('E2E fingerprint changed')
    write_json(path,manifest);write_json(out/'positions.json',positions)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda p:analyze_parent(p,cfg,out),positions))
    rows=[r for result in results for r in result['rows']]
    write_json(out/'candidates.json',rows)
    selected=[]
    for side in ('sente','gote'):
        candidates=[r for r in rows if r['attacker_side']==side and not r['not_escalated_reason']]
        # Purposive cost strata, never pass-ranked; no negative-eval cutoff.
        for order in ('low_cost','rare_quiet','high_cost')[:e['max_candidates_per_side']]:
            remaining=[r for r in candidates if r not in selected]
            if not remaining:break
            if order=='low_cost':key=lambda r:(r['candidate_eval_loss'] if r['candidate_eval_loss'] is not None else float('inf'),r['candidate_id'])
            elif order=='rare_quiet':key=lambda r:(r['candidate_move_frequency'],r['is_check'] or r['is_capture'],r['candidate_id'])
            else:key=lambda r:(-(r['candidate_eval_loss'] if r['candidate_eval_loss'] is not None else -float('inf')),r['candidate_id'])
            r=min(remaining,key=key);r['selection_stratum']=order;selected.append(r)
    data=examples(cfg);splits=json.loads((Path(cfg['raw_dir'])/'splits_v2.json').read_text())
    train_ids=set(splits['time']['train']);train=[r for r in data['rows'] if r['game'] in train_ids]
    model=Policy(data,train,cfg['policy']['smoothing'])
    metrics=json.loads(Path('reports/human_policy_v2/policy_metrics.json').read_text())['time']
    kind=metrics['selected_on_validation'];choice=metrics['models'][kind]
    position_lookup={p['position_id']:p for p in positions};response_records=[]
    with Engine.from_config(e['engine_config']) as engine:
        for r in selected:
            parent=Position.from_sfen(position_lookup[r['position_id']]['sfen']);child=parent.apply_move(r['move'])
            p=describe(child.sfen);prefix=' '.join(position_lookup[r['position_id']]['move_history']+[r['move']])
            probabilities=model.predict(p,r['resulting_position_id'],prefix,kind,choice['threshold'],choice['temperature'])
            replies=[]
            for reply,prob in sorted(zip(p['moves'],probabilities),key=lambda x:-x[1]):
                f=reply_features(parent,r['move'],reply)
                replies.append(f|{'human_probability':prob,'result':encode(engine.evaluate(child.apply_move(reply),e['nodes']))})
            summary=reply_summary(replies,r['normal'],r['attacker_side'],len(p['moves']),e['tolerances'])
            reference=summary['reference_eval'] if summary['numeric_comparable'] else None
            human=response_metrics(replies,reference,r['attacker_side'],e['tolerances'])
            neutral=any(x['obvious'] and x['is_good_100'] for x in replies) if summary['numeric_comparable'] else None
            r.update(human,legal_fragility={k:v for k,v in summary.items() if k.startswith('good_reply_') or k=='legal_reply_count'},
                obvious_reply_neutralizes=neutral,policy_exact_support=sum(model.exact.get(r['resulting_position_id'],{}).values()),
                policy_training_scope='time train only; no test refit',policy_out_of_distribution_warning=True)
            if neutral and 'obvious_reply_neutralizes' not in r['not_escalated_reason']:r['not_escalated_reason'].append('obvious_reply_neutralizes')
            r['not_escalated_reason'].append('human_policy_ood_and_response_set_calibration_unverified')
            response_records.append({'candidate_id':r['candidate_id'],'responses':replies,**summary,**human})
            write_json(out/'human_responses.json',response_records);write_json(out/'candidates.json',rows)
    exports=Path('exports/human_e2e');exports.mkdir(parents=True,exist_ok=True)
    kif=[]
    for r in selected:
        file=export_candidate(out,r['candidate_id'],exports/(r['attacker_side']+'_'+r['candidate_id']+'.kif'))
        validation=validate_kif(file.read_text())
        warnings=json.loads(file.with_suffix('.json').read_text())['warnings']
        kif.append({'file':str(file),'candidate_id':r['candidate_id'],'validation':validation,'warnings':warnings})
    summary={'parent_positions_considered':len(positions),'parent_positions_scanned':sum(bool(r['rows']) for r in results),
        'candidates_examined':len(rows),'obvious_reply_rejects':sum(r['obvious_reply_neutralizes'] is True for r in rows),
        'redundant_nonpromotion_rejects':sum(r['redundant_nonpromotion'] for r in rows),
        'human_evaluated_candidates':len(selected),'response_evaluations':sum(len(r['responses']) for r in response_records),
        'nodes':e['nodes'],'selected':[{'candidate_id':r['candidate_id'],'side':r['attacker_side'],'move':r['move'],
            'reach':r['reach_probability'],'parent_eval':r['best_eval'],'candidate_eval':r['candidate_eval'],
            'P_good':r['P_good'],'human_gap':r['human_gap'],'covered_probability':r['covered_probability'],
            'V_optimal':r['V_optimal'],'E_human':r['E_human'],'human_eval_delta':r['human_eval_delta'],
            'obvious_reply_neutralizes':r['obvious_reply_neutralizes'],
            'policy_exact_support':r['policy_exact_support'],'selection_stratum':r['selection_stratum']} for r in selected],
        'large_scan_allowed':False,'kif':kif}
    write_json(out/'summary.json',summary);print(json.dumps(summary,ensure_ascii=False),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',default='config/human_pilot.yaml');run(p.parse_args().config)
