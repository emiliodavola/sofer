# Spec: parquet-conversion — Automatic CSV-to-Parquet Conversion

- **Change:** parquet-default
- **Capability:** `parquet-conversion` (new)
- **Status:** Draft
- **Author:** sdd-spec executor
- **Date:** 2026-07-30

---

## 1. Overview

The `parquet-conversion` capability transforms CSV files into Apache Parquet format
before uploading to Hugging Face Hub. Parquet is the standard tabular format on the
Hub — it reduces storage, preserves column type metadata, and enables faster
remote reads. CSV becomes an explicit opt-in per file.

Conversion happens **after** compliance generation and **before** upload, operating
on files staged in a temporary directory. The original CSV files on disk are left
untouched (unless `--keep-csv` requests a local copy).

### 1.1 Design constraints

- **pyarrow-only**: All Parquet I/O SHALL use `pyarrow` — the de-facto standard
  Python Parquet library. No other Parquet library SHALL be introduced.
- **No upstream mutation**: Conversion reads the original CSV and writes a new
  Parquet file in the staging directory. Original files on disk are never modified
  or deleted.
- **Graceful degradation**: A conversion failure for a single file SHALL NOT abort
  the entire upload. The file SHALL be uploaded as CSV with a printed warning.
- **Zero-day backward compatibility**: Existing TOML files without `upload_as_csv`
  SHALL behave as before, except that CSV files are now converted before upload
  instead of uploaded raw.

---

## 2. Data Model — `FileEntry` changes

### 2.1 `upload_as_csv` field

The `FileEntry` dataclass in `src/sofer/model.py` SHALL gain an optional
boolean field:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `upload_as_csv` | `bool` | `False` | When `True`, skip Parquet conversion and upload the raw CSV file. |

```python
# model.py — FileEntry
@dataclass
class FileEntry:
    local: Path
    remote: str
    recursive: bool = False
    upload_as_csv: bool = False   # NEW
```

#### 2.1.1 TOML representation

```toml
[[file]]
local = "data/survey.csv"
remote = "survey.csv"

[[file]]
local = "data/raw.csv"
remote = "raw.csv"
upload_as_csv = true       # ← skipped conversion, uploaded as-is
```

#### 2.1.2 Resolution rule

When `upload_as_csv` is absent from the TOML (the common case), it defaults to
`False`, meaning all CSV files are converted to Parquet. This is the P0 default
behaviour.

### 2.2 `from_toml` changes

The `DatasetConfig.from_toml()` classmethod SHALL read `upload_as_csv` from each
`[[file]]` entry with `.get("upload_as_csv", False)`.

---

## 3. Dependency: pyarrow

### 3.1 Version requirement

```
pyarrow >= 14.0
```

Version 14.0 is the minimum that provides stable, round-trip-safe
CSV-to-Parquet type casting (string → large_string, timestamp resolution, etc.).

### 3.2 Size impact

`pyarrow` adds approximately 40 MB to the install footprint. This is accepted as
the standard Parquet library in the Python ecosystem — any alternative would
require shipping a C++ Parquet implementation.

### 3.3 `pyproject.toml` change

```toml
dependencies = [
    ...,
    "pyarrow>=14.0",
]
```

---

## 4. Conversion Logic — `uploader.py`

### 4.1 New module function

A new module-level function SHALL be added to `src/sofer/uploader.py`:

```python
def _convert_to_parquet(
    csv_path: Path,
    staging_dir: Path,
) -> Path | None:
    """Convert a CSV file to Parquet in *staging_dir*.

    Args:
        csv_path:    Path to the original CSV file.
        staging_dir: Temporary directory for the converted file.

    Returns:
        Path to the converted Parquet file on success,
        ``None`` on conversion failure (warning already printed).

    Behaviour:
        1. Read CSV via ``pyarrow.csv.read_csv(csv_path)``.
        2. Write via ``pyarrow.parquet.write_table(table, parquet_path,
           compression='zstd')``.
        3. Return the Parquet path.
        4. On ``pyarrow.ArrowException`` (or any exception), print a
           warning and return ``None``.
    """
```

