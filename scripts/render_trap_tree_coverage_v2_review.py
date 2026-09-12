"""Render the coverage-v2 saved evidence as short, human-review KIFs."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

import shogi

from surprise.kif_export import ExportedKif, VariationNode, _move_text, to_kif

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/trap_tree_coverage_v2"
OUT = ROOT / "exports/trap_tree_coverage_v2_review"
PV_PREFIX = 3


def side_prefix(board: shogi.Board) -> str:
    return "▲" if board.turn == shogi.BLACK else "△"


def human_move(board: shogi.Board, move: str) -> str:
    return side_prefix(board) + _move_text(board, move)


def human_pv(board: shogi.Board, moves: list[str]) -> str:
    local = shogi.Board(board.sfen())
    out: list[str] = []
    for move in moves[:PV_PREFIX]:
        if shogi.Move.from_usi(move) not in local.legal_moves:
            raise ValueError(f"illegal saved PV move: {move}")
        out.append(human_move(local, move))
        local.push_usi(move)
    return " ".join(out)


def replay(board: shogi.Board, moves: list[str]) -> shogi.Board:
    local = shogi.Board(board.sfen())
    for move in moves:
        if shogi.Move.from_usi(move) not in local.legal_moves:
            raise ValueError(f"illegal saved move: {move}")
        local.push_usi(move)
    return local


def cp(score: int | None) -> str:
    return "評価値なし" if score is None else f"{score:+d}cp"


def add_line(parent: VariationNode, board: shogi.Board, moves: list[str], comments: list[str]) -> None:
    node = parent
    local = shogi.Board(board.sfen())
    for index, move in enumerate(moves):
        if shogi.Move.from_usi(move) not in local.legal_moves:
            raise ValueError(f"illegal saved branch move: {move}")
        child = next((item for item in node.children if item.move == move), None)
        if child is None:
            child = VariationNode(move=move)
            node.children.append(child)
        if index == 0:
            for comment in comments:
                if comment not in child.comment:
                    child.comment.append(comment)
        local.push_usi(move)
        node = child


def load() -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    deep = json.loads((REPORT / "deep_checks.json").read_text(encoding="utf-8"))
    handoff = json.loads((REPORT / "ASTRA_HANDOFF.json").read_text(encoding="utf-8"))
    mate = json.loads((REPORT / "mate_proof_checks.json").read_text(encoding="utf-8"))
    return deep["groups"], handoff, mate


def group(groups: list[dict[str, Any]], ident: str) -> dict[str, Any]:
    return next(item for item in groups if item["id"] == ident)


def result(g: dict[str, Any], move: str, nodes: int = 80_000_000) -> dict[str, Any]:
    level = next(item for item in g["levels"] if item["nodes"] == nodes)
    return level["results"][move]


def history_board(history: list[str]) -> shogi.Board:
    return replay(shogi.Board(), history)


def intro(title: str, purpose: str, status: str, focus: str, detail: list[str]) -> list[str]:
    return [
        "【trap-tree coverage v2 人間レビュー資料】",
        f"今回確認する局面：{title}",
        f"この資料の目的：{purpose}",
        f"この枝の研究上の扱い：{status}",
        f"人間に確認してほしい点：{focus}",
        "評価値はすべて先手視点。＋は先手有利、－は後手有利。",
        *detail,
        "深い解析の値は、事前に選んだ比較対象または部分集合を同じ条件で比べた値であり、全合法手の完全ランキングではない。",
        "Human Policyは今回使用しておらず、人間の選択確率や成功確率は測定していない。",
        "trap-tree構築法全体の判定：INCONCLUSIVE。",
    ]


def source_comments(board: shogi.Board, rec: dict[str, Any], limit_label: str = "保存済み80M比較") -> list[str]:
    score = rec.get("score", {}).get("score_cp")
    pv = list(rec.get("pv") or [])
    lines = [f"{limit_label}のこの指し手後評価：{cp(score)}。"]
    if pv:
        lines.append("保存済み解析の進行（先頭3手）：「" + human_pv(board, pv) + "」")
        lines.append("上の進行と直後のKIF分岐は、同じ保存済み解析レコードから作成している。")
    return lines


def make_alt_branch(g: dict[str, Any], first: str, second: str, filename: str) -> None:
    root = history_board(g["history"])
    root_node = VariationNode(move=first)
    first_board = replay(root, [first])
    r1 = result(g, first)
    if g["id"] == "candidate_3d2d":
        purpose = "▲2四飛の後で、旧ルールから漏れた静かな△2三歩が候補生成に入ったかを確認する。"
        status = "今回比較した候補内で5つの探索予算すべて上位だったが、評価安定条件は未達。候補昇格ではない。"
        focus = "△2三歩が盤面上で自然な奇襲準備手に見えるか。旧MultiPVには現れていたが、top1 + forcing枠の選択規則から漏れていた。"
        extra = ["比較対象の旧候補△６七角成は+1331cp。△２三歩の+622cpとの比較は、全合法手の順位付けではない。"]
    else:
        purpose = "▲3六飛の後で、△6七角成と旧treeで調べた△8八飛成を同じ保存済み条件で比較する。"
        status = "今回深く比較した候補の中では△6七角成が一貫して有力だったが、評価安定条件は未達。確定最善手ではない。"
        focus = "浅い解析だけで最善手や罠を断定しないこと。"
        extra = ["80M比較対象内では△６七角成-295cp、△８八飛成+468cp。先手視点なので、△６七角成の方が763cp後手に良い。"]
    root_node.comment = intro(
        f"△4五角の後の比較（調べる指し手：{human_move(root, first)}）",
        purpose, status, focus, extra,
    )
    add_line(root_node, first_board, list(r1.get("pv") or [])[:PV_PREFIX], source_comments(first_board, r1))
    # The second value is explained in the human-facing comments.  The KIF
    # variation is deliberately kept to the primary saved record so that no
    # value from one record is paired with a PV from another record.
    title = "▲2四飛後の△2三歩と比較対象を確認する短い進行" if g["id"] == "candidate_3d2d" else "▲3六飛後の△6七角成と比較対象を確認する短い進行"
    out = OUT / "branches" / filename
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(to_kif(ExportedKif(filename, root.sfen(), g["history"], root_node), title=title), encoding="utf-8")


def make_reply_branch(g: dict[str, Any], candidate: str, replies: list[str], filename: str, title: str, purpose: str, status: str, focus: str, details: list[str], mate_reply: str | None = None) -> None:
    # Reply groups store the candidate move as the final history element.
    # Keep it as the KIF branch point rather than replaying it twice.
    if not g["history"] or g["history"][-1] != candidate:
        raise ValueError(f"saved reply history does not end in {candidate}")
    base_history = g["history"][:-1]
    root = history_board(base_history)
    if shogi.Move.from_usi(candidate) not in root.legal_moves:
        raise ValueError(candidate)
    candidate_node = VariationNode(move=candidate)
    after_candidate = replay(root, [candidate])
    for reply in replies:
        response_board = replay(after_candidate, [reply])
        rec = result(g, reply)
        comments = [
            f"注目する相手の応手：{human_move(after_candidate, reply)}",
            "この応手が自然に見える理由：盤上の駒を取り返す、または攻め合いを続けるという人間にも理解しやすい発想を確認する。",
            *source_comments(response_board, rec),
        ]
        if mate_reply == reply:
            comments += [
                "この応手の後、通常エンジンは19手詰みを検出した。19手はこの応手の直後から数え、△８八飛成を含む。",
                "これは研究上採用したエンジン検出結果であり、独立証明による最短手数保証ではない。",
            ]
        add_line(candidate_node, after_candidate, [reply] + list(rec.get("pv") or [])[:PV_PREFIX], comments)
    candidate_node.comment = intro(title, purpose, status, focus, details)
    out = OUT / "branches" / filename
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(to_kif(ExportedKif(filename, root.sfen(), base_history, candidate_node), title=title), encoding="utf-8")


def render(groups: list[dict[str, Any]], handoff: dict[str, Any], mate: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    g2d = group(groups, "candidate_3d2d")
    g3f = group(groups, "candidate_3d3f")
    r3e = group(groups, "reply_3d3e")
    r2d = group(groups, "reply_3d2d")
    make_alt_branch(g2d, "P*2c", "4e6g+", "01_R2d_P2c.kif")
    make_alt_branch(g3f, "4e6g+", "8f8h+", "02_R3f_B6g.kif")
    make_reply_branch(r3e, "4e6g+", ["7h6g", "7h7i", "B*7g"], "03_R3e_B6g_replies.kif",
        "▲3五飛後の△6七角成：応手比較", "▲同金・▲7九金・▲7七角打がどのように見えるかを比較する。",
        "条件付きで人間レビューを続ける枝。比較全体の安定条件は未達。",
        "▲7九金をランダムな悪手と決めつけず、浮いた金を逃がす理由と19手詰みを別々に確認する。",
        ["80M比較対象内では▲7七角打+34cp、▲同金-770cp、▲8七金-1893cp。ただし確定値として扱わない。"], "7h7i")
    make_reply_branch(r2d, "4e6g+", ["7h6g", "7h7i", "7h8g", "2d2a+"], "04_R2d_B6g_replies.kif",
        "▲2四飛後の△6七角成：応手比較", "自然な▲同金が十分良いか、他の応手が大きく損をするかを分けて確認する。",
        "条件付きで人間レビューを続ける枝。自然な応手だけで有力奇襲とは認定しない。",
        "▲同金が十分良い一方、▲7九金には19手詰み、▲2一飛成には攻め合いの発想があることを盤面で確認する。",
        ["80M比較対象内では▲同金+1296cp、▲8七金-1513cp、▲2一飛成-2174cp。ただし確定値として扱わない。"], "7h7i")
    write_readme(groups, handoff)
    write_html(groups)


def write_readme(groups: list[dict[str, Any]], handoff: dict[str, Any]) -> None:
    text = """# trap-tree coverage v2 人間レビュー

