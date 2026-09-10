# Trap-tree benchmark: INCONCLUSIVE

A four-branch graph was built mechanically, with two conditional tactical contrasts supported by matched100k checks. But one tested continuation has an obvious adequate defense and another alleged trap reverses ranking at100k. This is a useful prototype result, not a reliable automated repertoire or production approval.

## Generated tree and final research interpretation

All moves below branch from the same20ply root after △4五角. The signs of every CP value remain sente-oriented.

```text
△4五角 (root; sente to move)
├─ ▲7七角打
│  └─ △8八飛成                         trap_branch; conditional evidence
│     ├─ ▲同金 → △3四角                selected100k response -865
│     └─ ▲同角 → △3四角                selected100k response +215
│          └─ normal-play exit; subsequent ▲1一角成 in saved PV
├─ ▲2四飛
│  └─ △6七角成                         opponent_refutes: tested continuation only
│     ├─ ▲同金 → △8八飛成               selected100k response +740; natural adequate defense
│     └─ ▲2一飛成 → △7八馬             selected100k response -1601; premature counterattack
│  [△2三歩 was in MultiPV but not proposed by the frozen candidate rule]
├─ ▲3六飛
│  ├─ △8八飛成                         needs_review; selected shallow trap fails pair check
│  │  ├─ ▲同金                         selected100k response +360
│  │  └─ ▲1五角打 (check)              selected100k response -470
│  │       [the10k supposed best/error ordering reversed]
│  └─ △同角 ▲同歩                     normal_branch option;10k response -123, no100k claim
└─ ▲3五飛
   └─ △6七角成                         trap_branch; conditional on opponent deviation
      ├─ ▲同金 → △8八飛成               selected100k response -585
      └─ ▲7七角打 → △7八馬             selected100k response -130
           [▲9五角打 also within98cp at10k; no unique-defense claim]
```

The tree's explicit expansion stops at root-relative4ply. Longer PVs are evidence annotations, not recursively searched book branches. Normal exits/fallbacks are not promises of a fully analyzed middlegame.

## What was frozen and what was actually selected?

PLAN checkpoint `b52514e` preceded new engine work; mechanical output and the prespecified confirmation pairs were checkpointed at `a38a7c5` before100k evaluation. Root legal responses were evaluated at10k; top3 were B*7g,R2d,R3f, and the best remaining safe rook retreat added R3e. Their explicit root losses are0/18/163/348cp. Engine rank/salience is not observed human probability.

Each branch tested the top engine recommendation plus one highest-salience forcing alternative. Eight candidates and694 explicit opponent replies were analyzed. Three candidates were rejected by the unchanged tactical gate and never selected as trap continuations. Those alternatives are retained only as diagnostic subgraphs. The three established bishop-loss regressions remain reject.

The candidate rule has a concrete coverage flaw: after R2d, MultiPV returned B6g+,P*2c,B6g+, but the rule retained B6g+ and forcing R8h+. Thus it missed the quiet P*2c move already in the engine shortlist. We did NOT add it retrospectively. Duplicated returned PV moves are saved as observed; three MultiPV entries do not necessarily mean three distinct candidates.

## Metrics and interpretation

| Opponent branch | Selected our move | Initial cost10k | Natural reply being tested | Full10k gap | Selected100k pair gap | Final status |
|---|---|---:|---|---:|---:|---|
| B*7g | R8h+ | 0 | Gx8h vs Bx8h | 941 | 1080 | trap_branch |
| R2d | B6g+ | 0 | immediate R2a+ vs Gx6g | 1487 | 2341 | opponent_refutes |
| R3f | R8h+ | 550 | Gx8h vs B*1e | 407 | -830 | needs_review |
| R3e | B6g+ | 0 | Gx6g vs B*7g | 416 | 455 | trap_branch |

- Initial cost means the sacrifice in evaluation versus the best TESTED explicit candidate child at10k, not a proven global optimum. The550cp estimate is shallow and not confirmed at100k. Candidate CP was never a hard rejection cutoff.
- Gap/penalty means the conditional difference between a defense and a selected alternative. It is NOT expected human loss, probability of error, or win rate. The100k numbers compare selected pairs only, not full100k best-defense sets.
- A large gap can be irrelevant: in R2d the good response is the natural gold recapture, so a bad premature rook promotion does not establish a difficult trap. At10k the gate reference+274 was just below defender advantage300; the natural defense is+740 at100k. The frozen10k result is preserved; no mixed-budget gate recalculation or production activation was performed.
- The R2d refutation label is LOCAL to the evaluated first-response test. Its PV still requires later counterplay such as R2a+ after R8h+. We have not established that every later decision is easy, or that a longer multi-stage version lacks practical traps. Such a claim would exceed this4ply benchmark.
- In R3f the sign of the claimed penalty reverses. Gx8h is830cp BETTER than the previously preferred bishop check in the selected100k comparison. Do not call it a mistake or the check a difficult required defense. The competing Bx3f Px3f line is an already-tested normal option, not a new post-hoc search.
- Supported mechanisms differ: B*7g requires choosing which piece recaptures a sacrificed rook; R3e exposes a poisoned horse whose gold recapture enables rook invasion. Both remain conditional human-review hypotheses, not measured practical traps.

## Path quality and transpositions

The root uses the known short20ply sharp opening, not the old unnatural17.B7g scaffold. Prior prefix audits and the +881→+155 root/child horizon swing are explicitly retained as uncertainty. No claim of an independently certified natural history is made. R3e loses348cp against the best tested root response; that is a plausible deviation to cover, but not clean independent false-negative safety evidence. Parent-imbalance/deviation flags are recorded separately from candidate decisions and preserved per incoming history.

The graph has59 nodes and59 unique move edges. Two nodes have multiple incoming histories: R3f/R3e → R8h+ → R3b+, and their common R8i continuation. These are diagnostic/error paths, not two successful traps to count twice. A separate commuting-move test validates board/turn/hands identity, move-number exclusion and history retention. No reflection is used.

## Rediscovery versus prior exposure

No external opening search was performed in this cycle. Root and earlier references were already externally informed in the repository, so this is NOT blind independent rediscovery. R3e→B6g+ matches a prior reference exactly; the rook-sacrifice motif recurs after an earlier bishop drop but exact-line novelty remains unknown. No novel discovery is claimed. P*2c was visible in the engine shortlist but its continuation was not reconstructed under the frozen selection rule.

## Work, conclusion and STOP

714 new engine requests:708 at10k and6 at100k.109 cache hits;8 confirmation positions include2 cached100k results. Nominal queried work including cache hits8,950,000 nodes across823 distinct requests; no individual1M/10M search. Human Policy calls0, acquisition0, no independent270 reuse, no production/ranking changes, no Vast. All new analyses remain in the existing cache.

INCONCLUSIVE applies to reliable meaningful trap-tree generation. Graph construction and two contrasts are encouraging, but salience/selection failures and a major shallow reversal prevent a stronger result. Production gate also remains INCONCLUSIVE independently. The next question, only after human review, is improving quiet candidate coverage and response salience/stability; it is NOT implemented in this cycle.

Authoritative files: tree.json (graph and final interpretations), evidence.json (frozen10k selection), confirmation.json (selected100k pairs), ASTRA_HANDOFF.json. Display/KIF work is assigned to Luna in LUNA_TASK.md. No next research after final checkpoint.

Verification:22 tests passed (5 tree/evidence tests,6 frozen-gate tests,11 existing position/pipeline tests). All694 explicit candidate-reply PVs were legally replayed. Graph histories, canonical transpositions and role sides were checked. No ShogiHome GUI review or new KIF rendering by Astra.
