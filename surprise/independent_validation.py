"""Fixed-protocol acquisition/measurement adapter. No fit or model selection."""
import argparse
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import sqlite3
import urllib.parse

import yaml

from .frozen_policy import verify_freeze, load_frozen, sha, immutable_json
from .human_data import PublicClient, digest, millis, rating_band
from .reach import ReachDB, normalize_game
from .research import write_json
from .human_policy import examples
from .response_calibration import prepare, probabilities, SETS, PRIMARY, event_metric
from .response_cache import ResponseDiagnosticCache
from .calibration_review import bootstrap

CFG_PATH = Path('config/independent_policy_validation.yaml')


def cfg():
    verify_freeze()
    return yaml.safe_load(CFG_PATH.read_text())


def exposure(c):
    return json.loads((Path(c['raw_dir'])/'prior_exposure.json').read_text())


def frame(c, client):
    root=Path(c['raw_dir']);dest=root/'sampling_frame.json'
    if dest.exists():return json.loads(dest.read_text())
    excluded=set(exposure(c)['players']);members={};teams={}
    for page in c['sampling']['team_pages']:
        result=client.get('/api/team/all?page='+str(page))['data']
        for team in result['currentPageResults']:
            key=team['id']
            if key in teams or key in c['sampling']['exclude_teams']:continue
            reply=client.get('/api/team/'+urllib.parse.quote(key,safe='')+'/users',True,True)
            teams[key]={'status':reply['status'],'members':len(reply['data'])}
            for member in reply['data']:members.setdefault(member['id'].lower(),member)
    pools=defaultdict(list)
    for key,m in members.items():
        if key in excluded or m.get('title')=='BOT' or m.get('disabled') or m.get('seenAt',0)<millis(c['sampling']['since']):continue
        perf=m.get('perfs',{}).get('realTime',{})
        pools[rating_band(perf.get('rating') if perf.get('games',0) else None)].append(key)
    bands={k:len(v) for k,v in pools.items()}
    queues={k:deque(sorted(v,key=lambda p:digest(c['seed']+':focal:'+p))) for k,v in pools.items()}
    selected=[]
    while any(queues.values()) and len(selected)<c['sampling']['focal_players_max']:
        for band in sorted(queues):
            if queues[band] and len(selected)<c['sampling']['focal_players_max']:selected.append(queues[band].popleft())
    result={'members':members,'teams':teams,'eligible_bands':bands,'focal_players':selected}
    immutable_json(dest,result)
    return result