## 今回の結論

quietな候補と、人間が思いつきやすい理由を持つ応手の生成漏れは改善した。一方、6つの比較群で事前に決めた全体安定条件を満たさず、人間的動機の絞り込み精度も未検証である。そのため、trap-tree構築法の判定は **INCONCLUSIVE**。実際の奇襲候補への昇格は0件であり、新しい有力奇襲を発見した資料ではない。

評価値はすべて先手視点。＋は先手有利、－は後手有利。80Mの値は、事前に選んだ比較対象または部分集合を同じ条件で比べた値で、全合法手の完全ランキングではない。Human Policyは今回使用していない。

## 4つのレビュー局面

| 資料 | 何を確認するか | 保存済み比較 | 研究上の扱い | 人間が見る点 |
|---|---|---|---|---|
| [01_R2d_P2c.kif](branches/01_R2d_P2c.kif) | ▲2四飛の後の△2三歩 | 80M比較対象内で+622cp。5つの予算すべてで今回比較した候補内の上位 | quietな候補の生成漏れが改善したかの確認。評価安定条件は未達 | △2三歩が盤面上で自然な奇襲準備手に見えるか |
| [02_R3f_B6g.kif](branches/02_R3f_B6g.kif) | ▲3六飛の後、△6七角成と△8八飛成を比較 | △6七角成-295cp、△8八飛成+468cp。差は763cp | 深い比較で有力だった候補の確認。確定最善手とは扱わない | 浅い評価だけで最善・罠を断定できないこと |
| [03_R3e_B6g_replies.kif](branches/03_R3e_B6g_replies.kif) | ▲3五飛 △6七角成後の4応手 | ▲7七角打+34cp、▲同金-770cp、▲8七金-1893cp（▲7九金は詰み表示） | 条件付きでレビューを続ける枝。比較全体の安定条件は未達 | ▲7九金の人間的理由と、19手詰みを分けて確認 |
| [04_R2d_B6g_replies.kif](branches/04_R2d_B6g_replies.kif) | ▲2四飛 △6七角成後の4応手 | ▲同金+1296cp、▲8七金-1513cp、▲2一飛成-2174cp（▲7九金は詰み表示） | 自然な応手が十分良いので、別の誤応手だけでは有力奇襲としない | ▲同金の自然さ、▲2一飛成の攻め合いの発想 |

