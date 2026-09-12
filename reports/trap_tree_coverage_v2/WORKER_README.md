# Standalone coverage-v2 worker

This worker runs the already frozen protocol without Codex, a model, credentials,
network access, or automatic publication. Execution completion is **not** a
research verdict. No engine/NNUE/environment replacement is performed.

## Commands (normal Linux host terminal)

```bash
cd /home/mackerel38/shogishock
./scripts/shogishock-worker run
```

From another terminal, in the same directory:

```bash
./scripts/shogishock-worker status
./scripts/shogishock-worker stop
./scripts/shogishock-worker resume
```

`run` adopts the existing scientific ledger. If a worker session already exists
but is unfinished, use `resume`. A completed session is a no-op; it does not
retry scientifically INCONCLUSIVE results. Alternative entry point:
`.venv/bin/python scripts/shogishock_worker.py <command>`.

To close the terminal while computing, use **nohup** (the one recommended
background method for this MVP):

```bash
cd /home/mackerel38/shogishock
nohup ./scripts/shogishock-worker run > reports/trap_tree_coverage_v2/worker_console.log 2>&1 < /dev/null &
```

After a stop, use the same command with `resume` instead of `run`. Do not start
both. `status` is sufficient to monitor it; no assistant/model polling is needed.
The computer must remain powered on and awake; this is not an auto-start service.

## Exactly what runs

1. `experiment.py deep`: only remaining frozen comparison levels/requests.
2. `prove_mate.py`: only remaining proof cases, with the existing frozen hints.

The ordinary `mate` stage is already complete and is never launched. Neither
`screen`, `finalize.py`, new candidates, Human Policy nor next-cycle work is run.
No new move after ply30 is generated; post30 continuation is tactical proof only.
The original budgets, comparison selection, stability criteria, proof search
order and 100,000-state limit are unchanged. The existing proof implementation
counts the cutoff-detecting visit as100001; this has not been changed to extend
the search. The worker never classifies mate evidence or activates production.

## Lock and old-process migration

Linux `flock` is held for the entire session. Patched direct stage invocations
also acquire the same lock. The lock file can remain after exit; do not delete
it to bypass a lock. A stale PID file is not the authority. The supervisor
passes the lock's open file description to its stage child; if the supervisor
dies, that child keeps exclusivity until it reaches a safe stop boundary.

Before any stage the launcher checks the host process table for old invocations
of this project's `experiment.py` or `prove_mate.py`. It refuses and reports
matching PIDs/commands rather than killing them. Use the normal host terminal,
not an isolated PID namespace or the `/tmp` publication clone. Existing old
scripts started before this patch do not obey its cooperative stop mechanism.
The previously identified legacy deep parent and its engine were stopped during
migration; no production long run was started to test the worker.

## Stop/resume semantics

- `stop` atomically requests cancellation for the current run ID. It does not
  send a broad kill signal. SIGINT/SIGTERM/SIGHUP to the supervisor or patched
  stage are also cooperative: signal handlers set a flag, not an exception in
  the middle of a JSON write or board mutation.
- A current engine query may take a long time. It finishes, is committed to the
  existing cache/JSON ledger, and then stops before the next query. Group-level
  comparison rows can be incomplete: saved individual requests are reused.
- Completed deep levels are skipped. A full80M endpoint is completed execution
  even if its saved stability flag is false. No retry-until-stable behavior.
- Proof cancellation unwinds board pushes through `finally`. Only complete
  case rows are saved. A completed cutoff/INCONCLUSIVE case is skipped on resume.
  **There is no mid-case proof-frontier resume**: an interrupted case restarts
  from its original root, the SAME hints and bound. Earlier complete cases stay.
- Historical proof rows with a descendant SFEN label are preserved verbatim;
  case identity is checked using the saved move history. This worker does not
  correct their scientific metadata. Astra must inspect that provenance later.
