# Research paused — 2026-09-11 (trap-tree benchmark)

> Latest: `reports/trap_tree_benchmark/ASTRA_HANDOFF.json`, `tree.json`, `analysis.md`.
> Method INCONCLUSIVE:4 root branches,2 conditional tactical contrasts,1 local first-response refutation,1 ranking reversal/needs_review; normal fallback retained.
>59 nodes/59 edges;2 shared diagnostic nodes.8 our candidates,3 gate rejects;3 old reject regressions pass.
>714 new requests (708x10k,6x100k),109 cache hits;8 confirmation positions. No Human Policy/external opening lookup or mass scan.
>22 tests pass;694 reply PVs checked. Known reference exposure acknowledged; no blind/new discovery claim.
> KIF/display is Luna's task in `LUNA_TASK.md`; no Luna agent invoked. STOP for human review.
> Production gate remains INCONCLUSIVE. Do not expand search, retrofit missing P*2c, or tune from these confirmations.

> Latest cycle: `reports/tactical_falsification_v2/ASTRA_HANDOFF.json` and `analysis.md`.
> Production automatic rejection: INCONCLUSIVE. Original long-history exchange controls are NOT safety evidence.
> New23ply rook-sacrifice control survives;22ply horse control survives but precedingR3e loses454cp, so remains borderline.
> UserR2b+ rejects; P*8b has straightforward adequate pawn captures despite passing narrow gate. N*8f is not unique.
> Original3 reject regressions pass. Gate/policy/independent270 unchanged.421x10k +12x100k requests, no1M/10M or mass scan.
>22 tests passed;372 reply PVs legally validated. New KIF/display is Luna's task per `LUNA_TASK.md`, not yet generated.
> STOP for human review. No production activation or next research. Historical instructions below are superseded.

> Completed independent confirmation: `reports/independent_policy_validation/analysis.md`.
> 270 real-time games / 250 new known accounts; old account/game overlap 0; 6,501 moves.
> Frozen models only, no refit or selection. Relative improvement replicated, but recapture/recovery remain ~20pp underpredicted.
> Next small surprise scan: **NO**. Review `report.html`, `metrics.json`, and `decision.json` in that directory.
> No new candidate/engine/KIF. After final checkpoint push: STOP for human review; do not tune on this confirmation sample.

> Current completed cycle, 2026-09-09: `reports/response_calibration/analysis.md`.
> Response-set calibration improved but remains inadequate for P_good candidate promotion.
> Time capture mass: 8.06% → 19.15% (observed 21.58%); recapture/recovery remain underpredicted.
> Fixed △3二銀 capture mass: 3.03% → 60.80%, still a diagnostic, never actual candidate.
> Review: `reports/response_calibration/review.html`, `review.json`, `exports/response_calibration/`.
> Actual 0 / diagnostic 1 / controls 2. No acquisition or engine calls. Reused tests are exploratory.
> After final checkpoint push: STOP. Await human visual review and explicit continuation.

> Checkpoint policy: commit+push at meaningful milestones and before long work. See `CHECKPOINTING.md`.
> Current public handoff and data exclusions: `PUBLIC_CHECKPOINT.md`. Preserve all local collaborator changes.

> Current checkpoint: 2026-09-09, `RESEARCH_V3.md`. Terashock seed audit, human sampling,
> corrected held-out Human Policy evaluation, and a bounded 4-parent E2E are complete.
> Do not expand scanning: conditional capture calibration failed. Historical instructions below are superseded.

> Superseded on research resumption, 2026-09-08: Stage A diagnostics and a small reach prototype are complete.
> Do NOT execute the old deep/audit continuation below. Follow `RESEARCH_V2.md` and
> `reports/reach_pilot/analysis.md`. No new scan or large deep run is authorized by this checkpoint.
> The historical pause record below is retained for provenance.

User requested a pause and a GitHub backup. Do not resume engine experiments until requested.

## Completed and preserved

- Existing engine/environment reused, not rebuilt: YaneuraOu + Suisho5 NNUE.
- Smoke test passed. Research regression suite: 20 tests passed.
- Phase 1–4 implementation: legal opening prefixes, transposition deduplication, all-legal-move evaluation,
  virtual pass, raw/relative pass, per-side offline HTML, SQLite checkpoint/resume.
- Current valid shallow run: `reports/pass_pilot`, cache schema **5**.
- **148 positions, 6,314 / 6,314 candidates, complete=true**.
- 10,000 nodes normal and pass; 8 workers, 1 engine thread each, 16MB hash.
- Seed source: 10 authored opening scaffolds, 188 occurrences, 0–40 ply. These are NOT human game frequencies.
- `report_sente.html` and `report_gote.html` generated with boards, PVs, scores and clickable scatter plots.

