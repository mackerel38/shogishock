# Human pilot — 取得前計画 2026-09-09

目的は局面reachと人間着手予測の動作・外挿限界の検証。一般人間全体の頻度推定ではない。
旧19対局・pass pilotは新train/testに混ぜない。旧反証実験も繰り返さない。

## sourceと標本枠

[公式API案内](https://lishogi.org/developers) はHTTP/JSON APIの利用を案内している。
[公式API仕様](https://raw.githubusercontent.com/WandererXII/lishogi/master/ui/@build/static/assets/doc/lishogi-api.yaml)
の公開team一覧・公開member一覧・user game exportのみを利用する。
[利用規約](https://lishogi.org/terms-of-service) の教育/開発目的と負荷制限を確認した。
少量ローカル研究として利用し、データ再配布の包括許諾とは扱わない。81Dojoは取得しない。

公式team一覧1ページ15チーム（予備確認で最大456名、全1034チーム）を枠とし、明示BOTチームを除く。
変則将棋チームも恣意的に削らず、取得ゲーム段階でstandardに限定する。
公開member一覧が認証を要求したチームは飛ばして記録し、アクセス制限を回避しない。
公開team所属・人気順というcoverage biasがある。Lishogi全体の人口や分布はこの枠から推定しない。

直近の活動日時が期間開始以降の非BOT会員から、realTime ratingを <1200 / 1200–1599 /
1600–1999 / >=2000 / unknown の層に分け、層間round-robin、層内固定hash順で160 focal playersを選ぶ。
ratingは将来のモデル入力には使わず、標本枠形成と偏り監査だけに使う。現在ratingと対局時ratingの差に留意。
期間は2025-09-01以上、2026-09-01未満。各focalから期間内直近最大12対局を取得する。
双方の参加者について最大12受理対局の上限を課し、頻繁に現れる対戦相手の集中も抑える。
ゲームID重複排除後、固定hash順で上限を適用する。旧便宜標本は除外。
最大1920件の取得候補。受理ゲーム数はBOT混入・非活動・変則・上限制御で減り得る。件数目標のための無制限追加はしない。

## 取得管理

逐次リクエスト、最短2秒間隔、レスポンス8MB上限、ローカルcheckpoint再利用。
429はRetry-Afterまたは最低60秒の再開可能時刻を記録し、その実行を停止。5xx/ネットワーク失敗も記録して停止。
自動無限retryはしない。再開時に同URLの成功データを再利用する。
request URL、UTC取得時刻、レスポンスhash、規約URL、rated/casual、rating、clock、日時、variant、BOT/AI、採否理由を保存。
raw/個人識別子を含むDB・学習snapshotはローカルのみ。公開物は集計・コード・研究用候補変化。

## Reachと不確実性

0–24plyの局面を盤面・手番・持駒で統合。左右反転なし。
ゲーム単位と参加プレイヤー単位のreachを分離し、分子/分母、ply範囲、再訪数、着手分布を保存。
親→子の実観測edgeについて、親到達ゲーム数に対するそのedge通過ゲーム数をconditional reachとする。
単一の親だけを割り当てずtranspositionの各edgeを保持する。
ゲームreachのWilson区間は参考値。ゲーム間の同一プレイヤー依存を無視するため、母集団CIとは呼ばない。

## 予測評価の事前仕様

0–24plyの実着手を対象とし、合法手分布を予測する。testを閾値/temperature調整に使わない。
1. game-group: ID hashで60/20/20、同一対局を混ぜない。
2. time: 対局開始日時順60/20/20、境界同時刻は同じ側へまとめる。
3. strict player-group: 全プレイヤーをhashで60/20/20へ分け、双方が同じ群の対局だけ使う。
   群跨ぎ対局をpurgeし、双方のplayer集合が完全非重複であることをassertする。標本減少を報告する。

比較: uniform、合法手上global USI popularity、opening-prefix頻度、exact-position平滑頻度。
提案MVPはexact support十分なら実測頻度、疎な場合は駒種/駒取り/成/歩接触/後退等の実測行動class priorへfallback。
巨大NN・追加ライブラリ導入はしない。複雑なkNNはこのbaseline群の結果を見てから判断する。
validationでexact閾値2/5/10とtemperature 0.75/1/1.25/1.5を選ぶ。
NLL（nats）、multiclass Brier、top1/3/5、top-label ECE/reliabilityを記録。exact/fallback・ply帯も別集計。
同一局面が別対局に現れることはexact baselineの本来の適用範囲として可視化し、未知局面の性能と分離する。

小規模E2Eへの最低条件: timeおよびstrict-player test各15対局以上、提案のNLLがpopularityより0.02以上良く、
選択済モデルのtop-label ECE<=0.10。より強いexact baselineを上回らなければ提案モデルは採用せず比較結果を報告。
これは小規模動作実験の基準であり、大量scanへの許可条件ではない。応手集合P_goodの校正やOOD安全性まで保証しない。
不足/失敗なら原因分析で止め、テスト成功を捏造するために再分割・大型化しない。

E2Eを実施できる場合のみ、各側最大2親局面・全合法候補10k、代表各3候補まで応手評価。
parent有利/余計な不成/明白良応手を別タグにし候補は保存。pass順では選ばない。
未解析massは明示しP_good上下界を保存。全massのCP評価なしではE_human/human_gapを確定値にしない。
先後別KIFを出し、GUI操作できなくても分岐検証とユーザー目視依頼を行う。
