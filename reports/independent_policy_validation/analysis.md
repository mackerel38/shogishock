# 凍結Human Policyの独立確認 — 2026-09-09

## 判断：次の小規模奇襲探索へ進めてよいか → **NO**

**集合確率の相対的な改善は独立標本でも再現した。しかし、取り返し・回収集合の校正不足も再現した。**
新棋譜を使った再fit・再選択・閾値変更は0。新candidate scan / engine / deep / Vast.ai / KIF候補生成も0。
凍結したabstentionを維持し、P_goodによる候補昇格へ進めない。

これは「改善の再現に失敗した」という結論ではない。
取得前から区別した **相対改善の再現** と **自然応手集合の十分な校正** のうち、前者は支持、後者は未達。
未達に合わせた新しい数値閾値を後付けしたのではなく、既存の保留を解除する根拠が得られなかった。

## 取得前freezeと独立性

- 元checkpoint：742432c1b8e26664c7cae9fb560ab55a6f608e40。
- 取得前計画・freezeを先にGitHubへ保存：6ec953a0ecb4f26761fadb1084e4f95780a2d50a。
- freeze時刻：2026-09-09 06:20:37 UTC。
- 標本封印時刻：2026-09-09 06:33:56 UTC。予測値は封印後に初めて計算した。
- 主モデル：旧time-train統計＋shrinkage k=5＋旧timeの種別tilt係数。
- 比較対象：同じtime-train統計の旧hard-thresholdモデル（support 2、alpha5、temperature1）。
- 旧player/game snapshotも保存済み係数のまま感度分析。新標本でwinnerを選んでいない。

[frozen_model_fingerprint.json](frozen_model_fingerprint.json) にコード・十分統計・split・元入力・
集合定義・係数・取得計画のhashを記録した。旧統計を取得前にシリアライズし、新標本の評価時は
`load_frozen`で復元するだけ。旧/新比較用のモデルを新データから構築していない。
freeze文書内のvalidation_completed=false等は取得前状態であり、現在の判断は [decision.json](decision.json)。

旧612局の採用標本だけでなく、却下棋譜・旧reach試作・raw取得済み棋譜を含む
**614アカウント・1,283対局ID**を除外リストに固定した。
採用された新標本との交差は両参加者・対局とも **0**。独立性は既知アカウントの非重複として検証。
同一人物の別アカウント、共通知識、チーム内交流などの潜在依存まで排除したとは主張しない。
新規取得・未使用棋譜だが全てがfreeze後に指された前向き標本ではなく、過去棋譜の未使用標本である。

## Sampling結果

[取得前sampling plan](SAMPLING_PLAN.md) と [dataset summary](dataset_summary.json) が詳細。
Luna向けの定型取得・保存・集計仕様は [LUNA_TASK.md](LUNA_TASK.md) に切り出し、今回の続行は
既存PublicClient/ReachDBと最小adapterで実行した。独立性監査・評価解釈はAstraが担当。

|項目|結果|
|---|---:|
|公式team pages 2/3/4のチーム数|45|
|重複除去後frameアカウント|1,185|
|旧参加者等の除外後eligible|275|
|事前固定focal|160（全員分取得完了）|
|取得レコード / uniqueゲーム|770 / 743|
|採用リアルタイム対局|270|
|distinct players|250|
|旧プレイヤー / 旧ゲーム重複|0 / 0|
|correspondence採用|0|
|予測対象着手|6,501（従来と同じ0–24ply）|
|exact positions|5,252|

1人あたり棋譜数は中央値1、最大6。分布（局数:人数）は1:146、2:44、3:10、4:8、5:8、6:34。
rated141 / casual129。対局時rating540観測、欠損0、最小770・中央値1542・最大2306。
rating帯は<1200が69、1200–1599が253、1600–1999が196、>=2000が22。
月別は2026年6月76局、7月64局、8月75局、9月55局。
API clock.totalTimeによる参考区分は<180秒14局、180–599秒44局、600–1799秒155局、>=1800秒57局。
これは実際の消費時間ではない。clock/byoyomi/increment/periodsの元の集計もJSONに保存した。

除外理由は重複可：人間属性不明94、非平手開始19、旧参加者139、明示BOT/AI162、
参加者6局上限69、未完了扱い2、着手なし1。合計300局上限には達しなかったが、追加取得はしていない。
BOT/AI属性がないことは、隠れたAI利用がない証明ではない。

