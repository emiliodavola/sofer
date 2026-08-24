# Spec: repo-compliance — Parquet-aware Schema Report (Delta)

- **Change:** parquet-default
- **Capability:** `repo-compliance` (modified)
- **Parent spec:** `openspec/specs/repo-compliance/spec.md`
- **Status:** Draft
- **Author:** sdd-spec executor
- **Date:** 2026-07-30

---

## 1. Summary of Change

When Parquet conversion is active, `build_schema_report` SHALL read from the
converted Parquet file in the staging directory instead of the original CSV.
Parquet carries native column type metadata (`parquet_schema`), which replaces
the heuristic `infer_column_type`-based classification for those files.

This is a delta spec: it modifies § 3.3 of the parent spec
(`openspec/specs/repo-compliance/spec.md`). All other sections of the parent
spec remain unchanged.

### 1.1 Why this matters

The current CSV-based type inference (`infer_column_type`) is heuristic — it
samples values and guesses "numeric", "categorical/text", etc. Parquet stores
the actual schema types (int64, float64, string, bool, timestamp, etc.),
providing **authoritative** type metadata. The schema report becomes more
accurate and useful for downstream consumers.

### 1.2 Flow change

```
BEFORE (parent spec):
  build_schema_report reads CSVs → heuristic type inference

AFTER (this delta):
  upload() converts CSVs → build_schema_report reads Parquet → native types
```

The conversion step MUST run **before** `build_schema_report` when Parquet
conversion is enabled. The orchestrator (`upload()`) is responsible for passing
the staging directory path to `build_schema_report`.

---

## 2. Modified: `build_schema_report` signature

### 2.1 New signature

```python
def build_schema_report(
    cfg: DatasetConfig,
    csv_delimiter: str | None = None,
    csv_encoding: str = "utf-8-sig",
    staging_dir: Path | None = None,       # NEW
) -> list[ColumnSchema]:
```

### 2.2 Parameter behaviour

| Parameter | Type | Default | Behaviour |
|-----------|------|---------|-----------|
| `staging_dir` | `Path \| None` | `None` | Directory containing converted Parquet files. When provided and a matching `.parquet` file exists for a CSV entry, read from Parquet instead of the original CSV. When `None`, fall back to CSV-only reading (original behaviour). |

### 2.3 Resolution logic

For each `FileEntry` whose `remote` path ends with `.csv` (case-insensitive):

1. If `staging_dir` is not `None` AND the entry does NOT have
   `upload_as_csv = True` (i.e., it was converted):
   a. Look for `staging_dir / <stem>.parquet`.
   b. If the Parquet file exists, read schema and metadata from it.
   c. If the Parquet file does not exist, fall back to CSV reading.
2. Otherwise (no `staging_dir`, or `upload_as_csv = True`, or file not found):
   use the existing CSV-based reading path.

---

## 3. Parquet-based Column Analysis

### 3.1 Reading from Parquet

When a Parquet file is used, the function SHALL:

```python
import pyarrow.parquet as pq

parquet_file = pq.ParquetFile(parquet_path)
schema = parquet_file.schema_arrow  # pyarrow.Schema
metadata = parquet_file.metadata    # parquet.FileMetaData
num_rows = metadata.num_rows
```

### 3.2 Column `dtype` mapping

The `dtype` field of `ColumnSchema` SHALL be derived from the Parquet physical
type instead of `infer_column_type`:

| Parquet physical type | `ColumnSchema.dtype` |
|-----------------------|----------------------|
| `INT{8,16,32,64}` | `"numeric"` |
| `FLOAT`, `DOUBLE` | `"numeric"` |
| `DECIMAL` | `"numeric"` |
| `BOOLEAN` | `"categorical/text"` |
| `BYTE_ARRAY` (string-like) | `"categorical/text"` |
| `FIXED_LEN_BYTE_ARRAY` | `"categorical/text"` |
| `STRING` | `"categorical/text"` |
| `LARGE_STRING` | `"categorical/text"` |
| `ENUM` | `"categorical/text"` |
| `TIMESTAMP`, `DATE`, `TIME` | `"categorical/text"` (model stores as text) |
| `INT{32,64}` with `isAdjustedToUTC` / logical timestamp | `"categorical/text"` |
| `LIST`, `MAP`, `STRUCT` | `"unknown"` |

