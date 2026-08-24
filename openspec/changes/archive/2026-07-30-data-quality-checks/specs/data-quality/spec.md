# Spec: data-quality — Content Quality Checks

- **Change:** data-quality-checks
- **Capability:** `data-quality` (new)
- **Status:** Draft
- **Author:** sdd-spec executor
- **Date:** 2026-07-30

---

## 1. Overview

The `data-quality` capability inspects CSV **content** (not just structure) after
structural validation passes and before upload. It detects duplicates, null
columns, format inconsistencies, encoding errors, corrupt records, and
out-of-range values — all via stdlib-only streaming checks.

### 1.1 Pipeline position

```
cfg.validate()          → structural checks (checks.py)
QualityValidator.run()  → quality checks  (quality.py)   ← NEW
build_schema_report()   → Dataset Card    (repo_compliance.py)
upload()                → HF push
```

### 1.2 Design constraints

- **Stdlib only** — no runtime dependencies beyond `csv`, `statistics`, `codecs`.
- **Streaming** — all checks are single-pass or sample-limited; no full dataset in memory.
- **100K sample cap** — checks that don't require full scan read at most `max_sample` rows (default 100 000).
- **Severity model** — `fail` blocks upload (exit 1), `warn` is advisory.
- **Sensible defaults** — quality checks run even without `[[quality]]` TOML section.

---

## 2. Data Model — `model.py`

### 2.1 `QualityCheck` dataclass

Added to `src/sofer/model.py`:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `check` | `str` | (required) | Check name, one of the P0 identifiers listed in § 3. |
| `severity` | `str` | `"warn"` | `"warn"` or `"fail"`. Overrides `QualityConfig.default_severity`. |
| `columns` | `list[str] \| None` | `None` | Column subset the check applies to (`None` = all columns). |
| `max_null_pct` | `float \| None` | `None` | Threshold for `null_profiling` (0.0–100.0). |
| `min` | `float \| None` | `None` | Minimum acceptable value for `value_range`. |
| `max` | `float \| None` | `None` | Maximum acceptable value for `value_range`. |
| `min_unique` | `int \| None` | `None` | Minimum distinct values for `duplicates`. |
| `ignore_values` | `list[str] \| None` | `None` | Values to treat as non-missing / ignore during type inference. |

### 2.2 `QualityConfig` dataclass

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `checks` | `list[QualityCheck]` | `field(default_factory=list)` | Per-check overrides. |
| `default_severity` | `str` | `"warn"` | Fallback severity when a check has no explicit severity. |
| `max_sample` | `int` | `100_000` | Max rows to read per file for checks that sample. |

### 2.3 `from_toml()` update

The `DatasetConfig.from_toml()` classmethod SHALL parse a new `[[quality]]` TOML
section. Each entry maps to one `QualityCheck`. Unknown `check` values SHALL be
reported as configuration warnings (not hard errors).

**TOML representation:**

```toml
[[quality]]
check = "duplicates"
severity = "fail"

[[quality]]
check = "null_profiling"
max_null_pct = 15.0
columns = ["age", "income"]

[[quality]]
check = "value_range"
columns = ["age"]
min = 0
max = 120

[[quality]]
check = "format_consistency"
ignore_values = ["N/A", "UNKNOWN"]
```

#### 2.3.1 Scenarios

**Full [[quality]] section**

```
GIVEN a TOML file with two [[quality]] entries:
      one setting duplicates→fail and one setting
      null_profiling with max_null_pct=15.0
WHEN from_toml(path) is called
THEN DatasetConfig.quality SHALL be a QualityConfig
     with two QualityCheck entries
  AND duplicates severity SHALL be "fail"
  AND null_profiling max_null_pct SHALL be 15.0
```

**No [[quality]] section**

```
GIVEN a TOML file with no [[quality]] entries
WHEN from_toml(path) is called
THEN DatasetConfig.quality SHALL be a QualityConfig
     with an empty checks list
  AND QualityValidator SHALL use built-in defaults
  AND no configuration error SHALL be raised
```

