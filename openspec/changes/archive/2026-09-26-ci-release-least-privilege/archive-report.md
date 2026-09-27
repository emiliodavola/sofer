# Archive Report: scope release.yml write access to the release job (GitHub #261)

**Change**: `2026-09-26-ci-release-least-privilege`
**Archived to**: `openspec/changes/archive/2026-09-26-ci-release-least-privilege/`
**Branch**: `ci/261-release-permissions` (base `dev`)

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `ci` | Updated | CI-15 added (1 requirement, 2 scenarios); 2 Test Mapping rows appended |

Composition was performed with
`gentle-ai sdd-archive-compose --canonical openspec/specs/ci/spec.md --delta openspec/changes/2026-09-26-ci-release-least-privilege/specs/ci/spec.md`;
the `## Test Mapping` rows were appended directly (the tool merges requirements only).

## Archive Contents

- `explore.md` — present
- `proposal.md` — present
- `specs/ci/spec.md` (delta) — present
- `design.md` — present
- `tasks.md` — present, all tasks complete
- `apply-progress.md` — present
- `verify-report.md` — present

## Source of Truth Updated

- `openspec/specs/ci/spec.md` — CI-15 (least-privilege release permissions) is canonical.
- `.github/workflows/release.yml` — workflow-level read-only; only the `release` job writes.

## SDD Cycle Complete

Implementation: complete. Verification: independent read-only verifier PASS on all
claims; full suite `1994 passed, 2 skipped`; checker exit 0; ruff/mypy/pyright clean.
Unfinished tasks and unresolved findings: none.
