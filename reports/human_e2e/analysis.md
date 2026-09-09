# 小規模E2E：成立した配線と、Human Policyの反例

## 結論

book seed → human reach注釈 → 既存engine親評価 → 全合法候補 → obvious/不成診断 →
Human Policy → 応手engine評価 → P_good/human_gap → 分岐KIF、まで小規模に実行できた。
ただし **新しい奇襲の成立は確認していない。現Human Policyを大量scanに使う価値はまだ実証できていない**。
むしろ、明白な駒得応手を過小評価して巨大human_gapを生むfalse positiveを確認した。

[先手HTML](report_sente.html) / [後手HTML](report_gote.html) / [held-out校正](../human_policy_v2/calibration.html)

## 範囲

- 700T/WCSC29の0–12ply universeと実棋譜支持の共通部分から、先後各2親局面。
- 親局面の現engine評価も確認。全4局面で奇襲側が既に300cp以上有利ではなかった。
- 全144合法候補を保存。候補後評価でhard cutoffはしない。
- 明白良応手で最終14件、不成ノイズで1件を通常昇格から除外。候補レコードは残す。
- コスト低・稀な静かな手・コスト高、という目的抽出で各側3候補を確認。passで順位づけしない。
- 6候補の全240合法応手を10kで評価。95%までに限定せず残りも評価したためcoverageは100%。
- すべて既存engine/cacheを利用。100k / 1M / 10M / Vast.aiは未使用。

Human Policyはtime splitのtrainのみで学習したvalidation選択済モデルを固定して使った。
testをE2E用に再学習していない。reachは全612ゲーム標本内の注釈。

## 元局面

初期局面からの手順を明示する。高reach順位で選んだ少数局面で、全戦型を代表しない。

- `2g2f 3c3d 7g7f`：後手用、sample reach 75/612=12.25%、現parent +136。
- `2g2f 3c3d 2f2e`：後手用、70/612=11.44%、現parent +94。
- `2g2f 3c3d 2f2e 2b3c`：先手用、59/612=9.64%、現parent +60。
- `2g2f 3c3d 7g7f 4c4d`：先手用、36/612=5.88%、現parent +204。全36合法候補を保存した。
  代表3候補は上の先手親から選ばれた。

## 代表6候補

評価値はすべて正＝先手有利。P_goodはモデル推定、human_gapは奇襲側利益の派生量。

|側・候補|reach|parent eval|candidate eval|P_good 100cp|P_good 200cp|human_gap|候補後exact支持|
|---|---:|---:|---:|---:|---:|---:|---:|
|先手 7g7f|9.64%|+60|+105|17.34%|70.82%|+266.7|16|
|先手 1i1h|9.64%|+60|-332|47.75%|55.45%|+364.9|0|
|先手 6i5h|9.64%|+60|-336|49.58%|59.85%|+401.0|0|
|後手 2b3c|11.44%|+94|+60|55.95%|93.32%|+80.8|35|
|後手 1a1b|12.25%|+136|+513|9.41%|46.56%|+685.3|0|
|後手 3a3b|12.25%|+136|+3808|3.03%|3.03%|+4050.5|1|

V_optimalは全合法応手を同じbudgetで個別探索した中の受け側最良推定値。
候補root評価とは探索地平が違うので両方を保存する。正確なゲーム理論値ではない。
E_humanは確率を掛けた通常先手視点評価の和。今回の6例は全massがCPで評価できたので確定した計算値を出せた。
一般の部分解析では未解析massを再正規化せず、P_good上下界を保存し、E_human/human_gapをnullにする実装・テストを追加した。

## 決定的なfalse positive：後手3a3b

`2g2f 3c3d 7g7f` の後に後手 `3a3b`。
先手 `8h2b+` で角を取ると+3681、`8h2b` も+3691。自然な駒回収で先手が大きく有利。
ところがHuman Policyはこの2手合計に **3.03%** しか置かず、
P_good≈3%、V_optimal=+3691、E_human=-359.5、後手human_gap≈+4050.5を出した。
これを「人間に難しい強力な奇襲」と読めば明らかなfalse positiveである。

初期のobvious診断ではroot +3808と応手後の+3681/+3691に約117–127cpの差があり、100cp基準でneutralizesに届かなかった。
全合法応手の同一形式比較ではneutralizes=trueになった。
したがって、shallow rootと明示的応手探索の差が閾値付近にあるとき、falseを確証として昇格させない工夫も必要。
今回は最終的に `obvious_reply_neutralizes` と `human_policy_ood_and_response_set_calibration_unverified` で保留。

[この反例のKIF](../../exports/human_e2e/gote_5c46af1026197c8aeb70_3a3b.kif)

## 他の実例と閾値感度

後手1a1bでは、モデルは先手7i6hへ約5.5%を置くが、応手後評価は-3072。
元の高reach局面から一手外れただけで、一般的な着手priorが戦術的意味を捉えなくなる可能性を示す。
これが本当に人間を誘うのか、単にモデルが悪いのかは未検証。香を動かすだけで勝率改善とは主張しない。

先手7g7fは普通の駒組みへの比較用例。P_goodが100cpで17.3%、200cpで70.8%と大きく変わる。
後手2b3cも200cp基準ならP_good93.3%。最善一致や厳しすぎるtoleranceだけで難しさを誇張しない。

余計な不成としてタグ付けしたのは後手 `5c46af1026197c8aeb70_2b7g`。
同じfrom/toの成との浅い差は奇襲側291cp、王手状態・先頭応手は同じ。
P/B/R限定の説明可能なheuristicであり、銀・桂・香を一律に落とさない。戦術的意味の否定証明ではないのでDBには残す。

## ShogiHome

各側3件、計6 KIFを `exports/human_e2e/` に生成。
候補、engine PV、全合法応手のHuman Policy確率、obvious signal、good判定、応手後PVを枝・コメントに含めた。
各ファイルのKIFを再パースし、全分岐の手数と合法性を検証。警告0。
Lunaのexport機能は再利用し、長い主PVの後に分岐開始手数がずれるバグだけを回帰テスト付きで修正した。
既存AppImage/起動スクリプトは変更していない。

- [先手・普通の駒組み比較](../../exports/human_e2e/sente_8e41531c4f23213c9b17_7g7f.kif)
- [先手・香移動](../../exports/human_e2e/sente_8e41531c4f23213c9b17_1i1h.kif)
- [先手・金移動](../../exports/human_e2e/sente_8e41531c4f23213c9b17_6i5h.kif)
- [後手・通常の角上がり比較](../../exports/human_e2e/gote_fa2a3aee31df970cb704_2b3c.kif)
- [後手・香移動](../../exports/human_e2e/gote_5c46af1026197c8aeb70_1a1b.kif)
- [後手・明白角取りの反例](../../exports/human_e2e/gote_5c46af1026197c8aeb70_3a3b.kif)

**KIF generated / branches validated / user visual review required**。
GUIでの画面確認は未実施。KIFは研究点検用であり、新戦法成立の認定ではない。

## 次の研究判断

大量scanへ進まない。元局面のbook universe分離は有用だが、Human Policyの集合校正の問題を解決しない。
次は駒取り・取り返し・明白な回収を含む独立検証標本、fallbackの校正、未知局面での予測保留を優先する。
モデルを大型化して今回の反例を無理に隠さない。AI評価が不利な候補をhard filterする方向にも戻らない。
全体NLLの改善、集合確率の失敗、scanへの不採用を別々の研究成果として残す。