**Unknown check name**

```
GIVEN a [[quality]] entry with check = "bogus_check"
WHEN from_toml(path) is called
THEN a warning SHALL be reported (not a hard error)
  AND the bogus entry SHALL be ignored
```

---

## 3. Shared CSV Reader — `_csv_reader.py`

A new module `src/sofer/_csv_reader.py` SHALL provide a single
generator:

```python
def stream_csv(
    path: Path,
    delimiter: str = ";",
    encoding: str = "utf-8-sig",
    max_sample: int = 100_000,
) -> Generator[tuple[list[str], list[str] | None], None, None]:
    """Yields (header, row) tuples, encoding-fallback aware."""
```

### 3.1 Behaviour

1. Open file with the given encoding and `csv.reader`.
2. Yield the header row as first tuple with `row=None`.
3. Yield data rows as `(header, row)` tuples.
4. Stop after `max_sample` data rows (or EOF).
5. When a file has no rows (completely empty or header-only): yield
   `(header, None)` where `header` is the list of parsed column names (or `[]`
   for a completely empty file), then stop without error.
6. On `UnicodeDecodeError` (or `UnicodeError`): retry with `encoding="utf-8"`
   after printing a warning. On second failure: retry with `encoding="latin-1"`,
   then `encoding="cp1252"`. If all fallbacks fail: raise `ValueError`.
7. On every data row: the consumer SHALL detect corrupt records via
   `len(row) != len(header)` on each row. (`csv.reader` defaults to
   `strict=False`, so it does NOT raise `csv.Error` on inconsistent lengths.)

### 3.2 Scenarios

**Normal CSV**

```
GIVEN a valid UTF-8 CSV with 50 rows and 4 columns
WHEN stream_csv(path) is called
THEN the first yielded tuple SHALL have row=None (header only)
  AND exactly 50 data row tuples SHALL be yielded
  AND every row SHALL have len 4
```

**Encoding fallback**

```
GIVEN a Latin-1-encoded CSV with accented characters
WHEN stream_csv(path, encoding="utf-8-sig") is called
THEN open SHALL fail with UnicodeDecodeError on first attempt
  AND the reader SHALL retry with encoding="utf-8"
  AND utf-8 SHALL also fail
  AND the reader SHALL retry with encoding="latin-1"
  AND all rows SHALL be yielded successfully
  AND a warning SHALL be printed
```

**Unrecoverable encoding**

```
GIVEN a binary file passed as CSV
WHEN stream_csv(path) is called
THEN utf-8-sig, utf-8, latin-1, and cp1252 attempts SHALL all fail
  AND ValueError SHALL be raised
```

**Sample cap**

```
GIVEN a CSV with 200 000 data rows
WHEN stream_csv(path, max_sample=100_000) is called
THEN exactly 100 000 rows SHALL be yielded
  AND the generator SHALL stop (no further reads)
```

**Empty file**

```
GIVEN a CSV file with 0 data rows (empty or header-only)
WHEN stream_csv(path) is called
THEN no crash SHALL occur
  AND the first yield SHALL contain the header (or [] for empty file) with row=None
  AND no data rows SHALL be yielded
  AND the generator SHALL stop cleanly
```

---

## 4. P0 Quality Checks — `quality.py`

A new module `src/sofer/quality.py` SHALL contain the
`QualityValidator` class. Every check SHALL be implemented as a method
`_check_<name>(self)` that accumulates state as rows are streamed by `run()`
via a shared single pass of `stream_csv`. After all files are scanned, the
method SHALL append its results to `self.report`.

### 4.0 `QualityValidator` class

```python
class QualityValidator:
    def __init__(self, cfg: DatasetConfig): ...
    def run(self) -> ValidationReport: ...
```

`run()` SHALL execute every active check in a fixed order. It SHALL NOT stop
on the first failure — all checks run regardless.

### 4.1 Duplicates — row-hash based, streaming

