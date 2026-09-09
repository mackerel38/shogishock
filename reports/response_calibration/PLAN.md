# Response-set calibration: frozen small-cycle plan

Question: can a small probability correction improve natural-response set calibration,
without interpreting unsupported predictions as human difficulty?

Recorded before fitting on 2026-09-09. Preserve all previous reports and Luna's plumbing.
No acquisition, engine calls, new seed scan, deep analysis, or cloud compute in this cycle.

## Definitions

All sets are legal-move sets and may overlap. Condition event metrics on at least one
available move in the set; report opportunities, games, chosen count and probability.

- capture_any: captures an opposing piece.
- captures_candidate: captures the piece moved/dropped on the immediately preceding ply.
- recapture: captures_candidate and that preceding move was itself a capture.
- material_recovery: existing obvious.py material_recovery_proxy; no legal immediate
  recapture onto the destination, OR victim's static value exceeds mover's static value.
  This is NOT a proof of safe material gain, SEE, or an engine-backed good response.
- pawn_contact_capture: pawn captures pawn (existing definition).
- high_value_capture: victim is bishop/rook, including promoted versions.
- promotion: legal promotion move.

Record victim/mover types and values, immediate legal recapturability, and static
material_gain_proxy = victim value minus mover value if immediately recapturable.
Values reuse research.PIECE_VALUES; they are feature scales, not CP engine evaluations.
Do not implement candidate_was_just_exposed this cycle: captures_candidate is not the
same claim as newly exposed, and noncandidate victims can be exposed by opening a line.

## Fixed comparisons and fitting

Reuse corrected game/time/strict-player splits and train-only base policies.
Old tests have informed this hypothesis: ALL tests here are exploratory reused held-out,
not independent final confirmation. No split rerolls or fixture-driven parameter changes.

1. Existing hierarchical: hard support threshold 2, smoothing 5, temperature 1.
2. Continuous shrinkage: (counts + k*fallback)/(n+k), k in {2,5,10}.
3. Capture-only exponential tilt of continuous k=5 distribution.
4. Differentiated exponential tilt: seven set indicators plus victim-value/1000,
   positive material-gain-proxy/1000, and immediate recapturability.

Divide original validation by game into disjoint calibration-fit / selection halves,
using a new domain-separated deterministic hash. Fit tilt coefficients on calibration-fit
human moves only (multinomial NLL, L2=0.01, 80 full-batch gradient steps, step size 0.5).
Select among the fixed variants by mean binary Brier over four primary sets
(capture_any/captures_candidate/recapture/material_recovery), subject to selection NLL
not worsening by more than 0.02 against existing. Do not use the known bishop fixture.
Base policies see no calibration/selection/test labels. Save coefficients and all metrics.

Report multiclass NLL/Brier/top1/3/5/top-label ECE; all seven event calibration curves;
support 0/1/>=2 and fallback slices; low-support fraction; paired game bootstrap for
primary-set Brier deltas (descriptive, not population-independent confidence intervals).

## Decision and bounded review

Clear exploratory improvement requires lower primary-set mean Brier in time and strict
player tests, no >0.02 NLL regression, and no primary set >0.01 Brier deterioration.
Also report sparse-event support rather than treating this gate as calibration certification.
No independent final validation exists, so response_set_calibration_status remains
exploratory_only and actual candidate promotion abstains throughout this cycle.
P_good arithmetic mass bounds are NOT uncertainty bounds on true human probabilities.
Keep model-derived P_good separately; true-human bound is uninformative [0,1] when abstaining.

Only if the exploratory gate passes, reweight previously cached 10k responses for Luna's
three fixed review cases: bishop diagnostic and two ordinary controls. No new candidate scan.
If it fails, still produce these three prediction-only diagnostic/control KIFs, with no new
E2E interpretation. actual_candidate=0 is expected and valid. No successful example invented.

Checkpoint must include JSON, HTML, three classified KIFs, interpretation, source fingerprints,
tests, and explicit review questions. Commit + push, verify remote SHA, STOP for human review.
