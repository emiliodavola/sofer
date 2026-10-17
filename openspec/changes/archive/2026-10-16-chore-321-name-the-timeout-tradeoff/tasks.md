# Tasks — `2026-10-16-chore-321-name-the-timeout-tradeoff`

> **Change** `2026-10-16-chore-321-name-the-timeout-tradeoff` · issue **#321** · branch
> `fix/325-codex-home-and-321-delegation` (from `fix/316-321-bug-chore-followups`).

| ID | Task | Spec | State | Evidence |
| --- | --- | --- | --- | --- |
| TT-1 | Establish whether option 1 can deliver its claim | — | done | `atomic_write`'s three branches and `merge()`'s wholesale assignment: TOML/JSON rewrites, only YAML splices (D1) |
| TT-2 | Measure when `--no-timeout` actually restores delegation | D2 | done | The truth table in D2, taken from the gate itself |
| TT-3 | RED: the hint appears when `timeout` is the sole reason | D2 | done | `test_decline_names_no_timeout_when_timeout_is_the_only_reason` failed on stderr `"  !  codex native mcp add cannot express timeout; falling back to file edit\n"` |
| TT-4 | Guard: the hint is absent when it would be false | D2 | done | `test_decline_does_not_name_no_timeout_when_env_also_blocks`, passing before and after by construction |
| TT-5 | Implement the hint, conditioned on the exact predicate | D2 | done | `src/sofer/cli.py`, with the measurement in the comment |
| TT-6 | The flag's `--help` states the trade-off | D3 | done | `--no-timeout` help text |
| TT-7 | Both READMEs state it too (rule 13) | D3 | done | `README.md` `--no-timeout` row and timeout paragraph; `README_ES.md` the same two |
| TT-8 | Full suite on the frozen revision | — | done | 2238 passed / 9 skipped — the #325 revision's 2236 plus the two tests this change adds; `cli.py` re-verified at 100.00% because this change adds a branch to it |
| TT-9 | Publish the #321 framing correction | — | done | comment `6221654849` on #321 |
| TT-10 | Archive report | — | done | this folder's `archive-report.md` — archived late, see its §7 |

## Explicit non-deliveries

- **The issue's option 1** (proposal §2, design D1) — rejected on measurement, and the measurements are in
  this folder rather than only in the conversation.
- **A surgical TOML writer** — would deliver claim 1; its own change, and it should begin by measuring
  codex's own writer on a host that has codex. Codex is not installed on this machine.
- **No spec delta** (design D4): the MCP-REG-05 clause is kept, not reversed.
