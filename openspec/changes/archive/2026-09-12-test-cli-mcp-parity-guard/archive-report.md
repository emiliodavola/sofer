# Archive Report — 2026-09-12-test-cli-mcp-parity-guard

**Change**: `2026-09-12-test-cli-mcp-parity-guard`
**Issue**: GitHub #152/#153/#154/#155 root cause
**Date**: 2026-09-12/13 (archived 2026-09-13)
**Artifact store**: `openspec` (hybrid)
**Status**: **archived** (housekeeping; delivery already merged to `dev`)
**Verify verdict**: **PASS** — `blockers: 0`
**Branch**: `test/mcp-cli-parity-guard` (merged via PR #163)
**Archived path**: `openspec/changes/archive/2026-09-12-test-cli-mcp-parity-guard/`

## Summary

Adds the CLI<->MCP parity guard (tests/test_parity.py) as the systemic root-cause gate behind #152/#153/#154/#155, referenced by the sibling parity changes.

## Files / gaps

- proposal.md, tasks.md, verify-report.md\n- MISSING: design.md and specs/ (test-only change; the scenario mapping lives in verify-report.md)

## Spec Sync

**NOT absorbed into canonical specs.** No `sync-report.md` exists for this
change and `openspec/specs/(no delta specs)` carries no provenance for it. The delta
specs are preserved verbatim inside this archived folder; absorbing them into
the canonical domain is a pending follow-up, not performed at archive time.

## Delivery

Already merged to `dev` via PR #163. Verified PASS, blockers 0. Only the
optional spec-sync follow-up remains.
