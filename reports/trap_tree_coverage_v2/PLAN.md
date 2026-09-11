# Frozen coverage benchmark plan

Research source: 437a7ca93dcd20e645b6c1a7b63cd8a14e6f1547.
Display source: d5be34c898967884cf4ea1755b43c360ec01293d.

## Question and scope

Can a union generator retain quiet tactical candidates and reasoned non-best
defenses omitted by top1 + forcing selection? This is an exposed benchmark,
not independent rediscovery or a human-frequency validation.
Use the existing 20-ply position after B*4e and the existing R2d, R3e, R3f
branches. Keep B*7g entry plausibility separate from conditional tactical severity.
No external opening lookup, new human data, Human Policy use/training, cloud,
production gate activation or other seed expansion.

## Move limit

New candidates only at absolute ply <=30. Beyond30 only continuation of a
tactic already initiated: forced mate, material resolution, tactical proof.
History remains explicit; never change the turn to manufacture a mate.

## Frozen generation rules

Evaluate all legal children at10k at the three candidate positions and the
three positions following B6g+. This is proposal only. Preserve every legal
record, including unselected moves. Rank explicit child scores, not duplicate
MultiPV records. Retain top8 distinct moves plus the following union, without
quota competition: captures, checks, promotions, all pawn drops, newly created
attacks on enemy non-pawns, moves of attacked or undefended non-pawn/non-king
pieces, moves newly defending an own non-pawn or a square adjacent to own king.
Also retain quiet engine-top8 moves and quiet silver/gold development toward
the opponent from their home three ranks. No named move insertion.

Shared geometry supplies tags (heuristics, not tactical truth): capture /
recapture / material recovery from existing obvious.py; grab_material,
counterattack (major-piece capture/promotion), escape_attacked_piece,
save_hanging_piece (undefended non-pawn), reinforce_piece, protect_king,
block_invasion (new defense of an empty king-neighbor square), piece_attack,
develop_with_tempo/development, pawn_drop_setup, promotion, check.
Pseudo-attack geometry is only a motive proxy; legality always checked.
Moves may have multiple tags; a tag does not assert the move works.
Nonpromoted pawn/bishop/rook pairs remain stored but are not independently
promoted by a generic forcing tag. Engine top8 can still retain them.

Replies use the same union (not all legal moves labeled human), with history-
aware recapture/candidate-capture flags. No Human Policy threshold. Specifically
track G7i/G8g/R2a+ legality and coverage without adding them to the generator.
Track P*2c and B6g+ afterR3f likewise. Human-supplied cases are regression
targets, NOT held-out validation. Report union size and old-rule omissions.

## Deep confirmation, frozen before new scores

10k cannot confirm a trap, blunder or best defense. At each candidate position,
confirm the union of top8 proposal moves and the user-exposed P*2c, B6g+, R8h+
where legal. These named moves are diagnostic deep comparisons, not generator
inclusions. At each B6g+ reply position confirm top8 plus all captures,
promotions, gold moves with saving/defensive tags and the explicit review
targets where legal. Keep engine-best references explicit and same-budget.

Use100k ->1M ->5M ->20M ->80M child searches as necessary. Stop a comparison
only after two consecutive transitions satisfy: all compared CP changes<=100,
best move unchanged modulo a100cp near-tie, and each compared continuation's
first move stable. Record PV first2 stability separately. Mate transitions
are typed, not CP. If80M is still unstable, mark unresolved for human review;
this is a finite benchmark endpoint, not a claim that more time is impractical.
Subset comparisons do NOT prove global best or complete good-response width.
Preserve all intermediate scores and scope of references.

## Mate hypotheses

R3e/B6g+/G7i/R8h+ and R2d/B6g+/G7i/R8h+ are unconfirmed human claims.
Search the actual positions before/after R8h+, including defender to move.
Use the same progressive budgets. A stable engine mate score with a legal
terminal PV is engine evidence; distinguish it from an exhaustive AND/OR
certificate. If necessary inspect existing solver capability before invoking
`go mate`: do not assume the normal NNUE binary implements DFPN. Never treat
a single winning PV as proof against all defenses. Unknown != no mate.
Record distance origin, attacker, first forcing move and whether terminal PV
is complete. A19ply upper-bound claim needs evidence, not agreement.

## Interpretation, regressions, stopping

Plausibility and severity separate; rare-but-reasoned can be important.
Engine loss is not a candidate hard cutoff. Broad geometry can overgenerate;
measure this and do not call every selected move natural. Existing3 obvious
reject regressions must still reject using their saved evidence and unchanged
gate. Production status remains INCONCLUSIVE.

YES only if targets arise from general rules, reply motives are explainable,
coverage is bounded on this benchmark, and relevant tactical comparisons are
stable. Unresolved ranking/mate or unvalidated motive specificity may warrant
INCONCLUSIVE. Do not optimize rules from outcomes. Save prospective changes
for a future cycle. Publish results/handoff and STOP for human review.
Luna receives only deterministic display tasks with short tactical prefixes.
