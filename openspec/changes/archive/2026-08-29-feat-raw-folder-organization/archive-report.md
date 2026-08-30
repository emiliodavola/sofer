# Archive Report: 2026-08-29-feat-raw-folder-organization

**Change**: 2026-08-29-feat-raw-folder-organization
**Branch**: feat/raw-folder-organization
**Archived to**: `openspec/changes/archive/2026-08-29-feat-raw-folder-organization/` (hybrid — filesystem + Engram)
**Archive date**: 2026-08-29 (ISO) — re-archive after branch cleanup (branch at 442f773)
**Mode**: hybrid (openspec + engram)
**Verdict**: PASS — 38/38 scenarios, 984/152 tests, ruff/mypy green

## Artifact Traceability (Engram IDs)

| Artifact | Observation ID | Sync ID | Title |
|----------|---------------|---------|-------|
| proposal | 685 | obs-de27f0f2408f958e | sdd/2026-08-29-feat-raw-folder-organization/proposal |
| spec (delta) | 687 | obs-a6907204230bb257 | sdd/2026-08-29-feat-raw-folder-organization/spec |
| design | 689 | obs-a949cb8ceb492df9 | sdd/2026-08-29-feat-raw-folder-organization/design |
| tasks | 691 | obs-0d904e2c332a6b12 | sdd/2026-08-29-feat-raw-folder-organization/tasks |
| apply-progress | 693 | obs-afa1c34acc2f9fc1 | Apply raw-folder-organization — 18/18 tasks complete (remediation tests committed) |
| verify-report (PASS re-verified) | 695 | obs-53f89338bd490ce8 | sdd/2026-08-29-feat-raw-folder-organization/verify-report |
| archive-report (this) | 697 | obs-cec70e320c7bdf1b | sdd/2026-08-29-feat-raw-folder-organization/archive-report |

All 6 predecessor observations retrieved via `mem_get_observation` before archive. No missing artifacts. `actionContext.mode` was not `workspace-planning` — no guard triggered. Re-archive: previous archive at 8a58b85 (fix branch) was preserved; this re-archive restores 2026-08-29 folder after cleanup where Test-Path was False. Branch `feat/raw-folder-organization` verified at 442f773 (5 commits after dc6821c).

## Task Completion Gate

**Persisted tasks artifact**: `openspec/changes/archive/2026-08-29-feat-raw-folder-organization/tasks.md` (moved from `openspec/changes/2026-08-29-feat-raw-folder-organization/tasks.md`)

- Checked: `- [ ]` count = 0, `- [x]` count = 18 — **PASS**
- No stale unchecked implementation tasks. `sdd-apply` (progress 693, remediation 442f773) correctly marked all 18 tasks complete across Phases 1-5.
- No exceptional reconciliation needed. `apply-progress` (693) and `verify-report` (695) prove completion — archive did not need to repair checkboxes.

## Specs Synced

Delta specs merged BEFORE archive move per SDD archive rule.

| Domain | Action | Details |
|--------|--------|---------|
| scan | Updated | 1 ADDED (SCN-07 Source Layout and Copy-Only), 4 MODIFIED (SCN-01 File Discovery, SCN-02 TOML Merge, SCN-03 File Copy, SCN-06 Error Handling) — Purpose updated `data/` → `cache/` (`OUTPUT_DIR`); total reqs 6→7 (SCN-04/05 preserved) |
| tool-config | Updated | 1 ADDED (TC-10 Raw directory bootstrap key), 1 MODIFIED (TC-07 Bootstrap keys anchor on cwd — now includes `raw_dir`); total reqs 9→10 (TC-01..09 preserved, TC-10 appended) |
| cli | Updated | 2 ADDED (CLI-R07 init creates raw/ and --move-existing, CLI-R08 Help for init --move-existing), 1 MODIFIED (CLI-R02 Help text accurate for new commands — init template `raw/` convention); total reqs 6→8 (CLI-R01,R03,R04,R05,R06 preserved) |

### Merge details

