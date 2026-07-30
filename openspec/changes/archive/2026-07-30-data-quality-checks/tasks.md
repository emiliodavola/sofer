# Tasks: Data Quality Checks

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~600 |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | auto-forecast |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: single-pr
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Foundation: `_csv_reader.py` + model dataclasses + `from_toml()` | PR 1 | Base for everything below |
| 2 | Core: `quality.py` with all 9 checks | PR 1 | Depends on Unit 1 |
| 3 | Wiring: `cli.py` + `checks.py` print_summary | PR 1 | Depends on Unit 2 |
| 4 | Tests: `test_quality.py` TDD | PR 1 | Depends on Unit 2 |

## Phase 1 — Foundation: _csv_reader.py + model dataclasses

- [x] 1.1 Create `src/data_uploader/_csv_reader.py` with `stream_csv()` generator — encoding fallback chain utf-8-sig→utf-8→latin-1→cp1252, `max_sample` cap, empty-file handling
- [x] 1.2 Add `QualityCheck`, `QualityConfig`, `QualityResult` dataclasses to `src/data_uploader/model.py`
- [x] 1.3 Add `quality: QualityConfig` field to `DatasetConfig` (default: empty checks) and parse `[[quality]]` TOML section in `from_toml()`, warn on unknown check names

## Phase 2 — Core: quality.py with all 9 P0 checks

- [x] 2.1 Create `src/data_uploader/quality.py` with `QualityValidator.__init__()` — merge `QualityConfig.checks` with built-in defaults table
- [x] 2.2 Implement `run()` — single-pass interleaving: open each CSV file once via `stream_csv()`, distribute rows to all active check accumulators
- [x] 2.3 Implement `_check_duplicates()` — set-of-row-hashes, report duplicate row numbers
- [x] 2.4 Implement `_check_empty_rows()` — detect rows with all fields empty/NA/NULL
- [x] 2.5 Implement `_check_empty_columns()` — detect columns with zero populated values
- [x] 2.6 Implement `_check_null_profiling()` — per-column null% vs `max_null_pct` threshold
- [x] 2.7 Implement `_check_format_consistency()` — reuse `codebook.infer_column_type`, detect mixed numeric/text columns, respect `ignore_values`
- [x] 2.8 Implement `_check_corrupt_records()` — `len(row) != len(header)` per row, severity `fail`
- [x] 2.9 Implement `_check_value_range()` — streaming min/max per configured column, compare against `min`/`max` bounds
- [x] 2.10 Implement `_check_cross_file_types()` — collect per-file type map, compare after all files scanned
- [x] 2.11 Implement `_check_encoding_validation()` — read first 8 KB, try fallback chain, fail if all fail

## Phase 3 — Wiring: cli.py + checks.py integration

- [x] 3.1 Add `quality_results: list[QualityResult]` field to `ValidationReport` in `checks.py`
- [x] 3.2 Update `print_summary()` in `checks.py` — add `─── Quality checks ───` section when `quality_results` is non-empty
- [x] 3.3 Wire `QualityValidator` into `_cmd_validate` — call `quality.run()`, merge `quality_results`, exit 1 on fail
- [x] 3.4 Wire `QualityValidator` into `_cmd_upload` — same merge pattern, block upload on fail-severity quality results
- [x] 3.5 Update `_INIT_TEMPLATE` in `cli.py` with commented `[[quality]]` example sections

## Phase 4 — Tests: test_quality.py (TDD: test-first)

- [x] 4.1 Test `stream_csv()` — normal CSV, encoding fallback, unrecoverable encoding, sample cap, empty file
- [x] 4.2 Test `_check_duplicates` — no duplicates, exact duplicates present
- [x] 4.3 Test `_check_empty_rows` — all populated, row with all-empty fields
- [x] 4.4 Test `_check_empty_columns` — all populated, fully empty column
- [x] 4.5 Test `_check_null_profiling` — below threshold, above threshold
- [x] 4.6 Test `_check_format_consistency` — uniform type, mixed numeric/text
- [x] 4.7 Test `_check_corrupt_records` — uniform lengths, short row (fail severity)
- [x] 4.8 Test `_check_value_range` — values in range, out-of-range value, no range configured (skipped)
- [x] 4.9 Test `_check_cross_file_types` — compatible types, type mismatch
- [x] 4.10 Test `_check_encoding_validation` — valid UTF-8, fallback success, unrecoverable
- [x] 4.11 Test `from_toml()` parsing — full `[[quality]]` section, absent section, unknown check name
- [x] 4.12 Test `print_summary()` quality section via `capsys`

## Phase 5 — Verification

- [x] 5.1 Run `uv run pytest tests/test_quality.py -v` — all tests pass
- [x] 5.2 Run `uv run ruff check src/data_uploader/ tests/` — no lint errors
- [x] 5.3 Run `uv run pytest tests/` — existing test suite still passes
