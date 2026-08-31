# Archive Report — fix-multisheet-codebook-card-collapse

- **Change**: `fix-multisheet-codebook-card-collapse` (#97 multisheet codebook wb.active bug + #98 collapsible Data Fields per-sheet)
- **Date**: 2026-08-30
- **Store**: hybrid (Engram + openspec)
- **Archived to**: `openspec/changes/archive/2026-08-30-fix-multisheet-codebook-card-collapse/`
- **Status**: archived — all 10 tasks complete, verify PASS (no CRITICAL)

## Lineage — Engram Observation IDs

| Artifact | Observation ID | Title / topic_key |
|----------|---------------|-------------------|
| explore | #739 | `sdd/fix-multisheet-codebook-card-collapse/explore` |
| proposal | #740 | `sdd/fix-multisheet-codebook-card-collapse/proposal` |
| spec | #741 | `sdd/fix-multisheet-codebook-card-collapse/spec` |
| design | #742 | `sdd/fix-multisheet-codebook-card-collapse/design` |
| tasks | #743 | `sdd/fix-multisheet-codebook-card-collapse/tasks` |
| apply-progress | #744 | `sdd/fix-multisheet-codebook-card-collapse/apply-progress` |
| verify-report | #745 | `sdd/fix-multisheet-codebook-card-collapse/verify-report` |
| archive-report | (this report) | `sdd/fix-multisheet-codebook-card-collapse/archive-report` |

`capture_prompt: false` for all SDD artifacts (automated pipeline outputs). Engram is source of truth for recovery; filesystem delta + main specs are audit trail.

## Task Completion Gate

- **Tasks artifact**: `openspec/changes/fix-multisheet-codebook-card-collapse/tasks.md` — 10/10 `[x]` (phases 1–5)
- **Apply progress**: Engram #744 — 10/10 complete, files changed: `config.py`, `pyproject.toml`, `docs/configuration.md`, `codebook.py` (`_read_xlsx_sheets`, `_read_xlsx` wrapper, `_codebook_output_for_rel`, `_normalize_codebook_collision_key`, sheet-expanded `generate_all` + `xlsx_cache`), `repo_compliance.py` (`_sheet_label_from_origin`, `_group_by_origin`, per-group `<details>` gated `len(group)>thr OR len(groups)>1` with blank line), `tests/test_codebook.py`, `tests/test_repo_compliance.py`, `README.md`, `README_ES.md`
- **Verify**: Engram #745 + `verify.md` — **PASS**, 1163 passed 2 skipped, ruff + mypy + ruff format green, all spec scenarios proven (CB-R09 01-07, CB-R03/R04 modified, RC-R21 01-08, TC-12 01-07, PRP-10 01-03), warnings only non-blocking coverage gaps
- **Gate result**: ✅ PASS — no unchecked implementation tasks, no CRITICAL blockers, stale-checkbox reconciliation not needed

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `codebook` | Updated | **1 ADDED** CB-R09 multisheet XLSX per sheet (7 scenarios) + **2 MODIFIED** CB-R03 batch generation (sheet-expanded collision, N-files, partial-write-then-raise) + CB-R04 root index (Tables counts sheets, per-sheet links) |
| `repo-compliance` | Updated | **1 ADDED** RC-R21 collapsible Data Fields per sheet with threshold (8 scenarios, per-table `<details>` + blank line, `thr OR groups>1`, `features` flat) |
| `tool-config` | Updated | **1 ADDED** TC-12 `card_collapse_threshold=15` (`_DEFAULTS`, `CARD_COLLAPSE_THRESHOLD`, `int>=0`, `reload` rebinding, tool-wide only) |
| `prepare` | Updated | **1 ADDED** PRP-10 prepare inherits multisheet N-files via `generate_all(output_dir=build)` (3 scenarios, no new XLSX logic) |

**Merge contract**: ADDED → appended; MODIFIED → replaced matching requirement preserving other requirements; no REMOVED/RENAMED; existing IDs preserved, no duplication.

### Main specs updated

- `openspec/specs/codebook/spec.md` — now contains CB-R09 (new) + updated CB-R03/CB-R04
- `openspec/specs/repo-compliance/spec.md` — now contains RC-R21
- `openspec/specs/tool-config/spec.md` — now contains TC-12
- `openspec/specs/prepare/spec.md` — now contains PRP-10

## Archive Contents

- `proposal.md` ✅ (intent #97+#98, scope in/out, approach A N-files, risks, rollback)
- `exploration.md` ✅ (wb.active bug, sanitize_sheet_name divergence, N-files vs one-file, HF `<details>` constraint)
- `specs/` ✅ (codebook/spec.md, repo-compliance/spec.md, tool-config/spec.md, prepare/spec.md — deltas)
- `design.md` ✅ (N-files provenance, sheet-expanded collision, tool-wide threshold, OR predicate, per-group `<details>`)
- `tasks.md` ✅ (10/10 tasks complete, review workload Low, single PR)
- `verify.md` ✅ (PASS — completeness + correctness matrix + build evidence + design coherence)
- `archive.md` ✅ (this file)

Active changes directory no longer has this change after move.

## Source of Truth Updated

The following specs now reflect the new behavior and are the authoritative source for future changes:

- `openspec/specs/codebook/spec.md` — CB-R09 + CB-R03 + CB-R04
- `openspec/specs/repo-compliance/spec.md` — RC-R21
- `openspec/specs/tool-config/spec.md` — TC-12
- `openspec/specs/prepare/spec.md` — PRP-10

## Project Config Updated

- `openspec/project.md` — Architecture notes updated: `generate_all()` N codebooks per XLSX sheet via `sanitize_sheet_name` + `seen` dedup, sheet-aware collision/index; `build_dataset_card()` per-sheet `<details>` gated by `CARD_COLLAPSE_THRESHOLD=15`; tests count updated 1031→1163. Last-updated footer stamped 2026-08-30.
- `openspec/config.yaml` — unchanged (no archive rule trigger, no new testing infra)

## README / Docs Sync

- `README.md` + `README_ES.md` already synced in apply (codebook `codebooks/<rel>/<stem>__<sanitized>.md` + per-sheet collapsible `<details>` HF-compatible *cada tabla por separado* + `card_collapse_threshold` default 15) — confirmed, no further edit
- `docs/configuration.md` already documents `card_collapse_threshold | 15` — preserved
- `pyproject.toml` `[tool.sofer] card_collapse_threshold = 15` — authoritative default, no literal elsewhere

## Verification post-sync

- Main specs contain new requirements (grep `CB-R09`, `RC-R21`, `TC-12`, `PRP-10` each count >=1) ✅
- No duplicated requirement headers (single `CB-R09`, single `RC-R21`, etc.) ✅
- Existing requirements preserved (CB-R01..R08, RC-R01..R17 etc.) ✅
- Change folder moved to `openspec/changes/archive/2026-08-30-fix-multisheet-codebook-card-collapse/` ✅
- Engram archive-report saved with lineage IDs ✅

## SDD Cycle Complete

The change has been fully planned, implemented, verified, and archived. Provenance chain `sheet → stem__sheet.parquet → stem__sheet.md → per-sheet <details>` is restored, gated by tool-wide `card_collapse_threshold=15`. Rollback via `card_collapse_threshold=999` or revert sources. Ready for the next change.

## Risks / Follow-ups

- **WARNING (verify #745)**: Dedup test uses `Ventas`/`Ventas!` not literal `Ventas`/`VENTAS` (openpyxl title uniqueness); third duplicate `_3` not explicitly asserted — non-blocking, sanitization parity proven. Suggested follow-up: add explicit 3-way dedup test via `wb.create_sheet`.
- **SUGGESTION**: Add regression that `generate()` on 2-sheet XLSX returns first sheet only (backward compat). Non-blocking.

---
*Archive performed by sdd-archive sub-agent, auto mode, hybrid store, single PR delivery. No git tag or version bump per AGENTS.md 12 (tag-driven release is manual).*