## 見落としと扱い

△2三歩は旧benchmarkでもMultiPVには現れていたが、事前に固定した「top1 + forcing枠」の候補選択規則から漏れていた。今回の広い候補生成では、特殊ケースとして名指しせず拾えた。今回は結果を見た後の候補追加はしていない。

▲7九金については、通常エンジンがその直後から19手詰みを検出した。19手には△8八飛成を含む。これは研究上採用したエンジン検出であり、独立証明による最短手数保証ではない。

同じ局面へ到達する履歴がある場合も、研究上の比較は保存済みの局面・比較レコードに従う。KIFはShogiHomeで再生できるよう、履歴を含めて表示している。

## 既存の明白な悪手3例

前回の3例は引き続きrejectであり、新しい候補には戻していない。既存の [人間レビュー一覧](../tactical_falsification_review/README.md) と [△3二銀KIF](../tactical_falsification_review/reject/reject_02_2b6f.kif) を参照すること。撤回済みcontrolを安全性の根拠として復活させていない。
"""
    (OUT / "README.md").write_text(text, encoding="utf-8")


def write_html(groups: list[dict[str, Any]]) -> None:
    cards = [
        ("01_R2d_P2c.kif", "▲2四飛後の△2三歩", "quietな候補の生成漏れが改善したか", "+622cp。今回比較した候補内で5予算すべて上位。評価安定条件は未達。"),
        ("02_R3f_B6g.kif", "▲3六飛後の△6七角成", "旧候補との深い比較", "△6七角成-295cp、△8八飛成+468cp。差763cp。確定最善手ではない。"),
        ("03_R3e_B6g_replies.kif", "▲3五飛 △6七角成後", "自然な応手と19手詰みの確認", "▲7七角打+34cp、▲同金-770cp、▲8七金-1893cp。比較全体は未安定。"),
        ("04_R2d_B6g_replies.kif", "▲2四飛 △6七角成後", "自然な▲同金と他の応手の区別", "▲同金+1296cp、▲8七金-1513cp、▲2一飛成-2174cp。"),
    ]
    body = "\n".join(f'<article><h2>{html.escape(t)}</h2><p>{html.escape(p)}</p><p>{html.escape(v)}</p><a href="branches/{f}">ShogiHome用KIFを開く</a></article>' for f,t,p,v in cards)
    doc = f"""<!doctype html><meta charset="utf-8"><title>trap-tree coverage v2 人間レビュー</title>
