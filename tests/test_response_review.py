import json

from surprise.response_review import build_review, history_aware_response_cache_key


def test_history_dependent_response_key_is_not_sfen_only():
    common = {"sfen": "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1",
              "candidate_move": "7g7f", "reply_move": "3c3d"}
    first = history_aware_response_cache_key(move_history=["7g7f"], **common)
    second = history_aware_response_cache_key(move_history=["2g2f", "8c8d"], **common)
    assert first != second
    assert first == history_aware_response_cache_key(move_history=["7g7f"], **common)


def test_review_manifest_is_manual_and_zero_actual_safe(tmp_path):
    source = tmp_path / "reports" / "human_e2e"
    source.mkdir(parents=True)
    (source / "candidates.json").write_text(json.dumps([
        {"candidate_id": "case", "attacker_side": "sente", "sfen": "sfen", "candidate_move": "7g7f"}
    ]))
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
