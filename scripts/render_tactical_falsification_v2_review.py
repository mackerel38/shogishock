"""Render Astra tactical falsification v2 evidence for human board review."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import shogi

from surprise.kif_export import ExportedKif, VariationNode, _move_text, to_kif

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "reports/tactical_falsification_v2/results.json"
OUT = ROOT / "exports/tactical_falsification_v2_review"

CASE_PATHS = {
    "bishop_block_rook_sacrifice": ("controls_provisional", "23ply_bishop_drop_rook_trap.kif"),
    "horse_entry_bad_gold_recapture": ("controls_borderline", "22ply_horse_entry_gold_recapture.kif"),
    "user_rook_counter_sacrifice": ("diagnostic_hypotheses", "user_rook_sacrifice.kif"),
    "user_pawn_drop_followup": ("diagnostic_hypotheses", "user_pawn_drop_followup.kif"),
}


def side_prefix(board: shogi.Board) -> str:
    return "▲" if board.turn == shogi.BLACK else "△"


def human_move(board: shogi.Board, usi: str) -> str:
    return side_prefix(board) + _move_text(board, usi)


def human_pv(board: shogi.Board, moves: list[str]) -> str:
    local = shogi.Board(board.sfen())
    rendered = []
    for move in moves:
        rendered.append(human_move(local, move))
        local.push_usi(move)
    return " ".join(rendered)


def add_branch(root: VariationNode, board: shogi.Board, moves: list[str], comments: list[str]) -> None:
    node = root
    local = shogi.Board(board.sfen())
    for index, move in enumerate(moves):
        parsed = shogi.Move.from_usi(move)
        if parsed not in local.legal_moves:
            raise ValueError(f"illegal v2 saved branch move: {move}")
        child = next((item for item in node.children if item.move == move), None)
        if child is None:
            child = VariationNode(move=move)
            node.children.append(child)
        if index == 0:
            child.comment.extend(item for item in comments if item not in child.comment)
        local.push(parsed)
        node = child


def cp(value: int) -> str:
    return f"{value:+d}cp"


def selected_response(case: dict[str, Any], move: str) -> dict[str, Any] | None:
    return next((item for item in case.get("responses", []) if item.get("move") == move), None)


def purpose(case: dict[str, Any]) -> str:
    if case["id"] == "bishop_block_rook_sacrifice":
        return "23手目の局面で、飛車を取る自然な応手が実際には悪い場合に、候補手を誤除外しないことを確認する。旧17手目の▲７七角とは別の、角を打つ進行である。"
    if case["id"] == "horse_entry_bad_gold_recapture":
        return "自然に見える金の取り返しが、候補手を明白に咎めるほど良い応手ではないことを確認する。ただし出発局面の質が十分でないため、きれいな安全性対照には採用しない。"
    if case["id"] == "user_rook_counter_sacrifice":
        return "人間から提案された飛車の捨て駒が、実際に成立しているかを小規模な保存済み解析で確認する。"
    return "▲８二歩打の後に、△８六桂打だけが見えにくい受けなのかを確認する。複数の強い応手を比較し、特定の一手だけを前提にしない。"


def case_comments(case: dict[str, Any], board: shogi.Board, candidate: str, replies: list[str]) -> list[str]:
    cid = case["id"]
    gate = case["final_gate_result"]["decision"]
    if cid == "bishop_block_rook_sacrifice":
        reason = "△２四歩は先手の２四飛を取る自然な応手だが、その後に先手が▲８六角として後手の飛車を取れる。ゲートは候補手を除外していない。"
        evidence = "保存済み100k解析は△２四歩と△８八飛成を選んだ応手同士の比較で、+1490cpと+357cp、差は1133cp。全合法応手を100kで順位付けした値ではない。"
        handling = "暫定的により良い対照として人間レビューを待つ。実際の奇襲候補としては扱わない。"
    elif cid == "horse_entry_bad_gold_recapture":
        reason = "▲同金は自然に見えるが、▲７七角打側より455cp悪い。さらに直前の▲３五飛は▲２四飛より454cp悪く、自然で評価上も明確な出発局面とは言い切れない。"
        evidence = "保存済み100k比較では、▲同金側は-585cp、▲７七角打側は-130cpで、差は455cp。これは安全性の成功例として数えない。"
        handling = "ゲートは通過したが、きれいな対照例としては保留する。"
    elif cid == "user_rook_counter_sacrifice":
        reason = "▲２二飛成の後に△同銀と進めた保存済み100k評価は約-2478cpで、成立した捨て駒の十分な補償を確認できなかった。"
        evidence = "小規模エンジン検証では、提案された捨て駒をprefilterが誤除外した証拠は得られなかった。"
        handling = "現在の提案は研究上採用しない。新しい奇襲候補として認定しない。"
    else:
        reason = "▲８二歩打は狭いゲートを通過したが、研究上の提案は採用されていない。△８六桂打だけでなく、△８二龍と△８二銀も比較対象にする。"
        evidence = "保存済み100kの選択応手比較では、△８六桂打は-2588cp、△８二龍は-2756cp、△８二銀は-2864cp。△８二銀も十分強く、比較した3応手では最も良い評価だった。"
        handling = "△８六桂打だけを見つければ成立する罠とは扱わない。現在の提案は研究上採用しない。"
    candidate_board = shogi.Board(board.sfen())
    candidate_board.push_usi(candidate)
    focus = human_move(candidate_board, replies[0])
    return [
        "【人間が盤面を確認する検証局面】",
        f"この局面で調べている指し手：{human_move(board, candidate)}",
        f"この資料の目的：{purpose(case)}",
        f"注目している相手の応手：{focus}",
        "その応手が自然に見える理由：候補手で攻撃された駒を取る、または取り返す手順だから。",
        f"ゲートの結果：{'候補手を除外していない' if gate == 'not_falsified' else '候補手を除外した'}。",
        f"研究上の扱い：{handling}",
        f"判定と評価の説明：{reason}",
        evidence,
        "評価値はすべて先手側から見た値で、＋は先手有利、－は後手有利を表す。",
        "10kの値は保存された全合法応手の比較、100kの値は選んだ応手同士の比較であり、100kで全合法応手を順位付けしたものではない。",
        "Human Policyは今回使用しておらず、人間の選択確率も測定していない。",
        "本番での自動除外への移行判断：INCONCLUSIVE。",
    ]


def render_case(case: dict[str, Any], destination: Path) -> None:
    root = shogi.Board()
    history = case["history"].split()
    for move in history:
        root.push_usi(move)
    if " ".join(root.sfen().split()[:4]) != " ".join(case["position"].split()[:4]):
        raise ValueError(f"history does not reach saved position: {case['id']}")
    candidate = case["candidate_move"]
    if shogi.Move.from_usi(candidate) not in root.legal_moves:
        raise ValueError(f"candidate is illegal: {case['id']}")
    after = shogi.Board(root.sfen())
    after.push_usi(candidate)
    replies = list(case["obvious_looking_replies"])
    if case["id"] == "bishop_block_rook_sacrifice":
        replies = ["2c2d", "8f8h+", "8f8h"]
    elif case["id"] == "horse_entry_bad_gold_recapture":
        replies = ["7h6g", "B*7g", "B*9e"]
    elif case["id"] == "user_rook_counter_sacrifice":
        replies = ["3a2b"]
    else:
        replies = ["N*8f", "8i8b", "7a8b"]
    node = VariationNode(move=candidate)
    node.comment = case_comments(case, root, candidate, replies)
    for move in replies:
        record = selected_response(case, move)
        if not record:
            raise ValueError(f"missing saved response evidence {case['id']} {move}")
        moves = [move] + list(record.get("result", {}).get("pv") or [])
        score = record["result"]["score"]
        comments = [
            f"この応手：{human_move(after, move)}",
            f"保存済み解析の応手後評価：{cp(score['score_cp'])}。評価値は先手側から見た値。",
            "この応手を指した後の保存済みエンジンの進行：" + human_pv(after, moves),
        ]
        add_branch(node, after, moves, comments)
    text = to_kif(ExportedKif(case["id"], case["position"], history, node), title=purpose(case))
    text = text.replace(f"先手：ShogiShock / {case['id']}", "先手：ShogiShock / 人間レビュー")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")


def render(results_path: Path = RESULTS, out: Path = OUT) -> None:
    data = json.loads(results_path.read_text(encoding="utf-8"))
    cases = data["cases"]
    if {case["id"] for case in cases} != set(CASE_PATHS) or len(cases) != 4:
        raise ValueError("unexpected Astra v2 case set")
    for case in cases:
        folder, filename = CASE_PATHS[case["id"]]
        render_case(case, out / folder / filename)
    write_readme(data, out)


def write_readme(data: dict[str, Any], out: Path) -> None:
    lines = [
        "# tactical falsification v2 人間レビュー一覧",
        "",
        "Astraのv2研究結果を盤面で確認するための資料です。研究判断・数値・分類は変更していません。",
        "",
        "本番での自動除外への移行判断：**INCONCLUSIVE**。Human Policyは今回使用していません。",
        "",
        "| 項目 | 何を調べる局面か | 調べる指し手 | 注目する応手 | ゲートの結果 | 研究上の扱い | KIF |",
        "|---|---|---|---|---|---|---|",
    ]
    for case in data["cases"]:
        root = shogi.Board()
        for move in case["history"].split():
            root.push_usi(move)
        candidate_board = shogi.Board(root.sfen())
        candidate_board.push_usi(case["candidate_move"])
        replies = list(case["obvious_looking_replies"])
        if case["id"] == "bishop_block_rook_sacrifice": replies = ["2c2d", "8f8h+", "8f8h"]
        elif case["id"] == "horse_entry_bad_gold_recapture": replies = ["7h6g", "B*7g", "B*9e"]
        elif case["id"] == "user_pawn_drop_followup": replies = ["N*8f", "8i8b", "7a8b"]
        label = human_move(root, case["candidate_move"])
        focus = human_move(candidate_board, replies[0])
        folder, filename = CASE_PATHS[case["id"]]
        if case["id"] == "bishop_block_rook_sacrifice": purpose_text, handling = "飛車取りが罠になる応手を誤除外しないか", "暫定的により良い対照例。奇襲候補ではない"
        elif case["id"] == "horse_entry_bad_gold_recapture": purpose_text, handling = "自然な金の取り返しを安全性根拠にできるか", "保留。安全性根拠には数えない"
        elif case["id"] == "user_rook_counter_sacrifice": purpose_text, handling = "提案された飛車の捨て駒が成立するか", "研究上採用しない"
        else: purpose_text, handling = "▲８二歩打で特定の受けだけが必要か", "研究上採用しない。△８六桂だけを前提にしない"
        gate = "候補手を除外していない" if case["final_gate_result"]["decision"] == "not_falsified" else "候補手を除外した"
        lines.append(f"| {purpose_text} | {purpose_text} | {label} | {focus} | {gate} | {handling} | [{filename}]({folder}/{filename}) |")
    lines += [
        "",
        "## 旧reject 3例",
        "",
        "前回の明白な悪手3例（△３二銀を含む）は、新しい解析をせず、引き続きrejectの回帰確認として参照します。",
        "",
        "- [△３二銀：除外例1](../tactical_falsification_review/reject/reject_01_3a3b.kif)",
        "- [除外例2](../tactical_falsification_review/reject/reject_02_2b6f.kif)",
        "- [除外例3](../tactical_falsification_review/reject/reject_03_8h4d.kif)",
        "",
        "以前の▲３三角成・△７七角成の2例は、候補手以前の進行に不自然な評価損・未処理戦術が確認されたため、安全性を裏付ける対照例から撤回済みです。既存KIFは削除していません。",
        "",
        "100kの数値は選択した応手同士の比較であり、全合法応手の100kランキングではありません。23手目局面の▲７七角打は旧17手目の▲７七角とは別の角打ち進行です。",
    ]
    (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=RESULTS)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    render(args.results, args.output)
