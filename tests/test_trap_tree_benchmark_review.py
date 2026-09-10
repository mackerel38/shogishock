import importlib.util
import json
from pathlib import Path

import shogi

ROOT = Path(__file__).resolve().parents[1]
TREE = ROOT / "reports/trap_tree_benchmark/tree.json"
HANDOFF = ROOT / "reports/trap_tree_benchmark/ASTRA_HANDOFF.json"
OUT = ROOT / "exports/trap_tree_benchmark_review"


def renderer():
    spec = importlib.util.spec_from_file_location("trap_tree_renderer", ROOT / "scripts/render_trap_tree_benchmark_review.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_four_review_kifs_match_frozen_root_branches():
    tree = json.loads(TREE.read_text(encoding="utf-8"))
    assert len(tree["branches"]) == 4
    assert {b["opponent_move"] for b in tree["branches"]} == {"B*7g", "3d2d", "3d3f", "3d3e"}
    assert len(list((OUT / "branches").glob("*.kif"))) == 4
    assert json.loads(HANDOFF.read_text(encoding="utf-8"))["next_step_decision"] == "INCONCLUSIVE"


def test_full_history_and_saved_branch_pv_moves_are_legal():
    tree = json.loads(TREE.read_text(encoding="utf-8"))
    root = shogi.Board()
    for move in tree["root_history"]:
        root.push_usi(move)
    for branch in tree["branches"]:
        branch_board = shogi.Board(root.sfen())
        branch_board.push_usi(branch["opponent_move"])
        for candidate in branch["candidates"]:
            candidate_board = shogi.Board(branch_board.sfen())
            candidate_board.push_usi(candidate["move"])
            for reply, continuation in candidate.get("continuations", {}).items():
                reply_board = shogi.Board(candidate_board.sfen())
                assert shogi.Move.from_usi(reply) in reply_board.legal_moves
                reply_board.push_usi(reply)
                for move in [continuation["move"]] + list((continuation.get("result") or {}).get("pv") or []):
                    assert shogi.Move.from_usi(move) in reply_board.legal_moves
                    reply_board.push_usi(move)


def test_side_and_move_conversion_matches_root_and_reply_turns():
    module = renderer()
    tree = json.loads(TREE.read_text(encoding="utf-8"))
    root = shogi.Board()
    for move in tree["root_history"]:
        root.push_usi(move)
    expected = {
        "B*7g": ("▲７七角打", "8f8h+", "△８八飛成(86)"),
        "3d2d": ("▲２四飛(34)", "4e6g+", "△６七角成(45)"),
        "3d3f": ("▲３六飛(34)", "8f8h+", "△８八飛成(86)"),
        "3d3e": ("▲３五飛(34)", "4e6g+", "△６七角成(45)"),
    }
    for branch in tree["branches"]:
        move = branch["opponent_move"]
        branch_board = shogi.Board(root.sfen())
        branch_board.push_usi(move)
        candidate = branch["our_response"]
        candidate_board = shogi.Board(branch_board.sfen())
        candidate_board.push_usi(candidate)
        assert module.human_move(root, move) == expected[move][0]
        assert module.human_move(branch_board, candidate) == expected[move][2]
        assert module.status_text(branch["branch_status"])


def test_human_kifs_avoid_internal_status_and_false_shallow_claims():
    forbidden = ("trap_branch", "opponent_refutes", "needs_review", "normal_branch", "P_good",
                 "人間選択確率", "100kで全合法手を比較した結果")
    for path in (OUT / "branches").glob("*.kif"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, (path, token)
        assert "INCONCLUSIVE" in text
        assert "先手視点" in text
        assert "Human Policyは今回使用しておらず" in text


def test_readme_records_coverage_gap_and_old_reject_links():
    text = (OUT / "README.md").read_text(encoding="utf-8")
    assert "△２三歩" in text and "後付けは行わず" in text
    assert "旧・除外例：△３二銀" in text
    assert "選択した応手同士" in text
    assert "830cp" in text
