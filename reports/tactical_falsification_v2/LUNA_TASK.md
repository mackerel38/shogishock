# Deterministic review presentation only

これはLuna向けの仕事です。No Luna agent was invoked by Astra in this cycle.

Use ASTRA_HANDOFF.json and results.json as authority; do not change gate, thresholds, evidence or admissions. No engine/model/data calls. Production decision remains INCONCLUSIVE.

1. Reuse the latest `surprise/kif_export.py` and `scripts/render_tactical_falsification_review.py` branch/history/side-prefix logic, not its old case explanations or titles. Export4 new cases plus links to the3 unchanged reject regressions (7 review items maximum).
2. Suggested folders: `controls_provisional/` (bishop_block_rook_sacrifice), `controls_borderline/` (horse_entry_bad_gold_recapture), `diagnostic_hypotheses/` (both user proposals). Zero actual_candidates. Preserve old files.
3. Include every move from startpos; validate history equals saved SFEN. Distinguish23.▲7七角打 from old17.▲8八角→7七角. Include prefix comparisons R3e/R2d and oldB7g/P*8g at their exact branch move numbers.
4. Branch priorities: first case Px2d, R8h+, R8h; second Gx6g, B*7g and B*9e; user rook Sx2b plus the saved Bx2b+ candidate alternative; user pawn N*8f, R8i8b, S7a8b. Use saved PVs only; validate every branch and side label.
5. Comments must separate expected_class (prospective hypothesis), final_gate_result, control_admission, surprise_move_decision and human_policy_reliability. In particular P*8b is NOT a promising candidate despite gate non-rejection.
6. Label10k values as full explicit-reply comparisons. Label100k as selected pairs/subsets, not full100k best-reply analysis. Raw CP always sente-oriented. Never add Human Policy probability or P_good.
7. Human-facing titles must state the purpose explicitly. Do not use “固定例確認”. Example: “飛車取りが罠になる応手を誤除外しないか：23手目▲7七角打”. Explain old control safety evidence is withdrawn after history review.
8. A compact HTML/table is optional; no need for extensive prose. Link the research JSON and highlight the four case-specific human_review_point fields. No claim of novelty, unique difficult N8f, two independent clean controls, or production readiness.
9. Run KIF branch-legality/side-display tests; commit+push presentation checkpoint, verify remote SHA, STOP. Return any research ambiguity to Astra rather than inventing conclusions.

New hypotheses, additional control acquisition or a broader pawn-capture gate are Astra research tasks requiring separate authorization, not part of this display task.
