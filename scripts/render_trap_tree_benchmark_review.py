"""Render the frozen trap-tree benchmark branches for human review only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import shogi

from surprise.kif_export import ExportedKif, VariationNode, _move_text, to_kif

ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "reports/trap_tree_benchmark/ASTRA_HANDOFF.json"
TREE = ROOT / "reports/trap_tree_benchmark/tree.json"
OUT = ROOT / "exports/trap_tree_benchmark_review"

BRANCH_FILES = {
    "B*7g": ("branch_01_B7g.kif", "▲７七角打"),
    "3d2d": ("branch_02_R2d.kif", "▲２四飛"),
    "3d3f": ("branch_03_R3f.kif", "▲３六飛"),
    "3d3e": ("branch_04_R3e.kif", "▲３五飛"),
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
            raise ValueError(f"illegal saved trap-tree move: {move}")
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


def status_text(status: str) -> str:
    return {
        "trap_branch": "条件付きで罠として成立する可能性がある枝",
        "opponent_refutes": "今回試した継続手が局所的に失敗した枝",
        "needs_review": "浅い解析と深い比較が食い違うため追加確認が必要な枝",
    }.get(status, "保存済み研究結果に基づく確認枝")


def branch_data(tree: dict[str, Any], move: str) -> dict[str, Any]:
    return next(item for item in tree["branches"] if item["opponent_move"] == move)


def confirmation_for(branch: dict[str, Any], reply: str) -> dict[str, Any] | None:
    return next((item for item in branch.get("confirmation", []) if item.get("reply") == reply), None)


def branch_intro(branch: dict[str, Any], root: shogi.Board, branch_move: str, candidate: str, replies: list[str]) -> list[str]:
    _, branch_label = BRANCH_FILES[branch["opponent_move"]]
    branch_board = shogi.Board(root.sfen())
    branch_board.push_usi(branch_move)
    candidate_board = shogi.Board(branch_board.sfen())
    candidate_board.push_usi(candidate)
    status = branch["branch_status"]
    if branch["opponent_move"] == "B*7g":
        purpose = "△８八飛成に対して、自然に見える▲同金と、より良い▲同角で評価が大きく変わるかを確認する。"
        detail = "100kでは▲同角側+215cp、▲同金側-865cpで、選択した応手同士の差は1080cp。全合法手を100kで比較した結果ではない。"
        status_text = "条件付きで罠として成立している可能性があるが、確定した実戦用定跡ではない。"
    elif branch["opponent_move"] == "3d2d":
        purpose = "▲２四飛に対して今回試した△６七角成の継続が、▲同金で対応されるかを確認する。"
        detail = "△６七角成は▲同金で十分対応できるため、この試した継続手だけが局所的に失敗した。▲２四飛の枝全体を否定する結果ではない。"
        status_text = "今回試した継続手は局所的に成立しない。枝全体の否定や奇襲候補の不採用を意味しない。"
    elif branch["opponent_move"] == "3d3f":
        purpose = "▲８八飛成に対する▲同金と、10kで有望に見えた角打ちの評価順が深い比較で変わるかを確認する。普通に指す△同角▲同歩も併記する。"
        detail = "10kでは角打ちの方が良いように見えたが、100kの選択応手比較では▲同金+360cp、比較相手の角打ち-470cpとなり、▲同金が830cp良い。"
        status_text = "浅い解析の見かけだけでは罠と認定できないため、追加確認が必要。▲同金を悪手とは扱わない。"
    else:
        purpose = "△６七角成に対する▲同金と▲７七角打などの耐える手を比較し、二枚替えの局面が実戦上どう見えるかを確認する。"
        detail = "100kの選択応手比較では、▲７七角打側-130cp、▲同金側-585cpで差は455cp。人間の選択確率は測定していない。"
        status_text = "条件付きで罠として成立している可能性があるが、確定した実戦用定跡ではない。"
    lines = [
        "【trap-tree benchmark 人間レビュー資料】",
        f"この局面で最初に調べる相手の指し手：{branch_label}",
        f"今回の確認目的：{purpose}",
        f"この枝の研究上の扱い：{status_text}",
        f"この枝でこちらが試した継続手：{human_move(root, branch_move)}の後の{human_move(branch_board, candidate)}",
        f"注目する相手の応手：{', '.join(human_move(candidate_board, move) for move in replies)}",
        "評価値の読み方：すべて先手視点。＋は先手有利、－は後手有利。",
        detail,
        "10kは保存された比較結果、100kは選択した応手同士または選択した部分集合の比較であり、全合法応手の100k順位ではない。",
        "Human Policyは今回使用しておらず、人間の選択確率や成功確率は表示していない。",
        "trap-tree構築法全体の判定：INCONCLUSIVE。",
    ]
    if branch["opponent_move"] == "3d3f":
        lines += [
            "10kで悪手と断定しない。100kで評価順が逆転したため、浅い解析だけで自然な誤答とは認定できない。",
            "比較相手の角打ちは、10kで有望に見えた比較対象であり、正解手や必須の防御手とは扱わない。",
            "普通に指す△同角▲同歩は通常進行の選択肢として分離している。",
        ]
    if branch["opponent_move"] == "3d2d":
        lines.append("△２三歩は候補一覧には存在したが、事前に固定した選択規則から漏れたため、このKIFへ後付けしていない。")
    return lines


def render_one(branch: dict[str, Any], root_sfen: str, history: list[str], destination: Path) -> None:
    root = shogi.Board()
    for move in history:
        root.push_usi(move)
    if " ".join(root.sfen().split()[:4]) != " ".join(root_sfen.split()[:4]):
        raise ValueError("trap-tree root history mismatch")
    branch_move = branch["opponent_move"]
    if shogi.Move.from_usi(branch_move) not in root.legal_moves:
        raise ValueError(f"illegal root branch move: {branch_move}")
    after_branch = shogi.Board(root.sfen())
    after_branch.push_usi(branch_move)
    candidates = branch["candidates"]
    selected = next(item for item in candidates if item["move"] == branch["our_response"])
    response_order = list(branch["opponent_natural_replies"])
    reply_moves = [item["move"] for item in response_order]
    if branch_move == "B*7g": reply_moves = ["7h8h", "7g8h"]
    elif branch_move == "3d2d": reply_moves = ["7h6g"]
    elif branch_move == "3d3f": reply_moves = ["7h8h", "B*1e"]
    elif branch_move == "3d3e": reply_moves = ["7h6g", "B*7g"]
    candidate_node = VariationNode(move=selected["move"])
    candidate_board = shogi.Board(after_branch.sfen())
    candidate_board.push_usi(selected["move"])
    for reply in reply_moves:
        continuation = selected.get("continuations", {}).get(reply)
        if continuation is None:
            # The saved tree stores some reply continuations in the branch
            # edge data rather than in the candidate convenience map.
            continuation = {"move": reply, "result": {"pv": []}}
        record = confirmation_for(branch, reply)
        comments = [f"この応手：{human_move(candidate_board, reply)}"]
        after_reply = shogi.Board(candidate_board.sfen())
        after_reply.push_usi(reply)
        if record:
            score = record["result"]["score"]
            comments.append(f"保存済み100k選択比較の応手後評価：{cp(score['score_cp'])}。")
            comments.append("保存済み100k解析の進行：" + human_pv(after_reply, list(record["result"].get("pv") or [])))
        # A confirmation record is the source of the displayed 100k score.
        # Replay that record's PV in the KIF as well; the older candidate
        # continuation is only a 10k PV and must not be mixed with this value.
        if record:
            pv = list(record["result"].get("pv") or [])
        else:
            pv = [continuation["move"]] + list((continuation.get("result") or {}).get("pv") or [])
        add_branch(candidate_node, candidate_board, [reply] + pv, comments)
    root_node = VariationNode(move=branch_move)
    root_node.comment = branch_intro(branch, root, branch_move, selected["move"], reply_moves)
    root_node.children.append(candidate_node)
    if branch.get("normal_alternative"):
        normal = next(item for item in candidates if item["move"] == branch["normal_alternative"])
        normal_node = VariationNode(move=normal["move"])
        normal_board = shogi.Board(after_branch.sfen())
        normal_board.push_usi(normal["move"])
        normal_reply_move = "3g3f"
        normal_reply = normal.get("continuations", {})[normal_reply_move]
        add_branch(normal_node, normal_board, [normal_reply_move, normal_reply["move"]] + list((normal_reply.get("result") or {}).get("pv") or []), ["通常進行の選択肢：奇襲へ無理に進まず、△同角▲同歩と指す進行。"])
        root_node.children.append(normal_node)
    exported = ExportedKif(f"trap-tree-{branch_move}", root_sfen, history, root_node)
    title = f"{BRANCH_FILES[branch_move][1]}：{status_text(branch['branch_status'])}"
    text = to_kif(exported, title=title).replace(f"先手：ShogiShock / trap-tree-{branch_move}", "先手：ShogiShock / 人間レビュー")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")


def write_readme(tree: dict[str, Any], root_sfen: str, out: Path) -> None:
    lines = [
        "# trap-tree benchmark 人間レビュー一覧",
        "",
        "Astraの保存済みtree.jsonとASTRA_HANDOFF.jsonを、人間がShogiHomeで確認できる形にした資料です。研究判断・評価値・branch分類は変更していません。",
        "",
        "**trap-tree構築法の判定：INCONCLUSIVE**",
        "",
        "評価値は先手視点です。＋は先手有利、－は後手有利を表します。100kの値は選択した応手同士または選択部分集合の比較であり、全合法応手を100kで順位付けした結果ではありません。Human Policyは未使用です。",
        "",
        "| 枝 | 調べる指し手 | 人間が確認する応手 | 研究上の扱い | KIF |",
        "|---|---|---|---|---|",
    ]
    labels = {"B*7g": "条件付きで罠として成立する可能性", "3d2d": "今回試した継続だけが局所的に失敗", "3d3f": "10k/100k逆転のため追加確認", "3d3e": "条件付きで罠として成立する可能性"}
    response_labels = {"B*7g": "▲同金 / ▲同角", "3d2d": "▲同金", "3d3f": "▲同金 / ▲１五角打 / △同角▲同歩", "3d3e": "▲同金 / ▲７七角打"}
    for branch in tree["branches"]:
        filename, move_label = BRANCH_FILES[branch["opponent_move"]]
        folder = "branches"
        root_board = shogi.Board(root_sfen)
        root_board.push_usi(branch["opponent_move"])
        lines.append(f"| {move_label} | {move_label}の後に{human_move(root_board, branch['our_response'])}を試す | {response_labels[branch['opponent_move']]} | {labels[branch['opponent_move']]} | [KIF]({folder}/{filename}) |")
    lines += [
        "",
        "## 根からの4枝",
        "",
        "```text",
        "△４五角",
        "├─ ▲７七角打 → 条件付きで罠として成立する可能性",
        "├─ ▲２四飛 → 今回試した△６七角成は局所的に失敗",
        "├─ ▲３六飛 → 10k/100kで評価順が逆転、追加確認",
        "└─ ▲３五飛 → 条件付きで罠として成立する可能性",
        "```",
        "",
        "▲３六飛の枝では、10kで有望に見えた角打ちを正解手とは扱いません。100kの選択応手比較では▲同金が+360cp、角打ちが-470cpで、▲同金が830cp良い結果に逆転しています。",
        "",
        "▲２四飛の枝の「今回試した継続手が局所的に失敗」という表示は、△６七角成という継続手だけに関するものです。▲２四飛の枝全体を否定するものではありません。",
        "",
        "△２三歩はエンジン候補一覧には存在しましたが、事前に固定した候補選択規則から漏れました。結果を見た後の後付けは行わず、候補生成の網羅性不足として記録しています。",
        "",
        "旧・除外例3例は今回もすべて除外のままです。新しい解析は行わず、既存KIFを参照します。旧▲３三角成・△７七角成の2例は安全性根拠から撤回済みです。",
        "",
        "同一局面へ合流するtree nodeはtree.json上で共有して扱われています。KIFではShogiHomeで合法に再生できるよう、履歴を分けて表示しています。",
        "",
        "- [旧・除外例：△３二銀](../tactical_falsification_review/reject/reject_01_3a3b.kif)",
        "- [旧・除外例2](../tactical_falsification_review/reject/reject_02_2b6f.kif)",
        "- [旧・除外例3](../tactical_falsification_review/reject/reject_03_8h4d.kif)",
    ]
    (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def render() -> None:
    handoff = json.loads(HANDOFF.read_text(encoding="utf-8"))
    tree = json.loads(TREE.read_text(encoding="utf-8"))
    if handoff["next_step_decision"] != "INCONCLUSIVE" or tree["next_step_decision"] != "INCONCLUSIVE":
        raise ValueError("Astra INCONCLUSIVE conclusion changed")
    root_position = handoff["root_position"]
    for branch in tree["branches"]:
        filename, _ = BRANCH_FILES[branch["opponent_move"]]
        render_one(branch, root_position["sfen"], root_position["history"], OUT / "branches" / filename)
    write_readme(tree, root_position["sfen"], OUT)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    render()
