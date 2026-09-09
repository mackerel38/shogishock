# 新奇襲探索：研究契約と最初の実験

> 2026-09-08再開後の現行設計は [RESEARCH_V2.md](RESEARCH_V2.md)。以下は旧pilotの実験記録として保存する。
> 大量deepに先行して反証診断・実棋譜reach prototypeを実施した。結果は [新しい考察](reports/reach_pilot/analysis.md)。

既存YaneuraOu・水匠5・python-shogi・SQLiteを使用する。環境の再構築は行っていない。
まずPhase 1–4のpass仮説だけを検証する。Human Policy、勝率推定、新規性の判定は未実装。

## 再現

プロジェクトルートから、既存venvで実行する。

```bash
.venv/bin/pytest -q
.venv/bin/surprise engine-test
.venv/bin/surprise benchmark
.venv/bin/surprise scan --config config/pass_pilot.yaml
.venv/bin/surprise deep --config config/pass_pilot.yaml --per-side 15 --nodes 100000 1000000
.venv/bin/python scripts/verify_pilot.py
node scripts/check_report.mjs
```

同じscan/deepコマンドで再開する。候補・engine解析は完了ごとにSQLiteへcommitする。
SIGINT/SIGTERMはscanの各workerに停止を伝え、現在の候補を完了して部分HTMLを生成する。
強制終了ではJSON出力に未反映でもSQLiteの候補・engine cacheから再開できる。
`--report-only`は既存JSONからHTMLを再生成する。
`--max-positions N`は元局面数の予算制限であり、各元局面の合法手は全て対象にする。

主な出力は`reports/pass_pilot/`内の`report_sente.html`、`report_gote.html`、
`positions.json`、`candidates.json`、`scan.sqlite3`、`manifest.json`、`checkpoint.json`、
`summary.json`、`review_candidates.json`、`deep.json`。最終考察は`analysis.md`。
HTMLはローカルで開ける単一ファイルで、CDN・外部画像・人間棋譜サービスに依存しない。

## 局面集合と頻度の意味

`data/opening_seeds.yaml`の10本は研究用に作成した合法な序盤手順。棋譜や正確な定跡の転載ではなく、
人間行動の代表標本でもない。相居飛車、角交換、角道を止めた形、四間飛車・三間飛車・中飛車、
早い歩の接触などを含む。各手順の全prefixを、設定されたply範囲内で取り込む。
0〜40 plyで188出現、148異なる局面。終盤や長い手順の人間頻度の推定には使わない。

`position_id`はSFENの盤面・手番・持駒をハッシュ化する。SFENの手数はIDに含めず、
各出現のply、元手順ID、game_id（存在すれば）、手順履歴を別に保持する。
左右反転・色の入替え・反転augmentationは行わない。
同一局面で千日手・連続王手の履歴が異なるケースは、このSFENのみの基盤では評価を区別できない。
本pilotの手順はその問題を対象にしていない。実棋譜の導入時には履歴条件の扱いを追加する。

`occurrence_count`と`move_distribution`は作成手順内の回数。
未観測候補のmove frequency=0は、人間が絶対に指さないことを意味しない。
`resulting_position_frequency`も同じ種局面集合での照合回数。
手順前後の統合と「同じ奇襲アイデア」の統合は異なる。隣接局面での同型アイデアはまだ関連候補として残る。

## 評価と欠測

- 元局面のbestと、候補後のnormalを個別に同じnodes上限で評価。全合法手を保存し、CPで除外しない。
- `candidate_eval_loss_signed = sign(attacker) * (best_eval - candidate_eval)`。
  表示用lossは`max(0, signed_loss)`。浅い探索の不整合はsigned値に残る。
  元局面と子局面は探索の起点が異なり、このlossは厳密なminimax損失ではない。
- 全engine評価は先手視点。`pass_eval_delta = V_pass - V_normal`。
  `pass_sensitivity`のみ先手でdelta、後手で-delta。
- relativeは同一元局面でCPペアがある候補の中央値との差。
  percentileは同順位にmidrankを与える`(小さい個数 + 0.5*同値個数)/個数`。
  zscoreは母標準偏差で割る。標準偏差0ではnull。
- 王手後はpass不能として保存。詰みはmateのまま保持し、巨大CPへの置換をしない。
  スコアのないengine応答はunknown。詰み・unknownの差分はnullで、CP散布図からのみ外れる。
- 未完了の元局面のrelativeはnullにする。CPペアの母数・中央値も保存する。
- `mate_allowed`、`large_material_loss`、`obvious_blunder`は削除条件ではない。
  駒損はnormal PVの最大8ply末尾での駒価値差proxy、blunderは設定CP損失proxy。
  手途中の一時的な交換損や将来の補償を厳密には判定しない。
