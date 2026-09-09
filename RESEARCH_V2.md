# 研究パイプライン v2 — 2026-09-08

> 2026-09-09の現行checkpointは [RESEARCH_V3.md](RESEARCH_V3.md)。book seedと人間推定を分離し、
> Human Policyのheld-out検証・4局面E2Eまで実施した。以下はv2時点の設計記録。

PAUSE.mdの旧deep/audit再開手順を置き換える。既存基盤を使い、Human Policy・大量deep・Vast.aiにはまだ進まない。
今回の到達点は [診断と研究判断](reports/reach_pilot/analysis.md)。旧pilotは反証用baselineとして保存する。

## 順序と独立指標

1. 利用条件を確認した実棋譜を小規模取得。BOT/AI・出自不明・不正手順を除外し、出典と取得日時を保存。
2. SFENの盤面・手番・持駒で局面統合。手数はキーから外し、左右反転はしない。
3. `games_reaching_position / total_games` を算出。同一ゲームの再訪は分子1票。着手分布は再訪も含む意思決定回数として別保存。
4. 探索元局面をreachとparent評価で選ぶ。既に有利な元局面は別枠。候補手の不利な評価とは混同しない。
5. 選んだ元局面の全合法候補を保存。shallow/passは特徴量で、候補評価値によるhard filterは置かない。
6. 明白な応手を抽出・評価。良い取りは降格、悪い取りは罠の可能性として保持。必要候補だけ全合法応手幅を測る。
7. 先手・後手別の盤面付きレポートをレビュー。その後に限って少数deep、後からHuman Policy。

`engine_eval`は常に正＝先手有利。符号を側別に変えるのは `parent_attacker_advantage`、pass sensitivity等の派生量だけ。
`parent_attacker_advantage >= parent_favorable_cp` の初期閾値300cpは設定値。candidate eval lossは独立の理論コスト。
reach、応手失敗確率、plyは別軸。失敗確率は未測定なのでpractical exposureを捏造しない。

## 実装・再現

- `surprise/obvious.py`: 候補駒の取り、取り返し、歩接触取り、material回収proxy。複数signalを併記。
- `surprise/diagnostics.py`: schema-5旧pilotのtop集合を診断、別出力で候補単位checkpoint/resume。
- `surprise/reach.py`: 取得provenance、ゲームID重複排除、全手順検証、SQLite reach DB。
- `surprise/reach_report.py`: reachとの結合、全6314件を残す保留理由、先後別HTML。新scanは実行しない。
- `config/reach_pilot.yaml`: 独立設定。10k応手診断・各側4例のみ100k全合法応手確認。

```bash
.venv/bin/pytest -q
.venv/bin/python -m surprise.diagnostics --config config/reach_pilot.yaml
.venv/bin/python -m surprise.reach --config config/reach_pilot.yaml
.venv/bin/python -m surprise.reach_report --config config/reach_pilot.yaml
node scripts/check_reach_report.mjs
```

診断は既存cacheを必須利用。baseline/config/engine/NNUEの識別情報を確認する。設定変更時は新outputを使う。
取得済みrawは再利用し、ゲームIDは冪等。raw棋譜・DBは公開対象外。利用条件の確認は [SOURCES.md](reports/reach_pilot/SOURCES.md)。

## 評価上の留保

明白さは合法手と局所materialによる仮説で、人間の着手確率ではない。
駒回収proxyは「直後の合法取り返しがない、または取られる駒の価値が取り手より大きい」であり、SEEや罠の証明ではない。
応手探索が否定しない限り捕獲可能性だけで候補を消さない。

部分応手診断ではroot評価と解析済み応手評価の受け側最良値を暫定基準とする。
全合法応手診断では応手後評価の受け側最良値を基準とする。rootとの探索地平差も保存。
詰み・bound・unknownが混在する場合、CPのgood判定・幅は未確定とする。
`good_reply_count_*`は部分解析時には解析済み集合内の数のみ。
`good_reply_fraction_*`は全合法応手が比較可能な場合のみ。部分集合の区間も暫定基準に条件付けられたもので確率予測ではない。
これらを `P_good` と呼ばない。狭い合法良応手集合でも、その1手が明白なら奇襲の根拠にしない。

## 次scanの実行前条件

現19対局は取り込み動作検証のみ。2アカウントの便宜標本では局面到達率の一般化はできない。
設定の最低1000対局も十分性の保証ではなく、まず標本設計の検討が必要。
次は取得・利用範囲を確認し、期間・利用者の偏りとゲーム重複を制御した標本を用意する。
棋力別Human Policyはまだ作らないが、rating・time controlは偏りの監査用に保持する。
未観測はsample reach=0として記録する一方、母集団reachはunknownのままとする。

plannerは `sampling_design_not_validated` を明示して全候補の昇格を保留する。
`parent_already_favorable`、`low_reach`（標本内）、`obvious_reply_neutralizes`、`broad_good_reply_set`、未解析理由を個別保持する。
標本設計レビュー後に次scan専用config/outputを作り、この保留を明示的に改める。
one-shotも正式成果の方針は維持する。今回は新奇襲の成立も実戦勝率改善も主張しない。