This is a **lossless** mapping: the authoritative type is in the Parquet schema,
and `ColumnSchema.dtype` is a simplified category for the Dataset Card's
Codebook table. The exact Parquet physical type is not preserved in
`ColumnSchema` in P0.

### 3.3 Other `ColumnSchema` fields from Parquet

| Field | Source | Notes |
|-------|--------|-------|
| `name` | `schema.field(i).name` | Column name as declared in the Parquet file. |
| `dtype` | From § 3.2 mapping | Derived from physical type. |
| `nullable` | `schema.field(i).nullable` | Parquet schema declares nullability natively. |
| `example` | Sample first non-null value from first row group | Read up to 1000 rows from the first row group to find a non-null example. Empty string if all-null. |
| `unique` | Not available from schema | Sample up to `_SCHEMA_SAMPLE_SIZE` rows to compute unique count (same heuristic as CSV path). |
| `missing` | Not available from schema | Sample up to `_SCHEMA_SAMPLE_SIZE` rows to compute null percentage (same heuristic as CSV path). |

#### 3.3.1 Sampling from Parquet for `example`, `unique`, `missing`

When reading from Parquet, the function SHALL read a sample of up to
`_SCHEMA_SAMPLE_SIZE` rows from the first row group:

```python
table = parquet_file.read_row_groups([0])  # first row group only
df = table.to_pandas()  # or iterate column-by-column with pyarrow arrays
```

Then compute `example`, `unique`, and `missing` using the same logic as the CSV
path (reusing `infer_column_type` is NOT needed for `dtype`, but the sample is
still needed for `unique` and `missing`).

The `example` value SHALL be converted to string for storage in `ColumnSchema`.

### 3.4 Column name disambiguation

The same cross-file disambiguation rule from the parent spec applies: when the
same column name appears in multiple files, prefix with `"<filename>::"`.

When reading from Parquet, the filename SHALL be the Parquet file's stem plus
`.parquet` extension for consistency (e.g., `"survey.parquet::age"`).

---

## 4. Modified: `upload()` Orchestration

### 4.1 New sequence inside `upload()`

```
1. _ensure_repo(cfg)
2. CONVERSION: convert CSVs to Parquet in staging_dir    # NEW — before compliance
3. COMPLIANCE:
   a. schema = build_schema_report(cfg, staging_dir=staging_dir)  # reads Parquet
   b. card   = build_dataset_card(cfg, schema)
   c. license_text = build_license_file(cfg.license)
4. Write compliance files to staging_dir
5. Upload compliance files (README.md, LICENSE)
6. Upload data files (Parquet versions, unless upload_as_csv)
```

**Key change**: Conversion moves from after-compliance (as originally drafted in
proposal § 4.2) to **before** compliance, so `build_schema_report` can read the
converted Parquet files.

### 4.2 Staging dependency

`build_schema_report` now depends on the staging directory containing the
converted Parquet files. The orchestrator SHALL:

1. Create the staging tempdir.
2. Run conversion (write Parquet files into it).
3. Pass `staging_dir=tmpdir` to `build_schema_report`.
4. Write compliance artifacts into the same `tmpdir`.

### 4.3 Mixed-mode logging

The upload log SHALL report whether schema was read from Parquet or CSV per file:

```
  🔄  survey.csv → survey.parquet (converted)
  📊  survey.parquet → schema (Parquet native types)
  ↑  survey.parquet → survey.parquet
```

---

## 5. Scenarios

### Schema from Parquet — happy path

```
GIVEN a DatasetConfig with one CSV file entry "survey.csv"
  AND upload(cfg) is called
  AND conversion succeeds (survey.parquet is in staging_dir)
WHEN build_schema_report(cfg, staging_dir=tmpdir) is called
THEN the function SHALL read survey.parquet from staging_dir
  AND the dtype for an INT64 column SHALL be "numeric"
  AND the dtype for a BYTE_ARRAY column SHALL be "categorical/text"
  AND the nullable field SHALL match parquet_schema.field(i).nullable
  AND unique and missing fields SHALL be computed from a row-group sample
```

### Schema from CSV — no staging dir (backward compat)

