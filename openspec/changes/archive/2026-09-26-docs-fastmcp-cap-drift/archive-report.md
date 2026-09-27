# Archive Report: Align the fastmcp cap to `>=4,<5` (#257)

**Change**: `docs-fastmcp-cap-drift`
**Archived to**: `openspec/changes/archive/2026-09-26-docs-fastmcp-cap-drift/`
**Branch**: `docs/257-fastmcp-cap-drift` (base `dev` @ `5f6c2de`)

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `packaging` | Updated | PKG-06 cap `fastmcp>=3.4,<4` → `fastmcp>=4,<5` (requirement + 2 scenarios); provenance note added |
| `mcp-server` | Updated | MSP-R02 (requirement + alias + wheel scenario) and MSP-R12 (requirement + 2 scenarios) cap → `fastmcp>=4,<5`; provenance notes added |

The canonical specs were composed directly (MODIFIED requirement blocks replaced in place);
no scenario was added or removed. Both domains remain in `openspec/test-mapping-registry.md`
(the permanent declared backlog) — this change adds no `## Test Mapping` table, so the
registry bijection is unchanged.

## Archive Contents

- `exploration.md`, `proposal.md`, `specs/packaging/spec.md`, `specs/mcp-server/spec.md`,
  `design.md`, `tasks.md`, `apply-progress.md`, `verify-report.md` — all present.

## Source of Truth Updated

- `openspec/specs/packaging/spec.md`, `openspec/specs/mcp-server/spec.md` — `fastmcp>=4,<5`.
- `CONTRIBUTING.md`, `.github/dependabot.yml` — `<5` cap.
- `tests/test_packaging.py` — cap-consistency guard.

## SDD Cycle Complete

Implementation: complete (two specs, two prose homes, one guard).
Verification: independent read-only adversarial subagent — PASS on all six items; the two
material MINOR findings (W3/W4) fixed; negative controls fail on drift; full suite
`1989 passed, 1 skipped`; ruff check/format clean; checker exit 0.
Unfinished tasks and unresolved findings: none material (W1/W2 latent, reported).
