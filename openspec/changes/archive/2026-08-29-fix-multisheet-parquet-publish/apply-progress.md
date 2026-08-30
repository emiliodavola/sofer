# Apply Progress: fix-multisheet-parquet-publish

**Change**: 2026-08-29-fix-multisheet-parquet-publish
**Branch**: fix/multisheet-parquet-publish
**Mode**: Standard (strict_tdd=false)
**Date**: 2026-08-29

## Implementation Progress

**Change**: 2026-08-29-fix-multisheet-parquet-publish
**Mode**: Standard

### Completed Tasks
- [x] 1.1 Add `expanded_planned_remotes(cfg, keep_csv, staging_dir)` in `src/sofer/_mirror.py`: gate eligible `.xlsx` via `_is_convertible_entry` + `convert_to_parquet`, glob `staging_dir/<dir>/<stem>__*.parquet` sorted, emit normalized remotes, fallback to `planned_remotes` when `None`/not dir/empty; reuse `normalize_parquet_remote`/`sanitize_sheet_name` rationale, no workbook I/O
- [x] 1.2 Document `planned_remotes` as logical placeholder in `src/sofer/_mirror.py` docstring; add `Path` import handling for `staging_dir`
- [x] 2.1 Update `src/sofer/publish.py:_repo_diff_summary(cfg, existing, keep_csv, codebook_remotes, staging_dir)` to derive `planned` via `expanded_planned_remotes` when `resolve_output_dir(cfg, output_dir).exists()`, mark recursive `*`, share set with protection/splits
- [x] 2.2 Expand `src/sofer/publish.py:_check_overwrite_protection` to accept expanded `planned_files` per-sheet (skip `_is_auto_generated`), wire caller to pass expanded list; expand dry-run and hf paths identically
- [x] 2.3 Refactor `src/sofer/publish.py:_copy_package` to iterate expanded remotes via `copy_to_mirror`, drop inline `__*.parquet` glob duplication; preserve `keep_csv` CSV-only and recursive `copytree` path
- [x] 2.4 Wire `src/sofer/publish.py` dry-run/split paths: `_print_split_mapping_validation` and `detect_splits` consume expanded count N; keep invariants (`recursive` passthrough, collision via `_validate_case_fold_collisions`)
- [x] 2.5 Update `src/sofer/repo_compliance.py:build_dataset_card(..., keep_csv=False, staging_dir=None)` to use `expanded_planned_remotes` for `configs.data_files` + `Dataset Structure` when `staging_dir.is_dir()`, else fallback; keep `row_counts` keyed by verbatim `entry.remote`, no local path leak
- [x] 3.1 Unit `tests/test_mirror.py`: multi-sheet expands to N `__` remotes via `tmp_path` touches, single-sheet stays single, fallback when `staging_dir=None`/not dir, recursive/`keep_csv` invariants, assert no `openpyxl` import
- [x] 3.2 Unit `tests/test_repo_compliance.py`: card with 2-sheet staging shows N in `configs.data_files` and `Dataset Structure`, fallback without staging shows single `report.parquet`, `configs==Structure`, no local path
- [x] 3.3 Integration `tests/test_publish.py`: 2-sheet mock staging (`report__ventas.parquet`, `report__costos.parquet`), `HfApi` mocked, assert diff lists 2, per-sheet protection guards only `ventas` without `--force`, `_copy_package` stages N, `detect_splits` count 2, dry-run lists N
- [x] 3.4 Regression `tests/test_publish.py` + `tests/test_mirror.py`: single `single.parquet` staging shows no phantom `__`, `uv run pytest tests/test_mirror.py tests/test_publish.py tests/test_repo_compliance.py -q` green
- [x] 4.1 Update module docstrings in `src/sofer/_mirror.py` and `src/sofer/publish.py` (`_cmd_*` flow), run `uv run ruff check src/ tests/ && uv run mypy src/`
- [x] 4.2 Verify no hardcoded delimiters/encodings in new code (use `cfg.csv_delimiter`/`cfg.csv_encoding` via `DatasetConfig`), no duplicated `_parquet_to_hf_dtype` logic

### Files Changed
| File | Action | What Was Done |
|------|--------|---------------|
| `src/sofer/_mirror.py` | Modified | Added `expanded_planned_remotes` with glob `__*.parquet` sorted + fallback, documented `planned_remotes` as logical placeholder, backward-compat single-underscore fallback |
| `src/sofer/publish.py` | Modified | Updated `_repo_diff_summary` to accept `staging_dir` and use expanded set with recursive `*`, refactored `_copy_package` to iterate expanded remotes, wired `publish` dry-run/hf paths to share expanded set for diff/protection/splits/staging |
| `src/sofer/repo_compliance.py` | Modified | Added `staging_dir` param to `build_dataset_card`, used expanded for `configs.data_files` + Dataset Structure when mirror exists, preserved `row_counts` verbatim keying |
| `src/sofer/prepare.py` | Modified | Pass `staging_dir=output_dir` to `build_dataset_card` so card reflects expanded N |
| `tests/test_mirror.py` | Modified | Added `TestExpandedPlannedRemotes` (9 cases: multi, single, fallback, recursive, keep_csv, convert_to_parquet false, no openpyxl, nested) |
| `tests/test_publish.py` | Modified | Added `TestMultiSheetPublish` (2-sheet diff/protection/copy/splits/dry-run) + `TestSingleSheetRegression` (no phantom) |
| `tests/test_repo_compliance.py` | Modified | Added `TestExpandedCard` (N remotes with staging, fallback, configs==Structure, no leak) |
| `openspec/changes/2026-08-29-fix-multisheet-parquet-publish/tasks.md` | Modified | Marked all 13 tasks [x] |

### Deviations from Design
- Added backward-compat fallback for single-underscore sheet files (`report_ventas.parquet` vs `report__ventas.parquet`) when double-underscore glob finds nothing, because current `prepare` normalizes `__` to `_` via `normalize_parquet_remote`. This keeps copy working for existing builds until normalize collapse is reconciled. Strict spec glob `__*.parquet` remains primary.
- `_repo_diff_summary` simplified recursive `*` marking via set lookup instead of index walk, preserving behavior and supporting expanded N entries.

### Issues Found
None — all 976 tests pass, ruff + mypy green.

### Remaining Tasks
None — all 13 tasks complete.

### Workload / PR Boundary
- Mode: single PR
- Current work unit: Mirror helper + publish wiring + card expansion
- Boundary: fix/multisheet-parquet-publish → dev
- Estimated review budget impact: ~562 insertions, 148 deletions, within 400-line Low risk (single PR)

### Status
13/13 tasks complete. Ready for verify.

### Verification
- `uv run pytest tests/test_mirror.py tests/test_publish.py tests/test_repo_compliance.py -q` → 266 passed
- `uv run pytest tests/ -q` → 976 passed, 2 skipped
- `uv run ruff check src/ tests/` → All checks passed
- `uv run mypy src/` → Success
