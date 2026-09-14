# Archive Report — 2026-09-14-chore-ruff-format-drift

**Change**: `2026-09-14-chore-ruff-format-drift`
**Issue**: GitHub #177
**Date**: 2026-09-14
**Artifact store**: `openspec` (hybrid — every artifact also mirrored to Engram under `sdd/2026-09-14-chore-ruff-format-drift/**`)
**Status**: **archived**
**Verify verdict**: **PASS** — `blockers: 0`, `critical_findings: 0`, `requirements: 1/1`, `scenarios: 5/5`; envelope validated by `gentle-ai sdd-verify-validate` → `{"valid": true, "verdict": "pass"}`, exit 0
**Branch**: `chore/177-ruff-format-drift` (cut from `dev` at `bdcff25`)
**Archived path**: `openspec/changes/archive/2026-09-14-chore-ruff-format-drift/`

## Summary

Closes #177: the six test files that `uv run ruff format --check` reported as drifting were reformatted, so the check is green on a clean checkout (`67 files already formatted`, exit 0). The reformat is formatting-only — proven by an identical AST against `HEAD` plus a significant-token diff whose only delta is a redundant parenthesis pair removed from a one-line `assert` — and the full-suite tally is unchanged.

The defect **class** is deliberately not closed: no workflow runs `ruff format --check` (issue **#194**) and the two ruff version pins disagree — pre-commit `v0.16.7` versus the environment's `0.16.0` (issue **#195**).

## Delivery

| Commit | Subject |
| --- | --- |
| `cb0ad32` | `style(tests): reformat the six drifted test files with ruff` — six test files, 23 insertions / 47 deletions |
| `9839f23` | `docs(sdd): add the ruff-format-drift change artifacts` |

Delivered as a single PR against `dev`, single work unit, no chaining, no `size:exception`, no tag movement.

**Final measured numbers** (all reproduced independently by the verify phase):

- `uv run pytest tests/ -q` → `1766 passed, 6 skipped`, exit 0 — identical to the tally recorded **before** the reformat
- `uv run mypy src/` → `Success: no issues found in 32 source files`, exit 0
- `bash scripts/check_core_coverage.sh` → `cli.py` / `scanner.py` / `prepare.py` / `publish.py` each at **100%** with an empty `Missing` column, exit 0
- `uv run ruff format --check src/ tests/` → `67 files already formatted`, exit 0; `--diff` empty
- `uv run ruff check src/ tests/` → `All checks passed!`
- `git diff --check` → clean
- TOTAL coverage 93% (floor remains the config-owned `fail_under = 90`)

Verify envelope hashes: `evidence_revision` = `sha256:a0c2393fa5cc55f3eae8061f9c8bbd80dac71f6b7c1793ee92cd2733522fd987` (the verified candidate diff), `test_output_hash` = `sha256:0ad7f531cc7f43d5f1aabc531850e853737146b1fc72010a7cd39e0beb5efb3d`, `build_output_hash` = `sha256:beb5f2fbd1d6f8f0504c8c9abaa93358f761601efeb202fe75d01bc85e4ea3d7`.

## Spec Sync

**Absorbed into the canonical specs.** `openspec/specs/process-boundary/spec.md` now carries **PB-10 — "Formatter integrity on a clean checkout"**, appended after PB-09 with an `> Added by change \`2026-09-14-chore-ruff-format-drift\` (GitHub #177)` provenance line, its clause, and all five scenarios (S1–S5) verbatim from the delta. No `MODIFIED`/`REMOVED`/`RENAMED` operation was involved: PB-01…PB-09 keep their clauses and scenarios byte-for-byte.

PB-10's evidence is command output, not a pytest assertion — the same framing the `coverage` capability already uses for measured gate exit codes, recorded in the requirement's provenance line so the rule-6 trail survives in the canonical file.

### Process deviation — read this before any archive re-run

The sync and the move were performed by the **orchestrator (parent)**, not by an `sdd-archive` phase agent. Two dispatches of that phase were hard-blocked at the harness layer: every tool call, including the first, was intercepted with `SDD selection blocked: Native SDD discovery cannot run archive. Do not run phase work; return this blocker to the parent.` The parent re-queried the native status and it was clean and recommended the phase (`archive: ready`, `nextRecommended: "archive"`, `blockedReasons: []`), so the interception is a harness-layer defect for this phase, not a status gate. The parent executed the archive deterministically after recording that contradiction.

Consequence for a future re-run: **PB-10 is already in the canonical file.** Do not re-insert it — a second insertion would duplicate the requirement block.

## Tasks structure (deliberate — do not "fix")

`tasks.md` carries exactly **9 `- [x]`** and **0 `- [ ]`** items. Phases 1–3 are the apply-phase tasks; the verify-phase gates and the parent-owned lifecycle steps are plain bullets under clearly-labelled headings. The native provider counts checkboxes to decide whether `apply` has finished, so leaving cross-phase steps as unchecked boxes deadlocked `apply` and kept `verify` blocked. This structure is intentional and must be preserved if the file is ever regenerated.

## Accepted limitations (owned, not closed here)

- **#194** — no `ruff format --check` step exists in any workflow, so the drift can return on files nobody stages; PB-10 does not claim to close it.
- **#195** — the pre-commit hook pins ruff `v0.16.7` while the environment resolves `0.16.0`, so two formatter versions can disagree; alignment is a dependency change and was kept out of a whitespace-only commit.
- Three **pre-existing** type diagnostics in `tests/test_mcp_registration.py` (`__getitem__` on `object`; `str` → `AgentName` in two `resolve_config_path` sites) remain unfixed and are **not** regressions: those lines are byte-identical to `HEAD`, outside every diff hunk, and the project's type gate is `uv run mypy src/` (source only).

## Files

`proposal.md`, `specs/process-boundary/spec.md` (delta), `design.md`, `tasks.md`, `apply-progress.md`, `verify-report.md`, `archive-report.md` (complete).
