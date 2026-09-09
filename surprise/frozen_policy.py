"""Freeze pre-existing policy sufficient statistics; no new data or coefficient fitting."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

from .human_policy import Policy

PUBLIC = Path('reports/independent_policy_validation')
PRIVATE = Path('data/human_raw/independent_policy_validation')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encode_model(model):
    return {'alpha':model.alpha,'pop':dict(model.pop),'exact':dict(model.exact),
            'prefix':dict(model.prefix),'chosen':dict(model.chosen),'available':dict(model.available)}


def decode_model(state):
    model = object.__new__(Policy)
    model.positions = {}
    model.alpha = state['alpha']
    model.pop = defaultdict(Counter,{int(k):Counter(v) for k,v in state['pop'].items()})
    model.exact = defaultdict(Counter,{k:Counter(v) for k,v in state['exact'].items()})
    model.prefix = defaultdict(Counter,{k:Counter(v) for k,v in state['prefix'].items()})
    model.chosen = Counter(state['chosen']);model.available = Counter(state['available'])
    return model


def immutable_json(path, value):
    content = json.dumps(value,sort_keys=True,ensure_ascii=False,indent=2)+'\n'
    if path.exists():
        if path.read_text()!=content:raise ValueError(f'frozen content differs: {path}')
    else:
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(content)


def verify_freeze():
    manifest=json.loads((PUBLIC/'frozen_model_fingerprint.json').read_text())
    for path, expected in manifest['sha256'].items():
        if sha(path)!=expected:raise ValueError(f'frozen source/input changed: {path}')
    return manifest


def load_frozen(mode='time'):
    verify_freeze()
    state=json.loads((PRIVATE/'frozen_models.json').read_text())['models'][mode]
    return decode_model(state['base']),state['selected'],state['weights']


def freeze():
    if (PUBLIC/'frozen_model_fingerprint.json').exists():
        print('Already frozen; verified without rebuilding:',verify_freeze()['frozen_at'])
        return
    # Before freezing, insist that all prior model inputs match their recorded provenance.
    for manifest_path in ('reports/response_calibration/provenance.json','reports/response_calibration/review_provenance.json'):
        for path,expected in json.loads(Path(manifest_path).read_text())['sha256'].items():
            if sha(path)!=expected:raise ValueError(f'prior checkpoint mismatch: {path}')
    source=Path('data/human_raw/human_pilot')
    data=json.loads((source/'policy_examples.json').read_text())
    splits=json.loads((source/'splits_v2.json').read_text())
    metrics=json.loads(Path('reports/response_calibration/metrics.json').read_text())
    models={};exposed_players=set();exposed_games=set()
    for key,game in data['games'].items():
        exposed_games.add(key.split(':',1)[-1]);exposed_players.update(p.lower() for p in game['players'] if p)
    for mode in ('time','player','game'):
        train=set(splits[mode]['train'])
        base=Policy(data,[r for r in data['rows'] if r['game'] in train],5)
        state=encode_model(base)
        restored=decode_model(state)
        for pid in sorted(data['positions'])[:20]:
            p=data['positions'][pid]
            assert base.predict(p,pid,'','hierarchical',2,1)==restored.predict(p,pid,'','hierarchical',2,1)
        selected=metrics[mode]['selected']
        models[mode]={'base':state,'selected':selected,'weights':metrics[mode]['weights'][selected],
                      'train_games':len(train),'shrinkage_k':5,'old_threshold':2,'temperature':1}
    def walk(value):
        if isinstance(value,dict):
            if 'moves' in value and ('players' in value or 'player_ids' in value):
                gid=value.get('id') or value.get('game_id')
                if gid:exposed_games.add(gid)
                exposed_players.update(p.lower() for p in value.get('player_ids',{}).values() if p)
                for p in value.get('players',{}).values():
                    if isinstance(p,dict) and p.get('user',{}).get('id'):
                        exposed_players.add(p['user']['id'].lower())
            for item in value.values():walk(item)
        elif isinstance(value,list):
            for item in value:walk(item)
    audited=[]
    for directory in ('data/human_raw/human_pilot/requests','data/human_raw/reach_pilot'):
        for path in sorted(Path(directory).rglob('*.json')):
            walk(json.loads(path.read_text()));audited.append(str(path))
    for path in ('data/human_pilot.sqlite3','data/reach_pilot.sqlite3'):
        with sqlite3.connect(f'file:{path}?mode=ro',uri=True) as db:
            for payload, in db.execute('SELECT payload FROM games'):walk(json.loads(payload))
    immutable_json(PRIVATE/'frozen_models.json',{'schema':'frozen-policy-v1','models':models})
    immutable_json(PRIVATE/'prior_exposure.json',{'players':sorted(exposed_players),'game_ids':sorted(exposed_games),
                                               'raw_files_audited':audited})
    paths=['surprise/human_policy.py','surprise/response_calibration.py','surprise/obvious.py',
        'surprise/research.py','surprise/position.py','surprise/response_cache.py','surprise/frozen_policy.py',
        'reports/response_calibration/PLAN.md','reports/response_calibration/metrics.json',
        'reports/response_calibration/decision.json','reports/independent_policy_validation/SAMPLING_PLAN.md',
        'config/independent_policy_validation.yaml',str(PRIVATE/'frozen_models.json'),str(PRIVATE/'prior_exposure.json'),
        str(source/'policy_examples.json'),str(source/'splits_v2.json')]
    manifest={'schema':'independent-freeze-v1','frozen_at':datetime.now(timezone.utc).isoformat(),
        'source_checkpoint':'742432c1b8e26664c7cae9fb560ab55a6f608e40',
        'sha256':{p:sha(p) for p in paths},'prior_exposed_players':len(exposed_players),
        'prior_exposed_games':len(exposed_games),'primary_snapshot':'time',
        'models':{k:{a:b for a,b in v.items() if a!='base'} for k,v in models.items()},
        'new_games_acquired':0,'validation_completed':False,'refit_allowed':False,
        'candidate_promotion_allowed':False,'next_small_scan_decision':'INCONCLUSIVE'}
    immutable_json(PUBLIC/'frozen_model_fingerprint.json',manifest)
    print(json.dumps({k:v for k,v in manifest.items() if k not in ('sha256','models')}))


if __name__=='__main__':freeze()