Key details:

- **Compression**: `zstd` (pyarrow default). No user-facing compression selection
  in P0.
- **CSV reading options**: Use pyarrow's default CSV parser with auto-detect for
  delimiter and encoding. This is a best-effort read — if the CSV has unusual
  formatting, `pyarrow.csv.read_csv` may fail and trigger the fallback path.
- **Output path**: The Parquet file SHALL have the same stem as the original CSV
  with a `.parquet` extension (e.g. `survey.csv` → `survey.parquet`).

### 4.2 Conversion pipeline in `upload()`

The conversion step SHALL be inserted **after** compliance generation (schema
report, dataset card, license) and **before** the upload loop:

```
upload(cfg):
  1. _ensure_repo(cfg)
  2. compliance generation:
     a. schema = build_schema_report(cfg, ...)       # reads ORIGINAL CSVs
     b. card   = build_dataset_card(cfg, schema)
     c. license_text = build_license_file(cfg.license)
  3. Write compliance files to staging dir
  4. Upload compliance files (README.md, LICENSE)
  5. CONVERSION LOOP — iterate cfg.files:             # NEW
     for each FileEntry:
       if entry is .csv AND not upload_as_csv:
         parquet_path = _convert_to_parquet(local_path, staging_dir)
         if parquet_path:
           upload the parquet_path
         else:
           upload the original CSV (fallback)
       else:
         upload the original file as-is
  6. Clean up staging dir
```

#### 4.2.1 Staging directory

The existing `tempfile.mkdtemp()` staging area (`tmpdir`) SHALL be reused.
Converted Parquet files are written alongside the compliance artifacts in the
same temporary directory.

#### 4.2.2 Mixed-format handling

The conversion loop SHALL inspect each `FileEntry`:

| File extension | `upload_as_csv` | Action |
|----------------|-----------------|--------|
| `.csv` | `False` (default) | Convert to `.parquet`; upload Parquet |
| `.csv` | `True` | Skip conversion; upload CSV as-is |
| `.parquet` | irrelevant | Pass through; upload original file |
| any other | irrelevant | Pass through; upload original file |

Extension checks SHALL be case-insensitive.

### 4.3 Upload file selection

When conversion succeeds, the upload loop SHALL point `_hf_upload` at the
Parquet file inside `tmpdir` instead of the original file path. The remote
path SHALL also use the `.parquet` extension (replacing `.csv`).

Example:
- Original: `data/survey.csv` → remote `survey.csv`
- Converted: `tmpdir/survey.parquet` → remote `survey.parquet`

### 4.4 User feedback

The upload loop SHALL print conversion status lines:

```
  🔄  survey.csv  →  survey.parquet
  ↑  survey.parquet  →  survey.parquet
  ✓  survey.parquet
```

On conversion failure:

```
  ⚠  survey.csv: conversion failed — uploading as CSV
  ↑  survey.csv  →  survey.csv
  ✓  survey.csv
```

---

## 5. CLI: `--keep-csv` flag

### 5.1 Behaviour

When `--keep-csv` is passed to the `upload` subcommand, the original CSV file
SHALL be staged alongside the converted Parquet file **and** uploaded to the
Hub as a separate file. This preserves the raw source data for users who want
both formats.

Without `--keep-csv` (default), only the Parquet file is uploaded. The original
CSV stays on the local filesystem but is NOT sent to the Hub.

### 5.2 CLI change (`cli.py`)

```python
# upload subparser
upload_parser.add_argument(
    "--keep-csv",
    action="store_true",
    help="Upload the original CSV alongside the converted Parquet",
)
```

The flag is passed to `upload()`:

```python
def upload(cfg: DatasetConfig, keep_csv: bool = False) -> int:
```

### 5.3 Upload behaviour with `--keep-csv`

When `keep_csv=True` and a CSV was successfully converted:

1. Upload `tmpdir/survey.parquet` → `survey.parquet` (primary file).
2. Upload original `data/survey.csv` → `survey.csv` (secondary file, for
   users who want the raw CSV on the Hub).

