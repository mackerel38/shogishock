# Tactical falsification v2 — prospective gate freeze

Research question: can the unchanged obvious tactical gate retain plausible opening traps/sacrifices from short, defensible histories while rejecting the three established bishop-loss diagnostics?

Research source: 903f13a4c8a093709596e6716c35cce3dc071b5f. Latest reviewed presentation lineage: 86595f9a0fb8c22a68a47e0532a311ce6bc6de8a (includes full-history KIFs and side-display fixes). Local .git is unavailable; publish narrowly through an isolated clone, preserving Luna changes.

Previous controls 7g3c+ and 3c7g+ remain historical diagnostics only, NOT production false-negative safety evidence. Human review identified unnatural 17.B7g and repeatedly missed major rook tactics. Previous INCONCLUSIVE remains valid.

## Frozen gate, before new engine results

Reuse exact classifier in reports/tactical_falsification/prototype.py, SHA256 ab484b3318d5833c57ac0e8cbcccf0154239b2a74baf6c3754a4e27d16f78ed3, and obvious.py SHA256 290bdc28ed8eb9bcf11160fa84a93fc8961df22d36e6829cdf65cf8ad29c3f26.

- Strong naturalness proxy: free bishop/rook including promoted major with no legal immediate recapture; OR immediate recapture AND existing material_recovery_proxy (no immediate recapture OR victim value > mover value).
- Merely capturing candidate, pawn contact, generic capture/material recovery, check or forcing appearance is insufficient alone. No new strong signal.
- ALL legal replies evaluated at identical nominal budget; best explicit child-response reference, never root-child comparison. CP remains sente-oriented.
- Attacker sign s=+1 sente/-1 gote. gap=s*(reply-best). Main threshold gap<=100cp AND defender advantage -s*reply>=300cp AND strong witness => reject.
- Incomplete/duplicate coverage, bounded/unknown score or defender-winning mate => needs_verification in the CP-only classifier. Exact attacker-winning mates are dominated by finite CP for defender; never fake mate CP.
- Sensitivity grid stays gap50/100/200/300 x defender advantage300/500/1000. No choice or tuning from new results.
- not_falsified is neither soundness proof nor actual-candidate promotion.

## Selection and prospective labels

Before evaluating each new case, record full history, candidate, natural-looking reply, expected_class=should_keep and hypothesized category in selections.json. This is a hypothesis, not a guaranteed label. Reject unsuitable histories rather than retrofit expected labels; retain failed selections and reasons. Aim 2–4 proposals total; no numerical quota if quality is insufficient.

Use short established opening motifs where a tactical account can be stated without engine scores. Prefer <=20ply; explain longer prefixes. Source lookup is allowed for choosing a documented motif, not harvesting datasets. Include the user's R8i+ / R2b+ / Sx2b / P*8b as an exploratory seed, explicitly NOT a validated natural control; compare the P*8g repair and a few engine-proposed alternatives. Do not transplant the old long control and call it clean.

Natural-history audit: examine every prefix with cached/new10k roots, and selected-vs-best explicit child pairs at flagged deviations (>300cp root swing or apparent missed forcing move). These thresholds flag human review, not certify naturalness. 100k only on a few ambiguous pairs; no tuning or branch repair after results to manufacture validation success.

## Allowed computation and stop limits

Existing YaneuraOu/Suisho5/wrapper/cache unchanged. 10k default; <=4 new candidate full-response sets, <=12 exploratory alternative moves total, <=12 new100k requests, <=600 new engine requests overall. Prefix probes and same-budget comparisons included. Record requests/cache hits/nodes. No1M/10M, mass scan, dataset acquisition, Human Policy execution/training, independent270 reuse, ranking/seed changes or Vast.

A small root MultiPV shortlist is exploratory only; evaluate shortlisted child positions identically before numeric comparison. A full-response set is for a selected candidate, not a scan across candidate moves. No claimed human difficulty from engine rank alone.

## Decision criteria

YES requires all three established reject regressions, credible natural-history controls, no demonstrated false rejection, reasonable sensitivity stability and substantive poison/sacrifice coverage. Genuine valid trap/sacrifice rejected => evidence toward NO. Inadequate/contaminated controls, uncertain tactical results or shallow instability => INCONCLUSIVE. Do not promote to actual candidates or authorize production scans. Report A (bad apparent reply), B (compensation after good reply), C (poison) only when supported; overlap allowed.

Artifacts: selection record, complete analysis evidence, PLAN/analysis/results/ASTRA_HANDOFF, Luna instructions for deterministic presentation if needed. Commit+push plan before engine work, final checkpoint+remote SHA verification, STOP for human review.
