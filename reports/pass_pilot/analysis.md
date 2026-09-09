# Research paused

2026-09-08: the user requested a pause and GitHub backup.

The corrected cache-schema-5 shallow scan is complete: 148 positions and 6,314 candidates.
The positions come from authored opening scaffolds, not a human-game sample.

The current HTML and JSON contain the corrected shallow results. Deep analysis, current top-candidate
review, and qualitative conclusions remain pending. Do not use numerical conclusions from the older
`pass_bound_diagnostic` or `pass_warmup` runs as findings for these results.

See `PAUSE.md` at the project root for the exact state and resumption instructions.

---

## 2026-09-08 再開後の反証診断（追記・旧データ不変）

上記は停止時点の記録。新しい研究判断はPAUSE.mdの旧deep/audit手順に優先する。
schema-5の148局面・6314候補を読み、raw/relative各top30の和集合95候補を別outputで診断した。
HTML/JSON/SQLiteなど保存済みpilotは上書きしていない。旧bound/warmup/serial partialを混ぜていない。

|集合|明白な良応手あり（100cp、10k応手診断）|parent奇襲側有利300cp以上|ply中央値|normal first replyが候補駒を取る|
|---|---:|---:|---:|---:|
|先手raw top30|19/30 (63.3%)|21/30|22|14/30|
|先手relative top30|16/30 (53.3%)|6/30|15|29/30|
|後手raw top30|21/30 (70.0%)|17/30|23|20/30|
|後手relative top30|29/30 (96.7%)|3/30|20|29/30|

和集合では先手29/49、後手36/46、計65/95=68.4%が明白な良応手により反証された。
これは人間実測の誤応手率ではなく、局所的な明白応手proxyと浅いengine評価に条件付けた率。
95件すべてのnormal先頭応手が駒取りだったが、捕獲可能性だけで除外せず、応手後の評価で判定した。
親局面の奇襲側有利中央値はraw先手+2671.5、後手+2255cp。relativeでは+110.5、+51へ減るが駒取り型は残る。

8候補だけ100kで全合法応手確認。CP比較可能な5例すべてで、50–300cp以内の良応手は1手だけ、かつその1手が明白な駒取りだった。
例: 後手 `0a33fbe73571830519e4_2b6f`（5ply、親-54、候補+2793、pass sensitivity6753）に8h6fが+2803。
31合法応手中の唯一の良応手がこの取りである。合法応手の狭さだけでも奇襲を示せない。
残り3例はmate混在でCP幅を未確定として保持。無作為標本ではなく、この5/5を一般化しない。

rawは21–30plyに先手20/30・後手17/30が集中。ただし人工seedのplyや出現回数から実戦到達率は推定できない。
実棋譜の小規模prototypeは46件取得・BOT/AI等を除き19対局・708局面。
2アカウントの便宜標本であり、現段階で新scanのreach選別根拠にはしない。

結論: passを即時対応要求のcheap featureへ降格し、reach・parent有用性・明白応手の実評価を先行導入する。
全候補は保持し、新scan・大量deep・Vast.ai・Human Policyは保留。
詳細の閾値感度、ply分布、100k実例、出典利用条件、次の判断は
[診断レポート](../reach_pilot/analysis.md)、[先手盤面](../reach_pilot/report_sente.html)、
[後手盤面](../reach_pilot/report_gote.html)、[v2設計](../../RESEARCH_V2.md) を参照。
