# Archive Report: convert-all-formats-parquet

**Change**: convert-all-formats-parquet
**Branch**: sdd/convert-all-formats-parquet
**Archived**: 2026-08-29
**Archived to**: `openspec/changes/archive/2026-08-29-convert-all-formats-parquet/`
**Mode**: hybrid (Engram + openspec)
**Verdict**: PASS WITH WARNINGS — 0 critical, 3 warnings, ready for PR to dev

---

## 1. Intent

Universal `csv/tsv/xlsx/jsonl → normalized .parquet` by default in `prepare`/`publish`; `.parquet` passthrough. Excel → one Parquet per sheet (`stem__{sheet}.parquet` flat `__`, dedup `_{n}`, 0-row header-only). Remotes normalized (lowercase, NFKD accent-strip, spaces→`_`, `[^a-z0-9_./-]`→`_`, collapse `__+`); collisions on `lower(normalized)` error naming both remotes. Opt-out `FileEntry.convert_to_parquet: bool=True` (positive); deprecated `upload_as_csv` alias csv-only with warning; `prepare` gate/`publish` diff+copy delegate to `_mirror.planned_remotes` single source; `repo_compliance` schema via staged Parquet normalized keys.

## 2. Phases

| Phase | Artifact | ID / Path | Status |
|-------|----------|-----------|--------|
| Proposal | `sdd/convert-all-formats-parquet/proposal` + `proposal.md` | #669 `obs-2d612fb83014bc79` | done — 71 lines, intent/scope/A+B+C1 hybrid approach |
| Spec | `sdd/convert-all-formats-parquet/spec` + `specs/{4 domains}/spec.md` | #670 `obs-6f1e04c8a98e13a3` | done — 4 deltas, 10+ scenarios (PC-U01..U05, PRP-02/02a/02b, PUB-01/02/09, RC-Universal/Card) |
| Design | `sdd/convert-all-formats-parquet/design` + `design.md` | #675 `obs-3f37153ec113703c` | done — 112 lines, _converters dispatcher, DAG, flat `__`, TSV `\t`, JSONL fallback |
| Tasks | `sdd/convert-all-formats-parquet/tasks` + `tasks.md` | #676 `obs-4e1f51c65eb79149` | done — 16/16 [x], 9 phases, 400-line budget risk Low, single PR auto/2000 budget |
| Apply-progress | `sdd/convert-all-formats-parquet/apply-progress` + `apply-progress.md` | #677 `obs-ae5ac81d15d01269` | done — single commit 0cbea73, 1159 lines, deviations none |
| Verify-report | `sdd/convert-all-formats-parquet/verify-report` + `verify-report.md` | #678 `obs-84c2ff487c5364c1` | PASS WITH WARNINGS — 923 passed, ruff+mypy green, 0 critical |

**Task Completion Gate**: `tasks.md` 16/16 checked — no stale unchecked tasks. Verified via Engram #676 and file `archive/tasks.md`.

## 3. Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| parquet-conversion | Updated | 5 ADDED (PC-U01..U05) + 1 MODIFIED (universal pipeline) → appended as §13, preserves §§1-12 |
| prepare | Updated | 2 MODIFIED (PRP-02 universal, PRP-02a cross-format) + 1 ADDED (PRP-02b normalization gate) — replaces CSV-only §PRP-02 |
| publish | Updated | 2 MODIFIED (PUB-01 hf delegation, PUB-02 local delegation) + 1 ADDED (PUB-09 invariant) |
| repo-compliance | Updated | 1 MODIFIED (RC-Universal universal staged Parquet) + 1 ADDED (RC-Universal-Card data_files) → §§4.19-4.20 |

**Source of Truth Updated**:
- `openspec/specs/parquet-conversion/spec.md` — §13 universal appended
- `openspec/specs/prepare/spec.md` — PRP-02/02a/02b replaced/added
- `openspec/specs/publish/spec.md` — PUB-01/02/09 replaced/added
- `openspec/specs/repo-compliance/spec.md` — §§4.19-4.20 added

No REMOVED or RENAMED requirements; no destructive delta — preserved all other requirements per archive skill merge contract.

## 4. Archive Contents

- proposal.md ✅ (71 lines)
- specs/parquet-conversion/spec.md ✅ (111 lines delta, 4 requirements)
- specs/prepare/spec.md ✅ (66 lines)
- specs/publish/spec.md ✅ (51 lines)
- specs/repo-compliance/spec.md ✅ (55 lines)
- design.md ✅ (112 lines)
- tasks.md ✅ (16/16 complete)
- apply-progress.md ✅ (923 passed evidence)
- verify-report.md ✅ (PASS WITH WARNINGS, 0 critical)
- exploration.md / explore.md ✅ (20489 bytes, exploratory context)
- archive-report.md ✅ (this file)

**Active changes directory** no longer contains `convert-all-formats-parquet` — moved to `archive/2026-08-29-convert-all-formats-parquet/`.

