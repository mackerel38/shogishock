"""Export research candidates as branching, ShogiHome-compatible KIF files."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import shogi

from .position import Position

_FILES = "９８７６５４３２１"
_RANKS = "一二三四五六七八九"


@dataclass
class VariationNode:
    move: str | None = None
    comment: list[str] = field(default_factory=list)
    children: list["VariationNode"] = field(default_factory=list)


@dataclass
class ExportedKif:
    candidate_id: str
    root_sfen: str
    history: list[str]
    candidate: VariationNode
    warnings: list[str] = field(default_factory=list)


def _score(value: Any) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, dict):
        s = value.get("score", value)
        if s.get("score_type") == "mate":
            return f"mate {s.get('mate_distance')}"
        if s.get("score_type") == "cp":
            return f"{s.get('score_cp')}cp" + (f" ({s.get('bound')})" if s.get("bound") and s.get("bound") != "exact" else "")
    return str(value)


def _candidate_comment(row: dict[str, Any], parent: dict[str, Any]) -> list[str]:
    fields = [
        ("candidate_id", row.get("candidate_id")),
        ("attacker_side", row.get("attacker_side")),
        ("parent_eval", _score(row.get("best"))),
        ("candidate_eval", _score(row.get("normal"))),
        ("candidate_eval_loss", row.get("candidate_eval_loss")),
        ("pass_sensitivity", row.get("pass_sensitivity")),
        ("pass_relative_median", row.get("pass_relative_median")),
        ("ply", parent.get("ply")),
        ("is_check", row.get("is_check")),
        ("is_capture", row.get("is_capture")),
        ("source", parent.get("source")),
        ("reach_probability", row.get("reach_probability")),
        ("P_good", row.get("P_good")),
        ("human_gap", row.get("human_gap")),
        ("covered_probability", row.get("covered_probability")),
        ("obvious_reply_neutralizes", row.get("obvious_reply_neutralizes")),
    ]
    out = ["[ShogiShock candidate]"]
    out += [f"{k}: {v}" for k, v in fields if v is not None]
    if row.get("best", {}).get("pv"):
        # This PV belongs to the parent position, before the candidate move.
        out.append("parent_engine_best_pv: " + " ".join(row["best"]["pv"]))
    if row.get("pass_applicable") is False:
        out.append("pass_applicable: false")
    return out


def _add_branch(root: VariationNode, moves: list[str], comments: list[str], warnings: list[str], board: shogi.Board) -> None:
    if not moves:
        return
    node = root
    local = shogi.Board(board.sfen())
    for index, move in enumerate(moves):
        try:
            parsed = shogi.Move.from_usi(move)
            if parsed not in local.legal_moves:
                warnings.append(f"illegal move skipped in branch {comments[0] if comments else ''}: {move}")
                return
            child = next((x for x in node.children if x.move == move), None)
            if child is None:
                child = VariationNode(move=move)
                node.children.append(child)
            if index == 0:
                for comment in comments:
                    if comment not in child.comment:
                        child.comment.append(comment)
            local.push(parsed)
            node = child
        except (ValueError, TypeError) as exc:
            warnings.append(f"invalid move skipped in branch: {move} ({exc})")
            return


def build_tree(out: str | Path, candidate_id: str) -> ExportedKif:
    out = Path(out)
    rows = json.loads((out / "candidates.json").read_text(encoding="utf-8"))
    positions = {p["position_id"]: p for p in json.loads((out / "positions.json").read_text(encoding="utf-8"))}
    row = next((r for r in rows if r["candidate_id"] == candidate_id), None)
    if row is None:
        raise KeyError(f"candidate not found: {candidate_id}")
    parent = positions[row["position_id"]]
    root_sfen = parent["sfen"]
    history = list(parent.get("move_history") or [])
    warnings: list[str] = []
    candidate = VariationNode(move=row["move"], comment=_candidate_comment(row, parent))
    candidate_position = Position.from_sfen(row["resulting_sfen"])

    normal = row.get("normal") or {}
    _add_branch(candidate, list(normal.get("pv") or []), ["[engine PV after candidate]"], warnings, candidate_position.board)

    response_sources: list[dict[str, Any]] = []
    audit_path = out / "audit.json"
    if audit_path.exists():
        response_sources.extend(json.loads(audit_path.read_text(encoding="utf-8")))
    human_path = out / "human_responses.json"
    if human_path.exists():
        response_sources.extend(json.loads(human_path.read_text(encoding="utf-8")))
    # RESEARCH_V2 keeps the reach diagnostics separate from the pass pilot.
    # They are safe to use as optional explanatory branches, without changing rankings.
    for kind in ("obvious", "confirm"):
        diagnostic_dir = out.parent / "reach_pilot" / kind
        if out.name == "pass_pilot" and diagnostic_dir.exists():
            for path in sorted(diagnostic_dir.glob(f"{candidate_id}.json")):
                response_sources.append(json.loads(path.read_text(encoding="utf-8")))
    for audit in response_sources:
        if audit.get("candidate_id") != candidate_id:
            continue
        for response in audit.get("responses", []):
            moves = [response["move"]] + list((response.get("result") or {}).get("pv") or [])
            label = "obvious reply" if response.get("obvious") else "audited legal reply"
            comment = [f"[{label}]", "reply_engine_eval: " + _score(response.get("result"))]
            comment += ["signals: " + ", ".join(response["signals"])] if response.get("signals") else []
            if response.get("human_probability") is not None:
                comment += ["[Human Policy reply]", f"human_probability: {response['human_probability']}"]
            if response.get("good_by_tolerance") is not None:
                comment += ["good_by_tolerance: " + str(response['good_by_tolerance'])]
            _add_branch(candidate, moves, comment, warnings, candidate_position.board)

    deep_path = out / "deep.json"
    if deep_path.exists():
        deep = json.loads(deep_path.read_text(encoding="utf-8"))
        for record in (deep.get(candidate_id) or {}).values() if isinstance(deep, dict) else []:
            moves = list((record.get("normal") or {}).get("pv") or [])
            _add_branch(candidate, moves, ["[deep engine PV]"], warnings, candidate_position.board)

    return ExportedKif(candidate_id, root_sfen, history, candidate, warnings)


def _move_text(board: shogi.Board, move: str) -> str:
    parsed = shogi.Move.from_usi(move)
    file_index = parsed.to_square % 9
    rank_index = parsed.to_square // 9
    destination = _FILES[file_index] + _RANKS[rank_index]
    if parsed.drop_piece_type is not None:
        piece = shogi.Piece(parsed.drop_piece_type, board.turn)
        return f"{destination}{piece.japanese_symbol()}打"
    piece = board.piece_at(parsed.from_square)
    if piece is None:
        raise ValueError(f"no piece on source square for {move}")
    source_file = 9 - (parsed.from_square % 9)
    source_rank = parsed.from_square // 9 + 1
    suffix = "成" if parsed.promotion else ""
    return f"{destination}{piece.japanese_symbol()}{suffix}({source_file}{source_rank})"


def _write_comments(lines: list[str], comments: list[str]) -> None:
    lines.extend(f"* {comment}" for comment in comments)


def _emit_line(lines: list[str], board: shogi.Board, move: str, number: int, comments: list[str]) -> None:
    lines.append(f"{number:4d} {_move_text(board, move)}")
    board.push_usi(move)
    _write_comments(lines, comments)


def _emit_main(lines: list[str], board: shogi.Board, node: VariationNode, number: int) -> int:
    if node.move is None:
        return number
    _emit_line(lines, board, node.move, number, node.comment)
    number += 1
    branch_number = number
    variation_base = shogi.Board(board.sfen())
    if node.children:
        # First child is the main continuation. Remaining children are KIF variations.
        number = _emit_main(lines, board, node.children[0], number)
        for variation in node.children[1:]:
            lines.append(f"変化：{branch_number}手")
            branch_board = shogi.Board(variation_base.sfen())
            _emit_branch(lines, branch_board, variation, branch_number)
    return number


def _emit_branch(lines: list[str], board: shogi.Board, node: VariationNode, number: int) -> None:
    if node.move is None:
        return
    _emit_line(lines, board, node.move, number, node.comment)
    variation_base = shogi.Board(board.sfen())
    if node.children:
        _emit_branch(lines, board, node.children[0], number + 1)
        # Nested variation headers use the next move number in the branch.
        for variation in node.children[1:]:
            lines.append(f"変化：{number + 1}手")
            _emit_branch(lines, shogi.Board(variation_base.sfen()), variation, number + 1)


def to_kif(exported: ExportedKif, title: str | None = None) -> str:
    lines = ["# ShogiShock branching KIF", "手合割：平手", f"先手：ShogiShock / {exported.candidate_id}", "後手：Research variation"]
    if title:
        lines.append(f"棋戦：{title}")
    lines.append("手数----指手---------")
    board = shogi.Board()
    use_history = bool(exported.history) or " ".join(exported.root_sfen.split()[:3]) == " ".join(board.sfen().split()[:3])
    if use_history:
        try:
            for move in exported.history:
                if shogi.Move.from_usi(move) not in board.legal_moves:
                    raise ValueError(move)
                _emit_line(lines, board, move, board.move_number, [])
            if " ".join(board.sfen().split()[:3]) != " ".join(exported.root_sfen.split()[:3]):
                raise ValueError("history does not reach root SFEN")
        except (ValueError, TypeError):
            lines.append("* warning: move_history could not be replayed; root SFEN is recorded below")
            use_history = False
    if not use_history:
        lines[1] = "手合割：その他"
        lines.append(f"開始局面：{exported.root_sfen}")
        lines.append(f"* root_sfen: {exported.root_sfen}")
        board = shogi.Board(exported.root_sfen)
    _emit_main(lines, board, exported.candidate, board.move_number)
    if exported.warnings:
        lines.append("* export warnings:")
        lines.extend(f"* - {warning}" for warning in exported.warnings)
    lines.append("まで")
    return "\n".join(lines) + "\n"


def export_candidate(out: str | Path, candidate_id: str, destination: str | Path) -> Path:
    exported = build_tree(out, candidate_id)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(to_kif(exported), encoding="utf-8")
    sidecar = destination.with_suffix(".json")
    sidecar.write_text(json.dumps({"candidate_id": candidate_id, "warnings": exported.warnings}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Export ShogiShock candidates to branching KIF")
    parser.add_argument("--input", default="reports/pass_pilot")
    parser.add_argument("--candidate-id")
    parser.add_argument("--output", default="exports/shogihome")
    parser.add_argument("--limit", type=int, default=10, help="export top rows per side when candidate-id is omitted")
    args = parser.parse_args()
    out = Path(args.input)
    rows = json.loads((out / "candidates.json").read_text(encoding="utf-8"))
    if args.candidate_id:
        ids = [args.candidate_id]
    else:
        ids = []
        for side in ("sente", "gote"):
            group = [r for r in rows if r.get("attacker_side") == side and r.get("pass_sensitivity") is not None]
            ids.extend(r["candidate_id"] for r in sorted(group, key=lambda r: (-r["pass_sensitivity"], r["candidate_id"]))[:args.limit])
    for cid in ids:
        path = Path(args.output) / f"{cid}.kif"
        export_candidate(out, cid, path)
        print(path)


if __name__ == "__main__":
    main()
