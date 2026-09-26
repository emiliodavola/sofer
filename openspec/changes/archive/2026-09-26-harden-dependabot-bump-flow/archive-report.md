# Archive Report: Harden the release/dependabot bump flow

**Change**: `2026-09-26-harden-dependabot-bump-flow`
**Archived to**: `openspec/changes/archive/2026-09-26-harden-dependabot-bump-flow/`
**Branch**: `ci/dependabot-bump-hardening` (base `origin/dev` @ `1ac716d`)

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `ci` | Updated | CI-13 "Literal-free, consistency-guarded version declarations" added (1 requirement, 3 scenarios); CI-14 "Dependabot update policy" added (1 requirement, 3 scenarios); Purpose sentence extended (CI-07..CI-14); Test Mapping: 6 rows appended |

The canonical `openspec/specs/ci/spec.md` was composed directly by appending
the two `ADDED Requirements` blocks at the end of the requirements section and
appending the six rows to the Test Mapping table; no existing requirement text
was modified beyond the Purpose sentence.

## Archive Contents

- `exploration.md` — present
- `proposal.md` — present
- `specs/ci/spec.md` (delta) — present
- `design.md` — present
- `tasks.md` — present, all tasks complete
- `apply-progress.md` — present
- `verify-report.md` — present (includes the adversarial findings and their resolution)

## Source of Truth Updated

- `openspec/specs/ci/spec.md` — CI-13 and CI-14 are canonical, with Test Mapping rows
  and registry bijection intact (the `ci` spec carries a `## Test Mapping` table, so it
  stays out of `openspec/test-mapping-registry.md`).

## SDD Cycle Complete

Implementation: complete (`tests/test_ci_workflows.py`, `.github/dependabot.yml`,
`CONTRIBUTING.md`, `AGENTS.md`, canonical `ci` spec).
Verification: independent read-only adversarial subagent adjudicated all six
scenarios and its three findings were fixed; focused guards 45 passed; six
negative-control probes fail on drift; full suite `1988 passed, 1 skipped`;
four core modules 100%; TOTAL 94%; checker exit 0; ruff/mypy/pyright clean.
Unfinished tasks and unresolved findings: none.
