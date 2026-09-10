# tactical falsification v2 人間レビュー一覧

Astraのv2研究結果を盤面で確認するための資料です。研究判断・数値・分類は変更していません。

本番での自動除外への移行判断：**INCONCLUSIVE**。Human Policyは今回使用していません。

| 項目 | 何を調べる局面か | 調べる指し手 | 注目する応手 | ゲートの結果 | 研究上の扱い | KIF |
|---|---|---|---|---|---|---|
| 飛車取りが罠になる応手を誤除外しないか | 飛車取りが罠になる応手を誤除外しないか | ▲７七角打 | △２四歩(23) | 候補手を除外していない | 暫定的により良い対照例。奇襲候補ではない | [23ply_bishop_drop_rook_trap.kif](controls_provisional/23ply_bishop_drop_rook_trap.kif) |
| 自然な金の取り返しを安全性根拠にできるか | 自然な金の取り返しを安全性根拠にできるか | △６七角成(45) | ▲６七金(78) | 候補手を除外していない | 保留。安全性根拠には数えない | [22ply_horse_entry_gold_recapture.kif](controls_borderline/22ply_horse_entry_gold_recapture.kif) |
| 提案された飛車の捨て駒が成立するか | 提案された飛車の捨て駒が成立するか | ▲２二飛成(26) | △２二銀(31) | 候補手を除外した | 研究上採用しない | [user_rook_sacrifice.kif](diagnostic_hypotheses/user_rook_sacrifice.kif) |
| ▲８二歩打で特定の受けだけが必要か | ▲８二歩打で特定の受けだけが必要か | ▲８二歩打 | △８六桂打 | 候補手を除外していない | 研究上採用しない。△８六桂だけを前提にしない | [user_pawn_drop_followup.kif](diagnostic_hypotheses/user_pawn_drop_followup.kif) |

## 旧reject 3例

前回の明白な悪手3例（△３二銀を含む）は、新しい解析をせず、引き続きrejectの回帰確認として参照します。

- [△３二銀：除外例1](../tactical_falsification_review/reject/reject_01_3a3b.kif)
- [除外例2](../tactical_falsification_review/reject/reject_02_2b6f.kif)
- [除外例3](../tactical_falsification_review/reject/reject_03_8h4d.kif)

以前の▲３三角成・△７七角成の2例は、候補手以前の進行に不自然な評価損・未処理戦術が確認されたため、安全性を裏付ける対照例から撤回済みです。既存KIFは削除していません。

100kの数値は選択した応手同士の比較であり、全合法応手の100kランキングではありません。23手目局面の▲７七角打は旧17手目の▲７七角とは別の角打ち進行です。
