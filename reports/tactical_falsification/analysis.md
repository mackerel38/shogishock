# Decision: INCONCLUSIVE for production automatic rejection

The narrow fixed-case conjunction rejects three clear bishop-loss examples and retains two bishop-exchange controls. It does not establish general false-negative safety. No engine or Human Policy calls, new games, scans, training, or production edits were performed. Existing 100k analyses were read, not rerun.

| Candidate ID suffix | Role | Explicit best reply CP | Witness / comparison | Decision |
|---|---|---:|---|---|
| 5c46…_3a3b | mandatory diagnostic | +3691 | 8h2b+ +3681, gap 10 | reject |
| 0a33…_2b6f | diagnostic | +2803 | 8h6f, gap 0 | reject |
| 5ecc…_8h4d | diagnostic | -2935 | 2b4d, gap 0 | reject |
| a77a…_7g3c+ | exchange control | +352 | 3b3c +2283 loses 1931 vs 4b3c | not_falsified |
| b1d9…_3c7g+ | exchange control | +144 | 7h7g -2184 loses 2328 vs 6h7g | not_falsified |

All raw scores are sente-oriented. Full explicit reply counts are 40/31/32/47/51. The first uses cached10k replies; others cached100k. All five classifications remain unchanged across the specified 12 tolerance/advantage combinations. This is fixture robustness, not statistical validation or parameter optimization.

## Interpretation

The old +3808 candidate-root versus +3681 child comparison mixed horizons. The correct local comparison here is +3691 versus +3681, both explicit reply-child analyses. Root +3808 and parent +136 are retained for context only. Even same-budget child searches remain noisy; these scores are not mathematical proofs.

Naturalness alone fails: both exchange controls include seriously inferior recaptures. Conversely, an adequate recapture alone does not prove a bad candidate: the best resulting positions here remain near equality or favorable to the attacker. The additional defender-advantage condition deliberately makes the automatic-reject hypothesis narrower than general obvious-reply neutralization. It does not redefine P_good or candidate rankings.

The two controls contain attacker-winning mate scores on alternative replies. These are typed outcomes worse for the defender than available finite CP responses; they are not converted into CP. Any opposite mate/unknown/bound prevents this CP-only classifier from deciding. No production parser changes were made.

## Safety limits

Fixtures were selected after inspecting saved results. Three positive and two exchange controls cannot estimate precision, false-negative rate, or human obviousness. The two exchanges are NOT independently validated poisoned-piece or successful-sacrifice examples. Strong recapture uses a local proxy that can itself be misleading. Nominal search budgets match within cases but cached metadata does not certify equal search depth, hash state, or tactical completeness. Therefore do not enable production automatic rejection yet.

Human Policy is unnecessary for these already-established tactical rejects. Failure to falsify means only absence of this particular evidence; it does not license actual-candidate promotion or trust in low-support policy probabilities. The independent-validation NO remains unchanged.

Next proposed work, only after human review: stronger negative-control coverage. Routine shadow-mode integration and presentation are specified for Luna, not executed. No large-search permission is granted. STOP after checkpoint.

## Reproduction and checks

Public-only replay: `PYTHONPATH=. .venv/bin/python reports/tactical_falsification/prototype.py --fixtures`. fixtures.json contains only five existing research positions and cached reply scores/PVs, not raw human games or policy probabilities. Original local-source and public-fixture replay produced identical results.json SHA256 `8f60f265d4afe8113b9cc1bdf1b813fada64b04f6f19e221c4ed32a6fe953075`.

Six prototype unit tests passed; eleven existing position/pipeline-v2 tests passed. Unit tests include incomplete, duplicate, bounded and typed mate evidence plus bad-capture/equal-exchange controls. Synthetic logic tests are not empirical negative-control validation.