When `keep_csv=True` and conversion failed (fallback), the CSV is uploaded once
(the only copy).

When `keep_csv=True` and `upload_as_csv=True`, the flag has no additional effect
(the CSV is already being uploaded).

---

## 6. Existing `.parquet` Passthrough

Files that already have a `.parquet` extension SHALL be uploaded without any
conversion, regardless of `upload_as_csv`. The conversion loop SHALL skip them.

Rationale: Parquet is the target format. Re-converting a Parquet file would be
wasteful and could introduce type drift. The file is uploaded as-is.

---

## 7. Type Preservation and Encoding

### 7.1 pyarrow type inference

`pyarrow.csv.read_csv()` infers column types from the data using its own
type-inference heuristics. In general:

| CSV value pattern | Inferred pyarrow type |
|-------------------|-----------------------|
| Integer only | `int64` |
| Decimal with `.` | `float64` / `double` |
| `true`/`false` | `bool` |
| ISO-8601 date/time | `timestamp[ms]` / `date32` |
| Mixed / text | `large_string` / `string` |
| Empty / null | `null` (promoted by column) |

### 7.2 Known type-conversion gaps

These scenarios MAY produce unexpected types (and trigger the CSV fallback
when they cause `pyarrow.csv.read_csv()` to raise):

- **Comma as decimal separator** (e.g. `3,14`): pyarrow interprets the comma
  as a delimiter rather than a decimal mark. Use a non-comma `csv_delimiter`
  in the TOML, or accept the CSV-fallback path.
- **Mixed-type columns** where >50 % of rows look numeric but some contain
  text: pyarrow may promote the column to `string` or raise.
- **Extremely long string fields** (>2 GB): pyarrow's `large_string` handles
  this, but the CSV parser may have memory limits.

These limitations SHALL be documented in the project README.

### 7.3 Encoding

`pyarrow.csv.read_csv()` defaults to UTF-8. Files using `utf-8-sig` (BOM) or
Latin-1 SHALL be handled automatically — pyarrow detects BOM and falls back
to UTF-8.

If encoding detection fails, the CSV fallback path SHALL be used with a warning.

---

## 8. Scenarios

### Happy path — CSV converted to Parquet

```
GIVEN a DatasetConfig with one [[file]] entry:
      local = "data/survey.csv", remote = "survey.csv"
  AND upload_as_csv is not set (default false)
WHEN upload(cfg) is called
THEN _convert_to_parquet("data/survey.csv", tmpdir) SHALL be called
  AND a file "survey.parquet" SHALL appear in the staging directory
  AND the upload loop SHALL upload tmpdir/survey.parquet → survey.parquet
  AND the original data/survey.csv SHALL NOT be uploaded
  AND the function SHALL return 0
```

### Upload as CSV override

```
GIVEN a DatasetConfig with a [[file]] entry:
      local = "data/raw.csv", remote = "raw.csv", upload_as_csv = true
WHEN upload(cfg) is called
THEN _convert_to_parquet SHALL NOT be called for raw.csv
  AND the upload loop SHALL upload data/raw.csv → raw.csv
```

### Existing .parquet file passthrough

```
GIVEN a DatasetConfig with a [[file]] entry:
      local = "data/existing.parquet", remote = "existing.parquet"
WHEN upload(cfg) is called
THEN _convert_to_parquet SHALL NOT be called
  AND the upload loop SHALL upload data/existing.parquet → existing.parquet
  AND the file SHALL NOT be re-converted
```

### Conversion failure — fallback to CSV

```
GIVEN a CSV file that cannot be parsed by pyarrow
      (e.g. comma-decimal numbers with comma delimiter)
WHEN _convert_to_parquet raises an ArrowException
THEN a warning SHALL be printed: "⚠  <file>: conversion failed — uploading as CSV"
  AND the upload loop SHALL upload the original CSV file
  AND the function SHALL return 0 (non-fatal)
```

### --keep-csv uploads both formats

