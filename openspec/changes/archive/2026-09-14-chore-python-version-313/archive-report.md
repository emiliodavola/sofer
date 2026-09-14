# Archive Report — 2026-09-14-chore-python-version-313

**Change**: `2026-09-14-chore-python-version-313`
**Issue**: GitHub #178 — closed 2026-09-14T14:30:19Z
**Date**: change authored 2026-09-14; **archived late**, after the sibling changes, to close the lifecycle
**Artifact store**: `openspec` (hybrid — artifacts also mirrored to Engram under `sdd/2026-09-14-chore-python-version-313/**`)
**Status**: **archived by the orchestrator**, not by an `sdd-archive` phase agent
**Verify verdict**: **N/A — no `verify-report.md` was produced.** See "The audit-trail gap" below; this is not a passing verdict and must not be read as one.
**Branch**: `chore/178-python-version-313` — merged via **PR #193** (merge commit `bdcff25`)
**Archived path**: `openspec/changes/archive/2026-09-14-chore-python-version-313/`

## Summary

Closes #178: the tracked development-interpreter pin said `3.10` while the gate-bearing CI jobs run on `3.13`. Because `pyproject.toml:27` declares `tomli>=2.0; python_version < '3.11'`, a 3.10 development environment installs the backport, which makes the `tomllib` arm of the five `try: import tomli as _tomli / except ImportError: import tomllib as _tomli` fallbacks dead. Two mandated gates were therefore unsatisfiable on a clean checkout for reasons unrelated to the code under change:

- `uv run mypy src/` → five `[no-redef]` errors on the duplicated `_tomli` binding;
- `bash scripts/check_core_coverage.sh` → `cli.py` at 99% with `439-440` missing, **and** the script aborted at its first file under `set -euo pipefail`, leaving the remaining three scoped gates unverified.

`# pragma: no cover` is forbidden in those four modules by AGENTS.md rule 14, so it was not an exit. Pinning the development interpreter to the same value CI already uses removes the backport locally, so the `except` arm executes and both gates are green with no flags.

`AGENTS.md` rule 12's latent-issue note was corrected in place: it named three of the five affected modules and quoted an import form that appears nowhere in `src/`.

No user-facing support changed: `requires-python` stays `>=3.10`, the CI matrix keeps exercising `3.10`–`3.14`, and the built wheel still declares `Requires-Python: >=3.10` with a marker-gated `tomli` dependency.

## Delivery

| Commit | Subject |
| --- | --- |
| `c3ab960` | `docs(sdd): add the python-version-313 change artifacts` |
| `7b3e993` | `chore(dev-env): pin the development interpreter to 3.13 and correct the rule-12 note (closes #178)` |

Production diff: **2 lines across 2 files** (`.python-version`, `AGENTS.md`). Merged via PR #193; the issue was closed manually because the PR targeted `dev` and closing keywords only fire against the default branch.

**Gates measured on the merged tree** (recorded in `apply-progress.md` and in PR #193's body):

- `uv run mypy src/` → `Success: no issues found in 32 source files`, exit 0
- `uv run mypy src/ scripts/` → `Success: no issues found in 33 source files`, exit 0
- `bash scripts/check_core_coverage.sh` → exit 0, `cli.py` / `scanner.py` / `prepare.py` / `publish.py` each at **100%**, empty `Missing` column — all four gates reached
- `uv run pytest tests/ -q` → `1766 passed, 6 skipped`, exit 0
- `uv run coverage report -m` → TOTAL 93% (floor `fail_under = 90`)
- `uv run ruff check src/ tests/` → `All checks passed!`
- `uv run pytest tests/test_ci_workflows.py -q` → `19 passed`, exit 0
- `git diff --stat` → exactly the two files

## Spec Sync

**Absorbed into the canonical specs — late.** `openspec/specs/ci/spec.md` now carries **CI-07 — "Dev interpreter pin matches the gate interpreter"**, appended after CI-06 with an `> Added by change ... (GitHub #178)` provenance line, its clause, all five scenarios, and five matching rows in the file's `## Test Mapping` table. CI-01…CI-06 keep their clauses and scenarios byte-for-byte; no `MODIFIED`, `REMOVED` or `RENAMED` operation was involved.

**Why it is late, and why this matters.** PR #193 merged on 2026-09-14 **without** this sync. The change therefore sat on `dev` as the last *active* change — a requirement living only inside an unfinished change folder, invisible to the canonical `ci` spec. This archive closes that lifecycle. **Consequence for any future re-run: CI-07 is already in the canonical file — do not re-insert it.**

## The audit-trail gap (read this before trusting the record)

**This change has no `verify-report.md` and never had one.** The reason is mechanical and worth recording:

1. The `apply` attempt's ledger entry recorded **912 changed lines against a 400-line budget**. Those 912 lines were **SDD artifact prose** — `design.md` 300, `specs/ci/spec.md` 233, `apply-progress.md` 347, plus the `tasks.md` checkbox edits and the two real code lines. The review-workload forecast correctly said "Low"; the attempt budget counted prose.
2. The over-budget decision is **sticky**: neither `settle --untracked-scope=select` nor `exclude` clears it. The provider's only offered continuation was `gentle-ai sdd-attempt reset ...` — a maintainer decision, which was **declined**.
3. With the objective in `decision_required`, `sdd-verify` could not open an attempt, so the verify phase **never ran** and produced no report. `archive` stayed blocked behind it.

So the eight gates above were measured by the **orchestrator** and recorded in `apply-progress.md` and PR #193 — command evidence, reproducible, but **not** a phase-owned verification artifact in the `gentle-ai.verify-result/v1` envelope form the provider requires. Anyone auditing this change should treat `apply-progress.md` as the evidence of record and note the missing verify report rather than assume it existed.

This is also why the change was archived last, after the two sibling changes, and why Fase 0 of the roadmap carried a known open item until this archive landed.

## Process deviations, both recorded

1. **Verify and archive did not run as native phases** for this change (reasons above). The canonical sync, the directory move and this report were performed by the orchestrator.
2. **The `sdd-archive` phase is hard-blocked in this installation.** Three dispatches across two changes were intercepted on their first tool call with `SDD selection blocked: Native SDD discovery cannot run archive`, while the native status was clean and recommended the phase (`archive: ready`, `nextRecommended: "archive"`, `blockedReasons: []`). The sibling changes `2026-09-14-chore-ruff-format-drift` and `2026-09-14-chore-agents-count-infer-type` were archived the same way, and their reports carry the same note.

## Accepted limitations (owned, not closed here)

- **#192** — the structural defect this change only sidesteps: five duplicated version-gated `tomli` fallbacks that make a non-3.13 dev pin and the COV-06 mandate mutually exclusive.
- **#194** — no `ruff format --check` step exists in any workflow.
- **#195** — the pre-commit hook pins ruff `v0.16.7` while the environment resolves `0.16.0`.
- **No pytest-level guard** protects CI-07's two statically-assertable scenarios. The delta's rule-6 resolution records this as a deliberate decision: a drift guard cannot prove the gates are green, and recurrence prevention belongs to #192. Accepted cost: a future local revert of `.python-version` to `3.10` would go uncaught by pytest; CI's 3.13-pinned `lint` and `coverage` jobs remain the authoritative gates.

## Files

`proposal.md`, `specs/ci/spec.md` (delta), `design.md`, `tasks.md`, `apply-progress.md`, `archive-report.md`.

**Not present, and never was:** `verify-report.md`. See "The audit-trail gap".
