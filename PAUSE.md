# Research paused — 2026-09-08

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
