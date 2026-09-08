"""Pass hypothesis pilot. No evaluation cutoff and no human-policy claims."""
from __future__ import annotations

import hashlib
import json
import signal
import sqlite3
import statistics
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from pathlib import Path

import shogi
import yaml

from .engine import Engine, CACHE_SCHEMA_VERSION
from .position import Position

SCHEMA = 1
PIECE_VALUES = {1: 100, 2: 300, 3: 320, 4: 450, 5: 550, 6: 800,
                7: 1000, 8: 0, 9: 550, 10: 550, 11: 550, 12: 550, 13: 1100, 14: 1300}


def identity(sfen):
    # Exclude move number only. No reflection, rotation, or colour swap.
    return hashlib.sha256(" ".join(sfen.split()[:3]).encode()).hexdigest()[:20]


def load_positions(path, min_ply=0, max_ply=40):
    if not 0 <= min_ply <= max_ply:
        raise ValueError("require 0 <= min_ply <= max_ply")
    document = yaml.safe_load(Path(path).read_text())
    positions = {}
    line_ids = set()
    for line in document["lines"]:
        if line["id"] in line_ids:
            raise ValueError("duplicate source line id")
        line_ids.add(line["id"])
        p = Position.from_sfen(line["sfen"]) if "sfen" in line else Position.startpos()
        history = []
        moves = line["moves"].split() if isinstance(line["moves"], str) else line["moves"]
        start_ply = int(p.sfen.split()[3]) - 1
        for offset in range(len(moves) + 1):
            ply = start_ply + offset
            if min_ply <= ply <= max_ply:
                key = identity(p.sfen)
                record = positions.setdefault(key, {
                    "position_id": key, "sfen": p.sfen, "ply": ply,
                    "side_to_move": "sente" if p.turn == shogi.BLACK else "gote",
                    "move_history": history.copy(), "source": document["source"],
                    "frequency_semantics": document.get("frequency_semantics", "source_occurrences"),
                    "occurrence_count": 0, "alternative_move_orders": [],
                    "occurrences": [], "move_distribution": {}, "families": [],
                })
                record["occurrence_count"] += 1
                if history not in record["alternative_move_orders"]:
                    record["alternative_move_orders"].append(history.copy())
                record["occurrences"].append({"line_id": line["id"], "game_id": line.get("game_id"),
                                              "ply": ply, "move_history": history.copy()})
                if line.get("family") not in record["families"]:
                    record["families"].append(line.get("family"))
                if offset < len(moves):
                    move = moves[offset]
                    record["move_distribution"][move] = record["move_distribution"].get(move, 0) + 1
            if offset < len(moves):
                try:
                    p = p.apply_move(moves[offset])
                except ValueError as error:
                    raise ValueError(f"{line['id']} ply {ply + 1}: {error}") from error
                history.append(moves[offset])
    return list(positions.values())


def encode(result):
    return Engine._encode_result(result)


def cp(result):
    return result["score"]["score_cp"] if (result["score"]["score_type"] == "cp"
        and result["score"].get("bound", "exact") == "exact") else None


def pass_metrics(normal, passed, side):
    n, p = cp(normal), cp(passed) if passed else None
    delta = p - n if n is not None and p is not None else None
    return {"pass_eval_delta": delta,
            "pass_sensitivity": delta * (1 if side == "sente" else -1) if delta is not None else None}


def relative_metrics(rows):
    values = [r["pass_sensitivity"] for r in rows if r["pass_sensitivity"] is not None]
    median = statistics.median(values) if values else None
    sd = statistics.pstdev(values) if values else None
    mean = statistics.mean(values) if values else None
    for row in rows:
        value = row["pass_sensitivity"]
        row.update(pass_relative_median=value - median if value is not None else None,
                   pass_percentile=(sum(v < value for v in values) + .5 * values.count(value)) / len(values)
                   if value is not None else None,
                   pass_zscore=(value - mean) / sd if value is not None and sd else None,
                   pass_reference_count=len(values), pass_reference_median=median)


