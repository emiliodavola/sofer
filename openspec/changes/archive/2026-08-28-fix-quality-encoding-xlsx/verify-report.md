```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:e03a2568539c6272cc54d3fa2ca02fa6d234080d840b1074aadbf23ba228a659
verdict: pass
blockers: 0
critical_findings: 0
requirements: 4/4
scenarios: 12/12
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:f19ddb4e62607bc5f77b15eb0c032fe87f2e2189f5ae764d8d3ea3dd04cef682
build_command: uv run ruff check src/ tests/ && uv run mypy src/
build_exit_code: 0
build_output_hash: sha256:a8ed24344a59964d451a9aa1e7b0115537acc8213a5c4600777a0d5468391583
```

## Verification Report

**Change**: fix-quality-encoding-xlsx
**Version**: N/A (delta spec for data-quality)
**Mode**: Standard (strict_tdd: false)

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 17 |
| Tasks complete | 17 |
| Tasks incomplete | 0 |

All 17 tasks across Phase 1 (Foundation — Format Registry, 3 tasks), Phase 2 (Core Implementation — Gated Dispatch, 5 tasks), Phase 3 (Testing/Verification, 7 tasks), Phase 4 (Documentation/Polish, 2 tasks) are marked `[x]` in `tasks.md` and confirmed in `apply-progress.md`. No unchecked implementation task remains.

### Build & Tests Execution

**Build**: ✅ Passed

```text
$ uv run ruff check src/ tests/
All checks passed!

$ uv run mypy src/
Success: no issues found in 26 source files

$ uv run ruff format --check
62 files already formatted
```

Build command as configured in `openspec/config.yaml verify.build_command`: `uv run ruff check src/ tests/ && uv run mypy src/` — exit code 0. Ruff format also clean (62 files formatted).

**Tests**: ✅ 923 passed, 2 skipped, 0 failed

```text
$ uv run pytest tests/ -q
........................................................................ [  7%]
........................................................................ [ 15%]
............................................s.........................s. [ 23%]
........................................................................ [ 31%]
........................................................................ [ 38%]
........................................................................ [ 46%]
........................................................................ [ 54%]
........................................................................ [ 62%]
........................................................................ [ 70%]
........................................................................ [ 77%]
........................................................................ [ 85%]
........................................................................ [ 93%]
.............................................................            [100%]
923 passed, 2 skipped, 13 warnings in 14.00s

$ uv run pytest tests/test_quality.py -q
61 passed in 0.34s
```

The 13 warnings are pre-existing `DeprecationWarning` for `_infer_type` in `test_codebook.py` (unrelated to this change). 61 quality tests (34 original + 27 new for this change) all pass.

**Coverage**: ➖ Not available — no coverage tool configured (`openspec/config.yaml coverage.available: false`). No threshold to meet.