## Important research validity fixes

The engine and NNUE were not replaced. Wrapper fixes were necessary:

1. MultiPV always resets to the requested value.
2. Cache identifies NNUE contents as well as the engine and settings.
3. Missing score is `unknown`, not fabricated 0cp.
4. In this engine version, `usinewgame` is a no-op. Per-request `isready` clears prior search state.
5. `upperbound` / `lowerbound` are NOT exact CP scores. `PvInterval=0` exposes completed iterations;
   parser selects the latest unbounded iteration. A bound-only result stays explicitly bounded and
   is not used in numeric pass deltas. Bound direction reverses when normalizing white to sente perspective.

“Exact” here means an unbounded USI search estimate, not a mathematically solved game value.
Raw info preserves the selected score line and, if different, the final interrupted line.
`best_move` and PV correspond to the selected score; the final protocol move is also in `reported_best_move`.

## Do not mix these runs

| Directory | Status |
| --- | --- |
| `reports/pass_pilot` | Current schema-5 shallow results; use these |
| `reports/pass_bound_diagnostic` | Earlier run that treated bounds as CP; invalid for final rankings |
| `reports/pass_warmup` | Earlier run with search-state carryover; diagnostic only |
| `reports/pass_serial_partial` | Interrupted serial trial; diagnostic only |

Deep/audit files under old diagnostic directories are NOT a validated deep analysis of current results.

## Remaining work

- Review current per-side raw/relative top-30 unions. Earlier provisional reviews used now-invalid output;
  do not transfer their numerical conclusions to schema 5.
- Run the implemented deep analysis and legal-reply diagnostic on current candidates.
- Complete evidence-backed `reports/pass_pilot/analysis.md`.
- Actual browser visual QA: unavailable because no browser was connected. Portable HTML code can be
  verified using `node scripts/check_report.mjs`, but this does not replace a real visual check.
- Human Policy, human game ingestion, P_good, human_gap, novelty validation, and rollout are not implemented.
- No new surprise opening or practical win-rate improvement has been established.

## Resume when requested

Run from `/home/mackerel38/shogishock`, preserving the existing environment and `data/`.

```bash
.venv/bin/pytest -q
.venv/bin/surprise scan --config config/pass_pilot.yaml --report-only
.venv/bin/python scripts/verify_pilot.py
node scripts/check_report.mjs

# Only after research is resumed:
.venv/bin/surprise deep --config config/pass_pilot.yaml --per-side 15 --nodes 100000 1000000
.venv/bin/surprise audit --config config/pass_pilot.yaml --nodes 100000
.venv/bin/python scripts/summarize_pilot.py
```

Repeating `surprise scan --config config/pass_pilot.yaml` reuses completed candidates and cache.
The run fingerprint includes absolute engine/eval locations: moving to another machine/path may require
a new output directory or an explicit migration, not an unreviewed fingerprint bypass.

## Backup contents

The GitHub repository contains project source, configuration, tests, scripts, handoffs, seed data,
and small run manifests. The Release checkpoint archive contains all `reports/` directories and
`data/engine_cache.sqlite3`, preserving both current data and clearly separated diagnostics.
The existing engine binary, NNUE weights, `.venv`, third-party source checkout, and authentication files
are not bundled; their origin/fingerprints are documented in `HANDOFF.md` and remain on this machine.
Extract the checkpoint at the project root to restore `reports/` and the cache.

## Response-set calibration review operations checkpoint — 2026-09-09

問い: response-set calibration を、手動分類と区分別の再生・レビュー成果物として安全に受け渡せるか。

結論: `surprise response-set-review` が、既存の human E2E 成果物を変更せず、
`actual_candidate`・`diagnostic_counterexample`・`control` 別の manifest / HTML / KIF / JSON
を生成できる。actual candidate 0件も正常な空区分として扱う。分類は明示したレビューケースだけで決まり、
モデルスコアから自動決定しない。

変更: 既存△3二銀を diagnostic、通常の▲7六歩と△3三角を control とする manifest adapter、
区分別 export、履歴を含む response diagnostic cache key のテスト、CLI と公開 allowlist 対応を追加した。

未解決: actual candidate の研究上の追加指定、分類理由の承認、実験の再開判断。

レビュー対象KIF・HTML・JSON: `reports/response_set_review/` と
`exports/response_set_review/`。旧 `reports/human_e2e/` および旧 `exports/human_e2e/` は参照元として保持する。

確認点: 全テスト、manifest の区分と分類理由、actual candidate 空出力、同一SFENでも異なる履歴を分ける
cache key、公開除外ファイルが checkpoint に入っていないこと。

