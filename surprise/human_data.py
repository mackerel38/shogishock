"""Bounded public-API sampling and game/player-level reach; no engine calls."""
import argparse
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

import yaml

from .reach import ReachDB, normalize_game
from .research import write_json

TERMS = 'https://lishogi.org/terms-of-service'
API = 'https://lishogi.org/api'


def digest(x):
    return hashlib.sha256(x.encode()).hexdigest()


def millis(s):
    return int(datetime.fromisoformat(s).timestamp()*1000)


class PublicClient:
    def __init__(self, cfg):
        self.root = Path(cfg['raw_dir']) / 'requests'
        self.root.mkdir(parents=True, exist_ok=True)
        self.cfg = cfg['sampling']
        self.last = 0

    def get(self, path, ndjson=False, private_ok=False):
        url = 'https://lishogi.org' + path
        dest = self.root / (digest(url) + '.json')
        if dest.exists():
            return json.loads(dest.read_text())
        error_path = dest.with_suffix('.error.json')
        if error_path.exists():
            error = json.loads(error_path.read_text())
            if time.time() < error.get('resume_after', 0):
                raise RuntimeError('rate limit cooldown still active')
        time.sleep(max(0, self.cfg['request_interval_seconds']-(time.monotonic()-self.last)))
        request = urllib.request.Request(url, headers={'Accept': 'application/x-ndjson' if ndjson else 'application/json',
            'User-Agent': 'ShogiShock-small-human-research/1.0'})
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = response.read(self.cfg['max_response_bytes'] + 1)
            if len(payload) > self.cfg['max_response_bytes']:
                raise RuntimeError('response cap exceeded')
            data = [json.loads(x) for x in payload.splitlines() if x.strip()] if ndjson else json.loads(payload)
        except urllib.error.HTTPError as exc:
            if private_ok and exc.code in (401, 403, 404):
                record = {'request_url': url, 'status': exc.code, 'data': [], 'retrieved_at': datetime.now(timezone.utc).isoformat()}
                write_json(dest, record)
                return record
            retry = exc.headers.get('Retry-After', '60')
            try: delay = max(60, int(retry))
            except ValueError: delay = 120
            write_json(error_path, {'request_url': url, 'error': str(exc), 'resume_after': time.time()+delay})
            raise
        except (OSError, ValueError) as exc:
            write_json(error_path, {'request_url': url, 'error': str(exc), 'resume_after': time.time()+60})
            raise
        finally:
            self.last = time.monotonic()
        record = {'request_url': url, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
            'response_sha256': hashlib.sha256(payload).hexdigest(), 'terms_url': TERMS, 'api_url': API,
            'redistribution_approved': False, 'status': 200, 'data': data}
        write_json(dest, record)
        return record


def rating_band(x):
    return 'unknown' if x is None else '<1200' if x < 1200 else '1200-1599' if x < 1600 else '1600-1999' if x < 2000 else '2000+'


def frame(cfg, client):
    path = Path(cfg['raw_dir']) / 'sampling_frame.json'
    if path.exists(): return json.loads(path.read_text())
    teams = client.get('/api/team/all?page=1')['data']['currentPageResults']
    members, statuses = {}, {}
    for team in teams:
        if team['id'] in cfg['sampling']['exclude_teams']: continue
        result = client.get('/api/team/' + urllib.parse.quote(team['id'], safe='') + '/users', True, True)
        statuses[team['id']] = {'status': result['status'], 'members': len(result['data'])}
        for member in result['data']:
            key = member['id']
            if key not in members:
                members[key] = member | {'sampling_teams': []}
            members[key]['sampling_teams'].append(team['id'])
    eligible = [m for m in members.values() if m.get('title') != 'BOT' and not m.get('disabled')
                and m.get('seenAt', 0) >= millis(cfg['sampling']['since'])]
    strata = defaultdict(list)
    for m in eligible:
        perf = m.get('perfs', {}).get('realTime', {})
        strata[rating_band(perf.get('rating') if perf.get('games', 0) else None)].append(m['id'])
    pools = {k: deque(sorted(v, key=lambda x: digest(cfg['seed']+x))) for k,v in strata.items()}
    selected = []
    while len(selected) < cfg['sampling']['focal_players'] and any(pools.values()):
        for k in sorted(pools):
            if pools[k] and len(selected) < cfg['sampling']['focal_players']:
                selected.append(pools[k].popleft())
    result = {'teams': statuses, 'members': members, 'eligible_players': len(eligible),
        'eligible_rating_bands': {k:len(v) for k,v in strata.items()}, 'focal_players': selected}
    write_json(path, result)
    return result


