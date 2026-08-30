# Tasks: fix-multisheet-parquet-publish

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 320–380 (additions+deletions) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR (one work unit chain not needed vs 2000 budget) |
| Delivery strategy | auto-forecast |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Mirror helper + publish wiring + card expansion | PR 1 → fix/multisheet-parquet-publish → dev | Base branch dev; includes tests/docs; autonomous + rollback via revert |
| 2 | (reserve) split if review asks — test-only slice | PR 2 → PR 1 | Not needed at Low risk; only if diff exceeds 400 |

## Phase 1: Foundation — Mirror Helper

- [x] 1.1 Add `expanded_planned_remotes(cfg, keep_csv, staging_dir)` in `src/sofer/_mirror.py`: gate eligible `.xlsx` via `_is_convertible_entry` + `convert_to_parquet`, glob `staging_dir/<dir>/<stem>__*.parquet` sorted, emit normalized remotes, fallback to `planned_remotes` when `None`/not dir/empty; reuse `normalize_parquet_remote`/`sanitize_sheet_name` rationale, no workbook I/O
- [x] 1.2 Document `planned_remotes` as logical placeholder in `src/sofer/_mirror.py` docstring; add `Path` import handling for `staging_dir`

## Phase 2: Core Implementation — Publish + Card

- [x] 2.1 Update `src/sofer/publish.py:_repo_diff_summary(cfg, existing, keep_csv, codebook_remotes, staging_dir)` to derive `planned` via `expanded_planned_remotes` when `resolve_output_dir(cfg, output_dir).exists()`, mark recursive `*`, share set with protection/splits
- [x] 2.2 Expand `src/sofer/publish.py:_check_overwrite_protection` to accept expanded `planned_files` per-sheet (skip `_is_auto_generated`), wire caller to pass expanded list; expand dry-run and hf paths identically
- [x] 2.3 Refactor `src/sofer/publish.py:_copy_package` to iterate expanded remotes via `copy_to_mirror`, drop inline `__*.parquet` glob duplication; preserve `keep_csv` CSV-only and recursive `copytree` path
- [x] 2.4 Wire `src/sofer/publish.py` dry-run/split paths: `_print_split_mapping_validation` and `detect_splits` consume expanded count N; keep invariants (`recursive` passthrough, collision via `_validate_case_fold_collisions`)
- [x] 2.5 Update `src/sofer/repo_compliance.py:build_dataset_card(..., keep_csv=False, staging_dir=None)` to use `expanded_planned_remotes` for `configs.data_files` + `Dataset Structure` when `staging_dir.is_dir()`, else fallback; keep `row_counts` keyed by verbatim `entry.remote`, no local path leak

## Phase 3: Testing / Verification

- [x] 3.1 Unit `tests/test_mirror.py`: multi-sheet expands to N `__` remotes via `tmp_path` touches, single-sheet stays single, fallback when `staging_dir=None`/not dir, recursive/`keep_csv` invariants, assert no `openpyxl` import
- [x] 3.2 Unit `tests/test_repo_compliance.py`: card with 2-sheet staging shows N in `configs.data_files` and `Dataset Structure`, fallback without staging shows single `report.parquet`, `configs==Structure`, no local path
- [x] 3.3 Integration `tests/test_publish.py`: 2-sheet mock staging (`report__ventas.parquet`, `report__costos.parquet`), `HfApi` mocked, assert diff lists 2, per-sheet protection guards only `ventas` without `--force`, `_copy_package` stages N, `detect_splits` count 2, dry-run lists N
- [x] 3.4 Regression `tests/test_publish.py` + `tests/test_mirror.py`: single `single.parquet` staging shows no phantom `__`, `uv run pytest tests/test_mirror.py tests/test_publish.py tests/test_repo_compliance.py -q` green

## Phase 4: Cleanup / Documentation

- [x] 4.1 Update module docstrings in `src/sofer/_mirror.py` and `src/sofer/publish.py` (`_cmd_*` flow), run `uv run ruff check src/ tests/ && uv run mypy src/`
- [x] 4.2 Verify no hardcoded delimiters/encodings in new code (use `cfg.csv_delimiter`/`cfg.csv_encoding` via `DatasetConfig`), no duplicated `_parquet_to_hf_dtype` logic