- 王手・駒取りを除外しない。one_shotも正式な成果だが、passだけでは成立を証明できず、
  現段階の`surprise_type`はunclassifiedとする。

## 実行条件・基盤の限定修正

初回smoke testでは既存8 testsとengine-testが成功。実測benchmarkはキャッシュを使わず計測するよう修正。
MultiPVを毎回設定し、2→1の設定残留を防いだ。評価値のない応答を0cpに見せないようunknownを導入。
打切り時のupperbound/lowerboundを通常CPに扱っていた問題も修正した。
`PvInterval=0`で各反復のPVを出力し、最後に完了した境界指定のない評価を採用する。
境界値しかない場合はboundを保持し、通常CP差分には使わない。後手視点の符号反転では上下界も入れ替える。
`best_move`/PV/depthは採用評価に対応し、最終bestmoveは`reported_best_move`にも保存する。
nodes/timeはリクエスト全体の最終報告値。raw_infoは採用行と、異なる場合は打切り時の最終行を保存する。
cache keyはエンジンSHA、NNUE内容SHA、設定、SFEN、nodes、MultiPV、cache schemaを含む。
fingerprintはプロセス起動時に取得し、実行中にエンジン・NNUEファイルを書き換えない前提。

このYaneuraOuの`usinewgame`は空実装。`isready`で置換表と探索状態を初期化するため、
各未キャッシュ探索で`isready`を送信する。ソース：
`third_party/yaneuraou/source/engine.h`、
`third_party/yaneuraou/source/engine/yaneuraou-engine/yaneuraou-search.cpp`。
これにより前の候補の探索情報を持ち越さない。NNUE・エンジンの交換や再ビルドはしていない。
研究用設定は8 workers × 各1 thread、16MB hash。通常設定は2 threads・256MBのまま。
worker数は初期化待ち時間を重ねるためで、将棋探索スレッド数とは別。
履歴・TTの初期化なしの予備出力は`reports/pass_warmup/`に隔離した。
境界値を通常CPとして扱っていた診断用出力は`reports/pass_bound_diagnostic/`に隔離した。
どちらも最終的な研究ランキング・結論には使わない。現在のcache schemaは5。

## 次段階の判断基準

まずraw/relative上位30件ずつを先手・後手別に比較し、重複、王手、単純駒取り、
候補側の自らの駒の放置、非駒取り、悪いAI評価領域を調べる。
深掘りの候補集合は各側raw/relative上位の和集合で、重複を除く。単一総合scoreは作らない。
10k→100k→1Mでnormal/passを再評価。relativeを深掘りで再計算するには同一親の全合法手が必要なので、
選抜候補だけの深掘りにshallowの中央値を流用しない。

passは合法応手でも、人間が選ぶ応手でもない。「自分の駒を取らないでくれれば強い」手は
高passになり得る。そこで有望性判断では、実際の合法応手に置き換えても危険が残るかを確認する。
容易な第2・第3応手が残る候補を、人間に難しいと断定しない。

人間棋譜の公開APIの存在と、機械学習用棋譜データの利用許諾は別に確認する。
Lishogiの棋譜export APIは公式フォーラムから案内されている：
https://lishogi.org/forum/lishogi-feedback/feature-request-batch-download-of-kifu
今回、人間棋譜の収集やBOT混入データでの学習は行っていない。
人間棋譜段階ではsource、取得日時、利用条件URL、BOT/AIフラグ、rating、time control、game_idを保存し、
対局単位・時系列でtrain/validationを分離する。類似局面による漏洩も測る。

将来のHuman Policyは交換可能な手作り特徴量+kNN backendから始め、合法手上に確率を定義する。
複数の行動signalを同時に持ち、歩取り・駒得・穏便化の係数は実棋譜で推定・検証する。
棋力・持ち時間別モデルは初期段階では作らない。
応手評価ではAI最善一致でなく十分良い応手群の確率和をtolerance=50/100/200/300で計算する。
未解析確率がある場合、期待値の既評価分の和とcovered probabilityを保存し、無言で再正規化しない。
`P_good`は既評価良応手確率和を下限、それに未解析確率を加えた値を上限とする。
未解析部分に仮定を置かず、全体の期待値・human gapを確定値として表示しない。
Pareto比較は先手・後手で分離し、soundness/human gap/P_good/pass/familiarity/noveltyを独立軸にする。
multi_stage・opening_systemが見つかった場合だけ短いrolloutへ進め、奇襲側にはHuman Policyを使わない。
