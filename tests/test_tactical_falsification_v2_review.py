import json
from pathlib import Path

import shogi


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "reports/tactical_falsification_v2/results.json"
OUT = ROOT / "exports/tactical_falsification_v2_review"


def test_v2_has_four_human_review_kifs_and_preserves_gate_outcomes():
    cases = json.loads(RESULTS.read_text(encoding="utf-8"))["cases"]
    files = list(OUT.glob("**/*.kif"))
    assert len(cases) == len(files) == 4
    assert all(case["final_gate_result"]["decision"] in {"not_falsified", "reject"} for case in cases)
    assert "INCONCLUSIVE" in (OUT / "README.md").read_text(encoding="utf-8")


def test_v2_history_candidate_and_saved_branches_are_legal():
    cases = json.loads(RESULTS.read_text(encoding="utf-8"))["cases"]
    for case in cases:
        board = shogi.Board()
        for move in case["history"].split():
            board.push_usi(move)
        assert " ".join(board.sfen().split()[:4]) == " ".join(case["position"].split()[:4])
        assert shogi.Move.from_usi(case["candidate_move"]) in board.legal_moves
        after = shogi.Board(board.sfen())
        after.push_usi(case["candidate_move"])
        for move in case["obvious_looking_replies"]:
            assert shogi.Move.from_usi(move) in after.legal_moves


def test_v2_human_move_sides_and_destinations():
    import importlib.util
    spec = importlib.util.spec_from_file_location("v2_renderer", ROOT / "scripts/render_tactical_falsification_v2_review.py")
    renderer = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(renderer)
    cases = json.loads(RESULTS.read_text(encoding="utf-8"))["cases"]
    expected = {
        "bishop_block_rook_sacrifice": ("▲７七角打", "△２四歩(23)"),
        "horse_entry_bad_gold_recapture": ("△６七角成(45)", "▲６七金(78)"),
        "user_rook_counter_sacrifice": ("▲２二飛成(26)", "△２二銀(31)"),
        "user_pawn_drop_followup": ("▲８二歩打", "△８六桂打"),
    }
    for case in cases:
        board = shogi.Board()
        for move in case["history"].split():
            board.push_usi(move)
        candidate_text = renderer.human_move(board, case["candidate_move"])
        after = shogi.Board(board.sfen())
        after.push_usi(case["candidate_move"])
        reply_move = case["obvious_looking_replies"][0]
        if case["id"] == "user_pawn_drop_followup":
            reply_move = "N*8f"
        reply_text = renderer.human_move(after, reply_move)
        assert (candidate_text, reply_text) == expected[case["id"]]


def test_v2_kifs_do_not_expose_internal_or_ambiguous_display_labels():
    forbidden = (
        "expected_class", "prospective_control", "diagnostic_hypotheses", "not_falsified",
        "P_good", "Human Policy probability", "True", "False", "None",
        "100k response ranking", "固定例確認", "[engine PV after candidate",
    )
    for path in OUT.glob("**/*.kif"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, (path, token)
        assert text.count("本番での自動除外への移行判断：INCONCLUSIVE") == 1


def test_v2_index_has_required_scope_warnings_without_false_claims():
    text = (OUT / "README.md").read_text(encoding="utf-8")
    assert "固定例確認" not in text
    assert "1133cp" not in text or "100kで全合法応手を順位付け" in text
    assert "△８六桂だけを前提にしない" in text
    assert "安全性を裏付ける対照例から撤回済み" in text
    assert "新しい奇襲候補が発見された" not in text
