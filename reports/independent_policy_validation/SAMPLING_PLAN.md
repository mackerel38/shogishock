# Independent confirmation — frozen acquisition plan, 2026-09-09

Status: PRE-ACQUISITION. This document is not a completed validation report.
Scope: frozen response-set policy only. No candidate scan, engine call, book expansion,
KIF candidate generation, P_good promotion, deep, or cloud compute.

## Frozen model and hypotheses

Source checkpoint: 742432c1b8e26664c7cae9fb560ab55a6f608e40.
Primary model is the previous time-train policy plus continuous shrinkage k=5 and
the saved time differentiated-tilt coefficients. Comparator is the same frozen
time-train policy with old support threshold 2, alpha=5, temperature=1.
The saved player and game model pairs are predeclared sensitivity analyses, NOT
alternatives from which a new winner can be chosen. All see the same new validation sample.

Freeze old sufficient statistics (pop/exact/prefix/chosen/available), shrinkage, tilt
weights, feature definitions, code, input/split hashes, calibration status and decision
criteria. Reconstruct statistics only from OLD train rows before acquisition; serialize
them once. Never rebuild or refit using new games. Do not invoke response_calibration.run
or human_policy.run during this confirmation cycle. Snapshot contains no new labels.

All seven sets remain exactly as in ../response_calibration/PLAN.md. Five required primary
reported sets include high_value_capture. The inherited relative improvement gate is unchanged:
mean Brier across the original four gate sets improves, NLL does not worsen by >0.02,
and none of those four set Briers worsens by >0.01. Report it separately for time and
player frozen models; do not substitute game if player fails. Report high_value_capture
without inventing a post-result threshold or silently adding it to the old four-set mean.

There was NO previously validated absolute response-set ECE cutoff authorizing promotion.
Do not invent one after seeing confirmation data, nor reinterpret relative improvement
as adequate absolute calibration. Keep abstention and candidate_promotion_allowed=false.
The inherited all-abstain policy cannot be silently relaxed inside this cycle.

## Source and sampling frame

Official Lishogi API only. Rechecked on 2026-09-09:
- https://lishogi.org/developers welcomes HTTP API use.
- https://lishogi.org/terms-of-service permits educational/developmental uses subject to
  service rules and reasonable infrastructure load; this is not raw-data redistribution permission.
- https://raw.githubusercontent.com/WandererXII/lishogi/master/ui/@build/static/assets/doc/lishogi-api.yaml
  documents public user game export, perfType=realTime, since/until/max and newest-first order.

Use official popular-team listing pages 2,3,4, each once, and the public member endpoint
for each distinct team on those pages, excluding lishogi-bots. No top-player endpoint or
replacement teams chosen after seeing results. Team popularity is a convenience frame,
not a population-random sample. Membership overlap does not prove outcome leakage, but
both participants must pass the stricter prior-exposure exclusion below.

Exclude BOT/disabled accounts and accounts not seen since 2026-06-01. Using metadata only,
stratify by current realTime rating (<1200/1200–1599/1600–1999/>=2000/unknown); fixed hash
ordering within stratum and round-robin across sorted strata. Select at most 160 focals.
Use hash domain `seed + ':focal:' + player_id`, never reuse the acceptance-order hash domain.
Freeze the complete focal list before fetching any focal's games. Do not replace focals
with inconvenient BOT/correspondence/overlap/low-yield histories.

Period: 2026-06-01 inclusive to 2026-09-09 00:00 UTC exclusive.
Request each focal's newest <=12 games in that window, perfType=realTime, moves=true,
ongoing=false, finished=true, evals=false, clocks=false. Server-side filtering does not
replace local verification. Accept standard-start standard shogi with identified both
participants, no declared BOT/AI, finished game, full legal USI move sequence, clock object,
and no correspondence flag/daysPerTurn. Unknown time-control status is excluded, not guessed.
Rated and casual both retained and separately reported. Correspondence is excluded from
this primary sample; report incidental exclusions but do not launch a second collection.

