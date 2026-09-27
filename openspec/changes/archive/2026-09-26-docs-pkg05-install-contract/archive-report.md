# Archive Report: PKG-05 install contract (#259)

**Change**: `docs-pkg05-install-contract`
**Archived to**: `openspec/changes/archive/2026-09-26-docs-pkg05-install-contract/`
**Branch**: `docs/259-pkg05-install-contract` (base `dev` @ `5f6c2de`)

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `packaging` | Updated | PKG-05 rewritten to the git-tag install contract (requirement + renamed scenario + provenance note). No scenario added or removed. |

`packaging` remains in `openspec/test-mapping-registry.md` (permanent declared backlog) — no
`## Test Mapping` table was authored, so the registry bijection is unchanged.

## Archive Contents

- `exploration.md`, `proposal.md`, `specs/packaging/spec.md`, `design.md`, `tasks.md`,
  `apply-progress.md`, `verify-report.md` — all present.

## Source of Truth Updated

- `openspec/specs/packaging/spec.md` — PKG-05.
- `tests/test_packaging.py` — README git-tag install test.

## Discovered (reported, not fixed)

PKG-03 S2 requires `sofer-mcp --help` to exit 0; it blocks (`main()` runs a stdio server), exit
`124` under a timeout. Recorded in `verify-report.md` for a follow-up change.

## SDD Cycle Complete

Implementation: complete (one spec, one test).
Verification: independent read-only adversarial subagent — PASS on all eight items; the material
MINOR findings fixed (hardened bare-install check); negative controls fail on drift; full suite
`1989 passed, 1 skipped`; ruff check/format clean; checker exit 0.
Unfinished tasks and unresolved findings: none in scope.