次の提案: この checkpoint をレビュー後、明示的な続行指示があれば次の軽量実装サイクルを決める。

運用状態: 小サイクル → テスト・公開物確認 → commit + push → STOP → 明示的続行指示待ち。

## Tactical falsification v2 human-review package checkpoint — 2026-09-10

Astra source checkpoint: `d58a9b3bef8e909d67fd452578277860cdfacb11`。
v2の新4ケースを人間レビュー用KIFへ変換し、旧reject 3例へのリンクを含む一覧を追加した。
23手目局面の▲７七角打と旧17手目の▲７七角を区別し、100k選択応手比較を全合法手ランキングと
誤記しない説明を付けた。研究判断、数値、分類、Human Policy、INCONCLUSIVEは変更していない。

確認: 全履歴・候補手・保存済み分岐の合法性、手番表示、内部表示語漏れ、旧control撤回説明を検査。
pytest 65件成功、既存表示lint成功。

運用状態: 小サイクル → commit + push → STOP → 明示的続行指示待ち。

## Tactical fixed-case KIF package checkpoint — 2026-09-10

Astra source checkpoint: `903f13a4c8a093709596e6716c35cce3dc071b5f`。
5件の固定例（除外3件、対照2件）を `exports/tactical_falsification_review/` に出力し、
一覧を `README.md`、人間向け要約を `reports/tactical_falsification/REVIEW.md` に追加した。
研究データ、判定、数値、分類、INCONCLUSIVEの結論は変更していない。

確認: 5件の履歴と候補手の合法性、△3二銀の10cp比較、対照例の1931cp/2328cp比較、
内部表示語の漏れ、重複注意書き、判定矛盾を検査した。pytest 59件成功。

運用状態: 小サイクル → commit + push → STOP → 明示的続行指示待ち。

## 明白な応手による固定例検証の人間向け報告 checkpoint — 2026-09-10

Astra元checkpoint: `903f13a4c8a093709596e6716c35cce3dc071b5f`。
`reports/independent_policy_validation/ASTRA_HANDOFF.json` と固定例の引き継ぎを根拠にした。

今回直したもの: `reports/independent_policy_validation/REVIEW.md` と `report.html` に、固定例の中心結論
`INCONCLUSIVE`、△3二銀の除外理由、3つの明白な駒損例と2つの駒交換対照例の意味、本番自動除外へ移行しない理由を記載した。
△3二銀の+3808、▲2二角成後+3681、単純差127cp、同条件での最善級との差10cp、対照例の1931cp/2328cpを区別して表示した。

内部データは変更していない: 研究結論、判定、数値、分類、モデル、指標、候補、JSON内部キーは変更していない。
表示のみを既存成果物から再生成し、新しい研究計算・engine解析・候補探索・Human Policy変更は行っていない。

確認対象: `reports/independent_policy_validation/REVIEW.md`、`report.html`、
`exports/response_calibration/` の固定例KIF。表示では「奇襲手としての判定」と「Human Policyの信頼性」を分離した。

テスト結果: 54 tests passed、`node scripts/check_calibration_review.mjs` 成功、Astra元ファイルのhash一致。

未解決事項: 毒入り駒取り、成立した捨て駒などへの独立した十分な検査例がなく、本番自動除外の安全性は未確認。
次の小規模奇襲探索とP_goodによる候補昇格はAstra判断どおりNO。

運用状態: 小サイクル → commit + push → STOP → 明示的続行指示待ち。

## 固定例KIFの判定・内部表現修正 checkpoint — 2026-09-10

今回直したもの: △3二銀KIFの「除外」と「保留」の混在を解消し、奇襲手としての判定を除外、
Human Policyの確率推定への注意を別説明として表示した。親PV、候補手後PV、評価値の意味を分け、
内部ID・生辞書・真偽値・`none`を人間向けKIFから除去した。3つのresponse calibration KIFを同じrendererで再生成した。

研究内容は変更していない: Astra checkpoint `903f13a4c8a093709596e6716c35cce3dc071b5f` の判定、数値、分類、
除外条件、Human Policy、研究結論は変更していない。元のJSON、metrics、analysis、Astra handoffのhashは一致した。

確認点: △3二銀の▲2二角成、10cp差、+3808/+3681の127cp単純差を保持し、対照例の表示も同じlintで確認した。
同じ注意書きは各KIF一回までに制限した。

テスト結果: pytest 55件成功、`node scripts/check_calibration_review.mjs`成功、Astra source hashes OK。

未解決事項: 本番自動除外の移行判断はAstra指定どおりINCONCLUSIVE。毒入り駒取り・成立した捨て駒の十分な独立検査例はない。

