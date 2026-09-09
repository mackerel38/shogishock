# Fixed-case tactical falsification prototype

Question: can an obvious AND objectively adequate reply falsify a candidate before Human Policy?

Scope: five purposively selected existing fixtures, cached 10k/100k response analyses only. No engine, policy, dataset, ranking or production pipeline changes. Source checkpoint: 328a4df3f8a4568648a83134f4cd254c9005a4d5. This plan was written after inspecting existing fixture scores; it is NOT a preregistered independent validation.

Hypothesis: a narrow conjunction can reject free-major blunders without rejecting ordinary compensated exchanges. Naturalness remains a heuristic, not a measured human probability.

Prototype rule (parameters are provisional, not fitted):

- Strong witness: unrecapturable bishop/rook (including promoted pieces), or immediate recapture satisfying the existing material-recovery proxy. Unrecapturable means no legal immediate capture of the capturing piece, NOT tactical invulnerability.
- Candidate capture, pawn contact, generic material recovery, checks and forcing moves remain diagnostic signals; alone they do not trigger rejection. Single legal check evasion is natural by necessity, but no automatic tactical conclusion is implemented here.
- Compare ALL explicit legal reply positions at the same recorded nominal node budget. Never mix candidate-root and reply-child scores for the best-reply gap. Separate searches still have uncertainty; equal budgets do not guarantee equal depth or accuracy.
- For attacker sign s (+1 sente, -1 gote): best reply minimizes s*V; gap=s*(V_reply-V_best). Adequate requires gap<=100cp.
- Additionally require -s*V_reply>=300cp (clear defender advantage). A merely adequate reply to an equal or compensated exchange is not a proven blunder. This is a verified-response conjunction, not a candidate-eval cutoff.
- CP values stay sente-oriented. Exact attacker-winning mates are dominated by finite CP from the defender's perspective; never convert mate distances into CP. Defender-winning mates, unknown/bounded scores, or incomplete coverage cause needs_verification in this CP-only prototype.
- Parent evaluation describes the starting opportunity; candidate-root describes optimal-defense cost; reply-child describes retained compensation after the actual response. Parent/root differences are context, not precision certificates or rejection conditions. Parent-already-favorable remains a separate existing selection concern.

Outcomes: reject / not_falsified / needs_verification. not_falsified does not mean actual_candidate, nor permission to trust Human Policy. Retain every record.

Fixed cases: mandatory 3a3b; 2b6f and 8h4d free-bishop recaptures; two 7g3c+ / 3c7g+ bishop-exchange controls containing seriously bad alternative recaptures. No claim these controls are validated novel traps or successful sacrifices.

Checks: required blunder rejects; exchange controls survive; bad recaptures are not adequate; incomplete/bounded evidence abstains; no fake mate CP. Report sensitivity 50/100/200/300 gap and 300/500/1000 defender advantage without selecting a winning parameter.

Success on fixtures is necessary but insufficient for production. Missing independent poisoned-piece/sacrifice controls or naturalness validation => INCONCLUSIVE for production automatic rejection. Stop after artifacts, tests, GitHub push and remote SHA verification. No large-search permission.
