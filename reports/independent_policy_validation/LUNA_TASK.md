# Luna向け：凍結仕様に従う取得・保存・評価配線

研究判断は `SAMPLING_PLAN.md` と `config/independent_policy_validation.yaml` が正。
モデル・集合・係数・判定基準を変更しない。以下は定型実装の境界として切り出す。

1. PublicClientを再利用し、固定team pages 2/3/4から非重複参加者のfocal listを確定する。
2. 全focalの指定期間realTime最大12局を逐次取得し、以前の両参加者とgame IDを除外する。
3. 独立のaccept hash順で両参加者6局上限・合計300局上限を適用。合法性を検証する。
4. 全体の採否確定・dataset hash封印を終えるまで予測スコアを出さない。
5. load_frozenで既存統計と係数を読む。新標本でPolicy初期化・fit・選択を行わない。
6. 規定7集合の支持数・両参加者数・手番側プレイヤー数・校正・通常指標を集計する。
7. JSON/HTML・取得記録を保存。raw/SQLite/十分統計/除外IDは公開しない。
8. Astraの結果解釈後checkpointをpushしSTOP。

同定・除外・集計の意味が不明な場合、仕様を自分で変えずAstraへ返す。
今回の続行では既存関数を直接再利用する最小の実行adapterを用い、汎用CLIやUI改造は行わない。
