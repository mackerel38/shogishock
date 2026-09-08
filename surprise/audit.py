"""Legal-reply falsification test. Counts are not a Human Policy or P_good."""
import json
from concurrent.futures import ThreadPoolExecutor

import shogi

from .engine import Engine, CACHE_SCHEMA_VERSION
from .position import Position
from .research import prepare, encode, cp, write_json


def select_examples(rows):
    selected = {}
    for side in ("sente", "gote"):
        group = [r for r in rows if r["attacker_side"] == side and r["parent_complete"]
                 and r["pass_sensitivity"] is not None]
        sign = 1 if side == "sente" else -1
        strata = [("raw_top", group, "pass_sensitivity"),
                  ("relative_top", group, "pass_relative_median"),
                  ("quiet_moderately_adverse", [r for r in group if not r["is_capture"] and
                    -800 <= sign * r["candidate_eval"] <= -300], "pass_relative_median"),
                  ("quiet_near_equal", [r for r in group if not r["is_capture"] and
                    abs(r["candidate_eval"]) <= 300], "pass_relative_median")]
        for name, eligible, metric in strata:
            if not eligible:
                continue
            r = sorted(eligible, key=lambda r: (-r[metric], r["candidate_id"]))[0]
            selected.setdefault(r["candidate_id"], {"candidate": r, "strata": []})["strata"].append(name)
    return list(selected.values())


def audit_example(config, out, example, nodes):
    r = example["candidate"]
    path = out / ("audit_" + r["candidate_id"] + ".json")
    data = json.loads(path.read_text()) if path.exists() else {
        "candidate_id": r["candidate_id"], "attacker_side": r["attacker_side"],
        "strata": example["strata"], "nodes_budget": nodes, "responses": [],
        "probability_semantics": "none; counts are not P_good", "complete": False}
    if data["nodes_budget"] != nodes:
        raise ValueError("Audit budget changed; use another run directory")
    p = Position.from_sfen(r["resulting_sfen"])
    done = {x["move"] for x in data["responses"]}
    legal = p.legal_moves()
    with Engine.from_config(config) as engine:
        for move in legal:
            if move in done:
                continue
            child = p.apply_move(move)
            result = encode(engine.evaluate(child, nodes))
            data["responses"].append({"move": move, "result": result, "engine_eval": cp(result),
                "is_capture": bool(p.board.piece_at(shogi.Move.from_usi(move).to_square)),
                "is_check": child.is_check()})
            write_json(path, data)
    values = [x["engine_eval"] for x in data["responses"] if x["engine_eval"] is not None]
    optimum = (max(values) if p.turn == 0 else min(values)) if values else None
    data.update(complete=len(data["responses"]) == len(legal), legal_reply_count=len(legal),
                numeric_reply_count=len(values), V_optimal_observed_cp=optimum,
                optimum_scope="CP replies only; inspect mate/unknown separately", good_response_counts={})
    for tolerance in (50, 100, 200, 300):
        good = [x["move"] for x in data["responses"] if x["engine_eval"] is not None and
                ((x["engine_eval"] >= optimum - tolerance) if p.turn == 0 else
                 (x["engine_eval"] <= optimum + tolerance))]
        data["good_response_counts"][str(tolerance)] = {"count": len(good), "moves": good}
    write_json(path, data)
    print(f"Audited {r['candidate_id']}: {len(legal)} legal replies", flush=True)
    return data


def run_audit(config, nodes):
    cfg, out, _ = prepare(config)
    if nodes <= 0:
        raise ValueError("nodes must be positive")
    manifest = json.loads((out / "manifest.json").read_text())
    with Engine.from_config(config) as engine:
        if (manifest.get("cache_schema") != CACHE_SCHEMA_VERSION or manifest["config"] != cfg or
            manifest["engine_sha256"] != engine.binary_sha256 or manifest["eval_sha256"] != engine.eval_sha256):
            raise ValueError("Audit engine/config differs from scan fingerprint")
    rows = json.loads((out / "candidates.json").read_text())
    examples = select_examples(rows)
    with ThreadPoolExecutor(max_workers=min(cfg["research"].get("workers", 1), len(examples)) or 1) as pool:
        futures = [pool.submit(audit_example, config, out, e, nodes) for e in examples]
        results = [f.result() for f in futures]
    write_json(out / "audit.json", results)
    from .report import render_reports
    render_reports(out)
