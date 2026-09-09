# Seed方針変更 — 2026-09-09、候補scan前

取得中の人間標本とHuman Policy検証は継続するが、人間棋譜局面を探索元universeにはしない。

|データ層|責務|禁止する解釈|
|---|---|---|
|Terashock shallow book|探索元候補・定跡edge・定跡評価の供給|枝数・countを人間頻度と扱う|
|人間棋譜DB|reach、実着手分布、Human Policy教師|未観測book局面を到達不能と断定する|
|既存水匠5 engine/cache|探索前parentの再評価、候補・実応手評価|古い定跡評価と現在engine評価を同じ値と扱う|

bookの全候補枝だけを初期局面からBFSし、上限12/16/20plyを比較する。全合法手による木展開はしない。
SFENの手数は記録値として保存するが、深さはBFSで実際に初期局面から到達した最短ply。
盤面・手番・持駒をキーにし、左右反転や180度色反転を追加しない。
定跡に存在しても初期局面から指定上限内のbook edgeで到達できない局面は別扱い。

`parent_book_eval_sente` と `parent_engine_eval_sente` は別列。
book評価の分布で明らかに崩れた親局面を低優先度にするが、成立を保証しない。
実候補生成前に既存engineで親を再確認する。`parent_attacker_advantage >= 300` の既存別枠化も維持。
候補手が不利になることへのhard cutoffは引き続き置かない。

Human reach annotationはleft join。未観測book局面はsample count=0 / population reach unknown。
今回のE2E元局面は、選定深さのbook universe内かつ人間支持数十分な共通部分から少数選ぶ。
Human Policyのheld-out検証はbook内だけへ限定せず、人間序盤全体とbook内/外のsliceを区別する。
book評価・枝数をHuman Policy教師ラベルへ流用しない。

700T/WCSC29版を最初の小さい検査対象にする（公式ZIP約5.9MB）。別物である新ペタショック233万局面版へは黙って置換しない。
700T付属説明には利用方法があるが、明示的な再配布ライセンス文は見つからない。
まず公開配布物のローカル構造・集計検査のみ。raw book・抽出DBを公開しない。
再配布を伴う本採用は許諾確認、またはMITが明示された別版をユーザーと区別して選定する。

大量処理・新scanはこの設計変更と浅い構造集計の後。エンジンのBookFile/USI_OwnBook等は変更しない。
