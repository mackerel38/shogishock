# Response-set calibration checkpoint — 2026-09-09

## 今回の問いと結論

自然な駒取り集合への確率の過小配分を、小さな学習補正で改善できるか。
**探索的held-out再評価では改善した。しかし「奇襲後に十分校正されたHuman Policy」は未達。**
取り返し・material recoveryの過小評価、未知局面への不確実性、既知角取り反例の巨大human_gapが残る。
大量scanには採用せず、全レビューケースでabstainする。actual candidateは0件。

新規取得0、engine呼び出し0、Vast.ai使用0。既存612対局の固定分割と、既存10k解析だけを利用。
旧pilot、旧Human Policy、Lunaのreview成果物は上書きしない。

## 何を変更したか

研究実装は `surprise/response_calibration.py`、研究レビューは `surprise/calibration_review.py`。
既存モデル本体・engine・NNUE・seed universe・候補ランキングは変更していない。
Lunaの `ResponseDiagnosticCache` と手動review metadata、修正済みKIF exporterを再利用した。
機能追加が研究結論に関わる範囲だけ実装し、汎用CLIやUI改造は行っていない。

集合定義・固定比較・採否条件は実行前に [PLAN.md](PLAN.md) に記録。
駒取り、直前に動いた駒の捕獲、取り返し、material recovery代理、歩接触取り、大駒取り、成りの7集合。
material recoveryは「即時の合法取り返しがない、または被害駒の静的価値が移動駒より大きい」という既存heuristic。
安全な駒得の証明ではない。victim/mover typeとvalue、即時取り返し可能性、静的gainを保存。
`candidate_was_just_exposed` は未定義をnullで明示。captures_candidateと同一視していない。
△3二銀後の角取りは、capture_any / high_value_capture / material_recoveryに入り、
captures_candidate / recaptureには入らない（直前に動いたのは銀）。この違いをテストした。

比較は既存hard thresholdモデル、連続shrinkage k=2/5/10、capture一括tilt、10係数の種別tilt。
tiltは基準確率にexp(w・feature)を掛け、全合法手で正規化する。
係数は人間の実着手から学習し、角取りを必ず選ぶ等のhard ruleはない。
種別tiltは7集合と被害駒価値・正のgain代理・即時取り返し可能性を利用。
mover type単独の効果や各featureの因果的効果は今回同定していない。

## 分割と独立性

旧修正版splitを固定。base modelはtrainだけで学習。
旧validationを新しいdomain-separated game hashでfit/selectionに分けた。
fitは係数学習、selectionは主要4集合の平均Brierによるモデル選択に使用。
selection NLLが既存より0.02超悪化するモデルは選ばない。

|split|base train対局|補正fit対局|selection対局|test対局|
|---|---:|---:|---:|---:|
|time|367|54|68|123|
|strict player|274|12|9|26|
|game|357|63|75|117|

strict playerは双方の参加者をgroupで隔離した旧分割を保持。
game/timeには旧来のtrain–test player overlapが106/21人ある。
strict playerのselectionはわずか9対局で、モデル選択の不安定さが大きい。
**旧testから今回の仮説が生まれたため、独立最終評価ではない。**
testでの再選択・fixtureに合わせた係数調整はしなかったが、研究全体の適応的再利用の限界は消えない。

## 通常予測性能と集合Brier

各分割の新モデルはselectionで選んだもの。Brierはmulticlass、主要集合Brierは4集合の単純平均。

|split|選択モデル|NLL 旧→新|Brier 旧→新|主要集合Brier 旧→新|
|---|---|---|---|---|
|time|種別tilt|2.9113→2.8021|0.8877→0.8589|0.3931→0.1633|
|strict player|capture一括tilt|2.8768→2.7743|0.8770→0.8516|0.3304→0.1860|
|game|種別tilt|2.8206→2.7262|0.8745→0.8478|0.3729→0.1344|

timeの新top1/3/5は23.06/40.29/49.26%、top-label ECEは0.0383（旧0.0346）。
全体NLL改善とtop-label ECE改善は同じではない。
strict playerは27.52/42.08/50.40%、ECE0.0530。gameは24.61/41.16/49.21%、ECE0.0510。
全6variant、validation成績、binごとの値は [metrics.json](metrics.json)。

## 応手集合の校正：time held-out

nは集合内の合法手が一つ以上存在する局面観測数。同一局面の別ゲーム出現も観測として数える。
集合は重複し、観測の棋譜内依存もある。実測率はこの標本内の条件付き比率。

|集合|n / 対局数|実測|旧予測|新予測|Brier 旧→新|新ECE|
|---|---:|---:|---:|---:|---|---:|
|capture_any|1376 / 121|21.58%|8.06%|19.15%|0.1508→0.0895|0.0489|
|captures_candidate|374 / 112|50.00%|14.66%|42.30%|0.3295→0.1441|0.1235|
|recapture|133 / 70|85.71%|20.97%|65.81%|0.5667→0.1586|0.2058|
|material_recovery proxy|227 / 72|73.57%|16.44%|48.13%|0.5254→0.2609|0.2638|
|pawn_contact_capture|92 / 55|73.91%|22.13%|54.02%|0.4617→0.2487|0.2055|
|high_value_capture|314 / 90|28.03%|9.08%|22.90%|0.1983→0.1315|0.0657|
|promotion|750 / 118|10.80%|3.57%|7.16%|0.0969→0.0871|0.0392|

