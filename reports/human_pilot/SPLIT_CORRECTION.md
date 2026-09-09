# 2026-09-09 split依存の修正

最初の `reports/human_pilot/policy_metrics.json` は分割診断として保存し、現行Human Policyの判定には使わない。
同じhash(seed+player_id)をfocal抽出の昇順とplayer-group分割に使ってしまい、
focal160名がtrain149 / validation8 / test3に偏った。
ゲームcapのhash順とgame splitにも同種の依存があった。

性能閾値を下げたり、成功するsplitを探したりするのではなく、用途別domain separationを追加する。
分割に使う文字列を `seed + ':heldout-v2:' + mode + ':' + id` に固定。
人間データ・book universe・モデル・評価閾値は変更しない。time splitは元から日時順なので影響しない。
修正後出力は `reports/human_policy_v2/`、splitは `data/human_raw/human_pilot/splits_v2.json`。
旧結果を削除・上書きしない。

最初の結果を見てから実装修正した探索的実験であり、完全に手つかずの確認用datasetによる検証とは主張しない。
大量scan可否には、さらに独立した確認標本が必要。
