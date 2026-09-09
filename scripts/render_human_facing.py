"""Regenerate human-facing text from sealed existing artifacts; no model/engine calls."""
from __future__ import annotations
import html
import json
from pathlib import Path
from surprise.human_descriptions import (HUMAN_DESCRIPTIONS, classification_sentence,
    freeze_sentence, support_sentence, abstain_sentence, probability_difference_sentence,
    feature_set_sentence)

ROOT = Path(__file__).resolve().parents[1]
CAL = ROOT / "reports/response_calibration"
INDEP = ROOT / "reports/independent_policy_validation"


def readable_kif(path: Path, case: dict) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines:
        if "[diagnostic_counterexample; NOT an accepted surprise]" in line:
            out.extend(["* 【奇襲手としては除外済みの検査用の指し手】",
                        "* この指し手は奇襲手の候補ではない。",
                        "* 人間の応手予測モデルが明白な応手を適切に扱えるか確認するために残している。"])
            if case.get("candidate_move") == "3a3b":
                out.append("* この局面では、角を取る明白な応手がこの指し手を咎める。")
        elif "[control; NOT an accepted surprise]" in line:
            out.extend(["* 【通常の指し手に対する予測を確認するための指し手】",
                        "* この局面は、補正後の応手予測が通常の序盤局面で不自然になっていないか確認するために使っている。"])
        elif "reach=" in line and "exact_support=" in line:
            support = case.get("policy_exact_support")
            out.append("* " + support_sentence(support))
        elif "abstain=true" in line or "calibration=exploratory_only" in line:
            out.append("* " + abstain_sentence())
        elif "MODEL ONLY:" in line:
            out.append("* 以下の確率・評価値は研究中のモデルと既存解析による参考値であり、実際の人間がその確率で指すことを確認した値ではない。")
        elif "この応手が該当する特徴の集合：" in line or "response_sets:" in line:
            value = line.split("：", 1)[1].strip() if "：" in line else line.split(":", 1)[1].strip()
            out.append("* この応手の種類：" + feature_set_sentence(value))
        elif "Human Policy old=" in line:
            old, new = line.split("old=", 1)[1].split(" new=", 1)
            out.append(f"* 人間の実際の選択率と比較するための、補正前のモデル確率：{old}。補正後のモデル確率：{new}。")
        elif "cached 10k engine_eval=" in line:
            out.append(line.replace("cached 10k engine_eval=", "既存の10kノード解析による応手の評価値：").replace("; obvious=", "。この応手が候補手を明確に咎める応手か："))
        elif "good replies:" in line:
            out.append("* この応手が十分に良い応手に該当するか：" + line.split(":", 1)[1])
        elif "features:" in line:
            out.append("* この応手について保存している特徴の詳細は、機械可読JSONに記録している。")
        elif "Response calibration review" in line:
            out.append("# 応手予測の検証レビュー")
        else:
            out.append(line)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def render_review() -> None:
    review = json.loads((CAL / "review.json").read_text(encoding="utf-8"))
    parts = ["<!doctype html><html lang='ja'><meta charset='utf-8'><title>人間向け応手確率の検証レビュー</title>",
             "<style>body{font-family:system-ui;max-width:1100px;margin:2em auto;padding:1em;line-height:1.7}article{border:1px solid #ccc;padding:1em;margin:1em 0}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:.4em}.note{background:#fff8dc;padding:1em}</style>",
             "<h1>人間の実際の選択率とモデル予測の比較</h1>",
             "<p class='note'>このページは既存のreview.jsonとmetrics.jsonから表示だけを再生成した。モデル、係数、指標、分類、候補選抜は変更していない。</p>",
             f"<p>{freeze_sentence()}</p>",
             "<h2>特徴ごとにまとめた相手の応手</h2><p>captureやrecaptureなど、各応手がどの特徴集合に該当するかを比較している。</p>"]
    for case in review["cases"]:
        cls = case["classification"]
        responses = case.get("responses", [])
        rows = "".join(f"<tr><td>相手の応手</td><td>{r.get('previous_probability',0):.1%}</td><td>{r.get('human_probability',0):.1%}</td><td>{html.escape(feature_set_sentence(','.join(r.get('response_sets',[]))))}</td><td>{html.escape(str((r.get('result') or {}).get('score_cp', '不明')))}</td></tr>" for r in responses)
        parts.append(f"<article><h2>{html.escape(classification_sentence(cls, case.get('candidate_move')))}</h2>"
                     f"<p>元の局面のSFEN：<code>{html.escape(case.get('parent_sfen',''))}</code></p>"
                     f"<p>調べている指し手：<code>{html.escape(case.get('candidate_move',''))}</code>。{html.escape(support_sentence(case.get('policy_exact_support')))}"
                     f"{html.escape(abstain_sentence())}</p><p><a href='../../{html.escape(case['export_kif'])}'>ShogiHomeで確認するKIF</a></p>"
                     f"<table><tr><th>応手</th><th>補正前のモデル確率</th><th>補正後のモデル確率</th><th>応手の特徴</th><th>既存解析の評価値</th></tr>{rows}</table></article>")
    (CAL / "review.html").write_text("\n".join(parts) + "</html>", encoding="utf-8")

    md = ["# 今回の結論", "", "## 今回は何を調べたか", "", "既存の応手予測モデルが、特徴ごとの人間の指し手傾向をどのように予測しているかを、保存済みの検証結果で確認した。", "", "## 何が分かったか", "", "この文書は表示を読みやすくするための受け渡し資料であり、モデルや数値を再計算していない。", "", "## まだ何が分かっていないか", "", "人間の実際の選択率を新たに取得した確定結果、奇襲手としての採否、応手予測モデルの改善効果は、この資料だけでは確定していない。", "", "## 人間に確認してほしい局面・指し手", ""]
    for case in review["cases"]:
        md.append(f"- {classification_sentence(case['classification'], case.get('candidate_move'))}（{case.get('candidate_move')}）。{support_sentence(case.get('policy_exact_support'))}")
    md += ["", "## 次の段階へ進んでよいか", "", "モデル変更や追加実験へ進む判断は、表示確認後に研究担当が行う。"]
    (CAL / "REVIEW.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    for case in review["cases"]:
        readable_kif(ROOT / case["export_kif"], case)


def render_independent() -> None:
    data = json.loads((INDEP / "metrics.json").read_text(encoding="utf-8"))
    handoff = json.loads((INDEP / "ASTRA_HANDOFF.json").read_text(encoding="utf-8"))
    sets = handoff["important_numbers"]["response_sets"]
    parts = ["<!doctype html><html lang='ja'><meta charset='utf-8'><title>独立検証の人間向け報告</title>",
             "<style>body{font-family:system-ui;max-width:1100px;margin:2em auto;padding:1em;line-height:1.7}section{margin:2em 0}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:.4em}.note{background:#fff8dc;padding:1em}</style>",
             "<h1>新しい検証データでの人間応手予測の独立確認</h1>",
             "<p class='note'>新しい独立標本でも以前の確率補正による相対的改善は再現した。しかし、取り返し・駒得回収の確率は依然として約20ポイント低く予測されている。そのため、次の小規模な奇襲手探索へは進まない。</p>",
             f"<p>{freeze_sentence()}</p><p>対象は新しい270局、250人の識別可能なアカウント、予測対象6,501着手。新データでの再fit、モデル選択、エンジン解析、候補探索は行っていない。</p>",
             "<p>NLL（実際に選ばれた手へ低い確率を与えるほど悪化する指標）、Brier score（予測確率と実際の選択結果との二乗誤差）、ECE（予測確率と実際の選択率とのずれをまとめる指標）を保存済みの数値から表示している。</p>",
             "<h2>取り返し・駒得回収の実際の選択率とモデル予測</h2><p>実際の選択率は、その応手集合に合法手がある局面で実際に選ばれた割合。モデル予測は、同じ機会局面で補正モデルが集合全体へ割り当てた確率の平均。差は実際の選択率からモデル予測を引いたパーセントポイント。</p>",
             "<table><tr><th>応手の対象</th><th>機会局面数</th><th>実際の対局で選ばれた割合</th><th>モデルが予測した割合</th><th>実際の割合−予測の差</th></tr>"]
    for key, label in (("recapture", "取り返しが可能な局面"), ("material_recovery", "駒得を回収する応手が可能な局面")):
        item = sets[key]
        parts.append(f"<tr><td>{label}</td><td>{item['opportunity_count']}</td><td>{item['display']['observed_percent']:.1f}%</td><td>{item['display']['predicted_percent']:.1f}%</td><td>{item['display']['underprediction_percentage_points']:.1f}ポイント</td></tr>")
    parts.append("</table><p>取り返しでは実際の選択率83.6%に対して予測64.1%で19.5ポイント低く、駒得回収では実際の選択率71.5%に対して予測50.9%で20.6ポイント低い。</p>")
    for mode, value in data.items():
        parts.append(f"<section><h2>{html.escape(mode)}の検証結果</h2><p>この比較は、凍結前に決めたモデルを新しい検証データへ適用した結果である。</p><table><tr><th>比較するモデル</th><th>NLL</th><th>Brier score</th><th>上位1/3/5手の一致率</th><th>ECE</th></tr>")
        for name in ("old", "new"):
            m=value[name]["overall"]
            parts.append(f"<tr><td>{'比較対象の旧モデル' if name=='old' else '検証前に決めて変更していないモデル'}</td><td>{m.get('nll','不明'):.4f}</td><td>{m.get('brier','不明'):.4f}</td><td>{m.get('top1','不明'):.3f} / {m.get('top3','不明'):.3f} / {m.get('top5','不明'):.3f}</td><td>{m.get('ece','不明'):.4f}</td></tr>")
        parts.append("</table></section>")
    (INDEP / "report.html").write_text("\n".join(parts)+"</html>", encoding="utf-8")
    (INDEP / "REVIEW.md").write_text("# 今回の結論\n\n独立した新しい人間棋譜標本でも、以前の確率補正による相対的な改善は再現した。一方、取り返しと駒得回収の応手は実際の選択率を約20ポイント低く予測した。Human Policyを奇襲手の昇格判定に使えるほど十分に信頼できるとは、まだ判断していない。\n\n## 今回は何を調べたか\n\n研究判断、モデル、係数、応手集合、判定基準を検証前に決めたまま、新しい270局（識別可能なアカウント250人、予測対象6,501着手）へ適用し、旧モデルと検証前に決めて変更していない補正モデルの相対比較を確認した。新しい標本を使った再fitやモデル選択は行っていない。\n\n## 何が分かったか\n\n相対的な改善は再現した。取り返しが可能な311局面では、実際の対局で取り返しが選ばれた割合は83.6%だった。一方、モデルが取り返しに該当する応手全体へ割り当てた確率は64.1%で、実際の選択率を19.5ポイント低く予測した。\n\n駒得を回収する応手が可能な470局面では、実際にその応手が選ばれた割合は71.5%だった。モデルがその応手集合へ割り当てた確率は50.9%で、実際の選択率を20.6ポイント低く予測した。ここでいう駒得回収は既存の代理条件であり、安全な駒得の証明ではない。\n\n## まだ何が分かっていないか\n\n相対的な改善が確認できたことは、任意の応手集合の確率が十分に校正されたことや、個別の奇襲後局面で人間の応手確率を正確に推定できることを意味しない。今回の標本は一般人口の無作為標本ではなく、同じ局面の実例が少ない着手の割合も真の未知局面検出率ではない。\n\n## 人間に確認してほしい局面・指し手\n\n既存の△3二銀は奇襲手として除外されている。明白な▲2二角成で角を取られるためであり、Human Policyの信頼性が低いから保留されているのではない。このKIFはモデル診断用の検査資料として確認する。\n\n## 次の段階へ進んでよいか\n\nNO。取り返しと駒得回収の応手集合に約20ポイントの残存する過小予測があり、Human Policyの判定保留を解除する根拠が得られていない。現在のHuman Policyを使った次の小規模な奇襲手探索と、P_goodによる候補昇格には進まない。\n", encoding="utf-8")


if __name__ == "__main__":
    render_review(); render_independent()
