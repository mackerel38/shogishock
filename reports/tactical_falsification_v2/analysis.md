# Production candidate rejection: INCONCLUSIVE

The unchanged gate retained two prospective opening controls and rejected the proposed rook sacrifice. Only one new control is provisionally clean enough for human review as safety evidence. The second has a significant preceding inaccuracy. No actual candidate is promoted; no production scan is authorized.

## Design, provenance and independence

- Gate semantics frozen in checkpoint `1d0c529`; selections with expected should_keep recorded in `b6b747e651d15677ca1e69803422880ade2d01b9`, before new engine evaluation.
- Original research `903f13a4c8a093709596e6716c35cce3dc071b5f`; reviewed Luna/KIF lineage through `86595f9a0fb8c22a68a47e0532a311ce6bc6de8a`. Existing engine, gate, policy and old data were not edited.
- The previous long-history ▲3三角成 / △7七角成 controls are withdrawn as production false-negative safety evidence, not deleted. Their published survival does not establish natural histories.
- New move sequences were selected from the author's [4-five-bishop opening explanation](https://www.koichi.jp/shogi/yokofu/45kaku.php). This supplies a tactical hypothesis, not proof of soundness, modern optimality, reach frequency or human salience. The two controls share an opening family and are correlated.
- Main gate: strong naturalness proxy AND same-budget full-reply gap<=100cp AND defender advantage>=300cp. All12 original sensitivity combinations retained. Details and hashes in PLAN.md; no threshold tuning.

## Results at10k: every legal reply to each selected candidate

All CP is sente-oriented. Positive favors sente, negative favors gote. A “gap” below uses the best explicit child-response evaluation in that case, not candidate-root evaluation.

| Case | Candidate ply | Natural-looking response | Response CP / gap | Gate | Safety-evidence admission |
|---|---:|---|---|---|---|
| 角打ちで飛車取りを残す | 23 | ▲7七角打 → △2四歩 | +1230 /800 | not_falsified | provisionally cleaner, human review required |
| 馬を取り返すと飛車が侵入 | 22 | △6七角成 → ▲同金 | -404 /416 | not_falsified | borderline, not admitted as clean evidence |
| User rook counter-sacrifice | 19 | ▲2二飛成 → △同銀 | -2484 /0 | reject | failed hypothesis, not proven valid sacrifice |
| User pawn follow-up | 21 | ▲8二歩打 → △同銀 | -2697 /105 | not_falsified | negative diagnostic, not a valid control |

Full reply counts:45/104/88/135. Good-reply counts at tolerance50/100/200/300:2/2/2/2;1/2/3/3;1/1/1/1;2/2/3/3. These are legal-move counts, NEVER human probabilities. All four gate decisions survive the12 threshold combinations at10k. The three original bishop-loss regressions remain reject, replayed from saved evidence without new engine calls.

## What protects the new controls?

1. **23.▲7七角打**: the immediate pawn capture of rook2d is a frozen strong naturalness proxy, but an inferior response. ▲同角 on8f recovers the opposing rook. More accurate △8八飛成 first captures the silver; ▲同角 △2四歩 ▲1一角成 retains compensation. The best10k response is actually rook nonpromotion8f8h at+430; promotion8f8h+ is+473, only43cp worse. At100k the selected promoted-rook line is+357 and immediate pawn capture is+1490:1133cp apart. This is A/C (inferior apparent capture/poison) and B (compensation in the better line). The new23rd move is a bishop DROP, not the old17th move from8h to7g.

2. **22.△6七角成**: ▲同金 clears the defense for △8八飛成 and further rook penetration. ▲7七角打 is best in the full10k set; ▲9五角打 is also within100cp, so do not call the defense uniquely necessary. Selected100k scores: gold recapture-585 versus bishop defense-130, a455cp difference. This supports A/C and compensation after a better defense, but does not establish a clean prior history.

