# Luna task — only after user review

これはLuna向けの仕事です。

1. Read PLAN.md, analysis.md, ASTRA_HANDOFF.json and results.json. Preserve all research decisions and thresholds. No policy/engine execution or new data.
2. Optionally expose the existing five cases as shadow-only diagnostics. Never connect this prototype's reject field to production filtering or candidate ranking yet. INCONCLUSIVE is binding.
3. Display separate fields: candidate decision, human-policy reliability, naturalness heuristic, typed engine evidence, reference scope and uncertainty. not_falsified is not actual_candidate.
4. Using existing KIF/history-aware plumbing, export the three diagnostics and two controls with obvious replies/PVs from results.json. No invented Human Policy values. Explain raw CP is sente-oriented, nominal10k/100k evidence is cached. Validate branch legality.
5. Treat gap100 and advantage300 as provisional configuration, never alter them based on presentation examples. If integration semantics would change, return the question to Astra.
6. Preserve all candidate records. Incomplete/unknown/bounded evidence must remain needs_verification. Do not convert mate distance to CP.
7. Produce concise review links, tests and a separate checkpoint. No next research, scan or production activation without explicit approval.

Current research review should focus on whether the exchange controls are correctly retained. Additional genuine poisoned-piece/sacrifice controls require a separately authorized research cycle, not routine implementation.