**Requirement:** The system MUST detect exact duplicate rows by computing a
hash of each row's concatenated field values. Duplicate warnings MUST include
the offending row number and a sample value.

#### Scenarios

**No duplicates**

```
GIVEN a CSV with 100 unique rows
WHEN _check_duplicates() runs
THEN no warning SHALL be appended to the report
```

**Exact duplicates present**

```
GIVEN a CSV where rows 17 and 42 are identical
WHEN _check_duplicates() runs
THEN the report SHALL have a warning
  AND the warning SHALL mention the duplicate row numbers
```

### 4.2 Empty rows — all fields empty/NA/null

**Requirement:** The system MUST detect rows where every field is empty, `NA`,
`NULL`, `N/A`, or whitespace-only. Such rows are data entry errors.

#### Scenarios

**All rows populated**

```
GIVEN a CSV with no empty rows
WHEN _check_empty_rows() runs
THEN no warning SHALL be appended
```

**Row with all-empty fields**

```
GIVEN a CSV where row 33 has every cell empty
WHEN _check_empty_rows() runs
THEN a warning SHALL be appended mentioning row 33
```

### 4.3 Empty columns — all values empty/NA/null across sample

**Requirement:** The system MUST detect columns where every value in the
sampled rows is empty, `NA`, `NULL`, or `N/A`. These are structural defects.

#### Scenarios

**All columns populated**

```
GIVEN a CSV where every column has ≥ 1 non-empty value
WHEN _check_empty_columns() runs
THEN no warning SHALL be appended
```

**Fully empty column**

```
GIVEN a CSV where column "notes" is entirely empty
WHEN _check_empty_columns() runs
THEN a warning SHALL mention column "notes"
  AND the severity SHALL be warn
```

### 4.4 Null profiling — per-column null percentage threshold

**Requirement:** The system MUST compute the percentage of null/empty/missing
values per column and compare it against `max_null_pct` (default: 50.0%).
Columns exceeding the threshold MUST be reported.

#### Scenarios

**Below threshold**

```
GIVEN a column with 10% missing values
  AND max_null_pct = 50.0
WHEN _check_null_profiling() runs
THEN no warning SHALL be appended
```

**Above threshold**

```
GIVEN a column with 60% missing values
  AND max_null_pct = 50.0
WHEN _check_null_profiling() runs
THEN a warning SHALL mention the column and its null percentage
```

### 4.5 Format consistency — mixed types within column

**Requirement:** The system MUST detect columns where values are a mix of
numeric and text (e.g. `["42", "abc", "3.14"]`). Known missing-value
sentinels (`""`, `"NA"`, `"NULL"`, `"N/A"`, plus `ignore_values`) MUST be
excluded from type inference.

#### Scenarios

**Uniform type**

```
GIVEN a column where every value parses as float
WHEN _check_format_consistency() runs
THEN no warning SHALL be appended
```

**Mixed numeric/text**

```
GIVEN a column with values ["100", "200", "N/A", "thirty"]
WHEN _check_format_consistency() runs
THEN a warning SHALL be appended mentioning the column
```

### 4.6 Corrupt records — inconsistent row lengths, CSV errors

**Requirement:** The system MUST detect rows with unexpected field counts
(different from the header length) via manual `len(row) != len(header)`
comparison on every row. Default severity: `fail`.

#### Scenarios

**Uniform row lengths**

```
GIVEN a CSV where every row has the same number of fields as the header
WHEN _check_corrupt_records() runs
THEN no error SHALL be appended
```

**Short row**

```
GIVEN a CSV where row 55 has fewer fields than the header
WHEN _check_corrupt_records() runs
THEN a fail-level error SHALL be appended mentioning row 55
```

### 4.7 Value range — configurable min/max per column

**Requirement:** The system MUST check that numeric values in configured
columns fall within `[min, max]`. This check has no built-in default — it
SHALL be skipped unless a `QualityCheck` explicitly configures `min` or `max`.

#### Scenarios

**Values in range**