**駒取り全体の平均が近づいても、重要なsubsetは未校正。**
timeのpaired game-bootstrapによるBrier差95%参考区間はcapture [-0.0749,-0.0475]、
candidate capture [-0.2171,-0.1496]、recapture [-0.4642,-0.3550]、recovery [-0.3186,-0.2100]。
strict-player/gameでも4集合の差区間は負。ただし母集団独立CIや再利用test問題の解決ではない。
詳細は [bootstrap.json](bootstrap.json)。

被害駒別のtime診断（選択には不使用）は、歩n1016で実測15.06%・新予測14.77%、
角/馬n298で25.50%・21.88%、飛/龍n17で70.59%・39.39%。
特に飛車の標本は極小で、角と飛車を合わせた平均では欠陥を隠し得る。
[victim_slices.json](victim_slices.json) に全splitの支持とbinを保存した。

種別tiltのtime主要集合Brier0.1633はcapture一括0.2815より良い。
一方、strict-playerのselectionでは一括補正が選ばれた。種別feature全ての一般的優位を主張しない。

## Exact support / shrinkage

timeのNLLはhard threshold 2.9113、shrink2 2.8779、shrink5 2.8876、shrink10 2.9055。
support=1情報の切り捨ては有害になり得るが、kを最初から正解とは扱わない。
shrink単独より集合tiltの追加が効いた。

|time slice|n|NLL 旧→選択モデル|
|---|---:|---|
|exact support>=2|615|1.7561→1.7444|
|fallback support<2|2351|3.2135→3.0788|
|support=0|2213|3.2261→3.1202|
|support=1|138|3.0111→2.4148|

strict-playerのexact-supported NLLは1.8493→1.8893と悪化しており、全slice一様改善ではない。
低支持割合はtime79.27%、strict-player78.40%、game75.88%。これはOODの代理で、真のOOD検出率ではない。
独立確認もなく重要subsetの校正が残るため、今回の運用abstain率は全件100%。
モデル由来P_goodの解析mass上下界と、人間確率の不確実性は別物。
真の人間P_goodは根拠不足として[0,1]を別フィールドに保存し、昇格には使わない。

## 固定△3二銀 regression：改善しても反例は消えない

角取り2手へのmass：旧3.03%、shrink2 35.35%、shrink5 19.19%、shrink10 11.85%、
capture一括40.28%、選択された種別tilt60.80%。
新内訳は▲2二角成59.71%、▲2二角不成1.08%。合計して自然応手集合として評価する。
候補後exact support=1。少数のexact情報を保持する効果と、集合補正の両方が寄与している。

既存全合法応手10k解析の再重み付けではP_good100=60.80%、後手human_gap約+1643.94。
旧約+4050.54から減ったが、**角をただで取られる手にもまだ巨大gapが出る**。
値を成果と誤認せず、obvious_reply_neutralizes=trueかつdiagnosticとして残す。
この局面の実際の人間捕獲確率が60.8%という証拠は得ていない。

## Review packageと人間に見てほしいもの

事前の探索的改善条件を満たしたため、既存3例の全116合法応手を再重み付けした。
新親局面0、新候補scan0、新engine解析0。実験上の新しいactual candidateは0件。

- diagnostic 1件：[△3二銀](../../exports/response_calibration/diagnostic_counterexample/gote_5c46af1026197c8aeb70_3a3b.kif)
- control 2件：[▲7六歩](../../exports/response_calibration/control/sente_8e41531c4f23213c9b17_7g7f.kif)、[△3三角](../../exports/response_calibration/control/gote_fa2a3aee31df970cb704_2b3c.kif)
- [盤面・旧新確率・集合校正HTML](review.html)、[分類・応手・確率・P_good JSON](review.json)

controlの新P_good100は▲7六歩17.16%、△3三角55.95%。human_gapは約+267.82/+80.79。
普通の駒組みの低P_goodも、直ちに奇襲の証拠にはしない。
promising例は認定していない。borderline例を無理に追加せず、分類根拠を手動指定で維持した。

確認してほしい点：
1. △3二銀は改善後も「奇襲ではない」という判断が変わらないか。
2. 角取りに60.8%を置いた後の残り39.2%に、明らかに不自然な応手が残っていないか。
3. controlの自然な応手分布が補正によって不自然になっていないか。
4. material recovery proxyの枝が「安全な駒得」という誤解を招かないか。

KIFは修正済exporterを再利用し、全分岐を再パースして合法性と手数を検証（377/416/301着手行）。
GUI目視は未実施。KIF generated / branches validated / user visual review required。

## 再現・次の提案・STOP

```bash
.venv/bin/pytest -q
.venv/bin/python -m surprise.response_calibration
.venv/bin/python -m surprise.calibration_review
node scripts/check_calibration_review.mjs
```

既存private humanデータが必要。公開GitHubだけから同じ教師データを復元できるとは主張しない。
分割・入力・研究コードのfingerprintはprovenance.json。raw棋譜・SQLite・book・binaryは非公開。

次に進むなら、ユーザーレビューを踏まえ、未使用小標本で取り返し/回収subsetを確認する計画を提案したい。
ただし、このcheckpointでは取得・次モデル・次仮説を実行しない。
**GitHub push後STOP。明示的な人間レビューと続行指示を待つ。**
