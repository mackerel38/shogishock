# Coverage v2 — INTERIM, confirmation not complete

Do not treat this file as the final cycle decision. Frozen plan9634bb8;
research/display bases437a7ca/d5be34c. Human Policy and production gate unchanged.

## Established coverage findings

Three candidate positions:147/182 legal moves retained. Three B6g+ reply
positions:217/310 retained. These are pool sizes, NOT human frequencies.
P*2c, B6g+ afterR3f, G7i/G8g and legal R2a+ arise from general motive tags,
not named generator exceptions. Specificity remains unvalidated; retaining
70-81% of legal moves is broad coverage, not precise human selection.

Old P*2c omission: the move was already in MultiPV but lost to the top1 plus
forcing quota. Old B6g+ afterR3f: absent from the saved MultiPV3 and selected
slate. The new union retains both without consulting new scores (pawn-drop
and capture/promotion tags). Wider all-child screening also increases engine
work per parent; do not attribute all ranking differences solely to a heuristic.
R2a+ afterR2d was already displayed by the old rule. Gold retreats were omitted
from its displayed slate, though old all-legal10k response data existed.

## Tactical evidence currently unresolved

Both human G7i/R8h+ hypotheses produce mate19 PVs when searched BEFORE R8h+
at80M nominal, with legal checkmate endpoints. Starting from the explicit
AFTER-R8h+ child at80M instead yields CP(-8062/-6370). Intermediate searches
also change mate distances. This is ordinary-search inconsistency, NOT proof
of no mate and NOT a verified shortest19-ply mate. Supplementary all-defender
proof attempts use fixed hints and checkmate-only leaves; failure is inconclusive.

First proof attempt(R3e) reached the100,000-expansion bound without a complete
certificate(2,549 proven substates, but no proof of the root). The cutoff check
increments the visit counter to100,001. This does not refute the human mate claim.
R2d proof attempt remains pending. A cutoff-output bug left the printed SFEN at
a search descendant; finalization restores the root from the saved history and
preserves the erroneous label as provenance. The searched history/outcome do not
change. A board-restoration regression test was added;11 prototype tests pass.

Candidate R2d comparison completed through80M: P*2c ranks first in the compared
subset at all5 levels. Its CP values:442,573,414,602,622. At80M the next tested
candidate S2b is1095; B6g+ is1331, R8h+2300 (all raw sente perspective).
The best ordering persists, but the frozen whole-group two-transition CP/PV
criterion FAILS. Even P*2c changed188cp at5M->20M, then20cp at20M->80M.
Do not rename this a fully stable comparison. Remaining groups are pending.
10k remains proposal only. An easy adequate recapture may refute B6g+ afterR2d
despite a severe trap against G7i; that contrast is not candidate approval.

## Interpretation boundaries

- Entry plausibility (especially B*7g) is separate from conditional severity.
- Gold-saving tags describe attempted defense, not successful defense.
- Rare-but-reasoned replies can matter even without a frequency estimate.
- Original3 obvious-loss regressions remain reject; no reinstatement or production activation.
- Only the existing B4e benchmark is used. New candidates at22ply/replies23ply;
  later moves resolve already-started tactics rather than launch new searches.
- Final decision/short review branches will be in ASTRA_HANDOFF.json after completion.
