# ShogiShock environment handoff

Status: MVP execution base implemented and locally verified on 2026-09-08.

## Research handoff added 2026-09-08

Research is paused at the user's request. Read `PAUSE.md` and `RESEARCH.md` before continuing.
The existing engine and NNUE were reused. The current schema-5 shallow pass run completed 148 positions
and 6,314 candidates. Wrapper validity fixes and invalid earlier diagnostic runs are documented in
`PAUSE.md`. Human Policy and final candidate conclusions remain pending.

## Project and engine

- Project root: `/home/mackerel38/shogishock`
- YaneuraOu source: `third_party/yaneuraou`
- Upstream: `https://github.com/yaneurao/YaneuraOu`
- Source commit: `81f3b1fe1c1de385a1b2a522c9b47cd3075d044e` (`81f3b1f`)
- Built engine: `engines/yaneuraou/yaneuraou`
- Build: clang++, tournament target, `YANEURAOU_ENGINE_NNUE`, `TARGET_CPU=SSE42`
- Binary hash: run `sha256sum engines/yaneuraou/yaneuraou`; the cache also fingerprints it automatically.
- Built binary SHA-256: `10a220dd34fc4def0a9862d37f0bb0bd2faec219514b630b908c3c6388babeea`

YaneuraOu is GPLv3. The upstream README and build wiki document the source license and NNUE loading model: https://github.com/yaneurao/YaneuraOu and https://github.com/yaneurao/YaneuraOu/wiki/%E3%82%84%E3%81%AD%E3%81%86%E3%82%89%E7%8E%8B%E3%81%AE%E3%83%93%E3%83%AB%E3%83%89%E6%89%8B%E9%A0%86

## Evaluation function

- Name/version: 水匠5 (Suisho5 release asset; standard NNUE HalfKP256)
- File: `assets/eval/nn.bin`
- Source: `https://github.com/yaneurao/YaneuraOu/releases/download/suisho5/Suisho5.7z`
- SHA-256: `768068f0d534a0605a3d38bcd143de6bbca820d5f1c95a14d40863e5b7892d76`
- Usage terms: the release is publicly downloadable from the upstream project; retain the upstream archive/license notices when redistributing. Do not substitute restricted or paid evaluation files.

## Local machine

- Linux x86_64, Intel Pentium Silver N6000 @ 1.10GHz
- 4 CPUs / 4 cores / 1 thread per core; 7.5 GiB RAM; 79 GiB filesystem, 36 GiB free at setup
- CPU flags include SSE4.2; no AVX, AVX2, or AVX512
- git, gcc, clang, make, Python 3.14.7 available; cmake was not installed
- Local benchmark: `890617 nodes/sec` with 2 threads, 100,007 searched nodes, 0.1123 seconds (`surprise benchmark`).

## API and configuration

- Wrapper import: `from surprise.engine import Engine`
- Position import: `from surprise.position import Position`
- API: `evaluate(position, nodes)`, `search(position, nodes, multipv=1)`, `evaluate_after_move(position, move, nodes)`, `get_best_move(position, nodes)`, `Position.apply_move(usi)`, `Position.virtual_pass(attacker_side)`
- Config: `config/default.yaml`
- Cache: `data/engine_cache.sqlite3`, keyed by SFEN, search limit, MultiPV, engine binary hash, evaluation directory, threads, hash, and options
- Position library: `python-shogi`; score convention is fixed sente perspective (positive = sente advantage). Mate remains `score_type="mate"` with `mate_distance`.

## Vast.ai

Use the `Dockerfile` or `scripts/setup.sh`. Choose x86_64 CPUs with SSE4.2, stable sustained performance, adequate RAM/storage, and good CPU dollars per node/sec. Persist `data/` and any exported result files on a mounted volume. Reuse the same cache for resume. `Engine` commits each completed request and exits cleanly on context-manager close; worker orchestration should catch SIGTERM and close the engine.

## Verified commands

`./scripts/setup.sh` completed dependency installation, reused the existing build, created the evaluation link, and ran the setup checks. `surprise engine-test`, `surprise benchmark`, and `pytest` are the required follow-up checks.

Known limitations: setup currently assumes Linux tools `clang++`, `make`, `curl`, and `bsdtar`; the source build is not pinned to a release tag because upstream current source was requested. MultiPV is exposed and parsed; a later scan worker should implement per-move evaluation fallback when a deployment reports only one PV. Graceful batch checkpoint orchestration belongs to the later scanner, while the engine cache itself is incremental and resumable.

## ShogiHome export handoff

- Export module: `surprise.kif_export`
- CLI: `.venv/bin/surprise export-shogihome --input reports/pass_pilot --output exports/shogihome --limit 10`
- Single candidate: add `--candidate-id <candidate_id>`
- Output: UTF-8 branching `.kif` plus a same-stem `.json` warning sidecar
- Internal model: `VariationNode` tree; candidate, engine PV, and optional audit/obvious/confirm/deep responses are merged by USI move
- Existing ranking, score, report, and pilot files are read-only inputs
- ShogiHome: `tools/shogihome/ShogiHome-1.29.0.AppImage`, official Linux AppImage, SHA-256 `4b79e2ae833a07d7439ba58decbac4ec1b2a7098b117b4f5debdd71a6d6474ba`
- Version check: `ShogiHome-1.29.0.AppImage --appimage-version` returned `Version: effcebc`
- GUI visual QA: the binary is installed and executable, but GUI playback was not automated because no display session was available

## Response-set calibration review handoff

- CLI: `.venv/bin/surprise response-set-review`
- Aggregate manifest: `reports/response_set_review/review_manifest.json`
- Separated HTML: `reports/response_set_review/report_actual_candidate.html`,
  `report_diagnostic_counterexample.html`, and `report_control.html`
- Separated replay exports: `exports/response_set_review/{actual_candidate,diagnostic_counterexample,control}/`
- Classification source: the explicit `MANUAL_REVIEW_CASES` table in `surprise/response_review.py`.
  It is not inferred from model scores, features, splits, or rankings. `actual_candidate` may be empty.
- Existing `reports/human_e2e` and `exports/human_e2e` files are preserved as read-only sources.
- History-dependent response diagnostics must use `history_aware_response_cache_key`, which includes
  move history as well as SFEN, candidate move, and reply move. This protects recapture/repetition-sensitive
  values from an SFEN-only cache collision.
- Response diagnostic cache API: `from surprise.response_cache import ResponseDiagnosticCache, response_cache_key`.
  Use `get_or_compute(...)` with `sfen`, `move_history`, `candidate_move`, `reply_move`, and `feature_schema`.
  This cache is separate from the engine cache.
- KIF parent PV label: `parent_engine_best_pv`; candidate continuation remains labeled
  `[engine PV after candidate]`.
- Review manifest resolves parent metadata from `positions.json` by `position_id`, including
  `parent_sfen`, `move_history`, `ply`, `candidate_move`, and `attacker_side`.

## Human-facing output handoff

- Shared prose layer: `surprise.human_descriptions`.
- Regeneration command: `.venv/bin/python scripts/render_human_facing.py`.
- First-read summaries: `reports/response_calibration/REVIEW.md` and
  `reports/independent_policy_validation/REVIEW.md`.
- The renderer reads existing JSON/KIF/metrics and performs no engine calls, model fitting,
  probability recalculation, candidate scan, or research selection.