## 5. File Changes (single work-unit commit 0cbea73)

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/_converters.py` | Created | Dispatcher, 4 converters, `_write_parquet_table` (PARQUET_COMPRESSION/ROW_GROUP_SIZE/shard warn), `normalize_parquet_remote`, `sanitize_sheet_name`, `CONVERTIBLE_SUFFIXES` — 593 lines |
| `src/sofer/model.py` | Modified | `FileEntry.convert_to_parquet=True`, `upload_as_csv` deprecated alias csv-only warn via `__post_init__` + `from_toml` precedence |
| `src/sofer/_mirror.py` | Modified | `planned_remotes` universal normalized, `keep_csv` CSV-only, `_validate_case_fold_collisions` on `lower(normalized)` via `_converters` import (no cycle) |
| `src/sofer/prepare.py` | Modified | Gate to convertible set, normalized `converted` dict, dispatcher, `_check_local_overwrite` normalized + xlsx glob, `_assert_cross_file_schema` universal |
| `src/sofer/publish.py` | Modified | `_repo_diff_summary`/`_copy_package` delegate to `planned_remotes`, multi-sheet glob, keep_csv CSV-only |
| `src/sofer/repo_compliance.py` | Modified | `_build_schema_report_impl` universal set, normalized staged key, multi-sheet origins, generic fallback readers, `build_dataset_card` via `planned_remotes` |
| `src/sofer/cli.py` | Modified | `prepare`/`publish` help texts for universal conversion + keep_csv CSV-only |
| `README.md` / `README_ES.md` | Modified | Table + footnote ¹ sync (AGENTS 13, English literals preserved) |
| `docs/configuration.md` | Modified | Parquet conversion section per-file `convert_to_parquet` docs |
| `tests/test_mirror.py` / `test_prepare.py` / `test_repo_compliance.py` | Modified | Normalized expectations |

15 files, 1310 insertions, 168 deletions. All commits on branch `sdd/convert-all-formats-parquet`: single work-unit `0cbea73 feat(parquet): universal csv/tsv/xlsx/jsonl -> normalized parquet`.

## 6. Test Evidence

```
uv run pytest tests/ -q
923 passed, 2 skipped, 13 warnings in 23.31s

uv run ruff check src/ tests/
All checks passed!

uv run mypy src/
Success: no issues found in 27 source files

uv run ruff format --check src/ tests/
51 files already formatted
```

Subset re-run (`tests/test_mirror`, `test_prepare`, `test_parquet_conversion`, `test_repo_compliance`, `test_publish`) included in full suite. No HF network calls (offline package tests + mocked `_api`). Manual spot-checks verified accented normalization (`DATA GÖT Año.XLSX` → `data_got_ano.parquet`), multi-sheet XLSX (`report.xlsx` 1-sheet vs 2-sheet `Ventas`/`Costos` → `report__ventas`+`report__costos`), dedup, 0-row empty sheet, and `lower(normalized)` collision errors naming both remotes.

## 7. Warnings (non-blocking, per verify-report)

1. **Dead duplicated conversion helpers in `prepare.py`** — `_sniff_csv_delimiter`, `_cast_null_columns_to_string`, `_read_csv_raw_values`, `_check_conversion_parity`, `_convert_to_parquet` remain (lines ~83-327) though active path uses `_converters`. Bypass `config.CSV_ENCODING` (hardcoded `utf-8-sig`) and differ on sniff; violates AGENTS §4 DRY but not on new path. Follow-up dupe cleanup suggested (delete dead code, import from `_converters` if needed).
2. **Per-format unit test coverage thin** — no `tests/test_converters.py` for isolated TSV (`\t`), XLSX multi-sheet/dedup/empty, JSONL fallback; coverage via integration + manual spot-check. Spec scenarios pass functionally but parametrized unit tests preferred.
3. **Spec example vs impl hyphen** — spec scenario `A B`/`A-B` → `a_b`+`a_b_2` assumes hyphen collapsed, but design preserves `-` (`[^a-z0-9_./-]`), so `A-B` → `a-b` (actual `report__a_b` + `report__a-b` correct per design). Wording loose, not a code bug.

No CRITICAL issues — archive not blocked; warnings recorded as intentional-with-warnings per strict-vs-OpenSpec policy.

## 8. Breaking Change Note

Per AGENTS §12 and PC-U05: 0.x minor bump breaking change. Previously `tsv/xlsx/jsonl` staged as-is; now normalized `.parquet` (xlsx → N files). `report.xlsx` → `report.parquet` (or N `stem__sheet.parquet`). Migration: per-entry `convert_to_parquet=false` keeps original suffix (e.g. `remote="report.xlsx" convert_to_parquet=false`). Conversion failure warns and stages original; `keep_csv` remains CSV-only so `b.xlsx` not kept with `--keep-csv`. New collisions from accent/space normalization name both remotes.

## 9. Next Steps (follow-up)

- **Chore: dedup `prepare.py`** — delete dead `_sniff`/`_cast`/`_convert_to_parquet` duplicates; import from `_converters` if needed; satisfies AGENTS §4, prevents drift. Non-blocking, post-merge.
- **Test: add `tests/test_converters.py` parametrized** — `normalize_parquet_remote("DATA GÖT Año.XLSX")→data_got_ano.parquet`, `sanitize_sheet_name` dedup, XLSX 0-row, TSV `"\t"`, JSONL sparse fallback, shard-warn threshold.
- **Docs: align spec hyphen wording** — note `-` preserved in normalization; `A-B` → `a-b`.
- **Large XLSX cap deferred** — `read_only,data_only` mitigates; streaming cap if >100k-row workbooks proven.

## 10. SDD Cycle Complete

The change has been fully planned, implemented, verified (PASS WITH WARNINGS), and archived. Main specs now reflect universal parquet conversion behavior. Branch retains single work-unit commit 0cbea73 and is ready for PR to `dev`.

**Traceability**: All Engram IDs recorded; filesystem archive `openspec/changes/archive/2026-08-29-convert-all-formats-parquet/` is audit trail — never delete or modify archived changes.

---

*Generated by sdd-archive sub-agent (muse-spark-1.2-contributor) — hybrid persistence, Task Completion Gate passed, CRITICAL=0.*
