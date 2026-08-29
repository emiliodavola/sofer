# Apply Progress: fix-quality-encoding-xlsx

**Change**: fix-quality-encoding-xlsx
**Branch**: fix/quality-encoding-xlsx
**Mode**: Standard (strict_tdd: false)
**Date**: 2026-08-28

## Completed Tasks

- [x] 1.1 Add TEXT_SUFFIXES frozenset to _formats.py
- [x] 1.2 Implement is_text_eligible(Path) -> bool (case-insensitive suffix.lower())
- [x] 1.3 Update _formats.py module docstring for TEXT_SUFFIXES contract (.csv.gz→.gz false, README→"" false)
- [x] 2.1 Import is_text_eligible in quality.py; update module docstring
- [x] 2.2 Add `if not is_text_eligible(resolved): continue` in QualityValidator.run() after exists/is_dir
- [x] 2.3 Guard _check_encoding_validation early-return if not eligible (no result, no ran_checks)
- [x] 2.4 Guard _process_file early-return if not eligible (no accumulators, no ran_checks)
- [x] 2.5 Ensure ran_checks only for eligible files; binary-only yields [] + {} (publish shows 0 failed) via _had_eligible gating in post-scan checks
- [x] 3.1 Test binary skip: .xlsx/.parquet/.jsonl → quality_results == [], ran_checks == {}
- [x] 3.2 Test TSV eligible: .tsv short row → corrupt_records fail
- [x] 3.3 Test case/no-extension: DATA.XLSX/README skipped, Report.CSV/values.TSV checked; .csv.gz skipped
- [x] 3.4 Test binary-only no cross-file: two identical .xlsx → no duplicates/cross_file_types/empty_columns/corrupt_records
- [x] 3.5 Test defensive guards: direct helper calls on non-eligible paths → no result, no ran_checks
- [x] 3.6 Test mixed/ran_checks/encoding: a.csv+b.xlsx+c.tsv filtering, mixed ran_checks, latin-1 fails, UTF-8 passes, .xlsx skipped, mislabeled .csv PK → ValueError
- [x] 3.7 Verify: uv run pytest tests/ -q (923 passed), uv run mypy src/ (success), uv run ruff check/format (pass)
- [x] 4.1 Update docstrings for run(), _check_encoding_validation, _process_file (gated dispatch, UTF-8-only)
- [x] 4.2 Confirm _csv_reader.py unchanged and no new [tool.sofer] key in config.py

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `src/sofer/_formats.py` | Modified | Added TEXT_SUFFIXES frozenset + is_text_eligible(Path)->bool (suffix.lower() in TEXT_SUFFIXES), updated module docstring with .csv.gz→.gz and README→"" contract |
| `src/sofer/quality.py` | Modified | Imported is_text_eligible, updated module docstring, added run() filter after exists/is_dir, added _had_eligible tracking, defensive early-returns in _check_encoding_validation and _process_file, gated all post-scan checks on _had_eligible so binary-only yields empty ran_checks |
| `tests/test_quality.py` | Modified | Added 7 test classes covering binary skip, TSV eligible, case-insensitive/no-extension, binary-only no cross-file, defensive helper guards, mixed/ran_checks/encoding, and is_text_eligible direct checks |
| `openspec/changes/fix-quality-encoding-xlsx/tasks.md` | Modified | Marked all 17 tasks [x] |
| `src/sofer/_csv_reader.py` | Unchanged | Verified ENCODING_FALLBACKS remains ["utf-8-sig","utf-8"] |
| `src/sofer/config.py` | Unchanged | No new [tool.sofer] key added |

## Verification

- `uv run pytest tests/ -q`: 923 passed, 2 skipped
- `uv run pytest tests/test_quality.py -q`: 61 passed
- `uv run mypy src/`: Success, no issues in 26 source files
- `uv run ruff check src/ tests/`: All checks passed
- `uv run ruff format --check`: Pass (after formatting)

## Deviations from Design

None — implementation matches design. TEXT_SUFFIXES lives in _formats.py as single source of truth, is_text_eligible uses path.suffix.lower(), run() filter is primary gate with helper defensive guards, _had_eligible ensures ran_checks empty for binary-only.

## Issues Found

- TSV delimiter: validator uses config CSV_DELIMITER (";") for all files, so TSV test fixtures must use ";" delimiter to be parsed correctly. Adjusted tests to use ";" even for .tsv suffix — gate is suffix-based, not delimiter-based.
- PK bytes validity: b"PK\x03\x04..." are valid UTF-8 (all < 0x80), so mislabeled .csv test needed invalid bytes (\xff\xfe) to trigger ValueError. Fixed by using b"PK\x03\x04\xff\xfe\xfd\xfc".

## Remaining Tasks

None — all 17 tasks complete. Ready for verify.

## Workload / PR Boundary

- Mode: single PR (forecast 30-50 lines, actual 398 lines due to test coverage — still <400 budget? 398 just under)
- Current work unit: Gate all P0 checks to CSV/TSV + fix ran_checks + tests
- Boundary: Phase 1-4 complete, single commit
- Estimated review budget impact: ~398 insertions, low risk, no chained PRs needed

## Status

17/17 tasks complete. Ready for verify.