```
GIVEN a DatasetConfig with one CSV file entry
  AND upload(cfg, keep_csv=True) is called
  AND conversion succeeds
WHEN the upload loop runs
THEN tmpdir/survey.parquet → survey.parquet SHALL be uploaded
  AND data/survey.csv → survey.csv SHALL ALSO be uploaded
```

### Mixed files in config

```
GIVEN a DatasetConfig with three [[file]] entries:
      - survey.csv (default, no upload_as_csv)
      - raw.csv (upload_as_csv = true)
      - geo.parquet (pre-existing Parquet)
WHEN upload(cfg) is called
THEN survey.csv → survey.parquet (converted)
  AND raw.csv → raw.csv (as-is CSV)
  AND geo.parquet → geo.parquet (passthrough)
```

### Non-CSV file passthrough

```
GIVEN a [[file]] entry pointing to a JSON file:
      local = "data/metadata.json", remote = "metadata.json"
WHEN upload(cfg) is called
THEN the file SHALL be uploaded as-is
  AND _convert_to_parquet SHALL NOT be called
```

### No CSV files in config

```
GIVEN a DatasetConfig with no .csv file entries
WHEN upload(cfg) is called
THEN the conversion loop SHALL iterate zero files
  AND no conversion logic SHALL execute
  AND the upload SHALL proceed normally
```

---

## 9. Error Handling Summary

| Failure mode | Behaviour |
|---|---|
| `pyarrow.csv.read_csv()` raises | Catch, print warning, upload CSV |
| `pyarrow.parquet.write_table()` raises | Catch, print warning, upload CSV |
| CSV file not found | Existing check in `upload()` — print NOT FOUND, skip |
| Encoding not detected by pyarrow | Fall back to CSV with warning |
| pyarrow not installed | `ImportError` propagates to caller — hard failure |

All non-fatal conversion errors SHALL be caught and handled per-file. A single
file's conversion failure SHALL NOT prevent other files from being converted or
uploaded.

---

## 10. Testing

### 10.1 New test file

A new file `tests/test_parquet_conversion.py` SHALL be created with the
following test areas:

| Test area | Tests |
|-----------|-------|
| `TestConvertToParquet` | Basic CSV → Parquet; preserves row count; preserves column names; column types match. |
| `TestConvertToParquetFallback` | Unreadable CSV returns `None`; corrupt CSV returns `None`; warning printed to stdout. |
| `TestConversionPipeline` | Conversion called for .csv without `upload_as_csv`; skipped for `upload_as_csv=True`; skipped for existing .parquet. |
| `TestKeepCsv` | `keep_csv=True` uploads both formats; `keep_csv=False` uploads only Parquet. |
| `TestUploadFileSelection` | Upload path points to staging dir for converted files; remote path has `.parquet` extension. |
| `TestFileEntryModel` | `upload_as_csv` defaults to `False` in dataclass; parsed correctly from TOML. |

### 10.2 Test conventions

- Use `tmp_path` for temporary files and staging directories.
- Use real `pyarrow` calls for round-trip tests (no mocking of pyarrow itself).
- Mock `_hf_upload` (or `subprocess.Popen`) in pipeline tests to avoid real Hub calls.
- Test fallback with deliberately malformed CSV content (e.g. binary data).
- No integration tests against the real Hugging Face Hub.

### 10.3 Coverage target

All new code in the conversion module/function SHALL have unit-test coverage of at
least 90 % (branch coverage). The modified `upload()` function SHALL have at least
80 % coverage for the conversion-path branches.

---

## 11. File Checklist

### 11.1 Files to modify

| File | Change |
|------|--------|
| `pyproject.toml` | Add `pyarrow>=14.0` to `dependencies`. |
| `src/sofer/model.py` | Add `upload_as_csv: bool = False` to `FileEntry`; update `from_toml()` to read the field. |
| `src/sofer/uploader.py` | Add `_convert_to_parquet()` function; add conversion loop in `upload()`; update `_hf_upload` call sites; add `keep_csv` parameter. |
| `src/sofer/cli.py` | Add `--keep-csv` argument to upload subparser; pass to `upload()`. |

