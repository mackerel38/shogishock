# テラショック浅部をseed universeにする検討 — 2026-09-09

## 判断

主seed universeは **0–12ply** を暫定採用する設計が妥当。
既に30,421局面あり、小規模E2Eには十分広い。0–16は人間reachの支持がある戦型だけの追加枠、0–20は今回構造集計のみ。
これは全局面scanの提案ではない。Human Policyのheld-out確認後でも、最初は各側2親局面まで。

人間棋譜はreach / 着手分布 / Human Policyの推定専用とし、探索元候補の供給源と分離する。
bookの枝数、count、SFEN重複を人間頻度として使わない。

## 入手・形式・ライセンス

開始時点のプロジェクト内にはbookはなかった。既存engine/NNUE/cacheは変更せず、
[公式700T/WCSC29リリース](https://github.com/yaneurao/YaneuraOu/releases/tag/BOOK-700T-Shock)
の `700T-shock-book.zip`（5,862,919 bytes）を取得した。
SHA256は `0d14943c5e960fad35d554bea6700edcbd929e9cdb5fa048dc6c472a89cb90c3`。

`user_book1.db` はSQLiteではなく `#YANEURAOU-DB2016 1.00` テキスト。
`sfen ...` の後に `move ponder value depth count` の行が続く。
実ファイルには285,463局面レコード、手数を除いたidentityで284,227局面。
同じidentity/着手で内容が異なるレコードが1,567件ある。今回の評価集計はファイル先出レコードを採用し、衝突件数をmanifestに残した。
現在engineによる親再評価を省略してよいという意味ではない。

[公式解説](https://yaneuraou.yaneu.com/2019/04/16/100%E3%83%86%E3%83%A9%E3%82%B7%E3%83%A7%E3%83%83%E3%82%AF%E5%AE%9A%E8%B7%A1%E3%80%81%E5%85%AC%E9%96%8B%E3%81%97%E3%81%BE%E3%81%97%E3%81%9F/)
によるとvalueは定跡末端から伝播した評価、depthは最善手列で定跡が尽きるまでの距離で、通常の探索depthではない。
手番視点valueの最大値を親のbook評価proxyとし、後手番だけ符号を変えて先手視点列に正規化した。
ローカルの `third_party/yaneuraou/source/book/book.cpp` の手番側評価による選択実装とも照合した。

付属説明全文・公式リリースには明示的な再配布ライセンスを見つけられなかった。
公開配布の事実をMIT/GPLのデータライセンスとは解釈しない。現在はローカル構造検査に限定し、raw ZIP・抽出局面DBは公開対象外。
正式な再配布を伴う採用には許諾確認が必要。
別版である [新ペタショック233万局面](https://github.com/yaneurao/YaneuraOu/releases/tag/new_petabook233)
にはMITが明示されているが、今回はユーザー指定のテラショックから黙って置換していない。

## 浅さごとの比較

初期局面から **登録されたbook着手だけ** をBFSした。全合法手木は展開していない。
深さはSFENの記載手数ではなく、実際のbook経路の最短ply。
左右反転・色反転・未登録局面の補完をしていない。到達先がbookにないedgeは葉として打ち切る。
展開したedgeに非合法手は0件。上限20までの展開中、未登録局面へ出るedgeは73,271件。

|上限ply|distinct positions|book枝数 中央値 / p90 / 最大|parent book評価 最小 / 中央値 / p90 / 最大|絶対評価300以上|
|---|---:|---|---|---:|
|12|30,421|2 / 4 / 25|-3660 / +39 / +228 / +1158|1,466 (4.8%)|
|16|75,192|2 / 4 / 25|-4595 / +45 / +247 / +2517|5,290 (7.0%)|
|20|146,417|2 / 3 / 25|-5589 / +48 / +268 / +6113|13,739 (9.4%)|

評価はすべて先手視点だが **book由来proxy**。現在の水匠5評価分布は未測定で、0として埋めていない。
bookに載っているだけでAI的に健全とはいえない。浅部にも大きく壊れた親が含まれる。
手番側有利300以上の親は順に1,047 / 3,588 / 8,969局面。
`abs(parent_book_eval)>=300` は優先度を下げる属性とし、本採用時は既存engineで再評価する。
奇襲側が不利な親は一律禁止しない。候補手自身の評価cutoffも設けない。

|最短ply|局面数|最短ply|局面数|最短ply|局面数|
|---:|---:|---:|---:|---:|---:|
|0|1|7|2,014|14|10,425|
|1|16|8|2,848|15|11,929|
|2|61|9|3,822|16|13,411|
|3|146|10|5,081|17|15,222|
|4|339|11|6,382|18|16,902|
|5|715|12|7,646|19|18,723|
|6|1,350|13|9,006|20|20,378|

16plyは12plyの約2.47倍、20plyは約4.81倍に広がる。
人間支持がまだ不確かな段階で深さだけを増やすより、12ply内をreach注釈して少数選ぶ方が今回の問いに合う。

## pipeline v2への変更点

`book seed universe → book parent品質の仮タグ → human reachのleft join → 少数parentを既存engine再評価 → 全合法候補 → obvious/不成診断 → Human Policy応手評価`

- seed source、book評価、book branch countはbook列に閉じる。
- reach、実着手頻度、支持ゲーム数/プレイヤー数、Wilson参考区間は人間標本だけから付与する。
- 未観測はsample reach=0だが母集団reachはunknown。bookの枝数で補完しない。
- Human Policyは人間序盤のheld-outで検証し、book内/外のsliceも確認する。book着手は教師ラベルにしない。
- 既存エンジンの定跡使用を有効化しない。`USI_OwnBook=false` を維持する。
- 旧pass/reach pilotは変更しない。新しいseed設定は `config/terashock_seed.yaml`。

## 再現

```bash
.venv/bin/python -m surprise.book_seeds --max-ply 20
```

これは既存bookの読み取り集計であり、engine scan/deepではない。
新scan・Vast.aiは実施していない。次の可否は人間標本とHuman Policyの検証結果で判断する。

## 同日追記：人間支持による深さ選択の確認

612人間対局とのjoinでは、観測されたbook局面は0–12 / 16 / 20で1,119 / 1,398 / 1,585。
一方、**10対局以上かつ10プレイヤー以上の支持がある局面は、どの上限でも56局面**だった。
この標本では深くしても支持十分な探索元は増えない。主universeを12plyに留める根拠が強まった。
その後、Human Policyの修正後held-out確認を経て、12ply universe内の4親局面だけ10kのE2Eを実施した。
定跡全体scan・100k以上・Vast.aiは行っていない。結果と停止判断は [小規模実験](../human_e2e/analysis.md)。
