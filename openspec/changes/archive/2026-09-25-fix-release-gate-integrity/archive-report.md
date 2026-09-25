# Archive Report: Release gate integrity (CI-03/CI-10 contradiction + #233 lint parity)

**Change**: `fix-release-gate-integrity`
**Archived to**: `openspec/changes/archive/2026-09-25-fix-release-gate-integrity/`
**Branch**: `ci/release-gate-integrity` (base `dev`)

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `ci` | Updated | CI-10 amended (2 stale statements + 1 scenario removed); CI-12 added (1 requirement, 3 scenarios); Test Mapping: 1 stale CI-10 row removed, 3 CI-12 rows appended |

Composition was performed with `gentle-ai sdd-archive-compose --canonical
openspec/specs/ci/spec.md --delta openspec/changes/fix-release-gate-integrity/specs/ci/spec.md`
for the requirement blocks; the `## Test Mapping` table was edited directly because the tool
merges requirements only. The mechanical move of the change folder to the archive was verified
with an empty `diff -r` against a pre-move recursive snapshot.

## Archive Contents

- `explore.md` — present
- `proposal.md` — present
- `specs/ci/spec.md` (delta) — present
- `design.md` — present
- `tasks.md` — present, 14/14 tasks complete
- `apply-progress.md` — present
- `verify-report.md` — present

## Source of Truth Updated

- `openspec/specs/ci/spec.md` — CI-10 now agrees with shipped CI-03; CI-12 (release lint-job
  parity) is canonical.

## SDD Cycle Complete

Implementation: complete (`release.yml`, `tests/test_ci_workflows.py`, canonical `ci` spec).
Verification: independent read-only verifier PASS on all six claims; full suite
`1849 passed, 2 skipped`; checker exit 0; ruff/mypy/pyright clean.
Unfinished tasks and unresolved findings: none observed.
