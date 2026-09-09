"""Heuristic reply extraction followed by evaluation, never capture-based deletion."""
import shogi

from .position import Position
from .research import PIECE_VALUES, cp


def reply_features(parent, candidate, reply):
    child = parent.apply_move(candidate)
    cm, rm = shogi.Move.from_usi(candidate), shogi.Move.from_usi(reply)
    victim, mover = child.board.piece_at(rm.to_square), child.board.piece_at(rm.from_square) if rm.from_square is not None else None
    capture = victim is not None
    takes_candidate = capture and cm.to_square == rm.to_square
    recapture = takes_candidate and parent.board.piece_at(cm.to_square) is not None
    pawn_contact = bool(capture and mover and victim.piece_type == shogi.PAWN and mover.piece_type == shogi.PAWN)
    recovery = False
    if capture and mover:
        after = child.apply_move(reply)
        can_recapture = any(m.to_square == rm.to_square for m in after.board.legal_moves)
        recovery = not can_recapture or PIECE_VALUES[victim.piece_type] > PIECE_VALUES[mover.piece_type]
    tags = [name for name, value in (("captures_candidate", takes_candidate), ("recapture", recapture),
            ("pawn_contact_capture", pawn_contact), ("material_recovery_proxy", recovery)) if value]
    return {"move": reply, "is_capture": capture, "reply_captures_candidate": bool(takes_candidate),
            "signals": tags, "obvious": bool(tags)}


def obvious_replies(parent, candidate):
    child = parent.apply_move(candidate)
    return [f for m in child.legal_moves() if (f := reply_features(parent, candidate, m))["obvious"]]


def defender_gap(value, reference, attacker_side):
    if value is None or reference is None:
        return None
    # Positive means the defender gave the attacker additional advantage.
    return (value - reference) * (1 if attacker_side == "sente" else -1)


def reply_summary(responses, root, side, legal_count, tolerances):
    values = [cp(r["result"]) for r in responses if cp(r["result"]) is not None]
    # Root search and explicit reply searches differ in horizon. Keep both.
    full = len(responses) == legal_count
    reference_values = values if full else values + ([cp(root)] if cp(root) is not None else [])
    reference = (min(reference_values) if side == "sente" else max(reference_values)) if reference_values else None
    # Root/child CP comparisons are not meaningful if a compared result is mate/unknown/bounded.
    comparable = cp(root) is not None and len(values) == len(responses)
    result = {"reference_eval": reference, "root_eval": cp(root), "numeric_comparable": comparable,
              "reference_scope": "best explicitly evaluated reply" if full else "best of root estimate and explicitly evaluated replies; provisional",
              "root_reference_delta": cp(root) - reference if cp(root) is not None and reference is not None else None,
              "legal_reply_count": legal_count, "evaluated_reply_count": len(responses),
              "all_legal_replies_evaluated": len(responses) == legal_count}
    for r in responses:
        value = cp(r["result"])
        r["engine_eval"] = value
        r["gap_from_optimal_estimate"] = defender_gap(value, reference, side) if comparable else None
        r["gap_from_root_estimate"] = defender_gap(value, cp(root), side)
        for tolerance in tolerances:
            r[f"is_good_{tolerance}"] = r["gap_from_optimal_estimate"] <= tolerance if comparable else None
    for tolerance in tolerances:
        good = sum(r[f"is_good_{tolerance}"] is True for r in responses)
        result[f"good_reply_count_{tolerance}"] = good if comparable else None
        result[f"good_reply_fraction_{tolerance}"] = good / legal_count if comparable and len(responses) == legal_count and legal_count else None
        result[f"good_reply_fraction_bounds_{tolerance}"] = [good / legal_count, (good + legal_count - len(responses)) / legal_count] if comparable and legal_count else None
    return result


def escalation_reasons(parent_advantage, reach, neutralizes, good_fraction, cfg):
    reasons = []
    if parent_advantage is None:
        reasons.append("parent_eval_unknown")
    elif parent_advantage >= cfg["parent_favorable_cp"]:
        reasons.append("parent_already_favorable")
    if reach is None:
        reasons.append("reach_unknown")
    elif reach < cfg["min_reach_probability"]:
        reasons.append("low_reach")
    if neutralizes is True:
        reasons.append("obvious_reply_neutralizes")
    if good_fraction is not None and good_fraction >= cfg["broad_good_reply_fraction"]:
        reasons.append("broad_good_reply_set")
    return reasons
