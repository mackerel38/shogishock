# Tactical proof diagnostic (not a selection-rule revision)

Triggered by the planned ordinary-search mate checks: before R8h+ the R3e
case reports mate19 at80M nominal, while its explicit child reports CP at80M.
No generator, score threshold or primary stability criterion is changed.

No dedicated mate binary is available locally. The installed NNUE engine's
normal-search implementation is not a DFPN solver; sending `go mate` does not
provide an independent all-defenses certificate. No engine is rebuilt.

Supplementary proof attempt: after the prescribed R8h+, try to certify a mate
within18 remaining plies (19 including R8h+) against ALL legal sente replies.
Gote OR nodes try checking moves plus moves suggested by already saved engine
PVs. Sente AND nodes require every legal move to lose. Omitted gote moves make
failure inconclusive, never evidence of no mate. No evaluator decides a proof
leaf: only legal checkmate does. Draw/repetition paths cannot prove mate.

Bound:100,000 visited states per case, a finite proof-prototype resource bound,
not an assertion that more compute is infeasible. Same bound for both exposed
cases; no searching new candidates beyond30. Save exact hint-source hash,
state counts, cutoff/failure distinction, and any certificate. Verify any
certificate by replaying all defender children independently of move selection.
This diagnostic may run alongside ordinary confirmation but never writes its
engine ledger and makes ZERO new engine calls.