```
GIVEN column "age" with values [25, 30, 42]
  AND a QualityCheck for "age" with min=0, max=120
WHEN _check_value_range() runs
THEN no warning SHALL be appended
```

**Out-of-range value**

```
GIVEN column "age" with values [25, 200, 42]
  AND a QualityCheck for "age" with min=0, max=120
WHEN _check_value_range() runs
THEN a warning SHALL mention value 200 and row position
```

**No range configured**

```
GIVEN no QualityCheck sets min or max for any column
WHEN _check_value_range() runs
THEN the check SHALL be skipped entirely
```

### 4.8 Cross-file type consistency

**Requirement:** When the same column name appears in multiple CSV files, the
system MUST verify that inferred types are compatible (both numeric, both text,
etc.). Default severity: `warn`.

#### Scenarios

**Compatible types**

```
GIVEN two CSVs both with column "year" typed as numeric
WHEN _check_cross_file_types() runs
THEN no warning SHALL be appended
```

**Type mismatch**

```
GIVEN file_a.csv with column "year" typed as numeric
  AND file_b.csv with column "year" typed as text
WHEN _check_cross_file_types() runs
THEN a warning SHALL mention the column and both files
```

### 4.9 Encoding validation — detect non-UTF-8 files

**Requirement:** The system MUST verify every CSV file is decodable using the
same fallback chain as `stream_csv`: `utf-8-sig` → `utf-8` → `latin-1` →
`cp1252`. The check SHALL read the first 8 KB of each file and attempt decoding
with each encoding in order. If ANY encoding succeeds, the check SHALL pass.
Only fail if ALL fallbacks fail. Default severity: `fail`.

#### Scenarios

**Valid UTF-8**

```
GIVEN a CSV file with valid UTF-8 encoding
WHEN _check_encoding_validation() runs
THEN no error SHALL be appended
```

**Non-UTF-8 file decoded via fallback**

```
GIVEN a CSV file encoded in Windows-1252
WHEN _check_encoding_validation() runs
THEN the file SHALL pass (cp1252 is Python's name for the Windows-1252 encoding)
  AND no error SHALL be appended
```

**Unrecoverable encoding**

```
GIVEN a binary file that fails utf-8-sig, utf-8, latin-1, AND cp1252
WHEN _check_encoding_validation() runs
THEN a fail-level error SHALL be appended
  AND the error SHALL name the file
```

> **Known limitation:** The 8 KB peek may not detect binary files with
> UTF-8-like prologues (e.g., a PNG or PDF whose first 8 KB happen to be valid
> UTF-8). This is an accepted gap for P0 — full-file encoding detection would
> require reading the entire file, breaking the streaming constraint.

---

## 5. Integration

### 5.1 CLI changes — `cli.py`

Both `_cmd_validate` and `_cmd_upload` SHALL call `QualityValidator.run()`
after structural checks pass and before the command continues.

**`_cmd_validate` changes:**

```
cfg = DatasetConfig.from_toml(args.config)
config_errors = cfg.validate()         ← unchanged
if config_errors: return 1             ← unchanged

validator = DatasetValidator(cfg)
report = validator.run_all()           ← structural checks (unchanged)

quality = QualityValidator(cfg)              ← NEW
quality_report = quality.run()               ← NEW
report.quality_results = quality_report.quality_results  ← NEW

report.print_summary()
return 0 if report.passed else 1       ← unchanged
```

**`_cmd_upload` changes:** Same merge pattern. Upload SHALL be blocked when
quality checks produce any `fail`-severity result.

#### Scenarios

**Quality failures block upload**

```
GIVEN a TOML config with corrupt CSV (row length mismatch)
WHEN _cmd_upload(args) is called
THEN quality.run() SHALL be called after structural checks
  AND report.passed SHALL be False
  AND upload SHALL NOT proceed
  AND exit code SHALL be 1
```

**Quality warnings do not block upload**

