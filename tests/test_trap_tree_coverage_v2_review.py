import importlib.util
import json
import re
from pathlib import Path

import shogi


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/trap_tree_coverage_v2"
OUT = ROOT / "exports/trap_tree_coverage_v2_review"


def renderer():
    spec = importlib.util.spec_from_file_location("coverage_v2_renderer", ROOT / "scripts/render_trap_tree_coverage_v2_review.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_groups():
    return json.loads((REPORT / "deep_checks.json").read_text(encoding="utf-8"))["groups"]


def group(groups, ident):
    return next(item for item in groups if item["id"] == ident)


def result(g, move):
    level = next(item for item in g["levels"] if item["nodes"] == 80_000_000)
    return level["results"][move]


def kif_moves(path):
    moves = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*\d+\s+(.+)$", line)
        if match:
            moves.append(match.group(1))
    return moves


def replay_history(history):
    board = shogi.Board()
    for move in history:
        assert shogi.Move.from_usi(move) in board.legal_moves
        board.push_usi(move)
    return board


def assert_source_prefix_is_rendered(path, board, record):
    r = renderer()
    local = shogi.Board(board.sfen())
    expected = []
    for move in (record.get("pv") or [])[: r.PV_PREFIX]:
        expected.append(r._move_text(local, move))
        local.push_usi(move)
    assert expected
    actual = kif_moves(path)
    for start in range(len(actual) - len(expected) + 1):
        if actual[start : start + len(expected)] == expected:
            return
    raise AssertionError(f"saved PV prefix is absent as a contiguous KIF variation: {expected}")


def test_four_outputs_exist_and_no_internal_research_dump_leaks():
    expected = [
        "01_R2d_P2c.kif",
        "02_R3f_B6g.kif",
        "03_R3e_B6g_replies.kif",
        "04_R2d_B6g_replies.kif",
    ]
    for filename in expected:
        path = OUT / "branches" / filename
        assert path.is_file()
        text = path.read_text(encoding="utf-8")
        assert "INCONCLUSIVE" in text
        assert "先手視点" in text
        assert "Human Policyは今回使用しておらず" in text
        for forbidden in ("P_good", "actual_candidate", "candidate_coverage", "reply_coverage", "True", "False", "None"):
            assert forbidden not in text, (filename, forbidden)


def test_histories_and_source_pv_prefixes_match_rendered_variations():
    groups = load_groups()
    r = renderer()
    specs = [
        ("candidate_3d2d", "01_R2d_P2c.kif", ["P*2c"]),
        ("candidate_3d3f", "02_R3f_B6g.kif", ["4e6g+"]),
        ("reply_3d3e", "03_R3e_B6g_replies.kif", ["7h6g", "7h7i", "B*7g"]),
        ("reply_3d2d", "04_R2d_B6g_replies.kif", ["7h6g", "7h7i", "7h8g", "2d2a+"]),
    ]
    for ident, filename, moves in specs:
        g = group(groups, ident)
        if ident.startswith("reply_"):
            base_history = g["history"][:-1]
            base = replay_history(base_history)
            candidate = g["history"][-1]
            response_board = r.replay(base, [candidate])
            path = OUT / "branches" / filename
            for move in moves:
                reply_board = r.replay(response_board, [move])
                assert_source_prefix_is_rendered(path, reply_board, result(g, move))
        else:
            base = replay_history(g["history"])
            path = OUT / "branches" / filename
            for move in moves:
                move_board = r.replay(base, [move])
                assert_source_prefix_is_rendered(path, move_board, result(g, move))


def test_display_side_and_drop_notation_are_derived_from_the_move_board():
    r = renderer()
    board = replay_history(group(load_groups(), "candidate_3d2d")["history"])
    assert r.human_move(board, "P*2c").startswith("△２三歩打")
    board = replay_history(group(load_groups(), "candidate_3d3f")["history"])
    assert r.human_move(board, "4e6g+").startswith("△６七角成")
    board = replay_history(group(load_groups(), "reply_3d3e")["history"])
    assert r.human_move(board, "7h7i").startswith("▲７九金")
    board = replay_history(group(load_groups(), "reply_3d2d")["history"])
    assert r.human_move(board, "2d2a+").startswith("▲２一飛成")


def test_mate_wording_and_coverage_notes_are_precise():
    for filename in ("03_R3e_B6g_replies.kif", "04_R2d_B6g_replies.kif"):
        text = (OUT / "branches" / filename).read_text(encoding="utf-8")
        assert "19手詰み" in text
        assert "△８八飛成を含む" in text
        assert "独立証明による最短手数保証ではない" in text
        assert "独立証明済み" not in text
    readme = (OUT / "README.md").read_text(encoding="utf-8")
    assert "actual candidate" not in readme
    assert "実際の奇襲候補への昇格は0件" in readme
    assert "△2三歩は旧benchmarkでもMultiPVには現れていた" in readme
