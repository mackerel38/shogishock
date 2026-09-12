# Coverage v2 — completed execution, research INCONCLUSIVE

Question: generic recovery of quiet candidates and reasoned non-best replies,
with stable tactical confirmation on the exposed B4e benchmark.
Plan9634bb8; worker/source checkpoint bda84d13a39d30c3e8c92b2c841a5db798802a47.

## Execution and integrity

User-run deep and proof stages completed with exit0 in7234.85 seconds
(about2h00m35s), without stop/resume or errors. Input fingerprints and result hashes
match. No new engine calls were made for interpretation. Both proof cases were
already complete and skipped, not rerun until success.

All6 comparison groups reached80M; **0/6** passed the frozen two-transition
whole-group CP/PV stability test. Recomputing saved transitions reproduced their
flags. Some individual lines and best-move rankings persist, but that does not
make the whole comparison stable. Thresholds and budgets were not changed.

## Coverage: target recovery YES; specificity unvalidated

| Opponent root move | Candidate union/legal | Reply union/legal after B6g+ | Deep candidates/replies |
|---|---:|---:|---:|
| R2d (▲2四飛) |48/62|76/106|9/20|
| R3e (▲3五飛) |50/62|76/104|10/17|
| R3f (▲3六飛) |49/58|65/100|9/17|

Totals147/182 candidates (80.8%),217/310 replies (70.0%);28 candidate and54 reply
options progressively compared. Pool sizes are NOT human choice probabilities.
Geometry is deliberately broad; specificity remains unvalidated. Named review
targets were not inserted into the union, only into predeclared deep comparisons.

P*2c afterR2d was already in old MultiPV but lost to top1+forcing selection.
B6g+ afterR3f was absent from the old saved MultiPV3/slate. The new generic
capture/promotion tags retain it; it ranks first in all five confirmation budgets
within the tested subset. This is a coverage omission, not proof of global best.
R2a+ afterR2d was already displayed previously; do not claim it as a newly recovered
omission. G7i/G8g were omitted from the old displayed slate, not necessarily from
its all-legal screening. Broader screening also changes the proposal reference.

## Tactical contrasts

Raw evaluations always use sente perspective. Values below are80M explicit-child
measurements in the frozen compared subset; gaps remain provisional for unstable
comparisons.

- AfterR2d: P*2c=+622, S2b=+1095, B6g+=+1331, R8h+=+2300.
  P*2c ranks first at all five budgets, but its5M→20M change was188cp.
- AfterR3f: B6g+=-295 versus R8h+=+468 (763cp difference), Bx3f=-68.
  B6g+ ranks first at all five budgets, but its last CP values are
  -197→-90→-295: not a fully stable score.
- AfterR3e: B6g+=-153. This individual line passes its last two CP/first-PV
  checks, although the full comparison group does not.
- AfterR2d/B6g+: Gx6g=+1296, G8g=-1513, immediateR2a+=-2174.
  Ordinary recapture is best tested at all five budgets. Severe punishment of
  other replies does not justify promoting B6g+ here.
- AfterR3e/B6g+: best testedB*7g=+34, Gx6g=-770, G8g=-1893.
  Gx6g has persistent adverse scores and a stable individual tail, but its804cp
  gap to best remains provisional: B*7g changed161cp in the last transition.
- AfterR3f/B6g+: best testedB*7e=-251, Gx6g=-835, G7i=-1660, G8g=-1513.
  Do not transfer the R2d/R3e mate claim to this different rook position.

G7i has a gold-saving motive; G8g also attacks the rook. Neither describes a
successful defense or measured frequency. ImmediateR2a+ is legal only in theR2d
reply case here; timing differs from recapturing first. The disputed earlier
B*7g entry is a different position from B*7g afterB6g+.

## Mate evidence: engine reports, no all-defense certificate

Both R3e/B6g+/G7i and R2d/B6g+/G7i searches BEFORE R8h+ report mate19 at80M,
with legal terminal PVs. Mate distances were not stable across budgets.
Explicit AFTER-R8h+ searches instead end in CP(-8062 and-6370 respectively).
This inconsistency is unresolved; CP does not establish absence of mate.

Both all-defense attempts reached the100,000-state bound (cutoff-detecting visit
100001). Proven substates2549 forR3e and3619 forR2d; root certificates0/2.
Both results are INCONCLUSIVE, not no-mate findings. Do not claim a certified
19-ply upper bound, shortest19-ply mate, or refutation of the human claim.

Historical erroneous descendant SFEN labels remain unchanged in the raw proof
file. The derived handoff reconstructs roots from saved histories, preserving
original labels and correction provenance. No proof search was repeated.

## Decision and handoff

Overall **INCONCLUSIVE** for coverage with reliable tactical confirmation.
Target recovery is useful positive evidence. Motive specificity, global defense
coverage, full comparison stability and mate certification remain unresolved.
This is not failure because computation took two hours; no next budget expansion,
unknown seed scan, rule change or production activation is authorized.

All889 saved PVs replay legally. Original3 obvious-loss regressions still reject.
The cycle ledger contains670 non-cache-hit records and219 cache-hit records,
including pre-worker work; these are NOT new calculations in this interpretation.
No Human Policy, new human data or actual-candidate promotion.

Raw coverage/deep/proof/hints/ledger/manifest remain byte-identical.
ASTRA_HANDOFF.json is the derived interpretation; verification.json records checks.
Luna should render only the four short review groups in LUNA_TASK.md, then human
review. No Luna agent invoked. STOP.
