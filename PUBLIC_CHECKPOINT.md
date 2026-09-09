# Public research checkpoint — 2026-09-09

## Latest response-set calibration cycle

Read [response calibration analysis](reports/response_calibration/analysis.md) first.
Calibration improved on reused held-out tests, but recapture/material recovery remain underpredicted.
△3二銀 is still a diagnostic false positive. Actual 0 / diagnostic 1 / controls 2; all cases abstain.
Review [HTML](reports/response_calibration/review.html), [JSON](reports/response_calibration/review.json),
and three classified KIFs under `exports/response_calibration/`.
No new games or engine calls. **STOP after push; human review and explicit continuation required.**
Previous checkpoint details below are retained as history. No new raw/SQLite data is published.

Repository: https://github.com/mackerel38/shogishock (**public**).

## Current stage

Bounded human-policy/seed experiment complete. **No large scan, no further deep expansion, no Vast.ai.**
Read [RESEARCH_V3.md](RESEARCH_V3.md), then the four linked research reports.

## Completed / important findings

- Preserved Luna's ShogiHome integration; corrected KIF branch start numbering and added human metrics.
- 700T/WCSC29 book audit: 30,421 / 75,192 / 146,417 distinct reachable book positions at 12 / 16 / 20 ply.
- Separate human sample: 612 games, 457 players, maximum 12 accepted games per participant; biased convenience frame, not general population.
- Game/time/strict-player held-out baselines; corrected a sampling/split hash-domain dependency, retaining the old diagnostic locally.
- Four book parents, 144 legal candidates, 14 obvious-reply demotions, 1 redundant-nonpromotion demotion; six full response evaluations at 10k.
- NLL improved, but capture-event probability was 8.1% predicted vs 21.6% observed on held-out capture-available positions.
- A free bishop capture received only 3.03% model probability, producing a spurious +4050cp attacker human_gap.
  Therefore the model is **not approved for large-scale P_good ranking**.

## Public artifacts

- `reports/terashock_seed_audit/`: provenance, structural counts, seed-depth decision.
- `reports/human_pilot/`: sampling plan and aggregate bias/reach report.
- `reports/human_policy_v2/`: current held-out metrics, calibration, conditional-event falsification.
- `reports/human_e2e/`: generated candidate/response evaluations, per-side HTML, analysis.
- `exports/human_e2e/`: six branching KIFs, all branches legally replayed. User GUI review still required.
- `PUBLICATION_MANIFEST.json`: public paths/hashes and redaction scope.

## Resume on the original machine

Existing engine, NNUE, venv, raw games and SQLite remain local. Do not rebuild or overwrite them.
Use the commands in `RESEARCH_V3.md` only to reproduce the bounded checkpoint; successful API payloads and engine cache are reused.
Before any new acquisition or scan, commit+push the design/handoff following `CHECKPOINTING.md`.

## Resume from GitHub only

The public code, analyses and generated KIF/HTML are sufficient to understand findings and continue research design/review.
**The private/raw training snapshot is deliberately not included.** Exact retraining on these 612 games requires the preserved local inputs;
do not claim bit-identical dataset reproduction from the public aggregates. On another machine, arrange authorized access to those inputs,
or define a new sample/output and collect it through the documented official API under checked terms.
Do not reconstruct training data from the book or treat published book/candidate counts as human frequencies.

Public `positions.json` for the E2E omits raw book move/count/depth records but retains fields needed for KIF replay.
The original book ZIP/large extracted universe is not distributed here. 700T redistribution terms remain unconfirmed;
the separately published MIT new-petabook is a different version, not a silent replacement.
Raw human games, SQLite, credentials, binaries, NNUE, venv and AppImage are excluded.

## Next task / caveats

Validation before publication: 38 tests pass from the public source-only tree using the existing environment;
both per-side HTML scripts render six board SVGs each; all six E2E KIFs replay legally;
P_good bounds are valid and the preserved schema-5 baseline hashes are unchanged.

Inspect the KIF counterexample; improve or abstain on low-support fallback; test capture/recapture/material-recovery probability on independent data.
Do not equate low top-label ECE with calibrated P_good on novel tactical positions.
No novel surprise system or practical win-rate increase has been established. Negative findings are retained as formal results.
