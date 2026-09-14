# Delta for process-boundary

> **Change** `2026-09-14-chore-ruff-format-drift` (GitHub #177) · branch `chore/177-ruff-format-drift` · store **hybrid** (this file + Engram mirror under topic key `sdd/2026-09-14-chore-ruff-format-drift/spec`).
>
> **Repo state — resolves the proposal's stale row without editing it.** `proposal.md`'s "Verified state" row records HEAD on `refs/heads/dev`; that was true when written and the parent has since resolved it: `.git/HEAD` reads `ref: refs/heads/chore/177-ruff-format-drift`, and the loose refs `.git/refs/heads/dev` and `.git/refs/heads/chore/177-ruff-format-drift` are both `bdcff254c4f315362b6977be8de2d1c12257a7a4` (identical → the branch sits at `dev`'s SHA, zero commits ahead). `proposal.md` is deliberately **not** edited; the "commit lands on `dev`" risk is discharged by this citation.
>
> **Capability choice — `process-boundary`, justified.** This change has no behaviour change and no capability change: it reformats six test files. What it establishes is a durable verification property of the tree, and PB-07 ("Quality gates") already owns exactly that category — it enumerates the commands a change must satisfy (`pytest`, `ruff check`, `mypy`, `git diff --check`), so the formatter belongs beside the other gates. The alternative home, `ci` CI-06, was considered and **rejected**: CI-06 owns CI/workflow documentation truth, and this change deliberately adds **no CI step**, so a `ci` requirement naming a workflow step would be false. `ci` is cross-referenced only, never modified.
>
> **Additive, not destructive.** No existing `process-boundary` requirement text changes (PB-01..PB-09 keep clauses and scenarios byte-for-byte), so archive-time replacement of a canonical block would be a lossy no-op; the clause enters as **new** requirement **PB-10** (next free ID in this capability).
>
> **Domain hygiene:** `openspec/specs/process-boundary/spec.md` exists and was read before writing (delta, not full spec); no other non-archived change carries `specs/process-boundary/`; this change has no legacy flat `openspec/changes/<change>/spec.md`.

## ADDED Requirements

### Requirement: Formatter integrity on a clean checkout (PB-10)

> Added by change `2026-09-14-chore-ruff-format-drift` (GitHub #177).

The repository's Python sources and tests SHALL satisfy the project formatter: `uv run ruff format --check src/ tests/` SHALL exit **0** on a clean checkout of this change, reporting zero files to reformat. Achieving that SHALL be a formatting-only edit — exactly these six test files SHALL change (`tests/test_ci_workflows.py`, `tests/test_coverage_contract.py`, `tests/test_mcp_registration.py`, `tests/test_profile.py`, `tests/test_publish.py`, `tests/test_splits.py`) and the diff SHALL contain no other path (zero `src/sofer/`, zero `.github/workflows/`, zero `pyproject.toml` paths). The reformat SHALL NOT alter logic, assertions, imports, or test behaviour, and the two static contract guards SHALL keep their asserted strings, since the formatter does not rewrite string contents.

The requirement SHALL be satisfiable with **no new CI step**: enforcement remains the local pre-commit `ruff-format` hook on staged files, zero `format --check` invocations exist under `.github/workflows/` both before and after the change, and issue **#194** — not any clause here — SHALL own both the decision to arm such a gate and the resulting fact that this defect class stays open (drift can return on files nobody stages). The ruff pin mismatch (hook `v0.16.7` vs ambient `0.16.0`) SHALL stay unaddressed here and SHALL be owned by **#195**. Evidence for this requirement is command output, and the sibling gates SHALL stay green and unweakened (PB-05, PB-07, `ci` CI-01, `coverage` COV-06).

#### Scenario: Clean-checkout format check exits 0

- GIVEN a clean checkout with this change applied, no `--python` flag and no local formatting
- WHEN `uv run ruff format --check src/ tests/` runs
- THEN it SHALL exit 0 and report zero files to reformat
- AND `uv run ruff format --diff src/ tests/` SHALL emit no diff, so nothing is left to reformat

#### Scenario: Exactly the six test files changed

- GIVEN this change's diff
- WHEN `git diff --stat` is inspected
- THEN exactly the six named test files SHALL appear and no other path SHALL appear
- AND there SHALL be zero `src/sofer/`, zero `.github/workflows/`, and zero `pyproject.toml` paths

#### Scenario: Formatting-only — behaviour and asserted content preserved

- GIVEN the suite tally recorded immediately before the reformat
- WHEN `uv run pytest tests/ -q` runs after it
- THEN the passed/skipped/collected counts SHALL be identical and there SHALL be 0 failures
- AND `tests/test_ci_workflows.py` and `tests/test_coverage_contract.py` SHALL pass with their asserted strings unchanged — no logic, assertion, import, or test-behaviour edit SHALL be present

#### Scenario: No CI gate was armed, and recurrence stays owned by #194

- GIVEN `.github/workflows/**` before and after the change
- WHEN scanned for a `format --check` invocation
- THEN zero matches SHALL exist in both states and no workflow file SHALL appear in the diff
- AND enforcement SHALL remain the local pre-commit `ruff-format` hook on staged files, with recurrence owned by issue #194 rather than by any clause of PB-10

#### Scenario: Sibling gates stay green and unmoved

- GIVEN the change applied
- WHEN `uv run ruff check src/ tests/`, `uv run mypy src/`, `git diff --check`, and `uv run coverage run -m pytest` followed by `bash scripts/check_core_coverage.sh` run
- THEN each SHALL exit 0, the coverage script SHALL reach all four of its scoped gates with every row at 100.00% and an empty `Missing` column (`coverage` COV-06), and the TOTAL floor SHALL remain the config-owned `fail_under = 90` (`ci` CI-01)

---

## Rule-6 resolution: one command per scenario, no test invented

AGENTS.md rule 6 / `rules.specs` require every scenario to have a corresponding test. This change adds **no test** — there is no behaviour to unit-test — and invents no vacuous one; it resolves the rule the way this repo already resolves measurement-shaped requirements: the `coverage` spec records measured percentages and the four 100.00% rows as **verify-phase command evidence** enforced by the scoped gates' exit codes and explicitly "NOT pytest-assertable", `ci` CI-01's "Gate is config-driven" scenario is mapped partly to the local `uv run coverage report -m` exit code ("verify-phase runtime evidence"), `ci` CI-03's release scenario is mapped wholly to static evidence, and the immediately preceding change's CI-07 delta (`2026-09-14-chore-python-version-313`, `specs/ci/spec.md`) resolved it identically for the same reason. Every PB-10 scenario is measurement-shaped: asserting any of them from pytest would mean spawning `ruff format` / `mypy` / `coverage` inside the suite. **Accepted cost, stated plainly:** no drift guard is added, so a future reformat-shaped drift again escapes pytest — precisely the gap issue **#194** exists to close, which this requirement does not claim to close. Mapping: **S1** ← V1 `uv run ruff format --check src/ tests/` exit 0 with 0 to reformat, plus V6 `ruff format --diff` empty (runtime exit-code evidence); **S2** ← V6 `git diff --stat` showing exactly the six paths and no `src/sofer/`, `.github/workflows/`, or `pyproject.toml` path (static); **S3** ← V3 `uv run pytest tests/ -q`, baseline tally recorded before the format then identical, 0 failures, both contract guards green (runtime — PB-05's own gate, re-used not replaced); **S4** ← static `format --check` grep over `.github/workflows/**` = 0 matches before and after, no workflow path in the diff; **S5** ← V2 `ruff check` "All checks passed!", V4 `mypy src/` clean (32 files), V5 `scripts/check_core_coverage.sh` exit 0 with four 100.00% rows, `git diff --check` clean (runtime gate exit codes).

## Cross-referenced and deliberately untouched

- `process-boundary` PB-05 (complete-run gate), PB-07 (its four commands keep passing with unchanged text), PB-01..PB-04/06/08/09 — untouched: the six reformatted files are formatting-only, no boundary contract/fixture/offline rule changes, and the post-change suite run satisfies PB-05 exactly as before.
- `ci` CI-01 (config-owned `fail_under = 90`) and CI-06 (declared config + documentation truth), plus `coverage` COV-01 / COV-06 (floors, four-module 100.00% mandate, pragma ban) — untouched: no CI step, no `openspec/config.yaml` entry, no documentation surface, and covered lines are unmoved by a whitespace-only reformat; the scoped gates are re-run as evidence, never re-declared.

**Non-goals recorded by this delta:** no `ruff format --check` step in any workflow (#194); no ruff version-pin change (#195); no formatting change outside the six named files; no fix for the `AGENTS.md` rule-6 counts (#162), `openspec/project.md` (#184), or the `ruff.toml` reference (#187); no touch of `tasks.md`, `proposal.md`, canonical specs under `openspec/specs/**`, `.python-version`, `src/sofer/**`, or the still-active `openspec/changes/2026-09-14-chore-python-version-313/`; no commit, push, PR, or tag movement.

---