```
GIVEN a DatasetConfig with one CSV file entry
  AND build_schema_report(cfg) is called (no staging_dir)
THEN the function SHALL read the CSV file directly
  AND use infer_column_type for dtype
  AND behave identically to the parent spec's § 3.3
```

### Schema from CSV — upload_as_csv override

```
GIVEN a DatasetConfig with upload_as_csv = true for a CSV entry
  AND staging_dir=tmpdir is provided
WHEN build_schema_report processes that entry
THEN the function SHALL read the original CSV (not the Parquet)
  AND use infer_column_type for dtype
```

### Schema from CSV — Parquet file missing from staging

```
GIVEN a CSV entry that was NOT marked upload_as_csv
  BUT the .parquet file is missing from staging_dir
  (e.g., conversion failed silently)
WHEN build_schema_report processes that entry
THEN the function SHALL fall back to reading the original CSV
  AND use infer_column_type for dtype
```

### Schema from Parquet — no duplicate column disambiguation

```
GIVEN two CSV files: "a.csv" and "b.csv"
  AND both have a column named "value"
  AND both are converted to Parquet
WHEN build_schema_report(cfg, staging_dir=tmpdir) is called
THEN the returned list SHALL contain
  "a.parquet::value" and "b.parquet::value"
  (filename prefix uses the Parquet filename)
```

---

## 6. Backward Compatibility

### 6.1 Callers without Parquet

Any caller that invokes `build_schema_report(cfg)` without `staging_dir` SHALL
receive identical behaviour to the parent spec. No regression.

### 6.2 Callers with Parquet

Callers that pass `staging_dir` SHALL get the new behaviour. The return type
(`list[ColumnSchema]`) is unchanged. The `dtype` values are the same string
set (`"numeric"`, `"categorical/text"`, `"mixed (mostly numeric)"`,
`"unknown"`), so consumers of `ColumnSchema` require no changes.

### 6.3 `build_dataset_card` and `build_license_file`

These functions are unaffected. Their inputs (`DatasetConfig`, `list[ColumnSchema]`,
`recipe_content`) are unchanged. The schema report feeds into the Dataset Card's
Codebook section with more accurate dtypes — this is transparent to
`build_dataset_card`.

---

## 7. Testing

### 7.1 New / modified tests in `tests/test_repo_compliance.py`

| Test area | Tests |
|-----------|-------|
| `TestBuildSchemaReportParquet` | Happy path from Parquet; native type mapping for int, float, string, bool; nullable from schema; column name read from Parquet. |
| `TestBuildSchemaReportParquetFallback` | No staging_dir → CSV; staging_dir but .parquet missing → CSV; upload_as_csv override → CSV. |
| `TestBuildSchemaReportSampling` | Unique and missing computed from Parquet row-group sample; example from first non-null value. |
| `TestBuildSchemaReportDisambiguationParquet` | Column name collision across Parquet files with `.parquet` filename prefix. |

### 7.2 Test conventions

- Use `tmp_path` for temporary Parquet files.
- Write small Parquet files programmatically with `pyarrow.Table.from_pydict()`
  and `pyarrow.parquet.write_table()`.
- Test the type-mapping function independently of the sampling logic.
- Existing CSV-based tests (`TestBuildSchemaReport` from parent spec) SHALL
  continue to pass unchanged.

### 7.3 Coverage target

The new Parquet-reading code paths in `build_schema_report` SHALL have
unit-test coverage of at least 90 % (branch coverage).

---

## 8. File Checklist

### 8.1 Files to modify

| File | Change |
|------|--------|
| `src/sofer/repo_compliance.py` | Add `staging_dir` parameter to `build_schema_report`; add Parquet-reading logic; add type-mapping function. |
| `src/sofer/uploader.py` | Move conversion before compliance call; pass `staging_dir=tmpdir` to `build_schema_report`. |
| `tests/test_repo_compliance.py` | Add Parquet-based schema tests. |

### 8.2 Files unchanged

| File | Reason |
|------|--------|
| `src/sofer/model.py` | `FileEntry.upload_as_csv` is consumed by uploader, not by compliance. |
| `src/sofer/codebook.py` | `infer_column_type` unchanged — still used by CSV-fallback path. |
| `src/sofer/cli.py` | No CLI changes for compliance. |
| `pyproject.toml` | `pyarrow` dependency already declared by `parquet-conversion` spec. |