def wilson(k, n):
    if not n: return [None, None]
    z = 1.95996398454
    den = 1+z*z/n
    center = (k/n+z*z/(2*n))/den
    half = z*math.sqrt(k/n*(1-k/n)/n+z*z/(4*n*n))/den
    return [max(0,center-half),min(1,center+half)]


def build_reports(cfg, games, db, frame_info, counts):
    out = Path(cfg['output'])
    accepted = {key:json.loads(payload) for key,payload in db.db.execute('SELECT game_key,payload FROM games WHERE accepted=1')}
    participants = {key:set(g['player_ids'].values()) for key,g in accepted.items()}
    player_counts = Counter(p for ps in participants.values() for p in ps)
    rows = db.export()
    position_games = defaultdict(set)
    edge_games = defaultdict(set)
    histories = {}
    for key,g in accepted.items():
        visits = db.db.execute('SELECT ply,position_id FROM occurrences WHERE game_key=? ORDER BY ply',(key,)).fetchall()
        for ply,pid in visits:
            position_games[pid].add(key)
            histories.setdefault(pid,g['moves'][:ply])
        for (_,parent),(ply,child) in zip(visits,visits[1:]):
            edge_games[(parent,child,g['moves'][ply-1])].add(key)
    lookup = {r['position_id']:r for r in rows}
    for r in rows:
        players = set().union(*(participants[g] for g in position_games[r['position_id']]))
        r.update(distinct_players_reaching=len(players), distinct_player_count=len(players),
            total_distinct_players=len(player_counts), player_reach_probability=len(players)/len(player_counts),
            sample_count=r['games_reaching_position'], wilson_interval=wilson(r['games_reaching_position'],len(accepted)),
            uncertainty_scope='descriptive iid-game Wilson only; player dependence and frame bias not covered',
            move_history=histories[r['position_id']])
    edges = [{'parent_position_id':p,'position_id':c,'move':m,'games_using_edge':len(gs),
        'games_reaching_parent':len(position_games[p]),'parent_reach_probability':lookup[p]['reach_probability'],
        'conditional_reach_probability':len(gs)/len(position_games[p])} for (p,c,m),gs in edge_games.items()]
    def distribution(values):
        v=sorted(values)
        return {'n':len(v),'min':v[0] if v else None,'median':v[len(v)//2] if v else None,
            'p90':v[min(len(v)-1,int(.9*len(v)))] if v else None,'max':v[-1] if v else None}
    ratings=[v for g in accepted.values() for v in g['rating'].values() if v is not None]
    summary = {'downloaded_records': counts['downloaded'], 'unique_downloaded_games':len(games),
        'accepted_games':len(accepted),'distinct_players':len(player_counts),
        'games_per_player':distribution(list(player_counts.values())),
        'games_per_player_histogram':dict(Counter(player_counts.values())),
        'rating':distribution(ratings),'rating_bands':dict(Counter(rating_band(v) for v in ratings)),
        'missing_ratings':2*len(accepted)-len(ratings),
        'time_control':dict(Counter(json.dumps(g['time_control'],sort_keys=True) for g in accepted.values())),
        'speed':dict(Counter(g.get('speed','unknown') for g in accepted.values())),
        'rated':dict(Counter(str(g.get('rated')) for g in accepted.values())),
        'date_month':dict(sorted(Counter(datetime.fromtimestamp(g['created_at_ms']/1000,timezone.utc).strftime('%Y-%m') for g in accepted.values()).items())),
        'exclusion_reasons':dict(Counter(reason for _,payload in db.db.execute('SELECT accepted,payload FROM games WHERE accepted=0') for reason in json.loads(payload)['exclusion_reasons'])),
        'exact_positions':len(rows),'position_support':distribution([r['sample_count'] for r in rows]),
        'reach_distribution':distribution([r['reach_probability'] for r in rows]),
        'positions_support_ge10':sum(r['sample_count']>=10 for r in rows),
        'frame_unique_members':len(frame_info['members']),'frame_eligible':frame_info['eligible_players'],
        'frame_rating_bands':frame_info['eligible_rating_bands'],'focal_players':len(frame_info['focal_players']),
        'can_estimate_general_human_population':False}
    write_json(out/'reach_positions.json',rows)
    write_json(out/'reach_edges.json',edges)
    write_json(out/'sampling_summary.json',summary)
    print(json.dumps({k:summary[k] for k in ('downloaded_records','accepted_games','distinct_players','games_per_player','exact_positions')},ensure_ascii=False),flush=True)


def run(config):
    cfg=yaml.safe_load(Path(config).read_text())
    out=Path(cfg['output']);out.mkdir(parents=True,exist_ok=True)
    manifest=out/'sampling_config.json'
    if manifest.exists() and json.loads(manifest.read_text())!=cfg: raise ValueError('config changed; use new output')
    write_json(manifest,cfg)
    client=PublicClient(cfg)
    f=frame(cfg,client)
    print(f"Frame: {len(f['members'])} members, {f['eligible_players']} eligible, {len(f['focal_players'])} focal",flush=True)
    games={};downloaded=0
    c=cfg['sampling']
    for i,user in enumerate(f['focal_players']):
        params=urllib.parse.urlencode({'since':millis(c['since']),'until':millis(c['until'])-1,
            'max':c['games_per_request'],'moves':'true','ongoing':'false','finished':'true','evals':'false','clocks':'false'})
        r=client.get('/api/games/user/'+urllib.parse.quote(user,safe='')+'?'+params,True)
        if len(r['data'])>c['games_per_request']: raise ValueError('game cap exceeded')
        for raw in r['data']:
            downloaded+=1
            game=normalize_game(raw,{k:v for k,v in r.items() if k!='data'})
            game.update(rated=raw.get('rated'),speed=raw.get('speed'),sampling_focal=user)
            if not millis(c['since'])<=raw.get('createdAt',0)<millis(c['until']):game['exclusion_reasons'].append('outside_window')
            games.setdefault(game['game_id'],game)
        if (i+1)%20==0: print(f"Downloaded focal {i+1}/{len(f['focal_players'])}, unique games {len(games)}",flush=True)
    db=ReachDB(cfg['database'],c['max_ply'])
    try:
        counts=Counter()
        # Recompute deterministic acceptance before idempotent DB insertion.
        for key in sorted(games,key=lambda k:digest(cfg['seed']+k)):
            game=games[key]
            players=set(game['player_ids'].values())
            if not game['exclusion_reasons'] and any(counts[p]>=c['max_games_per_player'] for p in players):
                game['exclusion_reasons'].append('participant_game_cap')
            status=db.ingest(game)
            payload=json.loads(db.db.execute('SELECT payload FROM games WHERE game_key=?',('lishogi:'+key,)).fetchone()[0])
            if not payload['exclusion_reasons']:counts.update(players)
        assert max(counts.values(),default=0)<=c['max_games_per_player']
        build_reports(cfg,games,db,f,{'downloaded':downloaded})
    finally:db.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',default='config/human_pilot.yaml')
    run(parser.parse_args().config)