### Spec Compliance Matrix

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Text-eligible scope for all P0 checks | Binary formats skipped (.xlsx/.parquet/.jsonl -> empty results + empty ran_checks) | `tests/test_quality.py > TestBinaryFormatsSkipped::test_run_with_xlsx_parquet_jsonl_yields_empty` | ✅ COMPLIANT |
| Text-eligible scope for all P0 checks | TSV is eligible (short row -> corrupt_records fail) | `tests/test_quality.py > TestTsvEligible::test_tsv_short_row_produces_corrupt_records_fail` | ✅ COMPLIANT |
| Text-eligible scope for all P0 checks | Case-insensitive and no-extension skipped (DATA.XLSX/README skipped; Report.CSV/values.TSV checked) | `tests/test_quality.py > TestCaseInsensitiveAndNoExtension::test_uppercase_xlsx_and_readme_skipped` | ✅ COMPLIANT |
| Text-eligible scope for all P0 checks | .csv.gz -> .gz skipped (suffix .gz not eligible) | `tests/test_quality.py > TestCaseInsensitiveAndNoExtension::test_csv_gz_suffix_skipped` | ✅ COMPLIANT |
| Text-eligible scope for all P0 checks | Binary-only dataset — no cross-file findings (two identical .xlsx -> no duplicates/cross_file_types/empty_columns/corrupt_records) | `tests/test_quality.py > TestBinaryOnlyNoCrossFile::test_two_identical_xlsx_no_cross_file_findings` | ✅ COMPLIANT |
| UTF-8-only enforcement | latin-1 csv fails (José in latin-1 -> fail) | `tests/test_quality.py > TestCheckEncodingValidation::test_fallback_latin1` + `TestMixedAndRanChecksAndEncoding::test_latin1_csv_fails_utf8_passes_xlsx_skipped` | ✅ COMPLIANT |
| QualityValidator.run() — eligibility-gated dispatch | run() filters before accumulators (a.csv + b.xlsx + c.tsv -> only a/c reach probe/stream) | `tests/test_quality.py > TestMixedAndRanChecksAndEncoding::test_run_filters_before_accumulators` | ✅ COMPLIANT |
| QualityValidator.run() — eligibility-gated dispatch | Defensive helper guard (direct call on data.xlsx/data.parquet -> no result, no ran_checks) | `tests/test_quality.py > TestDefensiveHelperGuards::test_check_encoding_validation_guard` + `test_process_file_guard` | ✅ COMPLIANT |
| QualityValidator.run() — eligibility-gated dispatch | ran_checks empty for binary-only dataset (publish not blocked) | `tests/test_quality.py > TestMixedAndRanChecksAndEncoding::test_binary_only_ran_checks_empty` | ✅ COMPLIANT |
| QualityValidator.run() — eligibility-gated dispatch | Mixed dataset ran_checks (data.csv + extra.xlsx -> ran_checks same as data.csv alone) | `tests/test_quality.py > TestMixedAndRanChecksAndEncoding::test_mixed_ran_checks_reflects_only_eligible` | ✅ COMPLIANT |
| Encoding validation — detect non-UTF-8 | Valid UTF-8 csv/tsv pass (no error appended) | `tests/test_quality.py > TestCheckEncodingValidation::test_valid_utf8` + `TestMixedAndRanChecksAndEncoding::test_latin1_csv_fails_utf8_passes_xlsx_skipped` (UTF-8 branch) | ✅ COMPLIANT |
| Encoding validation — detect non-UTF-8 | Non-UTF-8 csv fails (8KB chunk fails utf-8-sig and utf-8 -> fail) | `tests/test_quality.py > TestCheckEncodingValidation::test_fallback_latin1` + `TestMixedAndRanChecksAndEncoding::test_mislabeled_csv_with_pk_raises_value_error` | ✅ COMPLIANT |
| Encoding validation — detect non-UTF-8 | xlsx skipped regardless of 8KB content (valid UTF-8 bytes in .xlsx still skipped) | `tests/test_quality.py > TestMixedAndRanChecksAndEncoding::test_latin1_csv_fails_utf8_passes_xlsx_skipped` (xlsx branch) + `TestBinaryFormatsSkipped` | ✅ COMPLIANT |
| Encoding validation — detect non-UTF-8 | is_text_eligible direct contract (case-insensitive, .csv.gz -> .gz false, README -> "" false) | `tests/test_quality.py > TestMixedAndRanChecksAndEncoding::test_is_text_eligible_direct` | ✅ COMPLIANT |
| Encoding validation — detect non-UTF-8 | Mislabeled .csv with PK + invalid bytes -> ValueError safety net + encoding_validation fail | `tests/test_quality.py > TestMixedAndRanChecksAndEncoding::test_mislabeled_csv_with_pk_raises_value_error` | ✅ COMPLIANT |

**Compliance summary**: 12/12 scenarios compliant (4 requirements fully satisfied). Every delta-spec scenario has a covering test that passed at runtime via `uv run pytest tests/test_quality.py -q` (61 passed) and full suite `uv run pytest tests/ -q` (923 passed). No `UNTESTED` or `FAILING` scenarios.

### Correctness (Static Evidence)

