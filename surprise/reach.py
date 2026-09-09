"""Small public-game ingestion and game-level reach counts, not Human Policy."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import urllib.parse
import urllib.request

import shogi
import yaml

from .position import Position
from .research import identity, write_json


def normalize_game(raw, provenance):
    players = raw.get('players', {})
    declared_ai = any('aiLevel' in p or p.get('user', {}).get('title') == 'BOT' or p.get('title') == 'BOT'
                      for p in players.values())
    identified = all(players.get(s, {}).get('user', {}).get('id') for s in ('sente', 'gote'))
    initial = raw.get('initialSfen') or raw.get('initialFen') or Position.startpos().sfen
    reasons = []
    if raw.get('variant') != 'standard': reasons.append('non_standard_variant')
    if raw.get('status') in (None, 'created', 'started', 'aborted', 'noStart'): reasons.append('not_finished_game')
    if declared_ai: reasons.append('declared_bot_or_ai')
    elif not identified: reasons.append('human_status_unknown')
    if initial != 'startpos' and identity(initial) != identity(Position.startpos().sfen): reasons.append('non_standard_start')
    moves = raw.get('moves', '').split()
    if not moves: reasons.append('no_moves')
    if not raw.get('id'): raise ValueError('missing game id')
    return {'source': 'lishogi', 'game_id': raw['id'], **provenance,
        'created_at_ms': raw.get('createdAt'), 'variant': raw.get('variant'), 'status': raw.get('status'),
        'rating': {s: players.get(s, {}).get('rating') for s in ('sente', 'gote')},
        'time_control': raw.get('clock') or raw.get('daysPerTurn'),
        'bot_ai_flag': True if declared_ai else False if identified else None,
        'human_classification': 'no_declared_bot_or_ai' if identified and not declared_ai else 'excluded',
        'player_ids': {s: players.get(s, {}).get('user', {}).get('id') for s in ('sente', 'gote')},
        'initial_sfen': Position.startpos().sfen if initial == 'startpos' else initial,
        'moves': moves, 'exclusion_reasons': reasons, 'source_url': 'https://lishogi.org/' + raw['id']}


class ReachDB:
    def __init__(self, path, max_ply=40):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.max_ply = max_ply
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS games(game_key TEXT PRIMARY KEY, accepted INTEGER NOT NULL, moves_hash TEXT NOT NULL, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS positions(position_id TEXT PRIMARY KEY, canonical_sfen TEXT UNIQUE NOT NULL, sfen TEXT NOT NULL, side_to_move TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS occurrences(game_key TEXT NOT NULL REFERENCES games(game_key), ply INTEGER NOT NULL,
          position_id TEXT NOT NULL REFERENCES positions(position_id), move TEXT, PRIMARY KEY(game_key,ply));
        CREATE INDEX IF NOT EXISTS by_position ON occurrences(position_id);
        ''')
        old = self.db.execute("SELECT value FROM meta WHERE key='max_ply'").fetchone()
        if old and int(old[0]) != max_ply: raise ValueError('reach horizon changed; use another database')
        self.db.execute("INSERT OR IGNORE INTO meta VALUES ('max_ply',?)", (str(max_ply),))
        self.db.commit()

    def ingest(self, game):
        key = game['source'] + ':' + game['game_id']
        digest = hashlib.sha256(json.dumps([game['initial_sfen'], game['moves']]).encode()).hexdigest()
        old = self.db.execute('SELECT moves_hash FROM games WHERE game_key=?', (key,)).fetchone()
        if old:
            if old[0] != digest: raise ValueError('conflicting game id/moves')
            return 'duplicate'
        game = dict(game, exclusion_reasons=list(game['exclusion_reasons']))
        occurrences, positions = [], {}
        if not game['exclusion_reasons']:
            board = shogi.Board(game['initial_sfen'])
            try:
                for ply in range(len(game['moves']) + 1):
                    sfen = board.sfen()
                    if ply <= self.max_ply:
                        pid = identity(sfen)
                        positions[pid] = (pid, ' '.join(sfen.split()[:3]), sfen, 'sente' if board.turn == 0 else 'gote')
                        occurrences.append((key, ply, pid, game['moves'][ply] if ply < len(game['moves']) else None))
                    if ply < len(game['moves']):
                        move = shogi.Move.from_usi(game['moves'][ply])
                        if not board.is_legal(move): raise ValueError('illegal move')
                        board.push(move)
            except (ValueError, KeyError, IndexError):
                game['exclusion_reasons'].append('invalid_move_sequence')
        accepted = not game['exclusion_reasons']
        with self.db:
            self.db.execute('INSERT INTO games VALUES (?,?,?,?)', (key, int(accepted), digest, json.dumps(game)))
            if accepted:
                self.db.executemany('INSERT OR IGNORE INTO positions VALUES (?,?,?,?)', positions.values())
                self.db.executemany('INSERT INTO occurrences VALUES (?,?,?,?)', occurrences)
        return 'accepted' if accepted else 'excluded'

    def export(self):
        total = self.db.execute('SELECT count(*) FROM games WHERE accepted=1').fetchone()[0]
        rows = self.db.execute('''SELECT p.position_id,p.sfen,p.side_to_move,count(DISTINCT o.game_key),
            min(o.ply),max(o.ply),count(*) FROM positions p JOIN occurrences o USING(position_id)
            GROUP BY p.position_id ORDER BY count(DISTINCT o.game_key) DESC,min(o.ply),p.position_id''').fetchall()
        result = []
        for pid, sfen, side, games, first, last, visits in rows:
            distribution = dict(self.db.execute('SELECT move,count(*) FROM occurrences WHERE position_id=? AND move IS NOT NULL GROUP BY move', (pid,)))
            result.append({'position_id': pid, 'sfen': sfen, 'side_to_move': side,
                'games_reaching_position': games, 'total_games': total,
                'reach_probability': games / total if total else None,
                'reach_scope': 'accepted convenience sample, within configured 0-max_ply window',
                'min_ply': first, 'max_ply': last, 'occurrence_count': visits,
                'move_distribution': distribution, 'move_frequency_semantics': 'observed decisions, including repeat visits'})
        return result

    def close(self): self.db.close()


def fetch_sample(cfg):
    c = cfg['ingestion']
    root = Path(c['raw_dir'])
    root.mkdir(parents=True, exist_ok=True)
    provenance = []
    # One small request at a time. HTTP errors stop; no automatic bulk retry.
    for user in c['users']:
        target = root / (user + '.json')
        if target.exists():
            provenance.append(target)
            continue
        params = urllib.parse.urlencode({'max': c['max_games_per_user'], 'moves': 'true',
            'ongoing': 'false', 'finished': 'true', 'evals': 'false', 'clocks': 'false'})
        url = 'https://lishogi.org/api/games/user/' + urllib.parse.quote(user, safe='') + '?' + params
        request = urllib.request.Request(url, headers={'Accept': 'application/x-ndjson', 'User-Agent': 'ShogiShock-reach-prototype'})
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read(10_000_001)
        if len(payload) > 10_000_000: raise ValueError('sample response exceeds cap')
        games = [json.loads(line) for line in payload.splitlines() if line.strip()]
        if len(games) > c['max_games_per_user']: raise ValueError('server exceeded sample cap')
        write_json(target, {'request_url': url, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
            'terms_url': c['terms_url'], 'api_url': c['api_url'], 'usage_scope': c['usage_scope'],
            'redistribution_approved': c['redistribution_approved'],
            'response_sha256': hashlib.sha256(payload).hexdigest(), 'games': games})
        provenance.append(target)
    return provenance


def run(config):
    cfg = yaml.safe_load(Path(config).read_text())
    sources = fetch_sample(cfg)
    db = ReachDB(cfg['ingestion']['database'], cfg['ingestion']['max_ply'])
    status = Counter()
    try:
        for path in sources:
            source = json.loads(path.read_text())
            for raw in source['games']:
                game = normalize_game(raw, {k: v for k, v in source.items() if k != 'games'})
                status[db.ingest(game)] += 1
        rows = db.export()
        exclusions = Counter(reason for payload, in db.db.execute('SELECT payload FROM games WHERE accepted=0')
                             for reason in json.loads(payload)['exclusion_reasons'])
        summary = {'this_ingestion': dict(status), 'accepted_games': rows[0]['total_games'] if rows else 0,
            'unique_positions': len(rows), 'exclusion_reasons': dict(exclusions), 'sampling': 'most recent up to 25 games of each of two named accounts; non-random',
            'can_estimate_population_reach': False, 'human_status': 'no declared BOT/AI; cheating cannot be ruled out',
            'max_ply': cfg['ingestion']['max_ply'], 'redistribution_approved': False}
        out = Path(cfg['output'])
        out.mkdir(parents=True, exist_ok=True)
        write_json(out / 'reach_positions.json', rows)
        write_json(out / 'reach_summary.json', summary)
        print(json.dumps(summary, ensure_ascii=False))
    finally:
        db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config/reach_pilot.yaml')
    run(parser.parse_args().config)
