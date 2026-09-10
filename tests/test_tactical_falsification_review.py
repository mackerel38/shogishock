import json
from pathlib import Path

import shogi


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "reports/tactical_falsification/results.json"
OUT = ROOT / "exports/tactical_falsification_review"


def test_all_five_frozen_cases_have_human_review_kif():
    cases = json.loads(RESULTS.read_text(encoding="utf-8"))["cases"]
    files = list((OUT / "reject").glob("*.kif")) + list((OUT / "control").glob("*.kif"))
    assert len(cases) == len(files) == 5
    assert sum(case["surprise_move_decision"] == "reject" for case in cases) == 3
    assert sum(case["surprise_move_decision"] == "not_falsified" for case in cases) == 2
    mandatory = next(case for case in cases if case["move_being_examined"] == "3a3b")
    assert mandatory["surprise_move_decision"] == "reject"
    assert "△3二銀" in (OUT / "reject/reject_01_3a3b.kif").read_text(encoding="utf-8")


def test_fixed_case_history_and_candidate_are_legal():
    cases = json.loads(RESULTS.read_text(encoding="utf-8"))["cases"]
    for case in cases:
        board = shogi.Board()
        for move in case["move_history"]:
            board.push_usi(move)
        assert " ".join(board.sfen().split()[:4]) == " ".join(case["position"].split()[:4])
        assert shogi.Move.from_usi(case["move_being_examined"]) in board.legal_moves


def test_human_review_kif_has_no_internal_display_values_or_raw_labels():
    forbidden = (
        "True", "False", "None", "parent_engine_best_pv", "candidate_eval", "parent_eval",
        "positive=sente", "response_sets", "exact_support=", "abstain=",
        "diagnostic_counterexample", "actual_candidate", "control", "not_falsified",
        "[engine PV after candidate", "{'",
    )
    for path in list((OUT / "reject").glob("*.kif")) + list((OUT / "control").glob("*.kif")):
        text = path.read_text(encoding="utf-8")
        assert "奇襲手としての判定：除外" in text or "この検査では除外しない" in text
        for token in forbidden:
            assert token not in text, (path, token)
        assert text.count("本番での自動除外への移行判断：INCONCLUSIVE") == 1
        assert "奇襲手としては除外" not in text
        assert "奇襲手として有望かどうかの判定：保留" not in text


def test_review_index_preserves_inconclusive_conclusion():
    text = (OUT / "README.md").read_text(encoding="utf-8")
    assert "INCONCLUSIVE" in text
    assert text.count(".kif)") == 5
    assert "1931cp" in text and "2328cp" in text
