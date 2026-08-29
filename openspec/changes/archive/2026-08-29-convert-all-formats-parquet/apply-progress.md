# Apply Progress: convert-all-formats-parquet

**Change**: convert-all-formats-parquet
**Mode**: Standard (strict_tdd: false)
**Date**: 2026-08-29
**Branch**: sdd/convert-all-formats-parquet

## Completed Tasks

- [x] 1.1 `src/sofer/_converters.py`: `CONVERTIBLE_SUFFIXES`, `normalize_parquet_remote`, `sanitize_sheet_name`
- [x] 1.2 `_write_parquet_table`: `PARQUET_COMPRESSION`/`ROW_GROUP_SIZE`, null→string, shard warn `PARQUET_SHARD_WARNING_MB`
- [x] 2.1 CSV sniff (`SNIFF_DELIMITERS`/`CSV_ENCODING`) + TSV `\t`
- [x] 2.2 XLSX (`read_only,data_only`, all sheets→`pa.Table`, dedup `_{n}`, 0-row) + JSONL (pyarrow.json+fallback)
- [x] 2.3 `convert_file_to_parquet -> dict[normalized_remote,Path]`, passthrough+recursive skip, tmp idx, failure→warn
- [x] 3.1 `src/sofer/model.py`: `convert_to_parquet=True`, `upload_as_csv` alias csv-only warn, precedence
- [x] 4.1 `src/sofer/_mirror.py` `planned_remotes` universal normalized, xlsx N, `keep_csv` CSV-only
- [x] 4.2 `_validate_case_fold_collisions` on `lower(normalized)`, import from `_converters` no cycle
- [x] 5.1 `src/sofer/prepare.py` gate→convertible set, `converted` keyed normalized, dispatcher, tmp idx
- [x] 5.2 Guards/parity: `_check_local_overwrite`+`_validate_case_fold_collisions` normalized, `_assert_cross_file_schema`+`_check_large_values` per-format
- [x] 6.1 `src/sofer/publish.py` `_repo_diff_summary`/`_copy_package` delegate to `planned_remotes`, CSV-only `keep_csv`
- [x] 7.1 `src/sofer/repo_compliance.py` `_build_schema_report_impl` convertible set, normalized staged key, multi-sheet origins, warn+fallback
- [x] 7.2 `build_dataset_card` `configs.data_files` via `planned_remotes`
- [x] 8.1 `README.md`/`README_ES.md` table+footnote, `docs/configuration.md`, `cli.py` help
- [x] 9.1 `tests/test_prepare.py`+`test_parquet_conversion.py` universal expectations, opt-out+passthrough
- [x] 9.2 `tests/test_mirror.py`+`test_repo_compliance.py`+`test_publish.py` normalized+N

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `src/sofer/_converters.py` | Created | Dispatcher, 4 converters, `_write_parquet_table`, `normalize_parquet_remote`, `sanitize_sheet_name`, parity, `CONVERTIBLE_SUFFIXES` |
| `src/sofer/model.py` | Modified | `convert_to_parquet=True` + `upload_as_csv` alias csv-only warn via `__post_init__` + `from_toml` precedence |
| `src/sofer/_mirror.py` | Modified | `planned_remotes` universal normalized, `keep_csv` CSV-only, `_validate_case_fold_collisions` on `lower(normalized)` via `_converters` import |
| `src/sofer/prepare.py` | Modified | Gate to convertible set, normalized `converted` dict, dispatcher, `_check_local_overwrite` normalized + xlsx glob, `_assert_cross_file_schema` universal |
| `src/sofer/publish.py` | Modified | `_repo_diff_summary`/`_copy_package` delegate to `planned_remotes`, multi-sheet glob, keep_csv CSV-only |
| `src/sofer/repo_compliance.py` | Modified | `_build_schema_report_impl` universal set, normalized staged key, multi-sheet origins, generic fallback readers |
| `README.md` | Modified | Table + footnote 1 sync (convert_to_parquet docs) |
| `README_ES.md` | Modified | Table + footnote 1 sync (translated prose, English literals) |
| `docs/configuration.md` | Modified | Parquet conversion section per-file docs |
| `src/sofer/cli.py` | Modified | `prepare`/`publish` help texts for universal conversion + keep_csv CSV-only |
| `tests/test_mirror.py` | Modified | Normalized expectation `data/prov/train.parquet` |
| `tests/test_prepare.py` | Modified | Normalized origin/path for `data/PROV/train.csv` |
| `tests/test_repo_compliance.py` | Modified | Normalized warnings `data/a/train.parquet` |

## Verification

```
uv run pytest tests/ -q
923 passed, 2 skipped, 13 warnings in 22.42s

uv run ruff check src/ tests/
All checks passed!

uv run mypy src/
Success: no issues found in 27 source files

uv run ruff format --check src/ tests/
1 file reformatted (now passes)
```

## Deviations from Design

None — implementation matches design. XLSX N-expansion in `planned_remotes` is single placeholder + glob in `_copy_package`/`prepare` (no workbook open at planning time, per design open question on large XLSX cap deferred).

## Issues Found

- `test_prepare` cross-file schema tests used legacy `converted` keys without `.parquet` suffix — made `_assert_cross_file_schema` tolerant to both legacy and normalized keys.
- `FileEntry` direct construction with `upload_as_csv=True` bypassed TOML precedence — added `__post_init__` csv-only alias for consistency.

## Remaining Tasks

None — all 16 tasks complete. Ready for verify.

## Workload / PR Boundary

- Mode: single PR (auto, within 2000 budget)
- Current work unit: 1-3 combined (600-800 est → 1159 actual, within 2000 budget)
- Boundary: phases 1→9 inclusive, one commit on `sdd/convert-all-formats-parquet`
- Estimated review budget impact: ~1150 lines, single PR

## Status

16/16 tasks complete. Ready for verify.