| Requirement | Status | Notes |
|-------------|--------|-------|
| TEXT_SUFFIXES frozenset + is_text_eligible in _formats.py | ✅ Implemented | `src/sofer/_formats.py:26-44`, `frozenset({".csv",".tsv"})`, `path.suffix.lower() in TEXT_SUFFIXES`, handles `.csv.gz->.gz` and `README->""`, case-insensitive |
| Import is_text_eligible + module docstring in quality.py | ✅ Implemented | `src/sofer/quality.py:1-16` docstring, `from ._formats import is_text_eligible` line 28 |
| QualityValidator.run() filter after exists/is_dir | ✅ Implemented | `src/sofer/quality.py:140-143`, `if not is_text_eligible(resolved): continue` before `_had_eligible = True` and probe/stream |
| _check_encoding_validation defensive guard | ✅ Implemented | `src/sofer/quality.py:540-541`, early-return before `ran_checks.add`, no finding for non-eligible direct calls |
| _process_file defensive guard | ✅ Implemented | `src/sofer/quality.py:216-217`, early-return before accumulator mutation, confirmed for .parquet/.xlsx/case-insensitive |
| ran_checks only for eligible files (binary-only -> empty) | ✅ Implemented | `self._had_eligible: bool` init in `__init__` and `_reset_accumulators`, gated in all 8 post-scan checks (`if not self._had_eligible: return`) plus before-add in helpers; `run()` sets `_had_eligible=True` only after eligibility check |
| ENCODING_FALLBACKS UTF-8-only (no latin-1/cp1252) | ✅ Implemented | `src/sofer/_csv_reader.py:27`, `["utf-8-sig","utf-8"]` only; `stream_csv` raises `ValueError` when exhausted, `_check_encoding_validation` probes 8KB with same chain, mislabeled .csv safety net preserved |
| Docstrings updated for gated dispatch + UTF-8-only | ✅ Implemented | `_formats.py:1-12`, `quality.py:1-16` module docstrings; `run():121-132`, `_process_file:211-217`, `_check_encoding_validation:532-539` method docstrings |
| No new [tool.sofer] key in config.py | ✅ Implemented | Verified `src/sofer/config.py` unchanged, no quality_eligible_suffixes key (as per design rejection) |
| _csv_reader.py unchanged except preserved contract | ✅ Implemented | No modification to fallback chain beyond existing UTF-8-only; `prepare.py` and `repo_compliance.py` untouched as planned |

### Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| Registry — TEXT_SUFFIXES lives in _formats.py | ✅ Yes | Single source of truth, distinct from SUPPORTED_FORMATS, no hardcode elsewhere; design § Architecture Decisions table option 1 chosen |
| Guard placement — run() filter + helper early-return (defense in depth) | ✅ Yes | Primary gate in `run()` before I/O, plus defensive guards in both helpers covering direct-call spec scenario; matches design rationale exactly |
| No new [tool.sofer] key (invariant, not preference) | ✅ Yes | No config churn, future formats extend frozenset; YAGNI respected |
| Why not magic-byte / NUL sniffing — suffix only | ✅ Yes | `path.suffix.lower()` O(1) deterministic, handles .parquet/.jsonl, mislabeled .csv with ZIP bytes correctly fails via ValueError safety net; design § Data Flow preserved |
| Data flow — eligibility before probe/stream, accumulators only for eligible, publish 0 failed | ✅ Yes | Flow `DatasetConfig.files -> run() -> exists/is_dir? -> is_text_eligible? -> _check_encoding_validation + _process_file -> post-scan checks (gated on _had_eligible) -> ValidationReport` matches design diagram; Path.suffix.lower() handles .XLSX/.CSV/.csv.gz/README |
| File changes as planned — _formats.py + quality.py + tests, no CLI/README change | ✅ Yes | `git diff main...HEAD` shows 32 lines in _formats.py, 62 lines in quality.py, 311 lines in test_quality.py; _csv_reader.py and config.py unchanged/verified |
| Testing strategy coverage | ✅ Yes | Unit tests for is_text_eligible, helper guards, binary skipped, TSV eligible, binary-only no cross-file, run filters before accumulators, UTF-8-only, mislabeled .csv ValueError, ran_checks — all present and passing |

### Issues Found

**CRITICAL**: None — all implementation tasks complete, every spec scenario has a passing covering test, full suite 923 passed, build clean, design followed with no spec-breaking deviations.

**WARNING**: None — no design deviations, no missing scenarios, no test failures. The 17-task forecast was 30-50 lines of prod code; actual prod diff is 94 lines (32+62), still well under the 400-line review budget. Test additions (311 lines) are expected and do not count toward prod budget risk. Single-PR delivery remains appropriate (no chained PRs needed).

**SUGGESTION**:
- Consider adding a brief `HISTORY` entry or PR description note that `_had_eligible` gating also covers future P0 checks added to `QUALITY_CHECK_NAMES` — current implementation already gates all 8 post-scan checks, so new checks must follow the same `if not self._had_eligible: return` pattern.
- The existing `DeprecationWarning` spam from `test_codebook.py` (8 warnings for `_infer_type`) is unrelated but could be cleaned up in a follow-up to reduce noise in CI logs.

### Verdict

**PASS**

All 17 tasks implemented and verified. 12/12 delta-spec scenarios have passing covering tests (binary skip, TSV eligible, case-insensitive, .csv.gz/no-extension, defensive guards, mixed/ran_checks, UTF-8-only encoding, mislabeled .csv ValueError). Full suite `uv run pytest tests/ -q` passes (923 passed, 2 skipped), `uv run ruff check src/ tests/` and `uv run mypy src/` clean (26 files), design coherence confirmed against all 4 architecture decisions, no deviations, no blockers. Ready for archive.
