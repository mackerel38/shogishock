import json
import shogi

from surprise.response_review import build_review, history_aware_response_cache_key
from surprise.response_cache import ResponseDiagnosticCache


def test_history_dependent_response_key_is_not_sfen_only():
    common = {"sfen": "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1",
              "candidate_move": "7g7f", "reply_move": "3c3d"}
    first = history_aware_response_cache_key(move_history=["7g7f"], **common)
    second = history_aware_response_cache_key(move_history=["2g2f", "8c8d"], **common)
    assert first != second
    assert first == history_aware_response_cache_key(move_history=["7g7f"], **common)


def test_response_diagnostic_cache_uses_history(tmp_path):
    common = {"sfen": shogi.Board().sfen(), "candidate_move": "7g7f", "reply_move": "3c3d"}
    with ResponseDiagnosticCache(tmp_path / "response.sqlite3") as cache:
        cache.put(move_history=["7g7f"], value={"signals": ["first"]}, **common)
        assert cache.get(move_history=["7g7f"], **common)["signals"] == ["first"]
        assert cache.get(move_history=["2g2f", "8c8d"], **common) is None


def test_review_manifest_is_manual_and_zero_actual_safe(tmp_path):
    source = tmp_path / "reports" / "human_e2e"
    source.mkdir(parents=True)
    (source / "candidates.json").write_text(json.dumps([
        {"candidate_id": "case", "attacker_side": "sente", "sfen": "sfen", "candidate_move": "7g7f"}
    ]))
    (source / "positions.json").write_text("[]")
    # The production manifest uses explicit cases; exercise zero-safe rendering
    # through a minimal direct input with no declared cases by verifying output
    # shape from a real build is governed by the fixed manual declarations.
    # This test also protects the schema contract without score-based filtering.
    # Use the repository fixture only when available.
    from surprise import response_review
    old = response_review.MANUAL_REVIEW_CASES
    response_review.MANUAL_REVIEW_CASES = ()
    try:
        result = build_review(source, tmp_path / "out", tmp_path / "exports")
    finally:
        response_review.MANUAL_REVIEW_CASES = old
    assert result["actual_candidate_count"] == 0
    assert json.loads((tmp_path / "out" / "review_manifest.json").read_text())["cases"] == []
    assert "0件" in (tmp_path / "out" / "report_actual_candidate.html").read_text()


def test_production_review_resolves_parent_from_positions():
    result = build_review()
    case = result["classifications"]["diagnostic_counterexample"][0]
    assert case["parent_sfen"]
    assert case["move_history"]
    board = shogi.Board()
    for move in case["move_history"]:
        board.push_usi(move)
    assert " ".join(board.sfen().split()[:3]) == " ".join(case["parent_sfen"].split()[:3])
    assert case["candidate_move"] == "3a3b"
    kif = open(case["export_kif"], encoding="utf-8").read()
    assert "parent_engine_best_pv:" in kif
    assert "engine_optimal_pv:" not in kif
    assert "[engine PV after candidate]" in kif
