# Archive Report — publish-readme-bugs

**Change**: publish-readme-bugs
**Branch**: fix/publish-readme-bugs
**Archived to**: `openspec/changes/archive/2026-08-17-publish-readme-bugs/`
**Archive date**: 2026-08-24
**Verdict**: ✅ ARCHIVED — **PASS WITH WARNINGS** (1 non-blocking warning)

## Verification Source

Engram observation #530 — topic `sdd/publish-readme-bugs/verify-report`
(session `ses_02b9608abffeINTbn7WVnIv15P`).

### SDD artifact traceability (Engram observation IDs)

| Artifact | Topic key | Observation ID |
|----------|-----------|----------------|
| proposal | `sdd/publish-readme-bugs/proposal` | #521 |
| spec | `sdd/publish-readme-bugs/spec` | #522 |
| tasks | `sdd/publish-readme-bugs/tasks` | #525 |
| apply-progress | `sdd/publish-readme-bugs/apply-progress` | #526 |
| verify-report | `sdd/publish-readme-bugs/verify-report` | #530 |
| archive-report | `sdd/publish-readme-bugs/archive-report` | this save |

## Task Completion Gate

`tasks.md`: 24/24 tasks checked (WU1–WU4 + verification phase). No stale
unchecked implementation tasks. Gate PASSED — specs sync and archive move
proceeded normally.

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| repo-compliance | Updated | 6 ADDED ID-tagged requirements (§ 4.6–4.11): RC-R05 column origin attribution, RC-R06 Data Fields File column, RC-R07 real num_examples, RC-R08 delivered repo-relative paths, RC-R09 config-driven schema_sample_size, RC-R10 sentinel-free unique counts. Per repo convention for this numbered-section spec; each requirement carries a "(Previously: …)" note stating what it replaces. Cross-references added where older sections (§ 3.3.3 prefixes, `_SCHEMA_SAMPLE_SIZE`) are superseded. |
| publish | Updated | PUB-03 MODIFIED (full block): auto-prepare now runs with all-files behavior enabled (`prepare --all-files`), new scenario "Auto-prepare generates codebooks". PUB-08 ADDED: codebook-absence warning before hf delivery (warn-and-deliver, never blocks). |
| codebook | Updated | CB-R07 ADDED (unique counts exclude missing sentinels, all formats) and CB-R08 ADDED (--max-sample default from `[tool.sofer] codebook_max_sample` via config.py, no CLI literal). Base spec had no prior named requirements covering these — recorded as ADDED per delta note. |
| profile | Updated | PRF-02 MODIFIED (full block): coarse-schema `unique` statistic counts distinct non-missing values only; new scenario "Sentinels excluded from unique counts". |

No REMOVED or RENAMED requirements. All merges non-destructive; requirements
not mentioned in the deltas were preserved verbatim.

## Work Unit Summary (4 WUs)

1. **WU1 — config + shared unique helper (foundation)** (860de05):
   `count_unique_non_missing()` added to `_sentinels.py`; `schema_sample_size`
   default 10_000 in config.py; inline unique logic replaced across
   repo_compliance/codebook/profile; `--max-sample` reads CODEBOOK_MAX_SAMPLE.
2. **WU2 — column origin + num_examples** (010a08e): `ColumnSchema.origin`,
   `build_schema_report_with_rows`, exact row counts via Parquet metadata /
   CSV len(rows); num_examples = sum of row_counts.
3. **WU3 — delivered paths in Data Structure** (fc3b8d3): card renders Data
   Structure from `planned_remotes(cfg, keep_csv)`; dead `"::"` guards removed.
4. **WU4 — publish auto-prepare + PUB-08** (b5e9933): auto-prepare uses
   `all_files=True`; codebook-absence warning printed before staging, delivery
   proceeds with rc==0.

## Verification Evidence (from verify-report #530)

- `uv run pytest tests/ -q` → **720 passed** (688 baseline + 32 new), zero regressions
- `ruff check`, `ruff format --check`, `mypy src/` → all clean
- Spec-compliance matrix: RC-R05..R10, PUB-03, PUB-08, CB-R07/R08, PRF-02 — all COMPLIANT
- Live CLI smoke: prepare/codebook/profile functional; `sofer --help` surface unchanged

## Warnings (non-blocking)

1. **WARNING — TDD evidence format**: apply-progress lacks a formal RED/GREEN
   Cycle Evidence table. Substantively compensated (per-task RED steps in
   tasks.md, all 32 tests exist and pass at runtime, work-unit ordered
   commits) → downgraded from CRITICAL; does not block archive per policy.
2. **SUGGESTION (follow-up candidate)**: design D7 documents basename-keyed
   row_counts same-name collision as known MVP limitation — consider a
   follow-up change if multi-dir same-basename datasets appear.
3. **Accepted spec deviation (recorded)**: recursive Data Structure entries
   render the staged tree ROOT path rather than per-file paths ("Labels/a.csv"
   wording) — design D3 supersedes; covered by
   `test_recursive_lists_staged_tree_prefix`. Noted inside RC-R08's recursive
   scenario in the synced base spec.

## Archive Contents

- proposal.md ✅
- exploration.md ✅
- specs/ ✅ (repo-compliance, publish, codebook, profile)
- design.md ✅
- tasks.md ✅ (24/24 complete)

## Source of Truth Updated

- `openspec/specs/repo-compliance/spec.md`
- `openspec/specs/publish/spec.md`
- `openspec/specs/codebook/spec.md`
- `openspec/specs/profile/spec.md`

## SDD Cycle Complete

The change has been fully planned, implemented, verified, and archived.
Ready for the next change.
