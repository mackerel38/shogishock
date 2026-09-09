"""Manual response-set calibration review manifests and separated exports.

This module is deliberately a review-data adapter.  It does not infer a
classification from engine scores, policy probabilities, or rankings.
"""
from __future__ import annotations

import hashlib
import html
import json
import shutil
from pathlib import Path
from typing import Any


# Review decisions are intentionally explicit and human maintained.  An empty
# actual_candidate list is valid while calibration is still diagnostic.
MANUAL_REVIEW_CASES: tuple[dict[str, Any], ...] = (
    {
        "candidate_id": "5c46af1026197c8aeb70_3a3b",
        "classification": "diagnostic_counterexample",
        "borderline": False,
        "classification_reason": "既存の△3二銀。応手集合の校正を検査する診断用カウンター例として指定する。",
        "review_status": "reference",
    },
    {
        "candidate_id": "8e41531c4f23213c9b17_7g7f",
        "classification": "control",
        "borderline": False,
        "classification_reason": "通常の▲7六歩を基準局面のcontrolとして指定する。",
        "review_status": "reference",
    },
    {
        "candidate_id": "fa2a3aee31df970cb704_2b3c",
        "classification": "control",
        "borderline": False,
        "classification_reason": "通常の△3三角を基準局面のcontrolとして指定する。",
        "review_status": "reference",
    },
)
CLASSIFICATIONS = ("actual_candidate", "diagnostic_counterexample", "control")


def history_aware_response_cache_key(*, sfen: str, move_history: list[str] | tuple[str, ...],
                                     candidate_move: str, reply_move: str,
                                     feature_schema: str = "response-review-v1") -> str:
    """Return a cache key for history-dependent response diagnostics.

    SFEN is retained for board identity, but move history is part of the key:
    repetition and recapture diagnostics cannot safely use an SFEN-only key.
    """
    payload = {"schema": feature_schema, "sfen": sfen,
               "move_history": list(move_history), "candidate_move": candidate_move,
               "reply_move": reply_move}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def _load_candidates(input_dir: Path) -> dict[str, dict[str, Any]]:
    rows = json.loads((input_dir / "candidates.json").read_text(encoding="utf-8"))
    return {row["candidate_id"]: row for row in rows}


def _source_path(input_dir: Path, row: dict[str, Any], suffix: str) -> Path:
    return input_dir.parent.parent / "exports" / "human_e2e" / (
        f"{row['attacker_side']}_{row['candidate_id']}{suffix}")


def _html_page(classification: str, cases: list[dict[str, Any]]) -> str:
    cards = []
    for case in cases:
        links = " ".join(f'<a href="{html.escape(case[key])}">{label}</a>'
                         for key, label in (("export_kif", "KIF"), ("export_json", "JSON"),
                                             ("source_kif", "旧KIF")) if case.get(key))
        cards.append(f"<article><h2>{html.escape(case['candidate_id'])}</h2>"
                     f"<p>{html.escape(case['classification_reason'])}</p>"
                     f"<p>side: {html.escape(str(case.get('attacker_side', '')))}; "
                     f"borderline: {str(case['borderline']).lower()}</p><p>{links}</p></article>")
    body = "".join(cards) or "<p>この区分のレビュー対象は0件です。</p>"
    return ("<!doctype html><meta charset='utf-8'><title>Response-set review: "
            f"{html.escape(classification)}</title><h1>{html.escape(classification)}</h1>"
            f"<p>件数: {len(cases)}</p>{body}")


def build_review(input_dir: str | Path = "reports/human_e2e",
                 output_dir: str | Path = "reports/response_set_review",
                 export_dir: str | Path = "exports/response_set_review") -> dict[str, Any]:
    """Build a new, classification-separated review package without mutating old outputs."""
    input_path, output_path, export_path = map(Path, (input_dir, output_dir, export_dir))
    candidates = _load_candidates(input_path)
    output_path.mkdir(parents=True, exist_ok=True)
    export_path.mkdir(parents=True, exist_ok=True)
    by_class = {name: [] for name in CLASSIFICATIONS}
    for classification in CLASSIFICATIONS:
        (export_path / classification).mkdir(parents=True, exist_ok=True)
    for declared in MANUAL_REVIEW_CASES:
        cid = declared["candidate_id"]
        if declared["classification"] not in CLASSIFICATIONS:
            raise ValueError(f"unsupported manual classification: {declared['classification']}")
        if cid not in candidates:
            raise ValueError(f"manual review candidate is missing: {cid}")
        row = candidates[cid]
        case = {**declared, "attacker_side": row.get("attacker_side"),
                "sfen": row.get("sfen"), "candidate_move": row.get("candidate_move", row.get("move")),
                "source_candidate_json": "reports/human_e2e/candidates.json"}
        source_kif = _source_path(input_path, row, ".kif")
        source_json = _source_path(input_path, row, ".json")
        destination = export_path / declared["classification"]
        if source_kif.is_file():
            kif_target = destination / source_kif.name
            shutil.copy2(source_kif, kif_target)
            case["source_kif"] = str(source_kif)
            case["export_kif"] = str(kif_target)
        if source_json.is_file():
            json_target = destination / source_json.name
            shutil.copy2(source_json, json_target)
            case["export_json"] = str(json_target)
        by_class[declared["classification"]].append(case)

    all_cases = [case for cases in by_class.values() for case in cases]
    manifest = {"schema": "response-set-review-v1", "classification_policy": "manual_specified",
                "model_score_classification": False, "actual_candidate_count": len(by_class["actual_candidate"]),
                "classifications": by_class, "cases": all_cases}
    (output_path / "review_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    for classification in CLASSIFICATIONS:
        cases = by_class[classification]
        (output_path / classification).mkdir(exist_ok=True)
        (output_path / classification / "manifest.json").write_text(
            json.dumps({"schema": manifest["schema"], "classification": classification,
                        "classification_policy": "manual_specified", "cases": cases},
                       ensure_ascii=False, indent=2) + "\n")
        (output_path / f"report_{classification}.html").write_text(
            _html_page(classification, cases), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    build_review()
