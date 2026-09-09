# Human Policyのheld-out検証 — 2026-09-09

## 判断

階層型MVPは単純baselineよりNLL/Brierを改善した。しかし **このまま大量scanのP_good推定には使わない**。
全体のtop-label校正は良く見える一方、駒取りという応手集合への確率を大きく過小評価している。
小規模E2Eでも、明白な角取りへ約3%しか確率を置かない反例が出た。
[端から端の実例](../human_e2e/analysis.md) が今回の主要な否定結果。

## モデルと検証設計

全モデルは人間実着手のみから学習。bookの評価・着手・countは教師にしていない。
合法手上で正の確率を定義し、exact/prefixはpseudo-count 5で平滑化。

- uniform: 合法手一様。
- popularity: 手番別USI着手頻度を合法手へ制限。
- prefix: 同一序盤手順の実着手分布、疎な場合popularity。
- exact: transposition統合局面の実着手分布、popularityで平滑化。
- behavior: 駒種・打ち・取り・成・歩接触取り・後退の結合classの選択/利用機会比とpopularityを半々に混ぜる。
- hierarchical: exact countが閾値以上なら実測分布をbehavior priorで平滑化、それ未満はbehavior fallback。

validationで閾値2/5/10、temperature 0.75/1/1.25/1.5を比較。hierarchicalは全splitで閾値2、temperature1を選んだ。
testはモデル・閾値選択には使っていない。大型NN、kNN、追加ライブラリは導入していない。
behaviorは仮説検証用の簡単な頻度モデルで、各要因の因果効果を同定するものではない。

最初の実装でsamplingとsplitに同じhashを使う依存が見つかったため、用途別domain separationで修正した。
旧結果は保存し、修正後の固定分割だけを以下に報告する。詳細は [修正記録](../human_pilot/SPLIT_CORRECTION.md)。
実装修正を挟んだ探索的検証なので、独立した最終確認標本での成績とは主張しない。

|split|train / validation / test対局|purge|train–test共通プレイヤー|
|---|---|---:|---:|
|game-group|357 / 138 / 117|0|106|
|time-based|367 / 122 / 123|0|21|
|strict player-group|274 / 21 / 26|291|0|

player-groupは双方のプレイヤーが同じ群に割り当てられたゲームだけを使い、群跨ぎ対局をpurge。
全splitで同一対局のtrain/test混在なし。timeは同時刻の境界も分けない。
position単位のランダム分割は使っていない。

## Held-out結果

NLLはnats、Brierはmulticlass sum-squared、ECEは10等幅binのtop-label ECE。いずれも着手観測単位の平均。

|time test（123対局・2966着手）|NLL↓|Brier↓|top1|top3|top5|ECE↓|
|---|---:|---:|---:|---:|---:|---:|
|uniform|3.6020|0.9697|1.79%|9.84%|16.39%|0.0138|
|popularity|3.3728|0.9539|13.28%|28.19%|37.93%|0.0686|
|prefix|3.1656|0.9145|17.67%|32.74%|41.44%|0.0448|
|exact|3.1489|0.9121|18.24%|33.68%|42.28%|0.0480|
|behavior|3.1477|0.9373|17.43%|32.70%|42.52%|0.0774|
|hierarchical|2.9113|0.8877|20.30%|36.82%|46.22%|0.0346|

|split|popularity NLL|exact NLL|hierarchical NLL / Brier|hierarchical top1 / top3 / top5|hierarchical ECE|
|---|---:|---:|---|---|---:|
|game（2670着手）|3.3020|3.0310|2.8206 / 0.8745|21.72 / 38.54 / 46.67%|0.0401|
|player（625着手）|3.3290|3.1048|2.8768 / 0.8770|24.32 / 37.76 / 46.08%|0.0779|

全baseline・各slice・bin値は `policy_metrics.json`。[reliability図](calibration.html) も生成した。
uniformのECEが小さくても予測は有用でない。ECEだけで採否を決めない。
hierarchical−popularityのNLL差はgame -0.4814、time -0.4614、player -0.4523。
固定game-cluster bootstrap参考95%区間は順に[-0.5415,-0.4263]、[-0.5125,-0.4061]、[-0.5513,-0.3538]。
残存プレイヤー依存をカバーする母集団CIではない。

## Exact / fallbackとbook内外

|time test slice|着手数|NLL|top1|ECE|
|---|---:|---:|---:|---:|
|exact support >=2|615|1.7561|48.62%|0.0688|
|fallback|2351|3.2135|12.89%|0.0283|
|完全未知exact|2213|3.2261|12.61%|0.0248|
|12ply book universe内|877|2.1995|37.06%|0.0575|
|12ply book universe外|2089|3.2102|13.26%|0.0262|

book内の方が予測しやすいが、これは頻出・浅い局面との交絡を含み、book利用の因果効果ではない。
特に奇襲候補の後はexact支持がなくなりやすい。元局面の高reachから候補後のモデル精度を保証できない。
strict-playerのexact-supported sliceは135着手、ECE0.1363。全体ECEだけで不確実性を隠さない。

## 集合確率の校正による反証

固定time testで、合法な駒取りが1手以上存在する1,376局面を後から診断した。
実際に駒取りしたのは297/1376=21.58%。モデルが駒取り集合へ置いた平均確率は8.06%。
この約13.5ポイントの不足は、P_good用途で重要な条件付き確率の問題を示す。
これはtop-label ECE0.0346だけでは見えなかった。

歩接触を取れる92局面では68回（73.91%）取っていた。成れる750局面では81回成り、
後退可能1,980局面では111回後退した。複数signalは重複可。
これらはこの標本・定義に条件付けられた観測比であり、無条件の人間ルールではない。
各eventの予測確率・Brier・reliabilityは `behavior_calibration.json` に保存。

## 次の判断

事前の最低条件を満たしたため4局面だけのE2Eを行ったが、その反例により大量scanは止める。
次は、独立した人間標本で駒取り・取り返し・駒回収の条件付き校正を確認し、
exactが疎な局面へのfallbackが自然応手を過小評価する原因を調べる。
単純USI priorと行動classの固定混合は、局面の戦術的な意味を十分表現していない。
未知・低支持局面ではP_goodを自信のある一点推定として昇格に使わず、abstain/要レビューにする。
P_goodは任意の応手集合への確率なので、top1校正だけで十分とはいえない。