100k covered selected pairs/subsets only, never the full legal response universe. Neither pair difference is advertised as a full100k optimal gap; the gate was not rerun using mixed budgets.

## History audit and its limitations

Every selected history prefix was evaluated at10k. Large root-to-child swings were flagged, then the played move and root-best alternative were compared as explicit child positions. This avoids treating every horizon difference as a real mistake.

For the23ply control, the flagged20...B*4e comparison did not show a >300cp loss against the root's alternative3b3c (signed loss -27cp). The21.R2d comparison is the same move, not independent validation. Raw roots nevertheless swing from+281 to+881 to+155 near this tactical setup: report this instability, do not hide it. We have no evidence here of repeated ignored free-rook tactics, but have not exhaustively certified every earlier alternative.

For the22ply control,21.R3e loses330cp against R2d at10k and454cp at100k (-103 versus+351). A documented side variation is not automatically a clean safety control. It remains a borderline tactical example and is not counted as a second fully admitted control.

The user's suggested repair is materially better: old17.B7g=-2477 versus17.P*8g=-30 at100k, a2447cp child-pair difference. This confirms the old source-history concern. We did not construct another long repaired line to force a desired validation outcome.

## R8i+ hypothesis and small mechanical comparison

After18...R8i+, the tested19.R2b+ meets the frozen rejection conjunction: Sx2b is a strong, best explicit response; its value is-2484 at10k and-2478 at100k. That is not evidence of a false rejection of a valid sacrifice; the prospective validity hypothesis failed.

The bounded shortlist found19.B7g2b+ at-2242 versus R2b+ at-2648 (10k child evaluations),406cp less bad. These are exploratory values, not proof of a better practical surprise. R2a+ is illegal here because bishop2b blocks the rook. After20...Sx2b, alternatives P*2c=-2577 and K4h=-2557 are less bad than P*8b=-3114, still not demonstrated promising surprises. Eleven alternative moves were compared in total; no exhaustive candidate search.

After21.P*8b, full10k analysis gives R8i8b and N*8f both-2802; S7a8b is-2697. The100k subset gives R8b=-2756, N8f=-2588, S8b=-2864. Direct pawn captures therefore refute the assertion that an obscure knight drop is required. In the knight line, Bx8f Rx8f P8a+ Rx8a explains tactical recovery. Human choice probabilities were not measured.

Important gate limitation:21.P*8b has zero frozen strong witnesses, because the direct pawn captures are neither free-major captures nor qualifying recaptures. Hence gate=not_falsified while research review rejects the current proposal on straightforward adequate defenses and lack of demonstrated compensation. We deliberately did not broaden the rule after seeing this example. Non-rejection is not a viability label or permission to promote using Human Policy.

## Work, reproduction and STOP

433 new cached engine requests:421 at10k (including3 MultiPV shortlists),12 at100k. Nominal total5,410,000 nodes across requests; recorded search work5,546,808. No individual1M/10M search. Cache hits0 on the new requests;3 regression cases use saved evidence separately. No Human Policy calls, acquisition, independent270 changes, refit, Vast or actual candidates.

Evidence is in results.json, engine_evidence.json, confirmation_results.json and ASTRA_HANDOFF.json. `experiment.py` performs bounded engine work and resumes saved requests; **do not rerun it to start new work after STOP**. `finalize.py` and unit tests are offline. Frozen gate, source hashes, plans and expectation records are preserved. Remaining routine KIF/display work is Luna's task, not a new research decision.

Verification:22 tests passed (5 new-cycle,6 frozen-gate,11 existing position/pipeline). All372 saved explicit reply PVs were legally replayed from their correct child positions. New KIF/display assembly is assigned to Luna; no GUI review was performed by Astra.

INCONCLUSIVE is about production automatic rejection, not permission for a scan. One provisionally cleaner control plus one borderline same-family example cannot establish general false-negative safety. Additional research requires Astra and separate human authorization; present this cycle for human review first.