```
GIVEN a TOML config with no [[quality]] section
  AND a CSV with 2% missing values (below any threshold)
WHEN _cmd_upload(args) is called
THEN report.passed SHALL be True
  AND upload SHALL proceed
```

### 5.2 `ValidationReport` extension — `checks.py`

The `ValidationReport` class SHALL gain a `quality_results: list[QualityResult]`
field (see § 5.3) and an optional quality section in its `print_summary()` output.
The quality section SHALL be populated from `quality_results`, not by merging
into `errors`/`warnings`. This keeps quality findings separable from structural
findings.

```
  Validation report: my-dataset
  ──────────────────────────────────
  Errors:   0
  Warnings: 0
  ─────  Quality checks  ───────────
  Errors:   1
    ✗  corrupt_records: Row 55 has 3 fields, header has 5
  Warnings: 2
    ⚠  duplicates: Row 17 = Row 42
    ⚠  empty_rows: Row 33 is completely empty
  ✓  Quality: 5 passed, 1 failed, 2 warnings
```

The quality section SHALL be printed only when quality checks were run (i.e.,
after `QualityValidator.run()` has been called).

### 5.3 `QualityResult` dataclass

Added to `src/sofer/model.py`:

| Field | Type | Description |
|-------|------|-------------|
| `check` | `str` | Check name identifier (e.g. `"duplicates"`). |
| `severity` | `str` | `"warn"` or `"fail"`. Maps directly to the severity model (§ 6.3). |
| `message` | `str` | Human-readable description of the finding. |

The `ValidationReport` class SHALL gain a `quality_results: list[QualityResult]`
field, initially empty. `QualityValidator.run()` SHALL append `QualityResult`
instances directly — it SHALL NOT merge into `report.errors` / `report.warnings`.
The `print_summary()` method SHALL iterate `quality_results` in a dedicated
`─── Quality checks ───` section (§ 5.2).

---

## 6. Behavioural Rules

### 6.1 Default behaviour (no `[[quality]]` section)

Without any `[[quality]]` TOML entries, the following checks SHALL run with
built-in defaults:

| Check | Default severity | Notes |
|-------|-----------------|-------|
| `duplicates` | `warn` | — |
| `empty_rows` | `warn` | — |
| `empty_columns` | `warn` | — |
| `null_profiling` | `warn` | Threshold: 50.0% |
| `format_consistency` | `warn` | — |
| `corrupt_records` | `fail` | Blocks upload |
| `encoding_validation` | `fail` | Blocks upload |
| `cross_file_types` | `warn` | — |
| `value_range` | (none) | Skipped; requires explicit config |

With defaults, all CSVs declared in `[[file]]` entries SHALL be checked.

### 6.2 Explicit `[[quality]]` override rules

- When a `[[quality]]` entry names a check, its severity and parameters SHALL
  replace the built-in defaults for that check.
- Checks NOT mentioned in any `[[quality]]` entry SHALL keep their built-in
  defaults.
- `columns` in a `QualityCheck` SHALL scope that check to specific columns.
  When `columns` is `None`, the check applies to ALL columns.

### 6.3 Severity model

| Severity | Behaviour |
|----------|-----------|
| `warn` | Message printed; upload NOT blocked. |
| `fail` | Message printed; upload blocked (exit code 1). |

### 6.4 Dependency constraint

The `QualityValidator` SHALL NOT import any runtime dependency outside the
Python 3.10+ standard library. Permitted stdlib modules: `csv`, `statistics`,
`codecs`, `collections`, `pathlib`, `hashlib`, `typing`, `dataclasses`.

---

## 7. Open Questions

- **Cross-file type consistency on large schemas**: If a dataset has 200+
  columns across 10 files, the type-compatibility report could be verbose.
  Tolerate as P0; paginate or summarise if feedback shows it's overwhelming.
- **(Resolved)** `max_sample` interaction with row-hash duplicates: the
  design uses set-of-hashes within the 100K sample. For P0 this covers
  typical CSVs; for multi-GB files a Bloom-filter approximation can be
  explored as P1.