Fetch the entire fixed focal list, not until a promising score or event count is reached.
Deduplicate game IDs, then sort by `SHA256(seed + ':accept:' + game_id)`.
Apply <=6 accepted games per BOTH participants and <=300 accepted games total. Maximum
raw export records=1920. Cap is fixed independently of response sets, results or moves.
No expansion if fewer games survive. A few hundred games is a target, not a reason to
weaken exclusion. Do not choose games because they contain a capture or a favorable prediction.

## Independence and exposure audit

Private exclusion snapshot unions both players and all IDs from ALL already downloaded
human game records, including rejected games and the old reach prototype, not just the
612 accepted policy games. Sources: old human/reach SQLite game payloads, recursively
audited raw requests, and policy_examples games. Frame-only member records without games
are not outcome exposure. Exclude both focal and opponent if in this exposure set.
Assert accepted player intersection=0 and accepted game intersection=0 before evaluation.
Keep IDs private; publish counts and hashes. Unknown/anonymous identity is excluded.
This establishes disjoint known accounts, not independence of latent people, unmarked bots,
shared preparation, teams or social groups. Same exact opening in distinct new games is
allowed and stratified by frozen exact support; it is not game leakage.

## Rate limits, stop/resume and sealing

Reuse PublicClient: sequential requests >=2s apart, <=8MB per response, timeout45s;
record source URL, terms URL, UTC retrieved_at, HTTP status and raw hash. No credentials.
401/403/404 for team membership may be recorded as unavailable; do not bypass access controls.
429/network/5xx stops acquisition, preserving partial state. At most one later retry per
failed URL after its cooldown; repeated failure ends this bounded attempt. No rapid polling.
Collect no new outcome metrics while deciding which games to fetch. Save and hash the
accepted dataset manifest before revealing any prediction scores. Freeze protocol/model
hashes must verify both before acquisition and before evaluation. No checksum regeneration
to accommodate a changed model. Identical rerun after output/IO failure is not a new experiment.

## Evaluation and reporting

Use the same 0–24ply observation convention as prior occurrences. No train/validation/test
resplitting of this dataset: every accepted game is confirmation-only, excluded from fitting.
For each legal-response set, condition on at least one available move and report opportunity
count, distinct games, BOTH distinct participants, actual movers, chosen count, observed
frequency, predicted mass, binary Brier, all 10 fixed bins and ECE. These player counts are
different denominators and must be labelled. Report all seven sets and prior-five primary set table.
Report NLL, multiclass Brier, top1/3/5, top-label ECE, exact>=2/fallback/0/1 slices and low-support rate.
Game-cluster paired bootstrap (300 fixed-seed draws) compares new vs old Brier; report absent
events as null, not zero. These intervals do not account for all player/team dependence.
Also give a descriptive player-equal-weight sensitivity, with game decision weight
0.5*(1/games_of_sente+1/games_of_gote), normalized within each metric's eligible observations.

Report rating/clock/date/rated distributions, games per player, missingness, exclusions,
known-overlap counts, and event support. Contrast with old exploratory figures, explicitly
noting removal of correspondence and the changed population/frame. Do not attribute all
metric differences causally to model quality. Require enough support to interpret a result;
there is no data-dependent acquisition extension to attain significance.

## Outcome semantics and handoff

Record relative-gate pass/fail/null independently of the research decision.
Zero-support events/partial acquisition/uncertain intervals imply INCONCLUSIVE for those claims.
Clear relative deterioration or remaining substantial systematic natural-response errors
support NO for advancing the model. Relative improvement alone does not imply YES: with
unchanged abstention and no established absolute calibration certification, report
INCONCLUSIVE or NO with the specific limitation, not an automatic permission to scan.
The final research interpretation belongs to Astra; Luna reports measurements without
changing definitions, coefficients, sample or thresholds. No new hypothesis within this sample.

△3二銀 is only a fixed sanity assertion: existing same-horizon obvious-response evidence
must classify it as diagnostic/neutralized. Do not evaluate or optimize its Human Policy mass.

Publish only plan/config/code, model fingerprints/coefficients and aggregated outputs.
Frozen sufficient statistics, participant exclusion lists, raw games and SQLite stay private.
When results are available, commit+push and STOP; user review required before any next cycle.