### 11.2 Files to create

| File | Purpose |
|------|---------|
| `tests/test_parquet_conversion.py` | Full test suite for the new capability. |

### 11.3 Files unchanged

| File | Reason |
|------|--------|
| `src/sofer/repo_compliance.py` | Schema report changes are covered by the `repo-compliance` delta spec (separate file). |
| `src/sofer/codebook.py` | No changes — `infer_column_type` remains CSV-based for downstream users. |

---

## 12. Open Questions / Future Work

- **Custom compression**: P0 uses `zstd` (pyarrow default). Future changes could
  expose `compression` in `[[file]]`.
- **Partitioned Parquet**: P0 is single-file only. Multi-file partitioned datasets
  are deferred.
- **Parquet → CSV reverse**: Not in scope for this change.
- **User-configurable CSV read options**: If pyarrow's auto-detect fails on a
  specific delimiter, the user currently has no way to hint. Could add
  `csv_delimiter` to `[[file]]` in a future iteration.

---

## 13. Universal Parquet Conversion — convert-all-formats-parquet (2026-08-29)

> Archived from `openspec/changes/convert-all-formats-parquet/specs/parquet-conversion/spec.md`.
> Supersedes §4 (CSV-only) with universal dispatch; adds PC-U01..U05. Preserves all other requirements.

### Requirement: Universal File-to-Parquet Conversion (PC-U01)

The system MUST convert every `[[file]]` with suffix `.csv/.tsv/.xlsx/.jsonl` to Parquet unless `convert_to_parquet=false`; `.parquet` MUST be passthrough and `recursive` entries SHALL be skipped. Readers SHALL be:

| Suffix | Reader |
|--------|--------|
| `.csv` | `pyarrow.csv.read_csv` sniffing `config.SNIFF_DELIMITERS` with `config.CSV_ENCODING` |
| `.tsv` | `pyarrow.csv.read_csv` with `delimiter="\t"` (hardcoded) |
| `.xlsx` | `openpyxl` `read_only,data_only`, all `wb.sheetnames` → `pa.Table` per sheet |
| `.jsonl` | `pyarrow.json.read_json` with `json`+`pa.Table.from_pylist` fallback |
| `.parquet` | Passthrough |

Writer MUST use `config.PARQUET_COMPRESSION`/`config.PARQUET_ROW_GROUP_SIZE`, cast null-col to string, warn at `config.PARQUET_SHARD_WARNING_MB`. Per-file failure SHALL warn and stage original.

#### Scenario: CSV sniff
- GIVEN `a.csv` with `;` delimiter
- WHEN dispatcher runs
- THEN `pyarrow.csv` SHALL sniff `;` and write normalized `a.parquet`

#### Scenario: TSV hardcoded tab
- GIVEN `b.tsv` tab-separated
- WHEN dispatcher runs
- THEN reader SHALL use `"\t"` and produce `b.parquet`

#### Scenario: JSONL fallback
- GIVEN `c.jsonl` with sparse keys where `pyarrow.json` raises
- WHEN fallback runs
- THEN `json`+`pa.Table.from_pylist` SHALL produce `c.parquet`

#### Scenario: Parquet passthrough and recursive skip
- GIVEN `d.parquet` and `recursive` dir entry
- WHEN pipeline runs
- THEN both SHALL be staged without conversion

### Requirement: Remote Normalization (PC-U02)

`normalize_parquet_remote(s)` MUST: lowercase, NFKD→ASCII strip, spaces→`_`, `[^a-z0-9_./-]`→`_`, collapse `__+`, preserve lowercased dirs. Case-fold collision on `lower(normalized)` MUST error naming both remotes. Values MUST be read from `config.py`/`[tool.sofer]`, never hardcoded.

#### Scenario: Accented and spaced file
- GIVEN `DATA GÖT Año.XLSX`
- WHEN normalized
- THEN result SHALL be `data_got_ano.parquet`