<style>body{{font-family:system-ui,sans-serif;max-width:980px;margin:2rem auto;padding:0 1rem;line-height:1.65;background:#fafafa;color:#222}}article{{background:white;border:1px solid #ddd;border-radius:8px;padding:1rem 1.25rem;margin:1rem 0}}.notice{{background:#fff4d6;border-left:4px solid #d99b00;padding:1rem}}</style>
<h1>trap-tree coverage v2 人間レビュー</h1>
<div class="notice"><strong>今回の判定：INCONCLUSIVE</strong><br>候補・応手のcoverageは改善したが、6比較群の全体安定条件と人間的動機のspecificityは未検証。actual candidateへの昇格は0件。</div>
<p>今回は、以前漏れていたquietな候補と、人間が思いつきやすい理由を持つ応手を保存済み解析から確認する。評価値はすべて先手視点。＋は先手有利、－は後手有利。80Mの値は選択した比較対象または部分集合の比較で、全合法手の完全ランキングではない。Human Policyは使用していない。</p>
<p>▲7九金の2枝では、通常エンジンがその直後から19手詰みを検出した。19手には△8八飛成を含む。研究上は採用するが、独立証明による最短手数保証ではない。</p>
{body}<h2>既存reject</h2><p>明白な悪手3例は引き続きreject。<a href="../tactical_falsification_review/README.md">既存一覧</a>から確認できる。</p>"""
    (OUT / "index.html").write_text(doc, encoding="utf-8")


def main() -> None:
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUT))
    args = parser.parse_args()
    OUT = Path(args.output)
    render(*load())


if __name__ == "__main__":
    main()