- **scan/spec.md**: Replaced SCN-01/02/03/06 with delta versions (stripped `(Previously: ...)` annotations), appended SCN-07, updated Purpose sentence to `cache/` (`OUTPUT_DIR`). Preserved SCN-04 (CLI Interface) and SCN-05 (Idempotency) verbatim. Verified `cache/` refs and `raw/` never-excluded clause; SCN-01 now includes `raw discovered, cache excluded` scenario.
- **tool-config/spec.md**: Replaced TC-07 with `default_config_name, output_dir, raw_dir` cwd-only list plus three scenarios (default_config_name, raw_dir, bootstrap limitation documented). Appended TC-10 with 3 scenarios (default raw_dir is "raw", pyproject overrides, dataset-dir wins over cwd).
- **cli/spec.md**: Replaced CLI-R02 with updated help/template description (prepare/publish flags, no stale upload, README `raw/` layout). Appended CLI-R07 (8 scenarios: creates raw/, idempotent, depth-1 only supported, collision guard, dry-run preview, non-interactive guard, prompt N aborts, template mentions raw/) and CLI-R08 (help lists flags).

No REMOVED or RENAMED requirements in this delta. No destructive merge — warning not needed. `rules.archive` from `openspec/config.yaml` is `Warn before merging destructive deltas` — no destructive delta present.

## Source of Truth Updated

The following specs now reflect the new behavior:

- `openspec/specs/scan/spec.md` — raw/cache/build pipeline, flatten_first_level, copy-only
- `openspec/specs/tool-config/spec.md` — raw_dir bootstrap key, walk-up precedence
- `openspec/specs/cli/spec.md` — init raw/ scaffolding, --move-existing/--dry-run/--force, help

## Archive Contents

Filesystem archive at `openspec/changes/archive/2026-08-29-feat-raw-folder-organization/`:

- proposal.md ✅ (from 685)
- specs/scan/spec.md ✅
- specs/tool-config/spec.md ✅
- specs/cli/spec.md ✅
- design.md ✅ (from 689)
- tasks.md ✅ (18/18 tasks complete — 0 unchecked, 18 checked)
- apply-progress.md ✅ (693 remediated 442f773)
- verify-report.md ✅ (695 PASS re-verified)
- exploration.md ✅ (optional, preserved)
- archive-report.md ✅ (this file)

Active changes directory `openspec/changes/2026-08-29-feat-raw-folder-organization/` no longer exists (Move-Item verified — Test-Path False).

## Verification (pre-archive)

From verify-report 695 (re-verified PASS, evidence_revision `sha256:988ede4d712fec839ff5f2c45cef8036c03c26166cefa4f69f7e001fb5addaf2`):

- verdict: pass, blockers: 0, critical_findings: 0, requirements: 10/10, scenarios: 38/38
- Tests: `uv run pytest tests/test_config.py tests/test_cli.py tests/test_scanner.py -q` — 152 passed; `uv run pytest -q` — 984 passed, 2 skipped, 13 warnings (pre-existing DeprecationWarning in test_codebook)
- Build: `uv run ruff check .` All checks passed; `uv run ruff format --check .` 64 files formatted; `uv run mypy src/` Success no issues in 27 files
- Previous 695 FAIL (20/38 UNTESTED, git diff tests/ empty) remediated by 442f773 (25 tests: 7 config + 11 cli + 7 scanner); git diff dev -- tests/ now non-empty, git diff dev --stat 18 files
- Tasks 18/18 complete honest; no CRITICAL issues — archive-eligible per strict-vs-OpenSpec policy
- Branch feat/raw-folder-organization is at 442f773 (5 commits after dc6821c), no archive folder yet before this re-archive (Test-Path False confirmed). Fix branch already archived at 8a58b85.

## SDD Cycle Complete

The change has been fully planned, implemented, verified, and archived. The delta specs are now the source of truth. Ready for the next change. Branch `feat/raw-folder-organization` ready for PR/merge — archive is audit trail, not deletion. This re-archive restores the lost archive after branch cleanup.

## Risks

None. No CRITICAL verification issues, no stale checkboxes, no destructive merge, no missing artifacts. SUGGESTION-level items from verify (S1 raw_dir type guard, S2 nested flatten already covered) are non-blocking.

## Execution Notes

- Task Completion Gate inspected before sync — 0 unchecked, so sync proceeded.
- Sync performed before Move — spec merge before Move-Item per archive contract.
- ISO date `2026-08-29` used for archive folder prefix — matches change date and re-archive instruction.
- Hybrid persistence: filesystem merge + move AND Engram archive-report with observation IDs for traceability.
- Re-archive note: previous archive-report observation 697 existed (from 2026-08-29 21:43:02) — this write upserts it via same topic_key `sdd/2026-08-29-feat-raw-folder-organization/archive-report`.
