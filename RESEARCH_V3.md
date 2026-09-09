# 研究checkpoint v3 — 2026-09-09

## 現在の判断

**大量scan・deep拡大・Vast.aiへ進まない。**
Human Policyの平均予測性能は改善したが、駒取り集合の確率校正に失敗し、明白角取りを見逃すfalse positiveを再現した。
次は独立標本での自然応手集合の校正と、疎な局面での予測保留を検証する。

## 最新成果物の正しい読み順

1. [テラショックseed検討](reports/terashock_seed_audit/analysis.md)：0–12plyを主universe。0–16は支持のある追加枠。20は集計のみ。
2. [人間sampling / reach](reports/human_pilot/analysis.md)：612対局、457名、最大12対局/人。一般人口代表標本ではない。
3. [Human Policy修正版評価](reports/human_policy_v2/analysis.md)：game/time/strict-player split、6 baseline。
4. [小規模E2Eと反例](reports/human_e2e/analysis.md)：4親局面、144候補、代表6件、10k、6 KIF。

`reports/human_pilot/policy_metrics.json` はsampling/splitのhash依存を含む**旧診断**。
現行性能は必ず `reports/human_policy_v2/` を使う。修正経緯は `reports/human_pilot/SPLIT_CORRECTION.md`。
過去のpass/reach pilotも履歴として保存し、現行標本・予測成績へ混ぜない。

## データ責務

- Terashock：探索元の供給。book枝数/countは人間頻度ではない。book評価も現在engine評価とは別。
- 人間棋譜：reach・実着手分布・Human Policy教師。未観測book局面は母集団reach unknown。
- 既存YaneuraOu/水匠5/cache：少数親の現在評価、候補・応手評価。交換・再構築していない。

700Tのraw/抽出DBはローカル保管。明示的再配布ライセンス未確認。MITの新ペタショックとは区別。
raw人間棋譜・個人識別子付きDBも公開しない。GitHub checkpointの公開範囲と再開手順は `PUBLIC_CHECKPOINT.md`。

## 再現（既存環境）

```bash
.venv/bin/pytest -q
.venv/bin/python -m surprise.human_data           # 成功済APIレスポンスを再利用
.venv/bin/python -m surprise.book_seeds           # book edgeのみ、上限20の構造集計
.venv/bin/python -m surprise.human_policy         # 修正版固定splitの評価
.venv/bin/python -m surprise.human_review         # held-out予測点検、engineなし
.venv/bin/python -m surprise.small_e2e            # 既存4局面のcheckpoint/cache再利用
PYTHONPATH=. .venv/bin/python scripts/render_human_results.py
```

上記は既存条件の再現用であり、追加取得・追加scanの勧めではない。
設定・データを変える場合は新outputと明示的研究計画を用いる。
次回は候補数を増やす前に、駒取り確率8.1%予測 vs 21.6%実測という失敗を解消できるか検証する。

## ShogiHome

LunaのAppImage/起動スクリプトは保存。exporterの分岐開始手数のバグを回帰テスト付きで修正し、
Human Policy確率/P_good/human_gapコメントを追加。旧書き出し済みKIFは上書きしていない。
新出力 `exports/human_e2e/` は全分岐の合法性・手数を再パース検証済み。GUI目視はユーザー確認が必要。