公式API仕様・利用条件は取得前に確認：[API案内](https://lishogi.org/developers)、
[規約](https://lishogi.org/terms-of-service)、
[公式API仕様](https://raw.githubusercontent.com/WandererXII/lishogi/master/ui/@build/static/assets/doc/lishogi-api.yaml)。
逐次・2秒以上間隔・1応答8MB上限を守り、API障害によるretryや枠拡張はなかった。
raw、SQLite、十分統計、除外IDは公開しない。規約はraw再配布の包括許諾とは扱っていない。

## 主モデル：response-set校正

集合定義は変更なし。material_recoveryは既存の静的・即時取り返しheuristicで、安全な駒得の証明ではない。
集合は重複可能。nは集合に合法手が一つ以上ある観測数。playersはその観測の対局の両参加者の和集合、
moversは実際にその局面で手番だった参加者の和集合。

|集合|n|対局|players / movers|実測|旧予測|凍結補正予測|Brier 旧→補正|補正ECE|
|---|---:|---:|---:|---:|---:|---:|---|---:|
|capture_any|2962|265|247 / 242|21.64%|8.23%|19.80%|0.1457→0.0830|0.0474|
|captures_candidate|833|238|231 / 203|51.86%|15.26%|43.96%|0.3357→0.1394|0.1311|
|recapture|311|157|178 / 143|83.60%|20.68%|64.11%|0.5444→0.1498|0.2008|
|material_recovery|470|155|179 / 145|71.49%|17.05%|50.91%|0.4939→0.2147|0.2058|
|high_value_capture|751|187|203 / 178|25.03%|8.03%|19.72%|0.1796→0.1162|0.0608|
|pawn_contact_capture|260|142|161 / 126|69.23%|23.21%|53.64%|0.4159→0.2270|0.1660|
|promotion|1730|261|246 / 214|9.19%|3.39%|6.81%|0.0822→0.0753|0.0248|

旧来4集合の平均Brierは **0.37994→0.14673**。
paired game bootstrap 300回による差の参考95%区間：
capture [-0.0713,-0.0542]、candidate capture [-0.2152,-0.1767]、
recapture [-0.4328,-0.3595]、recovery [-0.3130,-0.2431]。
これらは相対改善を支持するが、absolute calibrationの証明ではない。
同じ参加者・チーム間の依存を完全に補正した母集団CIではない。

事前指定のplayer-equal game weightingでも、recaptureは実測85.20%・予測64.56%、
recoveryは72.99%・50.45%。少数の頻繁なプレイヤーだけで残存誤差が生じたとは説明しにくい。
全10bin、重み付け感度、両側プレイヤー数、通常指標は [metrics.json](metrics.json)、
可視化は [report.html](report.html)。

## 通常予測性能・support別

|time主モデル|旧|凍結補正|
|---|---:|---:|
|NLL|2.9692|2.8685|
|multiclass Brier|0.8927|0.8635|
|top1|19.01%|21.32%|
|top3|34.33%|36.78%|
|top5|42.89%|44.95%|
|top-label ECE|0.0260|0.0402|

NLL/Brierの改善とtop-label ECE改善は同一ではない。前回同様、ECEの小ささだけで安全性を判断しない。

|time support slice|n|NLL 旧→補正|
|---|---:|---|
|exact>=2|1279|1.8550→1.8371|
|fallback <2|5222|3.2421→3.1211|
|support=0|5004|3.2452→3.1447|
|support=1|218|3.1715→2.5777|

低支持割合80.33%。これはOODの代理でありOODを完全に検知した率ではない。
abstainは凍結方針どおり100%を維持。新標本に合わせてsupport閾値を動かしていない。

固定sensitivityモデルも相対gateを通過した：
- playerのcapture一括tilt：NLL2.9812→2.9314、Brier0.8960→0.8805。
  ただしcapture全体を29.16%と過大予測し、recaptureは48.81%と過小予測。promotion Brierも悪化。
- gameの種別tilt：NLL2.9605→2.8573、Brier0.8925→0.8627。
  recapture65.20%、recovery53.20%と残存過小評価がある。

同一新標本で固定snapshotを比較した感度分析であり、新しいgame/time/player splitではない。
新標本で良かったsnapshotへ乗り換える選択は行っていない。

## 旧exploratory結果との比較

|time種別tilt|旧実測 / 予測|独立標本実測 / 予測|
|---|---|---|
|capture_any|21.58% / 19.15%|21.64% / 19.80%|
|captures_candidate|50.00% / 42.30%|51.86% / 43.96%|
|recapture|85.71% / 65.81%|83.60% / 64.11%|
|material_recovery|73.57% / 48.13%|71.49% / 50.91%|
|high_value_capture|28.03% / 22.90%|25.03% / 19.72%|

改善と未解消の欠陥の両方が似た形で再現した。
旧標本にはcorrespondenceが含まれ、新標本は除外されている。旧全標本rating中央値1706に対し今回は1542。
team枠、期間、rated/casual比も変わっており、旧新標本間の差を純粋なモデル効果とは解釈しない。
同一新標本内の旧モデル対補正モデル比較が今回の主な対照である。

## Sanity / verification / STOP

△3二銀は既存同一探索形式のobvious_reply_neutralizes=trueと除外理由だけを検証するsanity fixture。
Human Policyの角取り確率を再計算・最適化していない。新しいKIFやactual candidateは生成していない。

取得前・評価前・評価後にfreeze hashを照合。dataset封印のhashも評価後一致。
measurement_seal.jsonは結果と実行adapterのhashを固定し、同じ標本の再評価をデフォルトで拒否する。
公開source-only cloneでもテストを検証し、rawや認証情報を除外してcheckpointする。

```bash
# 状態検証のみ。既に封印済みなら新しい取得・評価をしない。
.venv/bin/python -m surprise.frozen_policy
.venv/bin/python -m surprise.independent_validation acquire
.venv/bin/python -m surprise.independent_validation measure
PYTHONPATH=. .venv/bin/python scripts/render_independent_validation.py
.venv/bin/pytest -q
```

同一教師・確認データの再現にはprivate snapshotが必要。公開GitHubだけからrawを復元できるとは主張しない。
この新標本は今後既知の確認標本であり、改良後の独立最終testとして再利用しない。

人間レビューで確認してほしい点：
1. 相対的な改善は再現した一方、recapture/recoveryに約20ポイントの誤差が残ること。
2. 全体captureの良好な平均で、重要なsubsetの誤差を隠していないこと。
3. 既存のabstentionを維持して次のscanへ進まない判断が妥当か。

次の研究課題をこの標本を見ながら実装しない。まずこの報告を人間レビューへ渡す。
**GitHub commit + push後STOP。次の候補探索・再学習・追加取得は行わない。**