def acquire():
    c=cfg();out=Path(c['output']);out.mkdir(parents=True,exist_ok=True)
    seal=Path(c['raw_dir'])/'dataset_seal.json'
    if seal.exists():
        verify_dataset(c);print('Dataset already sealed; no acquisition.');return
    client=PublicClient(c);f=frame(c,client)
    prior=exposure(c);excluded=set(prior['players']);old_ids=set(prior['game_ids'])
    games={};downloaded=0
    write_json(out/'acquisition_status.json',{'status':'fetching_fixed_focals','focal_players':len(f['focal_players']),
        'frame_members':len(f['members']),'eligible_rating_bands':f['eligible_bands'],'scores_revealed':False})
    print('Frame fixed:',len(f['members']),'members;',len(f['focal_players']),'focals',flush=True)
    s=c['sampling']
    for i,user in enumerate(f['focal_players']):
        params=urllib.parse.urlencode({'since':millis(s['since']),'until':millis(s['until'])-1,
            'max':s['games_per_request'],'perfType':'realTime','moves':'true','ongoing':'false',
            'finished':'true','evals':'false','clocks':'false'})
        response=client.get('/api/games/user/'+urllib.parse.quote(user,safe='')+'?'+params,True)
        if len(response['data'])>s['games_per_request']:raise ValueError('server game cap exceeded')
        for raw in response['data']:
            downloaded+=1
            game=normalize_game(raw,{k:v for k,v in response.items() if k!='data'})
            game.update(rated=raw.get('rated'),speed=raw.get('speed'))
            players={p.lower() for p in game['player_ids'].values() if p}
            if players & excluded:game['exclusion_reasons'].append('prior_exposed_player')
            if game['game_id'] in old_ids:game['exclusion_reasons'].append('prior_exposed_game')
            if not millis(s['since'])<=raw.get('createdAt',0)<millis(s['until']):game['exclusion_reasons'].append('outside_window')
            if raw.get('daysPerTurn') is not None or raw.get('speed')=='correspondence':game['exclusion_reasons'].append('correspondence')
            if not isinstance(raw.get('clock'),dict) or not raw['clock']:game['exclusion_reasons'].append('realtime_clock_unknown')
            games.setdefault(game['game_id'],game)
        if (i+1)%20==0:
            print('Fetched',i+1,'/',len(f['focal_players']),'focals;',len(games),'unique exports',flush=True)
            write_json(out/'acquisition_status.json',{'status':'fetching_fixed_focals','completed_focals':i+1,
                'focal_players':len(f['focal_players']),'unique_exports':len(games),'scores_revealed':False})
    counts=Counter();accepted=[];payloads=[];reasons=Counter()
    db=ReachDB(c['database'],s['max_ply'])
    try:
        for key in sorted(games,key=lambda k:digest(c['seed']+':accept:'+k)):
            game=games[key];players={p.lower() for p in game['player_ids'].values() if p}
            if not game['exclusion_reasons']:
                if len(accepted)>=s['accepted_games_max']:game['exclusion_reasons'].append('total_game_cap')
                elif any(counts[p]>=s['max_games_per_player'] for p in players):game['exclusion_reasons'].append('participant_cap')
            db.ingest(game)
            ok,payload=db.db.execute('SELECT accepted,payload FROM games WHERE game_key=?',('lishogi:'+key,)).fetchone()
            parsed=json.loads(payload)
            if ok:
                assert not players & excluded and key not in old_ids
                counts.update(players);accepted.append(key);payloads.append(parsed)
            else:reasons.update(parsed['exclusion_reasons'])
        positions=db.db.execute('SELECT count(*) FROM positions').fetchone()[0]
    finally:db.close()
    ratings=[r for g in payloads for r in g['rating'].values() if r is not None]
    ordered=sorted(counts.values())
    summary={'downloaded_records':downloaded,'unique_exports':len(games),'accepted_games':len(accepted),
        'distinct_players':len(counts),'games_per_player_histogram':dict(sorted(Counter(ordered).items())),
        'games_per_player_median':ordered[len(ordered)//2] if ordered else None,'games_per_player_max':max(ordered,default=0),
        'rating_bands':dict(Counter(rating_band(r) for r in ratings)),
        'rating_min_median_max':[min(ratings),sorted(ratings)[len(ratings)//2],max(ratings)] if ratings else None,
        'missing_ratings':2*len(accepted)-len(ratings),'clock_distribution':dict(Counter(json.dumps(g['time_control'],sort_keys=True) for g in payloads)),
        'rated':dict(Counter(str(g['rated']) for g in payloads)),
        'date_month':dict(sorted(Counter(datetime.fromtimestamp(g['created_at_ms']/1000,timezone.utc).strftime('%Y-%m') for g in payloads).items())),
        'exclusions':dict(reasons),'exact_positions':positions,'old_player_overlap':0,'old_game_overlap':0,
        'frame_members':len(f['members']),'frame_teams':len(f['teams']),'eligible_bands':f['eligible_bands'],
        'focal_players':len(f['focal_players']),'correspondence_in_primary':0,'population_representative':False}
    write_json(out/'dataset_summary.json',summary)
    immutable_json(seal,{'accepted_game_ids':sorted(accepted),'players':sorted(counts),
        'database_sha256':sha(c['database']),'sampling_frame_sha256':sha(Path(c['raw_dir'])/'sampling_frame.json'),
        'frozen_model_manifest_sha256':sha(out/'frozen_model_fingerprint.json'),
        'sealed_at':datetime.now(timezone.utc).isoformat(),'scores_revealed_at_sealing':False})
    write_json(out/'dataset_fingerprint.json',{'dataset_seal_sha256':sha(seal),
        'database_sha256':sha(c['database']),'accepted_games':len(accepted),'distinct_players':len(counts),
        'sealed_before_evaluation':True})
    write_json(out/'acquisition_status.json',{'status':'sealed','completed_focals':len(f['focal_players']),
        'scores_revealed':False,'accepted_games':len(accepted)})
    print(json.dumps(summary),flush=True)


def verify_dataset(c):
    seal=json.loads((Path(c['raw_dir'])/'dataset_seal.json').read_text())
    assert sha(c['database'])==seal['database_sha256']
    assert sha(Path(c['raw_dir'])/'sampling_frame.json')==seal['sampling_frame_sha256']
    assert sha(Path(c['output'])/'frozen_model_fingerprint.json')==seal['frozen_model_manifest_sha256']
    assert not set(seal['players']) & set(exposure(c)['players'])
    assert not set(seal['accepted_game_ids']) & set(exposure(c)['game_ids'])
    return seal


def score(records, name, weights, participants, movers, game_counts):
    import math
    from .human_policy import metric
    raw=[];events=defaultdict(list);eligible_games=defaultdict(set);weighted=defaultdict(list)
    for index,r in enumerate(records):
        q=probabilities(r,name,weights);label=r['label'];order=sorted(range(len(q)),key=lambda j:(-q[j],r['features'][j]['move']))
        raw.append({'game':r['game'],'support':r['support'],'nll':-math.log(q[label]),
            'brier':sum(p*p for p in q)-2*q[label]+1,'confidence':max(q),
            'top1':int(order[0]==label),'top3':int(label in order[:3]),'top5':int(label in order[:5])})
        w=.5*sum(1/game_counts[p] for p in participants[r['game']])
        for j,s in enumerate(SETS):
            if not any(f['sets'][j] for f in r['features']):continue
            prob=sum(p*f['sets'][j] for p,f in zip(q,r['features']));y=r['features'][label]['sets'][j]
            events[s].append((prob,y,r['game']));eligible_games[s].add(r['game'])
            weighted[s].append((w,prob,y,movers[index]))
    result={'overall':metric(raw),'sets':{},'abstain_fraction':1.0,'response_set_calibration_status':'frozen_abstention',
        'low_support_fraction':sum(r['support']<2 for r in raw)/len(raw) if raw else None}
    for key,test in [('exact_supported',lambda n:n>=2),('fallback',lambda n:n<2),('support_zero',lambda n:n==0),('support_one',lambda n:n==1)]:
        result[key]=metric([r for r in raw if test(r['support'])])
    for s in SETS:
        m=event_metric(events[s]);m['opportunity_count']=m['sample_count']
        m['distinct_players_both_sides']=len({p for g in eligible_games[s] for p in participants[g]})
        m['distinct_actual_movers']=len({p for w,q,y,p in weighted[s]})
        den=sum(w for w,q,y,p in weighted[s])
        m['player_equal_game_weighted']={'weight_sum':den,'observed':sum(w*y for w,q,y,p in weighted[s])/den if den else None,
            'predicted':sum(w*q for w,q,y,p in weighted[s])/den if den else None,
            'brier':sum(w*(q-y)**2 for w,q,y,p in weighted[s])/den if den else None}
        result['sets'][s]=m
    result['inherited_primary_mean_brier']=sum(result['sets'][s]['brier'] for s in PRIMARY)/4 if all(result['sets'][s]['sample_count'] for s in PRIMARY) else None
    return result


def measure():
    c=cfg();seal=verify_dataset(c);out=Path(c['output'])
    if (out/'measurement_seal.json').exists():
        seal2=json.loads((out/'measurement_seal.json').read_text())
        assert sha(out/'metrics.json')==seal2['metrics_sha256']
        print('Measurements already sealed; not re-evaluating.');return
    data=examples(c)
    rows=data['rows'];participants={g:[p.lower() for p in v['players']] for g,v in data['games'].items()}
    counts=Counter(p for ps in participants.values() for p in set(ps))
    # examples preserves normalized player_ids insertion order (sente, gote); verify from payloads.
    with sqlite3.connect(f"file:{c['database']}?mode=ro",uri=True) as db:
        by_side={g:json.loads(payload)['player_ids'] for g,payload in db.execute('SELECT game_key,payload FROM games WHERE accepted=1')}
    movers=[by_side[r['game']]['sente' if data['positions'][r['pid']]['side']==0 else 'gote'].lower() for r in rows]
    result={}
    for mode in ('time','player','game'):
        model,selected,w=load_frozen(mode)
        with ResponseDiagnosticCache(str(Path(c['raw_dir'])/'response_features.sqlite3')) as cache:
            records=prepare(model,data,rows,cache)
        weights={selected:w}
        old=score(records,'existing',weights,participants,movers,counts)
        new=score(records,selected,weights,participants,movers,counts)
        sufficient=bool(records) and old['inherited_primary_mean_brier'] is not None
        gate=(new['inherited_primary_mean_brier']<old['inherited_primary_mean_brier'] and
            new['overall']['nll']<=old['overall']['nll']+.02 and
            all(new['sets'][s]['brier']<=old['sets'][s]['brier']+.01 for s in PRIMARY)) if sufficient else None
        result[mode]={'frozen_selected':selected,'old':old,'new':new,'inherited_relative_gate':gate,
            'paired_game_bootstrap':bootstrap(records,selected,weights) if records else None,
            'sample_independent_of_previous_known_accounts':True,'selection_or_fit_on_new_sample':False}
        print(mode,'gate',gate,'NLL',old['overall'].get('nll'),new['overall'].get('nll'),flush=True)
    immutable_json(out/'metrics.json',result)
    immutable_json(out/'measurement_seal.json',{'metrics_sha256':sha(out/'metrics.json'),
        'adapter_sha256':sha(__file__),'frozen_model_manifest_sha256':sha(out/'frozen_model_fingerprint.json'),
        'dataset_seal_sha256':sha(Path(c['raw_dir'])/'dataset_seal.json'),
        'measured_at':datetime.now(timezone.utc).isoformat(),'new_fit_calls':0,'new_engine_calls':0})
    verify_freeze();verify_dataset(c)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['acquire','measure'])
    stage=p.parse_args().stage
    acquire() if stage=='acquire' else measure()
