# Archive Report — 2026-09-12-fix-residual-parity

**Change**: `2026-09-12-fix-residual-parity`
**Issue**: GitHub #153 + #155
**Date**: 2026-09-12/13 (archived 2026-09-13)
**Artifact store**: `openspec` (hybrid)
**Status**: **archived** (housekeeping; delivery already merged to `dev`)
**Verify verdict**: **PASS** — `blockers: 0`
**Branch**: `fix/153-155-residual-parity` (merged via PR #165)
**Archived path**: `openspec/changes/archive/2026-09-12-fix-residual-parity/`

## Summary

Closes the last two CLI-MCP parity gaps declared as known_gaps in the parity guard: publish clean/clean_cache (#153) and batch max_sample (#155).

## Files / gaps

- proposal.md, specs/{codebook,mcp-server}, tasks.md, verify-report.md\n- MISSING (ad-hoc flow): apply-progress.md, design.md

## Spec Sync

**NOT absorbed into canonical specs.** No `sync-report.md` exists for this
change and `openspec/specs/codebook, mcp-server` carries no provenance for it. The delta
specs are preserved verbatim inside this archived folder; absorbing them into
the canonical domain is a pending follow-up, not performed at archive time.

## Delivery

Already merged to `dev` via PR #165. Verified PASS, blockers 0. Only the
optional spec-sync follow-up remains.
