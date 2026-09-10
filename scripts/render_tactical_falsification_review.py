"""Render Astra's five fixed tactical fixtures as human-review KIF files.

This is a display-only renderer.  It reads the frozen results and never calls
an engine, changes a decision, or rewrites the research JSON.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import shogi

from surprise.kif_export import ExportedKif, VariationNode, _move_text, to_kif


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "reports/tactical_falsification/results.json"
OUT = ROOT / "exports/tactical_falsification_review"


CASE_LABELS = {
    "5c46af1026197c8aeb70_3a3b": ("除外例1", "△3二銀", "reject_01_3a3b.kif"),
    "0a33fbe73571830519e4_2b6f": ("除外例2", "△6二角", "reject_02_2b6f.kif"),
    "5ecc3699847f6446b58a_8h4d": ("除外例3", "▲4四角", "reject_03_8h4d.kif"),
    "a77ad58c704df8bb27bf_7g3c+": ("対照例1", "▲3三角成", "control_01_7g3c_plus.kif"),
    "b1d901d7811d5a04a762_3c7g+": ("対照例2", "△7七角成", "control_02_3c7g_plus.kif"),
}


def cp(value: Any) -> str:
    n = int(value)
    return f"{n:+d}cp"


def side_prefix(board: shogi.Board) -> str:
    return "▲" if board.turn == shogi.BLACK else "△"


def japanese_move(board: shogi.Board, usi: str) -> str:
    return side_prefix(board) + _move_text(board, usi)


def japanese_pv(board: shogi.Board, moves: list[str]) -> str:
    local = shogi.Board(board.sfen())
    rendered: list[str] = []
    for move in moves:
        rendered.append(japanese_move(local, move))
        local.push_usi(move)
    return " ".join(rendered)


def branch(root: VariationNode, board: shogi.Board, moves: list[str], comments: list[str]) -> None:
    node = root
    local = shogi.Board(board.sfen())
    for index, move in enumerate(moves):
        parsed = shogi.Move.from_usi(move)
        if parsed not in local.legal_moves:
            raise ValueError(f"illegal fixed-case PV move: {move}")
        child = next((candidate for candidate in node.children if candidate.move == move), None)
        if child is None:
            child = VariationNode(move=move)
            node.children.append(child)
        if index == 0:
            child.comment.extend(comment for comment in comments if comment not in child.comment)
        local.push(parsed)
        node = child


def case_explanation(case: dict[str, Any], board: shogi.Board, reply: dict[str, Any], is_reference: bool) -> list[str]:
    response = japanese_move(shogi.Board(board.sfen()), reply["move"])
    score = reply["score"]
    reply_gap = reply.get("gap")
    if case["purpose"] == "diagnostic_counterexample":
        if reply.get("free_major"):
            reason = "大駒を取る応手で、取られた側はその駒を直ちに取り返せない。"
        else:
            reason = "候補手を取り返す応手で、取られた駒の損失を回収できる。"
        quality = f"同じ条件で評価した最善級の応手との差は{reply_gap}cpで、応手後の評価値は{cp(score['score_cp'])}。"
        if is_reference:
            quality += "この応手を基準として、他の応手の良し悪しを比較している。"
        else:
            quality += "この応手は、明白そうなだけでなく実際にも十分良い応手である。"
        return [
            f"この応手：{response}",
            f"{reason}",
            f"{quality}",
            f"{response}が候補手を咎めるか：はい。",
        ]
    natural = not is_reference
    if natural:
        return [
            f"この応手：{response}",
            "駒を取り返すため、人間には自然に見える応手として比較する。",
            f"同じ条件で評価した最善級の応手との差は{reply_gap}cpで、応手後の評価値は{cp(score['score_cp'])}。",
            "この応手は自然に見えるが、実際には十分良い応手ではない。したがって、この例だけを理由に候補手は除外しない。",
        ]
    return [
        f"この応手：{response}",
        "同じ条件で評価した最善級の応手として、自然そうな取り返しと比較する。",
        f"応手後の評価値は{cp(score['score_cp'])}。自然そうな取り返しとの差は{reply_gap}cp。",
        "この応手を基準にして、自然そうな取り返しが実際にも十分良いかを確認する。",
    ]


def render_case(case: dict[str, Any], destination: Path) -> None:
    label, move_label, _ = CASE_LABELS[case["candidate_id"]]
    root = shogi.Board()
    for move in case["move_history"]:
        root.push_usi(move)
    if " ".join(root.sfen().split()[:4]) != " ".join(case["position"].split()[:4]):
        raise ValueError(f"history does not reach Astra parent position: {case['candidate_id']}")
    candidate_move = case["move_being_examined"]
    if shogi.Move.from_usi(candidate_move) not in root.legal_moves:
        raise ValueError(f"candidate is not legal: {case['candidate_id']}")
    candidate_board = shogi.Board(root.sfen())
    candidate_board.push_usi(candidate_move)
    candidate = VariationNode(move=candidate_move)
    replies = list(case["obvious_replies"])
    # Put the explicitly reviewed witness first.  For controls this is the
    # natural-looking but inferior recapture; its exact gap is part of Astra's
    # frozen evidence and must remain visible in the main KIF line.
    if case["purpose"] == "control":
        replies.sort(key=lambda item: int(item.get("gap") or 0), reverse=True)
    reference = case["engine_evidence"]["reference_eval"]
    comments = [
        "【固定例の人間向け確認資料】",
        f"この局面で調べている指し手：{move_label}",
        f"この例を確認する目的：{('明白な応手で咎められる候補手を、Human Policyで人間の選択確率を推定する前に除外できるか確認する。' if case['purpose'] == 'diagnostic_counterexample' else '自然そうな取り返しがあるだけでは候補手を除外しないことを確認する。')}",
        f"奇襲手としての判定：{'除外' if case['surprise_move_decision'] == 'reject' else 'この検査では除外しない'}",
        f"判定理由：{('明白で、同じ条件で評価しても十分良い応手があるため。' if case['surprise_move_decision'] == 'reject' else '自然そうな取り返しはあるが、同じ条件で評価した最善級の応手より大きく悪いため。')}",
        f"今回注目している相手の応手：{japanese_move(root, replies[0]['move'])}",
        "その応手が人間にとって明白そうと考える理由：駒を取る、または候補手を取り返す自然な手順だから。",
        f"その応手が実際にも良いか：同じ条件で評価した最善級の応手との差を確認する。基準となる評価値は{cp(reference)}。",
        "この事前確認は、明白で実際にも十分良い反証だけをHuman Policyによる確率推定の前に扱うためのもの。",
        "本番での自動除外への移行判断：INCONCLUSIVE。今回の固定例だけで一般的な安全性は確認していない。",
    ]
    if case["candidate_id"] == "5c46af1026197c8aeb70_3a3b":
        comments += [
            "▲2二角成で後手の角を取ることができ、後手はその馬を直ちに取り返せない。",
            "▲2二角成は、同じ条件で評価した最善級の応手から10cpしか離れていない。",
            "候補手直後の+3808と▲2二角成後の+3681の単純差127cpは、異なる局面の値の差であり、除外判定には使っていない。",
        ]
    candidate.comment = comments
    for response_index, reply in enumerate(replies):
        is_reference = reply["engine_eval"] == reference
        reply_comments = case_explanation(case, candidate_board, reply, is_reference)
        reply_comments.append(
            "この応手を指した後の局面で、保存済み解析から得たエンジンの進行："
            + japanese_pv(candidate_board, [reply["move"]] + list(reply.get("pv") or []))
        )
        branch(candidate, candidate_board, [reply["move"]] + list(reply.get("pv") or []), reply_comments)
    exported = ExportedKif(case["candidate_id"], case["position"], list(case["move_history"]), candidate)
    destination.parent.mkdir(parents=True, exist_ok=True)
    text = to_kif(exported, title=f"{label}：{move_label}")
    text = text.replace(f"先手：ShogiShock / {case['candidate_id']}", "先手：ShogiShock / 固定例確認")
    destination.write_text(text, encoding="utf-8")


def render(results_path: Path = RESULTS, out: Path = OUT) -> None:
    data = json.loads(results_path.read_text(encoding="utf-8"))
    cases = data["cases"]
    if len(cases) != 5 or {c["candidate_id"] for c in cases} != set(CASE_LABELS):
        raise ValueError("Astra tactical results do not contain the expected five fixed cases")
    for case in cases:
        _, _, filename = CASE_LABELS[case["candidate_id"]]
        folder = "reject" if case["surprise_move_decision"] == "reject" else "control"
        render_case(case, out / folder / filename)
    write_readme(cases, out)


def write_readme(cases: list[dict[str, Any]], out: Path) -> None:
    lines = [
        "# 固定例5件の人間レビュー資料",
        "",
        "この資料は、Astraが保存した5件の固定例を盤面で確認するためのものです。研究上の判定・数値・分類は変更していません。",
        "",
        "本番での自動除外への移行判断は **INCONCLUSIVE** です。除外3件と対照2件で狭い検査は成立しましたが、毒入りの駒や成立した捨て駒を含む一般的な安全性は確認されていません。",
        "",
        "| 例 | 調べる指し手 | この例の目的 | 注目する応手 | Astraの判定 | 人間が確認するポイント | KIFファイル |",
        "|---|---|---|---|---|---|---|",
    ]
    for case in cases:
        label, move_label, filename = CASE_LABELS[case["candidate_id"]]
        board = shogi.Board()
        for move in case["move_history"]:
            board.push_usi(move)
        replies = list(case["obvious_replies"])
        if case["purpose"] == "control":
            replies.sort(key=lambda item: int(item.get("gap") or 0), reverse=True)
        reply = replies[0]
        candidate_board = shogi.Board(board.sfen())
        candidate_board.push_usi(case["move_being_examined"])
        response = japanese_move(candidate_board, reply["move"])
        purpose = "明白で十分良い応手による除外の確認" if case["purpose"] == "diagnostic_counterexample" else "自然な取り返しだけでは除外しないことの確認"
        verdict = "除外" if case["surprise_move_decision"] == "reject" else "この検査では除外しない"
        point = "大駒を取った後に直ちに取り返されないか確認" if case["purpose"] == "diagnostic_counterexample" else "自然な取り返しと最善級の応手の評価差を確認"
        folder = "reject" if case["surprise_move_decision"] == "reject" else "control"
        lines.append(f"| {label} | {move_label} | {purpose} | {response} | {verdict} | {point} | [{filename}]({folder}/{filename}) |")
    lines += [
        "",
        "## 比較の読み方",
        "",
        "人間に自然そうに見えるかどうかと、エンジンが実際に十分良いと評価するかどうかを別々に確認しています。対照例では、自然そうな取り返しが最善級の応手より1931cpまたは2328cp悪いため、自然に見えることだけでは候補手を除外していません。",
        "",
        "△3二銀では、▲2二角成で後手の角を取れ、後手は直ちに取り返せません。同じ条件で評価した最善級の応手との差は10cpです。候補手直後の+3808と応手後の+3681の127cp差は異なる局面の単純差であり、除外判定には使っていません。",
        "",
        "KIF内の評価値と進行は保存済みの解析結果を表示したものです。新しいエンジン解析やHuman Policy計算は行っていません。",
        "",
    ]
    (out / "README.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=RESULTS)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    render(args.results, args.output)
