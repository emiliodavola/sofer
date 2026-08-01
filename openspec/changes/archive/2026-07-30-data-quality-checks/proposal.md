# Proposal: Data Quality Checks

## Intent

Add automated data quality checks to the upload pipeline — duplicate detection, null profiling, format consistency, encoding validation, and value-range enforcement — so data reliability problems are caught **before** data reaches Hugging Face Hub. Currently the tool validates structure (files exist, columns present) but never inspects the *content* of CSV rows.

## Scope

### In Scope
- New `quality.py` module with `QualityValidator` (stdlib-only: csv, statistics, codecs)
- New `_csv_reader.py` shared streaming CSV reader
- `[[quality]]` TOML section with `QualityCheck` / `QualityConfig` dataclasses in `model.py`
- P0 checks: duplicates, empty_rows, empty_columns, null_profiling, format_consistency, corrupt_records, value_range, cross_file_types, encoding_validation
- Severity model: `fail` blocks upload, `warn` is advisory
- Default behaviour: quality checks run even without `[[quality]]` section (sensible built-in defaults)
- Integration: both `validate` and `upload` commands run quality checks
- Report: extends `ValidationReport` with quality section

### Out of Scope
- **Outlier detection (IQR)** — deferred to P1; needs streaming percentile or two-pass approach
- **Pandas/numpy-backed checks** — not justified for stdlib-only P0; optional extras tracked as future work
- **`--json` output flag** — not needed for P0
- **Cross-dataset semantic accuracy** — out of scope for a single-dataset uploader
- **Parquet quality checks** — no parquet support yet in the tool

## Capabilities

### New Capabilities
- `data-quality`: Configurable per-dataset quality expectations (duplicates, nulls, format, encoding, ranges). Runs after structural validation, before upload. Configured via `[[quality]]` TOML section. Each check has configurable severity (`warn` / `fail`).

### Modified Capabilities
- None. Existing `repo-compliance` capability is unchanged; quality is additive.

## Approach

**Hybrid**: new `quality.py` module + shared `_csv_reader.py` + `[[quality]]` TOML section.

Pipeline order:
```
config.validate()     → structural checks (checks.py)
QualityValidator.run() → quality checks (quality.py) [NEW]
schema report        → Dataset Card (repo_compliance.py) [unchanged]
upload()             → HF push
```

Key design choices:
- **stdlib-only**: csv, statistics, codecs — zero new runtime dependencies
- **Streaming**: all checks are single-pass or streaming; no full dataset loaded into memory
- **100K default sample** for checks that don't need full scan (matching codebook's `--max-sample`)
- **Built-in defaults**: when no `[[quality]]` section exists, all P0 checks run with default severities
- **Reuses** existing `ValidationReport` model for output consistency

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/data_uploader/quality.py` | **New** | `QualityValidator` class with all P0 check methods |
| `src/data_uploader/_csv_reader.py` | **New** | Shared streaming CSV reader utility |
| `src/data_uploader/model.py` | Modified | Add `QualityCheck`, `QualityConfig` dataclasses; parse `[[quality]]` in `from_toml()` |
| `src/data_uploader/checks.py` | Modified | `ValidationReport.print_summary()` gets quality section |
| `src/data_uploader/cli.py` | Modified | Both `_cmd_validate` and `_cmd_upload` call `QualityValidator` |
| `tests/test_quality.py` | **New** | Unit tests for all check types |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Large-file perf (multi-GB CSVs) | Med | Streaming O(n), never buffered. Checks that can sample use 100K cap. |
| False positives in format_consistency | Med | Ignore known missing-value sentinels. Configurable `ignore_values`. |
| TOML config gets verbose for wide datasets | Low | Default check runs without per-column config. Override only when needed. |

## Rollback Plan

Revert by: removing `quality.py`, `_csv_reader.py`, reverting `model.py` changes (remove `QualityCheck`, `QualityConfig`, `[[quality]]` parsing), reverting `checks.py` report changes, reverting `cli.py` quality wiring, and deleting `tests/test_quality.py`. Quality is entirely additive — no existing behaviour is affected if removed.

## Dependencies

- None beyond stdlib (Python 3.10+ csv, statistics, codecs)

## Success Criteria

- [ ] All P0 checks pass with correct severity (fail/warn) on known-good and known-bad CSVs
- [ ] Both `validate` and `upload` commands surface quality issues
- [ ] Quality checks run with sensible defaults when `[[quality]]` section is absent
- [ ] 100% of P0 checks have unit tests in `tests/test_quality.py`
- [ ] Existing test suite continues to pass without modification
- [ ] Zero new runtime dependencies added to the project
