# Standalone local research worker — Luna implementation task

これはLuna向けの仕事です。研究判断を変更せず、既定の計算をCodexやモデルの
稼働とは独立した通常のOSプロセスとして実行できるようにする。
大きなGUIは不要。まず1コマンド起動・進捗・停止・再開ができるCLI。

## Research contract (do not modify)

- Frozen PLAN.md and PROOF_PROTOCOL.md apply unchanged.
- Existing candidate_coverage.json / reply_coverage.json are inputs; no rescan.
- Existing YaneuraOu/NNUE/config/cache remain. No model/API/cloud calls.
- Deep budgets/stability tests/30-ply boundary stay unchanged.
- Proof uses the SAME mate_proof_hints.json and100,000-state bound per case.
- No threshold tuning, Human Policy, new seeds, production activation or ranking.
- An experiment completing with INCONCLUSIVE is completed execution, NOT a
  reason to retry/tune until YES. Execution status and research verdict differ.

## Existing entrypoints (cwd must be the real project root)

```bash
.venv/bin/python reports/trap_tree_coverage_v2/experiment.py deep
.venv/bin/python reports/trap_tree_coverage_v2/prove_mate.py
```

Ordinary mate checks already completed: do not rerun `experiment.py mate`.
Do not run finalize.py automatically: Astra must inspect results and interpret
them before final research handoff. Publication clone is not the execution root.

## Required implementation

1. A launcher with run / status / stop / resume commands. Prefer one worker
   supervising these two stages sequentially; no assistant polling required.
2. Single-instance advisory lock for this cycle, released automatically on
   process death. Initial migration MUST verify old analysis processes stopped;
   the already-running legacy commands do not participate in a new lock.
   Never broadly kill Python/engine processes belonging to other work.
3. Durable progress/logs: stage, completed/total requests or cases, current
   position+budget, elapsed time, cache hits, last error. Label10k proposal-only.
   Progress writing is plumbing, not new scientific scoring.
4. Safe stop: finish/save current engine query when possible, then stop before
   the next. Immediate interruption may lose only the unfinished query; preserve
   existing cache/evidence. Handle signals and restore pushed proof boards.
5. Resume only unfinished work. Deep already caches each completed request.
   Add proof CASE-level resume: a completed cutoff/INCONCLUSIVE attempt is NOT
   unfinished. An interrupted case can restart from its frozen hints; clearly
   disclose that mid-case proof frontier resume is not implemented. Do not invent
   a new search order/frontier algorithm in this task.
6. Preserve proof root identity from saved history. The original cutoff process
   printed a descendant SFEN; retain correction provenance, do not change the
   searched case or silently rerun completed evidence.
7. Record scientific plan/input/engine/NNUE fingerprints and implementation
   revision. Refuse incompatible inputs rather than mixing results.
8. On completion write a small execution manifest and exit. No next research
   cycle or automatic model invocation. Notify user that Astra review is needed.
9. Test locking, resume, interruption, input mismatch and successful execution
   with scientifically INCONCLUSIVE results using mocks/small fixtures.

## Review/publication

Checkpoint worker source/tests/instructions before long execution. Use existing
public allowlist rules: no SQLite, binaries, NNUE, credentials or raw human data.
GitHub publication is separate from computation; do not build an unattended
credential-dependent auto-push feature into this MVP.

User workflow: Astra freezes research -> user starts worker -> user can leave
the terminal/process running without Codex -> worker finishes -> Astra reads
artifacts and makes the research decision -> checkpoint -> human review.

This file is a specification, not a claim that the standalone launcher already
exists. The underlying analysis scripts already run from a normal terminal.