def material_balance(p):
    value = 0
    for square in shogi.SQUARES:
        piece = p.board.piece_at(square)
        if piece:
            value += PIECE_VALUES[piece.piece_type] * (1 if piece.color == 0 else -1)
    for color in [0, 1]:
        value += sum(PIECE_VALUES[t] * n for t, n in p.board.pieces_in_hand[color].items()) * (1 if color == 0 else -1)
    return value


def pv_material_loss(p, result, side, horizon=8):
    start = material_balance(p)
    sign = 1 if side == "sente" else -1
    changes = [0]
    for move in result["pv"][:horizon]:
        p = p.apply_move(move)
        changes.append((material_balance(p) - start) * sign)
    # Descriptive PV endpoint, not an exchange-search proof.
    return max(0, -changes[-1]), len(changes) - 1


def evaluate_candidate(engine, position, move, best, cfg):
    p = Position.from_sfen(position["sfen"])
    child = p.apply_move(move)
    side = position["side_to_move"]
    sign = 1 if side == "sente" else -1
    normal = encode(engine.evaluate(child, cfg["search"]["shallow_nodes"]))
    virtual = child.virtual_pass(side)
    passed = encode(engine.evaluate(virtual.position, cfg["search"]["pass_nodes"])) if virtual.applicable else None
    bc, nc = cp(best), cp(normal)
    loss_signed = sign * (bc - nc) if bc is not None and nc is not None else None
    material_loss, horizon = pv_material_loss(child, normal, side)
    mate = normal["score"]["mate_distance"]
    # mate 0 has no sign after normalization; side to move loses at terminal.
    mate_allowed = normal["score"]["score_type"] == "mate" and (
        mate is not None and mate != 0 and mate * sign < 0)
    tags = []
    if mate_allowed:
        tags.append("mate_allowed")
    if material_loss >= cfg["research"]["large_material_loss"]:
        tags.append("large_material_loss")
    if loss_signed is not None and loss_signed >= cfg["research"]["obvious_blunder_loss_cp"]:
        tags.append("obvious_blunder")
    return {"candidate_id": position["position_id"] + "_" + move.replace("*", "-"),
            "position_id": position["position_id"], "attacker_side": side, "move": move,
            "resulting_sfen": child.sfen, "resulting_position_id": identity(child.sfen),
            "best_move": best["best_move"], "best": best, "normal": normal, "passed": passed,
            "best_eval": bc, "candidate_eval": nc, "V_normal": nc, "V_pass": cp(passed) if passed else None,
            "candidate_eval_loss": max(0, loss_signed) if loss_signed is not None else None,
            "candidate_eval_loss_signed": loss_signed,
            "pass_applicable": virtual.applicable, "pass_reason": virtual.reason,
            "is_check": child.is_check(), "is_capture": bool(p.board.piece_at(shogi.Move.from_usi(move).to_square)),
            "tags": tags, "pv_material_loss": material_loss, "pv_material_horizon": horizon,
            "surprise_type": "unclassified", "position_frequency": position["occurrence_count"],
            "candidate_move_frequency": position["move_distribution"].get(move, 0),
            **pass_metrics(normal, passed, side)}


