"""Validate exported research data against legal positions and stored formulae."""
import json
from pathlib import Path

import shogi

from surprise.position import Position
from surprise.research import identity, pass_metrics, relative_metrics


def verify(out):
    out = Path(out)
    rows = json.loads((out / "candidates.json").read_text())
    positions = {p["position_id"]: p for p in json.loads((out / "positions.json").read_text())}
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["complete"]
    assert len(rows) == manifest["expected_candidates"]
    assert len({r["candidate_id"] for r in rows}) == len(rows)
    pv_count = 0
    checked_pvs = set()

    def check_pv(p, r):
        nonlocal pv_count
        if r is None:
            return
        assert r["score"]["perspective"] == "sente"
        key = (p.sfen, tuple(r["pv"]))
        if key in checked_pvs:
            return
        board = shogi.Board(p.sfen)
        for move in r["pv"]:
            parsed = shogi.Move.from_usi(move)
            assert board.is_legal(parsed), (p.sfen, r["pv"], move)
            board.push(parsed)
        checked_pvs.add(key)
        pv_count += 1

    for key, position in positions.items():
        group = [r for r in rows if r["position_id"] == key]
        p = Position.from_sfen(position["sfen"])
        assert {r["move"] for r in group} == set(p.legal_moves())
        expected = [{"pass_sensitivity": r["pass_sensitivity"]} for r in group]
        relative_metrics(expected)
        for row, reference in zip(group, expected):
            child = p.apply_move(row["move"])
            assert child.sfen == row["resulting_sfen"]
            assert identity(child.sfen) == row["resulting_position_id"]
            assert row["attacker_side"] == position["side_to_move"]
            for k, v in pass_metrics(row["normal"], row["passed"], row["attacker_side"]).items():
                assert row[k] == v
            for k in ("pass_relative_median", "pass_percentile", "pass_zscore"):
                assert row[k] == reference[k]
            virtual = child.virtual_pass(row["attacker_side"])
            assert virtual.applicable == row["pass_applicable"]
            check_pv(p, row["best"])
            check_pv(child, row["normal"])
            if virtual.applicable:
                check_pv(virtual.position, row["passed"])
    deep_path = out / "deep.json"
    if deep_path.exists():
        by_id = {r["candidate_id"]: r for r in rows}
        for key, depths in json.loads(deep_path.read_text()).items():
            row = by_id[key]
            p = Position.from_sfen(positions[row["position_id"]]["sfen"])
            child = p.apply_move(row["move"])
            for d in depths.values():
                check_pv(p, d["best"])
                check_pv(child, d["normal"])
                check_pv(child.virtual_pass(row["attacker_side"]).position, d["passed"])
    audit_path = out / "audit.json"
    if audit_path.exists():
        by_id = {r["candidate_id"]: r for r in rows}
        for audit in json.loads(audit_path.read_text()):
            p = Position.from_sfen(by_id[audit["candidate_id"]]["resulting_sfen"])
            assert audit["complete"]
            assert {r["move"] for r in audit["responses"]} == set(p.legal_moves())
            for reply in audit["responses"]:
                check_pv(p.apply_move(reply["move"]), reply["result"])
    print(f"Verified {len(positions)} positions, {len(rows)} candidates, {pv_count} legal PVs; signs, relative metrics, coverage and identities OK")


if __name__ == "__main__":
    import sys
    verify(sys.argv[1] if len(sys.argv) > 1 else "reports/pass_pilot")
