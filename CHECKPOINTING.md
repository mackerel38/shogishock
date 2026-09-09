# GitHub checkpoint policy

User instruction, 2026-09-09: commit **and push** at each meaningful milestone, before long experiments,
and before a session may be interrupted. Do not leave important work only on the local machine.

Before publication:

1. Update `PAUSE.md` / current research handoff with stage, findings, artifacts, next commands, caveats.
2. Inspect Git status/history/diff. Never reset, checkout over, or pull over local collaborator changes.
3. Use the public allowlist in `scripts/prepare_checkpoint.py`; review the resulting diff and manifest.
4. Run tests and verify the staged tree for credentials and excluded files.
5. Commit with a descriptive `Checkpoint: ...` message; push without force; verify remote commit SHA.

Do not publish credentials, engine binary, NNUE, venv, ShogiHome AppImage, raw human games,
restricted SQLite/raw datasets, or Terashock raw/extracted book data whose redistribution permission is unconfirmed.
Generated engine analyses, aggregate human metrics, code/config/tests, and original research HTML/KIF are the intended public artifacts.

In this session `.git` is empty/read-only. Use an isolated temporary clone of the verified remote,
copy only reviewed public files into it, and commit/push there. Do not replace the workspace `.git`.
Preserve remote-only files; if concurrent remote changes overlap local edits, stop and resolve explicitly.

The helper prepares a tree but does not commit or push automatically. The agent must inspect and then complete those steps.
Public `reports/human_e2e/positions.json` omits raw book move/count/depth records; the local research file remains intact.
The publication manifest lists exported paths and hashes. No private input snapshot is disguised as a public reproducibility artifact.