class Store:
    def __init__(self, path, manifest):
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS meta (id INTEGER PRIMARY KEY, value TEXT)")
        self.db.execute("CREATE TABLE IF NOT EXISTS candidates (id TEXT PRIMARY KEY, value TEXT NOT NULL)")
        old = self.db.execute("SELECT value FROM meta WHERE id=1").fetchone()
        if old and json.loads(old[0]) != manifest:
            self.db.close()
            raise ValueError("Run fingerprint changed; use a different research.output_dir")
        self.db.execute("INSERT OR IGNORE INTO meta VALUES (1, ?)", (json.dumps(manifest, sort_keys=True),))
        self.db.commit()

    def get(self, key):
        row = self.db.execute("SELECT value FROM candidates WHERE id=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, row):
        self.db.execute("INSERT OR REPLACE INTO candidates VALUES (?,?)", (row["candidate_id"], json.dumps(row)))
        self.db.commit()

    def close(self):
        self.db.close()


def scan_partition(config, manifest, positions, out, stopped):
    """One independent engine and SQLite connection per worker thread."""
    cfg = manifest["config"]
    with Engine.from_config(config) as engine:
        if not engine.cache:
            raise ValueError("Research scans require engine cache")
        store = Store(out / "scan.sqlite3", manifest)
        try:
            for position in positions:
                if stopped.is_set():
                    break
                p = Position.from_sfen(position["sfen"])
                best = None
                for move in p.legal_moves():
                    if stopped.is_set():
                        break
                    key = position["position_id"] + "_" + move.replace("*", "-")
                    if store.get(key) is not None:
                        continue
                    if best is None:
                        best = encode(engine.evaluate(p, cfg["search"]["shallow_nodes"]))
                    row = evaluate_candidate(engine, position, move, best, cfg)
                    store.put(row)
                print(f"Position complete {position['position_id']} ply={position['ply']}", flush=True)
        except BaseException:
            stopped.set()
            raise
        finally:
            store.close()


def write_json(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def prepare(config):
    cfg = yaml.safe_load(Path(config).read_text())
    out = Path(cfg["research"]["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    positions = load_positions(cfg["research"]["seed_path"], cfg["research"]["min_ply"], cfg["research"]["max_ply"])
    return cfg, out, positions


def run_scan(config, max_positions=None, report_only=False):
    cfg, out, positions = prepare(config)
    if max_positions is not None:
        if max_positions <= 0:
            raise ValueError("max-positions must be positive")
        positions = positions[:max_positions]
    if report_only:
        from .report import render_reports
        render_reports(out)
        return
    stopped = threading.Event()

    def stop(*_):
        stopped.set()

    previous = {s: signal.signal(s, stop) for s in (signal.SIGTERM, signal.SIGINT)}
    all_rows = []
    started = time.monotonic()
    try:
        with Engine.from_config(config) as engine:
            if not engine.cache:
                raise ValueError("Research scans require engine cache")
            manifest = {"schema": SCHEMA, "cache_schema": CACHE_SCHEMA_VERSION, "config": cfg,
                        "seed_sha256": hashlib.sha256(Path(cfg["research"]["seed_path"]).read_bytes()).hexdigest(),
                        "engine_sha256": engine.binary_sha256, "eval_sha256": engine.eval_sha256}
            store = Store(out / "scan.sqlite3", manifest)
            store.close()
            workers = cfg["research"].get("workers", 1)
            if not isinstance(workers, int) or workers <= 0:
                raise ValueError("research.workers must be a positive integer")
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [pool.submit(scan_partition, config, manifest, positions[i::workers], out, stopped)
                           for i in range(workers)]
                for future in futures:
                    future.result()
            store = Store(out / "scan.sqlite3", manifest)
            try:
                known = {p["position_id"]: p for p in positions}
                expected = sum(len(Position.from_sfen(p["sfen"]).legal_moves()) for p in positions)
                for number, position in enumerate(positions, 1):
                    p = Position.from_sfen(position["sfen"])
                    legal = p.legal_moves()
                    rows = []
                    for move in legal:
                        key = position["position_id"] + "_" + move.replace("*", "-")
                        row = store.get(key)
                        if row:
                            row["resulting_position_frequency"] = known.get(row["resulting_position_id"], {}).get("occurrence_count", 0)
                            rows.append(row)
                    complete = len(rows) == len(legal)
                    relative_metrics(rows)
                    for row in rows:
                        row["parent_complete"] = complete
                        if not complete:
                            for field in ("pass_relative_median", "pass_percentile", "pass_zscore"):
                                row[field] = None
                    all_rows.extend(rows)
                    write_json(out / "checkpoint.json", {"last_position": position["position_id"],
                               "positions_visited": number, "candidates_exported": len(all_rows),
                               "expected_candidates": expected, "stopped": stopped.is_set()})
                    if number % 10 == 0:
                        print(f"{number}/{len(positions)} positions; {len(all_rows)}/{expected} candidates; {time.monotonic()-started:.1f}s", flush=True)
                write_json(out / "positions.json", positions)
                write_json(out / "candidates.json", all_rows)
                write_json(out / "manifest.json", manifest | {"complete": len(all_rows) == expected,
                           "expected_candidates": expected, "actual_candidates": len(all_rows),
                           "elapsed_seconds_this_invocation": time.monotonic() - started})
            finally:
                store.close()
    finally:
        for s, handler in previous.items():
            signal.signal(s, handler)
    from .report import render_reports
    render_reports(out)
    print(f"Reports: {out}/report_sente.html and report_gote.html", flush=True)


def select_review(rows, per_side):
    selected = {}
    for side in ("sente", "gote"):
        group = [r for r in rows if r["attacker_side"] == side and r["parent_complete"]]
        for metric in ("pass_sensitivity", "pass_relative_median"):
            eligible = sorted((r for r in group if r[metric] is not None), key=lambda r: (-r[metric], r["candidate_id"]))
            for r in eligible[:per_side]:
                selected[r["candidate_id"]] = r
    return list(selected.values())


def select_diverse(rows, per_side=15):
    """A separate review queue, retaining at most one move per parent per axis."""
    queues = {}
    for side in ("sente", "gote"):
        queues[side] = {}
        for metric in ("pass_sensitivity", "pass_relative_median"):
            ranked = sorted((r for r in rows if r["attacker_side"] == side and
                             r["parent_complete"] and r[metric] is not None),
                            key=lambda r: (-r[metric], r["candidate_id"]))
            parents, selected = set(), []
            for row in ranked:
                if row["position_id"] in parents:
                    continue
                parents.add(row["position_id"])
                selected.append(row["candidate_id"])
                if len(selected) == per_side:
                    break
            queues[side][metric] = selected
    return queues


def run_deep(config, per_side, budgets):
    cfg, out, _ = prepare(config)
    if per_side <= 0 or not budgets or min(budgets) <= 0:
        raise ValueError("positive review count and budgets required")
    rows = json.loads((out / "candidates.json").read_text())
    positions = {p["position_id"]: p for p in json.loads((out / "positions.json").read_text())}
    selected = select_review(rows, per_side)
    deep_path = out / "deep.json"
    deep = json.loads(deep_path.read_text()) if deep_path.exists() else {}
    with Engine.from_config(config) as engine:
        manifest = json.loads((out / "manifest.json").read_text())
        if (manifest.get("cache_schema") != CACHE_SCHEMA_VERSION or manifest["config"] != cfg or manifest["engine_sha256"] != engine.binary_sha256
                or manifest["eval_sha256"] != engine.eval_sha256):
            raise ValueError("Deep engine/config differs from scan fingerprint")
        for i, row in enumerate(selected, 1):
            side = row["attacker_side"]
            p = Position.from_sfen(positions[row["position_id"]]["sfen"])
            child = p.apply_move(row["move"])
            records = deep.setdefault(row["candidate_id"], {})
            for nodes in budgets:
                if str(nodes) in records:
                    continue
                best = encode(engine.evaluate(p, nodes))
                normal = encode(engine.evaluate(child, nodes))
                virtual = child.virtual_pass(side)
                passed = encode(engine.evaluate(virtual.position, nodes)) if virtual.applicable else None
                records[str(nodes)] = {"nodes_budget": nodes, "best": best, "normal": normal, "passed": passed,
                                      **pass_metrics(normal, passed, side)}
                write_json(deep_path, deep)
            print(f"Deep {i}/{len(selected)} {row['candidate_id']}", flush=True)
    from .report import render_reports
    render_reports(out)
