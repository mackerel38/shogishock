"""Produce review evidence; qualitative conclusions belong in analysis.md."""
import json
import statistics
from collections import Counter
from pathlib import Path

import shogi

from surprise.position import Position
from surprise.research import select_review, write_json


def summarize(out):
    out = Path(out)
    rows = json.loads((out / "candidates.json").read_text())
    positions = {p["position_id"]: p for p in json.loads((out / "positions.json").read_text())}
    deep = json.loads((out / "deep.json").read_text()) if (out / "deep.json").exists() else {}
    review = select_review(rows, 30)
    evidence = []
    for r in review:
        p = Position.from_sfen(r["resulting_sfen"])
        reply = r["normal"]["pv"][0] if r["normal"]["pv"] else None
        capture = bool(reply and p.board.piece_at(shogi.Move.from_usi(reply).to_square))
        takes_candidate = bool(capture and shogi.Move.from_usi(reply).to_square == shogi.Move.from_usi(r["move"]).to_square)
        evidence.append({"candidate_id": r["candidate_id"], "side": r["attacker_side"],
            "ply": positions[r["position_id"]]["ply"], "families": positions[r["position_id"]]["families"],
            "move": r["move"], "eval": r["candidate_eval"], "loss": r["candidate_eval_loss"],
            "pass": r["V_pass"], "sensitivity": r["pass_sensitivity"], "relative": r["pass_relative_median"],
            "candidate_capture": r["is_capture"], "normal_first_reply": reply,
            "normal_first_reply_capture": capture, "reply_captures_candidate": takes_candidate,
            "normal_pv": r["normal"]["pv"], "pass_pv": r["passed"]["pv"],
            "deep": {n: {"normal": d["normal"]["score"], "pass": d["passed"]["score"] if d["passed"] else None,
                          "sensitivity": d["pass_sensitivity"]} for n, d in deep.get(r["candidate_id"], {}).items()}})
    write_json(out / "review_evidence.json", evidence)
    for side in ("sente", "gote"):
        group = [r for r in rows if r["attacker_side"] == side]
        valid = [r for r in group if r["pass_sensitivity"] is not None]
        print(side, "candidates", len(group), "cp_pairs", len(valid), "checks", sum(r["is_check"] for r in group),
              "captures", sum(r["is_capture"] for r in group), "review_union", sum(r["side"] == side for r in evidence))
        print("raw_vs_loss_correlation", statistics.correlation([r["pass_sensitivity"] for r in valid], [r["candidate_eval_loss"] for r in valid]))
        for metric in ("pass_sensitivity", "pass_relative_median"):
            top = sorted(valid, key=lambda r: -r[metric])[:30]
            ids = {r["candidate_id"] for r in top}
            e = [r for r in evidence if r["candidate_id"] in ids]
            print(metric, "parents", len({r["position_id"] for r in top}),
                  "capture", sum(r["is_capture"] for r in top),
                  "reply_capture", sum(r["normal_first_reply_capture"] for r in e),
                  "takes_candidate", sum(r["reply_captures_candidate"] for r in e),
                  "families", Counter(f for r in e for f in r["families"]))
        print("review")
        for r in evidence:
            if r["side"] == side:
                print(r["candidate_id"], "ply",r["ply"], "E",r["eval"], "L",r["loss"], "S",r["sensitivity"], "R",r["relative"],
                      "takes_candidate",r["reply_captures_candidate"], "N",' '.join(r["normal_pv"][:5]),"P",' '.join(r["pass_pv"][:5]))


if __name__ == "__main__":
    import sys
    summarize(sys.argv[1] if len(sys.argv) > 1 else "reports/pass_pilot")
