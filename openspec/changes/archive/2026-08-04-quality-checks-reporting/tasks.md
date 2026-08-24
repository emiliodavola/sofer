# Tasks: Fix Quality Checks Reporting Bugs

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~60 (12 production + 48 tests) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

## Phase 1: Core Fixes (production code)

- [x] 1.1 Copy `ran_checks` in `cli.py:_cmd_validate` — add `report.ran_checks = quality_report.ran_checks` after line 61
- [x] 1.2 Copy `ran_checks` in `cli.py:_cmd_upload` — same line after line 95
- [x] 1.3 Scope `_dup_hashes` per file in `quality.py:_distribute_row` — change hash key from `row_str` to `f"{fname}|{row_str}"` at line 308
- [x] 1.4 Guard `_check_empty_columns` against zero-row files — iterate `_file_row_count` keys, skip when count == 0
- [x] 1.5 Guard `_check_cross_file_types` against zero-row files — iterate `_file_row_count` keys, skip when count == 0

## Phase 2: Regression Tests

- [x] 2.1 Add `test_ran_checks_propagates_to_report` — validates `_count_passed_quality(report.quality_results, report.ran_checks)` returns `(>0, _)` after a quality run
- [x] 2.2 Add `test_duplicates_file_scoped` — two files with identical row content at same position produce NO duplicate warning
- [x] 2.3 Add `test_empty_columns_skips_zero_row_file` — header-only CSV (0 data rows) produces no "empty_columns" finding
- [x] 2.4 Add `test_cross_file_types_skips_zero_row_file` — one data file + one header-only file with shared column name produces no type mismatch
- [x] 2.5 Add `test_cli_validate_reports_passed_gt_zero` — integration test capturing stdout from `_cmd_validate`, asserts "passed" > 0

## Phase 3: Verify

- [x] 3.1 Run `uv run pytest tests/ -q` — confirmed 457 tests pass (453 baseline + 4 new)
- [x] 3.2 Run `uv run ruff check src/ tests/ && uv run mypy src/` — confirmed lint and type check pass
