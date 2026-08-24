# Delta for Data Quality

## MODIFIED Requirements

### Requirement: Duplicates — row-hash based, streaming

The system MUST detect exact duplicate rows by computing a hash of each row's
concatenated field values, **scoped per file**. Two identical rows in different
files SHALL NOT be reported as duplicates. The hash key MUST include the
filename to prevent cross-file collisions. Duplicate warnings MUST include the
offending row number and a sample value.

(Previously: `_dup_hashes` was global across files, causing false "Row 1 = Row
1" duplicates when two files had matching data in the same row position.)

#### Scenario: No duplicates

- GIVEN a CSV with 100 unique rows
- WHEN _check_duplicates() runs
- THEN no warning SHALL be appended to the report

#### Scenario: Exact duplicates present

- GIVEN a CSV where rows 17 and 42 are identical
- WHEN _check_duplicates() runs
- THEN the report SHALL have a warning
  AND the warning SHALL mention the duplicate row numbers

#### Scenario: Identical rows in different files are NOT duplicates

- GIVEN file_a.csv row 1 equals file_b.csv row 1
- WHEN QualityValidator.run() processes both files
- THEN no duplicate warning SHALL be produced for those rows

### Requirement: Empty columns — all values empty/NA/null across sample

The system MUST detect columns where every value in the sampled rows is empty,
`NA`, `NULL`, or `N/A`. Files with zero data rows (header-only) SHALL be
excluded from this check to avoid false positives where `_col_nonempty` has no
entries.

(Previously: header-only files with no `_col_nonempty` entries were flagged as
having "fully empty columns".)

#### Scenario: All columns populated

- GIVEN a CSV where every column has >= 1 non-empty value
- WHEN _check_empty_columns() runs
- THEN no warning SHALL be appended

#### Scenario: Fully empty column

- GIVEN a CSV where column "notes" is entirely empty
- WHEN _check_empty_columns() runs
- THEN a warning SHALL mention column "notes"
  AND the severity SHALL be warn

#### Scenario: Header-only file (zero data rows)

- GIVEN a CSV with a header but zero data rows
- WHEN _check_empty_columns() runs
- THEN no warning SHALL be appended for that file

### Requirement: Cross-file type consistency

When the same column name appears in multiple CSV files, the system MUST verify
that inferred types are compatible. Files with zero data rows SHALL be excluded
from comparison to avoid `"unknown"` type mismatches against files with real
data.

(Previously: zero-row files with no `_col_samples` had type `"unknown"`,
causing false mismatches against files with actual numeric/text types.)

#### Scenario: Compatible types

- GIVEN two CSVs both with column "year" typed as numeric
- WHEN _check_cross_file_types() runs
- THEN no warning SHALL be appended

#### Scenario: Type mismatch

- GIVEN file_a.csv with column "year" typed as numeric
  AND file_b.csv with column "year" typed as text
- WHEN _check_cross_file_types() runs
- THEN a warning SHALL mention the column and both files

#### Scenario: Zero-row file excluded from type comparison

- GIVEN CPV2010.csv with header only (0 data rows) and column "CPV2010_REF_ID"
  AND PROV.csv with data and column "CPV2010_REF_ID" typed as numeric
- WHEN _check_cross_file_types() runs
- THEN no cross-file type mismatch SHALL be reported for "CPV2010_REF_ID"

### Requirement: CLI commands propagate ran_checks

Both `_cmd_validate` and `_cmd_upload` in `cli.py` SHALL copy
`quality_report.ran_checks` into `report.ran_checks` so
`_count_passed_quality` receives the set of checks that actually executed.
Without this, `_count_passed_quality` always reports `passed = 0`.

(Previously: `ran_checks` was set inside `QualityValidator.run()` but never
copied to the `DatasetValidator`'s `ValidationReport`.)

#### Scenario: Validate reports non-zero passed checks

- GIVEN a valid dataset TOML
- WHEN `_cmd_validate(args)` is called
- THEN the quality summary SHALL report `> 0 passed`
  AND the summary SHALL NOT say "0 passed, 6 skipped" when checks executed