- If killed with SIGKILL, power lost, or a child crashes, the current unfinished
  query may be lost; already saved evidence/cache remain. Atomic replacement and
  fsync are used before the script acknowledges a saved query or case. Hardware
  failures/disk corruption are outside the guarantee.
  SIGKILL of the stage itself can also leave an orphan engine process; inspect
  exact PIDs if this happens. The worker does not perform broad process cleanup.
- A hung engine query has no new automatic timeout/kill policy. Stop can wait
  indefinitely for it. Inspect the exact processes before manual intervention;
  never broadly kill Python or YaneuraOu. A surviving child holds the lock.

## Fingerprints / preserving evidence

`worker_contract.json` pins the plan, proof protocol, worker specification,
coverage inputs, frozen proof hints, experiment/proof sources, imported research
helpers, worker sources/launcher, engine config, engine binary, NNUE hashes and
runtime/dependency versions. Hashing does not launch the engine. The engine's
existing path/hash conventions are reused. `worker_revision` is a content hash
of the implementation sources, not a guessed Git SHA in this metadata-less
execution workspace.

At first run the ledger's engine/NNUE/plan/thread/hash identities are checked and
existing group/case structure is validated by the scripts. Runtime state records
the same fingerprints; resume refuses mismatches. Completed stage output hashes
are also checked. Do not edit source/config/inputs during execution. There is no
`--force` or automatic fingerprint refresh. If inputs or a completed output
change, stop and ask Astra to inspect; do not delete state to bypass the guard.

Initial adoption necessarily uses the already existing ledger provenance; it
cannot retroactively prove how historical queries were run. No historical
evidence is recomputed just to attach the new worker fingerprints. Scientific
scores, thresholds, hints and verdicts are never rewritten by the supervisor.

## Progress and output

Runtime files in this report directory:

- `worker_state.json`: session/stage, current case/position/budget, active elapsed
  seconds, completed stage cases/groups, ledger request count, cache hits, errors,
  stop request, fingerprints and child PID. Request/cache counts describe the
  **whole existing ledger**, including historical requests; cache hits are their
  stored `cache_hit` provenance, not a claim that every resumed lookup ran an engine.
- `worker_event.json`: single stage writer; supervisor merges telemetry into state.
- `worker_stop.json`, `worker.lock`: control files, not research evidence.
- `worker.log`: subprocess output and stage launches; `worker_console.log` is
  the optional nohup console redirection.
- `worker_manifest.json`: execution outcome, stage exit codes, timestamps,
  fingerprints, result hashes, interruptions/resumes; `research_verdict=null`,
  `requires_astra_review=true` even after a successful execution.

State/manifest timestamps are Unix seconds. Elapsed time is active supervisor
time across resumes, not time spent stopped. Progress after SIGKILL can be stale
until resume. `status` checks the actual advisory lock as well as saved state.

Runtime files are ignored by Git. The worker never commits/pushes or uses tokens.
Astra can deliberately publish a reviewed manifest later using an explicit
allowlist (`git add -f` for that manifest), without runtime PID/lock/stop files.
No binaries, NNUE, SQLite, raw human data, or credentials are part of this patch.

## Short tests only

```bash
.venv/bin/python -m pytest -q tests/test_research_worker.py
.venv/bin/python -m unittest discover -s reports/trap_tree_coverage_v2 -p 'test_*.py'
.venv/bin/python -m pytest -q tests/test_position.py tests/test_engine_parsing.py tests/test_cache.py
```

Worker tests use temporary directories, fake queries/subprocesses and tiny proof
fixtures. No long engine work is needed. They cover lock lifetime/second refusal,
status, safe stop, signals, supervisor death, cached-query resume, completed
stage skip, INCONCLUSIVE case skip, interrupted-case restart, incompatible
fingerprints/artifacts, child failure and an unevaluated research verdict.

## After completion: STOP

Resume Astra to read `worker_manifest.json`, `deep_checks.json`,
`mate_proof_checks.json`, and `engine_evidence.json`. Astra—not the worker—will
interpret stability/mate evidence, produce the research decision/ASTRA_HANDOFF,
and checkpoint the results for human review. No research YES is implied by exit0.
