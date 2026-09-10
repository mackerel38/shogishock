# Frozen small trap-tree benchmark

Research source d58a9b3bef8e909d67fd452578277860cdfacb11; reviewed display lineage94e1b24e99c811e82415f9c1ef0792993dc8b68a. No external opening lookup during exploration. Root is after20...B*4e, gote is us, sente is opponent:

`7g7f 3c3d 2g2f 8c8d 2f2e 8d8e 6i7h 4a3b 2e2d 2c2d 2h2d 8e8f 8g8f 8b8f 2d3d 2b8h+ 7i8h P*2h 3i2h B*4e`

Question: can deterministic bounded move generation produce a useful repertoire across opponent deviations, separating tactical traps, normal continuations, refutations and uncertainty?

This is a previously exposed benchmark. The root and reference motifs already came from external opening descriptions in the prior cycle. No reference continuation is forced into this search. Matches are mechanical reconstruction/rediscovered_known_motif under prior exposure, NOT blind independent rediscovery or novel discovery.

## Selection rules, before new evaluations

1. Evaluate every legal root reply at10k. Retain the best3 for sente, plus the best unselected noncapture rook retreat (destination rank closer to own back rank; rook not attacked there). If none, retain next engine-ranked move. Exactly4 root branches (unless fewer legal moves). Engine rank is not human probability; mark salience and root loss separately. This explores realistic rook flights without inserting named reference moves.
2. At each resulting gote node, use engine MultiPV3 (actual returned count recorded). Candidate1 is its top recommendation. Candidate2 is the highest salience legal forcing alternative: victim value +300 for promotion +200 for check; USI lexicographic tie-break. If no forcing alternative, next returned engine recommendation. At most2 per branch. Suppress paired pawn/bishop/rook nonpromotion during OUR candidate proposal only; no reply filtering and no silver/knight/lance blanket suppression. No candidate CP cutoff.
3. Evaluate each candidate child at10k, and ALL opponent replies to it at10k. Candidate initial cost=max(0,V_candidate-min(V_tested_candidates)) for gote; preserve reference scope as best tested same-budget child, not proven global optimum. Full-response best defense maximizes sente CP. Gap=V_best_defense-V_response. Never root-child comparisons.
4. Natural-looking replies for this prototype are existing obvious.py signals or capture/check; these are heuristic salience, not human frequencies. Store all replies. Visible children: best defense plus up to2 highest-salience natural-looking replies with gap>=300cp (same salience formula, USI tie-break). No claim that the selected errors are common. Extend each visible child by one engine-recommended gote continuation, evaluating its child at10k. Maximum root-relative depth4ply; no recursive expansion beyond this.
5. Frozen tactical gate unchanged (original hashes, gap100/defender advantage300 and existing strong proxies; all12 sensitivity settings). Gate reject cannot be a trap branch. Unknown scores/partial sets yield needs_review. Three old reject regressions replayed from cached fixtures. Production gate remains INCONCLUSIVE.
6. Mechanical trap flag requires not rejected, full comparable reply set, and a natural-looking response with gap>=300. Choose a flagged candidate by greatest such gap, then smaller initial cost then USI. If none, choose lowest-cost unrejected candidate. This deliberately stress-tests selection bias: large error gaps alone do not establish human salience or a valid trap; Astra's final interpretation may downgrade flag to needs_review, never retune search. If all candidates gate-reject => opponent_refutes; unflagged viable default => normal_branch. No need to force every branch into trap status.

## Naturalness and graph

Reuse prior prefix trajectory/paired audits and their horizon warnings. Root-edge loss>300 flags an opponent deviation;>600 or parent absoluteCP>1000 flags substantial prior imbalance for human review (not candidate deletion). Every graph node stores incoming histories and path flags, including inherited deviations. Not all node evaluations will exist; missing is explicit.

Canonical node key=SFEN board/turn/hands, excluding move number; no reflection. Node stores min root-relative ply and all incoming relative histories; edges separate actor, move and role. Merge repeated positions, preserve path-specific flags. Only selected visible replies enter graph; all evaluated replies remain in evidence.json. Test a commuting-move transposition even if this tree has no actual merges.

## Budgets and decisions

10k existing engine/cache; maximum1000 NEW requests,8 candidate full-response sets,4 root branches. If budget prevents complete evaluation mark needs_review, do not silently treat partial best as optimal. At most8 targeted100k child evaluations after10k: for each selected branch, best defense and highest-salience displayed error; chosen before seeing100k scores. These are pair checks, not full100k rankings. No further confirmation if unstable.

Metrics: candidate_initial_cost_cp is theoretical cost versus tested normal alternative; opponent_natural_replies are heuristic candidates, not probabilities; opponent_best_replies are full10k good replies; best_vs_natural_gap_cp/penalty_if_opponent_misses are conditional losses, not expected win rate; continuation_depth counts root-relative plies; compensation is a tactical interpretation with saved PV evidence.

YES requires multiple plausible opponent branches and more than one meaningful tactical motif, non-trap branches represented honestly, no obvious blunder admitted, sensible histories and working transposition representation. Pure engine lines, contaminated paths, indistinguishable bad moves, or fragile shallow effects => NO or INCONCLUSIVE. Method judgment and novelty judgment are separate. Known references matched only after mechanical selection. No probability of success for the tree.

Forbidden: external opening seeding/search during exploration, Human Policy execution/refit, independent270 tuning, mass scans, Terashock expansion,1M/10M per-search budgets, Vast/cloud, production activation, new ranking system. Freeze+push before engine work; final tree/evidence/analysis/ASTRA_HANDOFF, tests, push+remote SHA, STOP. KIF/display refinement goes to Luna with explicit instructions.
