# Archive Report: fix-sofer-init-cwd-windows-todo

**Change**: `fix-sofer-init-cwd-windows-todo` (issue #113, PR #114)
**Archived**: 2026-08-31
**Archived to**: `openspec/changes/archive/2026-08-31-fix-sofer-init-cwd-windows-todo/`
**Artifact store**: hybrid (Engram + openspec files) — persisted to both backends
**Execution mode**: auto | **Delivery strategy**: auto-forecast | **Review budget**: 3000 lines (single PR, Low risk)

## Summary

Fixed MCP `sofer_init` writing to parent directory and `TODO:` placeholders with `:` illegal on NTFS. Template `_INIT_TEMPLATE` (`src/sofer/cli.py`) now uses Windows-safe `raw/example.csv` (no colon, `ntpath.splitdrive` → `""`). `sofer_init` gains optional `cwd: str | None` with per-call `effective_root` contained under `_SERVER_ROOT` (`_contained_path` + `is_relative_to`, `PathOutsideRootError` on escape, no global mutation). `scanner.py:merge_entries` strips `raw/example*` placeholder so `sofer_scan_apply` cleans template and `sofer_validate` passes. 5 test groups (Windows placeholder, cwd containment, stale-root anchored, xlsx integration, schema contract) + `test_cli` literal update + `README.md`/`README_ES.md` Phase 0 sync. Verification: 1253 passed, 2 skipped, ruff clean, mypy 5 pre-existing `no-redef` only, 19/19 spec scenarios compliant, PASS.

## Task Completion Gate

- **Result**: PASS — all implementation tasks checked
- **Tasks**: 10/10 complete (1.1, 2.1, 2.2, 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2) — zero unchecked `- [ ]`
- **Verify**: `verify.md` verdict `pass`, `critical_findings: 0`, `blockers: 0`, `requirements 6/6`, `scenarios 19/19`
- **Source**: persisted `tasks.md` is audit trail; `apply.md` (10/10) and `verify.md` corroborate — no stale-checkbox reconciliation needed

## Spec Sync Results

| Domain | Action | Details |
|--------|--------|---------|
| `cli` | Updated | MODIFIED `CLI-R07` — merged Windows-safe `raw/example.csv` clause into description, preserved original 8 scenarios and added 3 new: `Windows-safe placeholder`, `ntpath drive`, `scan xlsx after init` (total 11). Non-destructive merge (warn threshold `rules.archive` observed; preserved existing scenarios, added delta scenarios). |
| `mcp-server` | Updated | MODIFIED `MSP-R03` — added `cwd: str \| None = None` per INIT-02 to description and added `sofer_init cwd schema` scenario (now 3 scenarios). Preserved `Constrained schemas` + `Annotations and output_schema` scenarios. |
| `mcp-server` | Created | ADDED `INIT-01` Windows-safe init placeholder (3 scenarios) |
| `mcp-server` | Created | ADDED `INIT-02` sofer_init cwd containment (5 scenarios) |
| `mcp-server` | Created | ADDED `INIT-03` Anchored writes under effective_root (3 scenarios) |
| `mcp-server` | Created | ADDED `INIT-04` xlsx discovery after init (3 scenarios) |

**Source of truth updated**:
- `openspec/specs/cli/spec.md` — CLI-R07 now Windows-safe
- `openspec/specs/mcp-server/spec.md` — MSP-R03 + INIT-01..04

Merge strategy: ADDED → append; MODIFIED → replace matching requirement by name while preserving other requirements; RENAMED/REMOVED none. No other requirements mutated.

## Archive Contents

| Artifact | File | Engram Topic | Observation ID | Status |
|----------|------|--------------|----------------|--------|
| explore | `explore.md` | `sdd/fix-sofer-init-cwd-windows-todo/explore` | #802 `obs-e42ec3be88b914f5` | ✅ |
| proposal | `proposal.md` | `sdd/fix-sofer-init-cwd-windows-todo/proposal` | #803 `obs-2cd36c2a31f850a3` | ✅ |
| spec (delta) | `specs/cli/spec.md` + `specs/mcp-server/spec.md` | `sdd/fix-sofer-init-cwd-windows-todo/spec` | #806 `obs-8b3f6b58d359b376` | ✅ |
| design | `design.md` | `sdd/fix-sofer-init-cwd-windows-todo/design` | #807 `obs-d98028995f49bd6c` | ✅ |
| tasks | `tasks.md` | `sdd/fix-sofer-init-cwd-windows-todo/tasks` | #808 `obs-d1b033b067be1b0a` | ✅ (10/10) |
| apply-progress | `apply.md` | `sdd/fix-sofer-init-cwd-windows-todo/apply-progress` | #809 `obs-bfb2dd29cd53cede` | ✅ |
| verify-report | `verify.md` | `sdd/fix-sofer-init-cwd-windows-todo/verify-report` | #810 `obs-e0c84768b2ae8d45` | ✅ (PASS) |
| archive-report | `archive.md` (this file) | `sdd/fix-sofer-init-cwd-windows-todo/archive-report` | (this save) | ✅ |

All 8 artifacts archived (7 prior + this report). Active `openspec/changes/fix-sofer-init-cwd-windows-todo/` no longer exists — moved with date prefix.

## Verification

- [x] Main specs updated correctly (cli + mcp-server)
- [x] Change folder moved to `archive/2026-08-31-fix-sofer-init-cwd-windows-todo/`
- [x] Archive contains all artifacts (proposal, specs/, design, tasks, apply, verify, explore, archive)
- [x] Archived `tasks.md` has no unchecked implementation tasks
- [x] Active changes directory no longer has this change
- [x] Verify report PASS, 0 critical, 0 blockers

## Files Changed (from apply.md)

- `src/sofer/cli.py` — `_INIT_TEMPLATE` Windows-safe placeholder
- `src/sofer/mcp_server.py` — `sofer_init` `cwd` + `effective_root` containment
- `src/sofer/scanner.py` — `merge_entries` strips `raw/example*`
- `tests/test_mcp_server.py` — 5 test groups (14 tests: placeholder, containment, stale-root, xlsx, schema)
- `tests/test_cli.py` — Windows-safe placeholder assertion
- `README.md`, `README_ES.md` — Phase 0 wording sync

## Next Steps

- None required for this change — SDD cycle complete (explore → propose → spec → design → tasks → apply → verify → archive)
- Follow-up deferred per proposal: Approach 2 — default live `Path.cwd()` + `cwd` on `sofer_scan_*` (file new issue)
- Optional Windows CI: `windows-latest` matrix deferred — `ntpath` unit test suffices; file follow-up if team wants matrix
- Ready for next change

## Risks

None — all scenarios compliant, no destructive merge, no critical findings.

## SDD Cycle Complete

The change has been fully planned, implemented, verified, and archived. The following canonical specs now reflect the new behavior:

- `openspec/specs/cli/spec.md` (CLI-R07 Windows-safe)
- `openspec/specs/mcp-server/spec.md` (INIT-01..04 + MSP-R03 cwd)

Ready for the next change.

---
*Generated by sdd-archive for fix-sofer-init-cwd-windows-todo. Hybrid persistence: Engram topic `sdd/fix-sofer-init-cwd-windows-todo/archive-report` + `openspec/changes/archive/2026-08-31-fix-sofer-init-cwd-windows-todo/archive.md`. Review budget 3000 lines; delivery strategy auto-forecast.*
