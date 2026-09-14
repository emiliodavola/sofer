# Archive Report — 2026-09-14-chore-agents-count-infer-type

**Change**: `2026-09-14-chore-agents-count-infer-type`
**Issue**: GitHub #162
**Date**: 2026-09-14
**Artifact store**: `openspec` (hybrid — every artifact also mirrored to Engram under `sdd/2026-09-14-chore-agents-count-infer-type/**`)
**Status**: **archived**
**Verify verdict**: **PASS** — `blockers: 0`, `critical_findings: 0`; envelope validated by `gentle-ai sdd-verify-validate` → `{"valid": true}`, exit 0
**Branch**: `chore/162-agents-count-infer-type` (cut from `dev` at `bdcff25`)
**Archived path**: `openspec/changes/archive/2026-09-14-chore-agents-count-infer-type/`

## Summary

Closes #162. Two hygiene defects, both fixed at the root rather than at the symptom:

1. **The coverage floor's anchor was stale, not just its number.** `AGENTS.md` rule 6 pinned the "never reduce coverage" floor to `1149 tests currently pass (1151 collected, 2 skipped)`, 617 tests out of date. Replacing the figure with a fresher one would re-stale the same way, so the rule now names the command that produces the tally and labels the figure an observation. The floor's force is unchanged.
2. **The suite emitted a `DeprecationWarning` on every run** from `tests/test_codebook.py` exercising the private deprecated `_infer_type` alias. The nine call sites now assert against the live `infer_column_type` API with identical inputs and identical expected outputs, and with no caller left the alias is deleted from `src/sofer/codebook.py`.

## Delivery

| Commit | Subject |
| --- | --- |
| `10b53fd` | `chore(tests): anchor the coverage floor to a command and retire the _infer_type alias` — 3 files, 22 insertions / 40 deletions |
| `7e95318` | `docs(sdd): add the agents-count-infer-type change artifacts` |

Delivered as a single PR against `dev`, single work unit, no chaining, no `size:exception`, no tag movement.

**Final measured numbers** (reproduced independently by the verify phase):

- `uv run pytest tests/ -q` → `1766 passed, 6 skipped` with **zero** `DeprecationWarning` lines from the codebook surface (was 10 occurrences of the message before the change)
- `uv run pytest tests/test_codebook.py -q` → `82 passed`, exit 0 — and the same under `-W error::DeprecationWarning`, exit 0
- `uv run mypy src/` → clean, 32 source files
- `uv run ruff check src/ tests/` → `All checks passed!`
- `bash scripts/check_core_coverage.sh` → exit 0, four core modules at 100%, empty `Missing` column
- `uv run coverage report -m` → TOTAL 93% (floor `fail_under = 90` untouched)
- `git diff --stat` → exactly `AGENTS.md`, `src/sofer/codebook.py`, `tests/test_codebook.py`

## Behavioural parity — proved, not asserted

Thirteen behavioural cases are preserved. The assertion count moves 17 → 13 because the four discarded `infer_column_type(v) == _infer_type(v)` checks were **tautologies**: the alias was a pure `return infer_column_type(values)`, so each compared a result with itself. The verify phase checked this against the git baseline of the file rather than accepting the claim; nothing was dropped, weakened, skipped, xfailed or parametrised away.

## Spec Sync

**Absorbed into the canonical specs.** `openspec/specs/process-boundary/spec.md` now carries **PB-11** ("Verifiable test-count anchor", two scenarios) and **PB-12** ("Zero deprecation warnings from the migrated codebook surface", three scenarios), appended with `> Added by change ... (GitHub #162)` provenance lines. PB-01…PB-09 keep their clauses and scenarios byte-for-byte; no `MODIFIED`, `REMOVED` or `RENAMED` operation was involved.

### Merge-order constraint — read this before merging

This branch's canonical file ends at **PB-09**, because **PB-10 belongs to the sibling change `2026-09-14-chore-ruff-format-drift` (PR #196), which is not merged into `dev` yet**. The delta therefore reserved **PB-11/PB-12**, and this archive appended them directly after PB-09.

Consequence: **PR #196 must merge first.** After it does, this branch's copy of `process-boundary/spec.md` will conflict with `dev` at the end of the file — resolve it by ordering **PB-10, then PB-11, then PB-12**. Requirement IDs are labels: a gap is cosmetic, and renumbering an already-merged requirement to close one would be the real regression. The archive step must not renumber anything.

### Process deviation — the archive was parent-executed

The canonical sync, the directory move and this report were performed by the **orchestrator (parent)**, not by an `sdd-archive` phase agent. In this installation that phase is hard-blocked at the harness layer: every tool call, including the first, is intercepted with `SDD selection blocked: Native SDD discovery cannot run archive`, while the native status is clean and recommends the phase (`archive: ready`, `nextRecommended: "archive"`, `blockedReasons: []`). The same defect blocked the archive of the sibling change `2026-09-14-chore-ruff-format-drift`, twice. The contradiction and its consequence — **PB-11 and PB-12 are already in the canonical file, so a future archive re-run must not re-insert them** — are recorded here for the next operator.

## Accepted limitations (owned, not closed here)

- **PB-11's two scenarios are prose/command facts**, not pytest-asserted. A static guard would need a fourth file (precedent: `tests/test_ci_workflows.py::test_agents_md_declares_core_100_mandate`), which the change's binding three-file scope excluded. Recorded as an explicit follow-up rather than silence.
- **A private, deprecated, uncalled symbol was removed** (`sofer.codebook._infer_type`). No public API impact; the compatibility note must appear in the PR description and the release notes. The documented fallback, if a reviewer objects, is design §D3 option (A) — a `pytest.warns` migration window.
- **`uv run ruff format --check src/ tests/` is red on six files** — pre-existing drift owned by the unmerged sibling PR #196, outside this change's scope, deliberately not touched.
- Other stale documentation numbers remain and are tracked separately: `openspec/project.md` (#184), the `ruff.toml` reference in `CONTRIBUTING.md` (#187), README counts and flags table (#183, #190). `openspec/config.yaml` is stale too but gitignored, hence local-only and not fixable by a PR.

## Files

`proposal.md`, `specs/process-boundary/spec.md` (delta), `design.md`, `tasks.md`, `apply-progress.md`, `verify-report.md`, `archive-report.md` (complete).
