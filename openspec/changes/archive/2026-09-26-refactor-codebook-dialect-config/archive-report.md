# Archive Report: codebook dialect defaults moved out of the signatures (GitHub #260)

**Change**: `2026-09-26-refactor-codebook-dialect-config`
**Archived to**: `openspec/changes/archive/2026-09-26-refactor-codebook-dialect-config/`
**Branch**: `refactor/260-codebook-dialect-config` (base `dev`)

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `codebook` | Updated | CB-R11 amended (literal-default clause retired, fail-closed scenario added); CB-R12 amended (`generate` defaults clause retired) |

Composition was performed with
`gentle-ai sdd-archive-compose --canonical openspec/specs/codebook/spec.md --delta openspec/changes/2026-09-26-refactor-codebook-dialect-config/specs/codebook/spec.md`.
The `codebook` capability has no `## Test Mapping` table (permanent declared backlog in
`openspec/test-mapping-registry.md`), so no mapping rows changed and the registry bijection holds.

## Archive Contents

- `explore.md` — present
- `proposal.md` — present
- `specs/codebook/spec.md` (delta) — present
- `design.md` — present
- `tasks.md` — present, all tasks complete
- `apply-progress.md` — present
- `verify-report.md` — present

## Source of Truth Updated

- `openspec/specs/codebook/spec.md` — CB-R11/CB-R12 now require the dialect parameters and forbid
  literal `";"` / `"utf-8-sig"` defaults.

## SDD Cycle Complete

Implementation: complete (`codebook.py`, `profile.py`, `cli.py`, the two test files, canonical
`codebook` spec). Verification: independent read-only verifier PASS on all claims; full suite
`2000 passed, 1 skipped`; core 100% gate script exit 0; checker exit 0; ruff/mypy/pyright clean.
Unfinished tasks and unresolved findings: none.
