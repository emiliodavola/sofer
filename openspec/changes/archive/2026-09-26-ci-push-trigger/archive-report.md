# Archive Report: add a push trigger to ci.yml (GitHub #262)

**Change**: `2026-09-26-ci-push-trigger`
**Archived to**: `openspec/changes/archive/2026-09-26-ci-push-trigger/`
**Branch**: `ci/262-ci-push-trigger` (base `dev`)

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `ci` | Updated | CI-16 added (1 requirement, 2 scenarios); 2 Test Mapping rows appended |

Composition was performed with
`gentle-ai sdd-archive-compose --canonical openspec/specs/ci/spec.md --delta openspec/changes/2026-09-26-ci-push-trigger/specs/ci/spec.md`;
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

- `openspec/specs/ci/spec.md` — CI-16 (ci.yml push/PR trigger contract) is canonical.
- `.github/workflows/ci.yml` — triggers on `push` and `pull_request` to `[main, dev]`.

## SDD Cycle Complete

Implementation: complete. Verification: independent read-only verifier PASS on all
claims; full suite `1994 passed, 2 skipped`; checker exit 0; ruff/mypy/pyright clean.
Unfinished tasks and unresolved findings: none.

## Sequencing Note

CI-16 is numbered 16 because the sibling release-permissions change (#261 / PR #268)
adds CI-15 and is intended to land first; after that merge the `ci` spec's sequence
is contiguous.