運用状態: 小サイクル → commit + push → STOP → 明示的続行指示待ち。

## Astra独立検証の人間向け報告 checkpoint — 2026-09-10

今回の入力: Astra checkpoint `f817675793949e1779216f30ec1fe1690d71efcd` と
`reports/independent_policy_validation/ASTRA_HANDOFF.json`。引き継ぎとanalysis/decisionの結論に矛盾はなかった。

今回直したもの: 独立検証の `REVIEW.md` と `report.html` に、検証目的、270局・250人・6,501着手、
相対改善の再現、取り返し83.6%対64.1%（19.5ポイント差）、駒得回収71.5%対50.9%（20.6ポイント差）、
次の小規模奇襲探索へ進まない理由を記載した。Human Policyの信頼性と、既存△3二銀の奇襲手判定は分離して表示した。

研究データは変更していない: model、係数、確率、評価値、指標、分類、候補、sampling、JSON内部キーは変更していない。
保存済み成果物を読み取り、表示のみを再生成した。独立検証標本での再fit、再評価、候補探索、engine呼び出しは行っていない。

人間が確認する成果物: `reports/independent_policy_validation/REVIEW.md`、`report.html`、
`exports/response_calibration/` の既存3KIF。主要表示に内部英語ID、生JSON辞書、True/False/Noneを出していない。

テスト結果: `node scripts/check_calibration_review.mjs` 成功、pytest 54件成功。

未解決事項: Astraが指定した通り、Human Policyの信頼性不足は残っており、次の小規模奇襲探索とP_good候補昇格はNO。

運用状態: 小サイクル → commit + push → STOP → 明示的続行指示待ち。

## Review metadata plumbing checkpoint — 2026-09-09

今回直したもの: KIF親局面PVのラベルを `parent_engine_best_pv` に修正し、候補後PVの
`[engine PV after candidate]` と区別した。review manifestは `positions.json` の
`position_id` から `parent_sfen`、`move_history`、`ply`、候補手、先後を解決するようにした。
履歴依存response診断用の `ResponseDiagnosticCache` を追加し、cache identityへSFEN、履歴、
候補手、応手、feature schemaを含めた。

テスト結果: 既存を含む40テストに今回の回帰テストを加え、全件pass。

生成成果物: `reports/response_set_review/` と `exports/response_set_review/` を修正後exporterから再生成した。
分類は actual_candidate 0件、diagnostic_counterexample △3二銀 1件、control ▲7六歩・△3三角 2件を維持した。
旧KIF・旧JSON・旧HTMLは変更していない。

Astraが次に使うAPI: `from surprise.response_cache import ResponseDiagnosticCache, response_cache_key`。
KIF exportは既存の `surprise.kif_export`、review生成は `surprise response-set-review` を使う。

未解決事項: response diagnosticでどの特徴量を計算するか、研究上の分類・ランキング、実験再開の判断。
これらはAstraの判断対象であり、このcheckpointでは変更していない。

運用状態: 小サイクル → commit + push → STOP → 明示的続行指示待ち。

## 人間向け表示整備 checkpoint — 2026-09-10

今回直したもの: 共通の `surprise.human_descriptions` を追加し、response calibration のKIF・HTML・
Markdownレビューと独立検証HTMLの表示を、対象（元の局面、調べる指し手、相手の応手、モデル値）を明記する文章へ更新した。
KIFの親PVと候補後PVを分け、support、fallback、shrinkage、tilt、判定保留の意味も説明するようにした。

内部データを変更していないこと: JSONの既存キー、内部ID、モデル、係数、評価指標、候補選抜、研究数値は変更していない。
既存metricsとreview JSONを読み取り、表示だけを再生成した。KIFは合法性を保つ既存分岐からコメントを置換した。

REVIEW.mdの場所: `reports/response_calibration/REVIEW.md` と
`reports/independent_policy_validation/REVIEW.md`。人間が最初に読む資料と詳細analysis・機械可読metricsを分離した。

テスト結果: 54 tests passed。主要な人間向け成果物に内部分類ID、`abstain=true`、`exact_support=`、
`calibration=exploratory_only`、旧PVラベル、内部feature名が残っていないことを確認した。

人間に確認してほしい成果物: `reports/response_calibration/review.html`、
`reports/response_calibration/REVIEW.md`、`exports/response_calibration/` の△3二銀・▲7六歩・△3三角KIF、
`reports/independent_policy_validation/report.html`、`REVIEW.md`。

運用状態: 小サイクル → テスト・公開物確認 → commit + push → STOP → 明示的続行指示待ち。