#### Scenario: Case-fold collision
- GIVEN `data/report.XLSX` and `DATA/report.xlsx` → same `data/report.parquet`
- WHEN `_validate_case_fold_collisions` runs
- THEN error naming both SHALL exit 1 before write

### Requirement: Excel Multi-Sheet Handling (PC-U03)

For `.xlsx`: 1 sheet→`stem.parquet`; N sheets→N files `stem__{sanitized}.parquet` (flat `__`). Sanitizer SHALL reuse normalization rules. Dupes MUST dedup `_{n}`; empty sheet with header SHALL still produce Parquet with 0 rows.

#### Scenario: Single vs multi-sheet
- GIVEN `report.xlsx` with 1 sheet vs 2 sheets `Ventas`,`Costos`
- WHEN converted
- THEN SHALL produce `report.parquet` vs `report__ventas.parquet`+`report__costos.parquet`

#### Scenario: Dedup and empty
- GIVEN sheets `A B`/`A-B` both `a_b` and an empty header-only sheet
- WHEN converted
- THEN SHALL produce `stem__a_b.parquet`+`stem__a_b_2.parquet` and header-only Parquet with `num_rows=0`

### Requirement: Opt-Out Flag (PC-U04)

`FileEntry.convert_to_parquet: bool` SHALL default `true`. `upload_as_csv` SHALL remain deprecated alias ONLY for `.csv`: `upload_as_csv=true` → `convert_to_parquet=false` with deprecation warning. Explicit `convert_to_parquet` takes precedence. Non-csv `upload_as_csv=true` SHALL be ignored with warning.

#### Scenario: Default converts
- GIVEN `[[file]] remote="a.csv"` without flags
- WHEN parsed
- THEN `convert_to_parquet=true` and output `a.parquet` SHALL exist

#### Scenario: Explicit opt-out
- GIVEN `remote="b.xlsx" convert_to_parquet=false`
- WHEN pipeline runs
- THEN no conversion SHALL occur and remote stays `b.xlsx`

#### Scenario: Alias honored for csv
- GIVEN `remote="c.csv" upload_as_csv=true`
- WHEN parsed
- THEN `convert_to_parquet=false` with deprecation warning and `c.csv` staged as-is

### Requirement: Breaking Change Documentation (PC-U05)

This is 0.x minor breaking change. Docs MUST state `tsv/xlsx/jsonl` previously staged as-is, now normalized `.parquet` (xlsx→N). Migration SHALL be `convert_to_parquet=false` per entry. Collision errors MUST name both remotes.

#### Scenario: Migration documented
- GIVEN `report.xlsx` previously expected as `report.xlsx`
- WHEN docs consulted
- THEN migration `convert_to_parquet=false` to keep `report.xlsx` SHALL be described

### Requirement: CSV→Parquet Conversion Pipeline — Universal (Modified, supersedes §4 CSV-only)

System SHALL convert all eligible `.csv/.tsv/.xlsx/.jsonl` via `src/sofer/_converters.py` dispatcher and shared writer, preserving normalized dir structure. Parity: CSV/TSV row/col/name+value-altered; XLSX row/col/name; JSONL key-union+row count. Overwrite/collision SHALL use normalized keys. `keep_csv` SHALL remain CSV-only.

(Previously: only `.csv` converted; others via `copy_to_mirror`; parity CSV-only; gates scanned only `.csv`.)

#### Scenario: Mixed universal conversion
- GIVEN `a.csv`, `b.tsv`, `c.xlsx` (2 sheets), `d.jsonl`, `e.parquet`
- WHEN `prepare` runs
- THEN outputs SHALL be `a.parquet`, `b.parquet`, `c__s1.parquet`, `c__s2.parquet`, `d.parquet`, `e.parquet`

#### Scenario: keep_csv stays CSV-only
- GIVEN `a.csv` and `b.xlsx` with `--keep-csv`
- WHEN publish stages
- THEN `a.csv` SHALL be kept alongside `a.parquet`; `b.xlsx` SHALL NOT
