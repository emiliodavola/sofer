# Design: Parquet as Default Upload Format

## Technical Approach

Add a conversion stage to the upload pipeline that transforms CSV files to Parquet
(via pyarrow) **before** compliance generation, so the schema report reads native
Parquet types. CSV remains an explicit opt-in via `upload_as_csv` per `[[file]]`
entry. The conversion is best-effort — failures fall back to CSV upload with a
warning.

## Architecture Decisions

### Decision: Conversion before compliance

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Convert after compliance | Schema report reads heuristic CSV types | ❌ Lower quality types in Dataset Card |
| **Convert before compliance** | Schema report reads native Parquet types | ✅ **Chosen** — authoritative dtype metadata |

The repo-compliance delta spec corrected the pipeline order: conversion runs before
`build_schema_report`, so the report reads from Parquet when available. This means
`upload()` orchestrates: repo → **convert** → compliance → upload.

### Decision: Single file per converted CSV

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Partitioned Parquet | Flexible, multi-file | ❌ Over-engineered for P0 |
| **Single `.parquet` file** | Simple, matches input shape | ✅ **Chosen** — one Parquet file per CSV entry |

### Decision: `staging_dir` parameter vs. global state

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Module-level global for staging path | Implicit coupling, hard to test | ❌ |
| **`staging_dir` parameter on `build_schema_report`** | Explicit dependency, unit-testable | ✅ **Chosen** — pure function contract |

### Decision: New test file vs. add to existing

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Add conversion tests to `test_uploader.py` | File doesn't exist yet, mixed concerns | ❌ |
| **Create `tests/test_parquet_conversion.py`** | Separate concern, clear ownership | ✅ **Chosen** — matches spec § 10.1 |

## Data Flow

```
        ┌─────────────────────────────────────────────┐
        │                  upload()                    │
        │                                              │
        │  1. _ensure_repo(cfg)                        │
        │                                              │
        │  2. ┌─ Conversion loop ──────────────┐       │
        │     │  For each CSV where             │       │
        │     │  not upload_as_csv:             │       │
        │     │    _convert_to_parquet()         │       │
        │     │    → .parquet in staging_dir    │       │
        │     └─────────────────────────────────┘       │
        │                                              │
        │  3. ┌─ Compliance ────────────────────┐       │
        │     │  build_schema_report(           │       │
        │     │    cfg, staging_dir=tmpdir)      │       │
        │     │  build_dataset_card(cfg, schema) │       │
        │     │  build_license_file(…)           │       │
        │     └─────────────────────────────────┘       │
        │                                              │
        │  4. Upload README.md + LICENSE                │
        │                                              │
        │  5. ┌─ Upload loop ──────────────────┐       │
        │     │  For each FileEntry:            │       │
        │     │    .parquet from staging_dir    │       │
        │     │    (or original if fallback)    │       │
        │     │    .csv if keep_csv=True        │       │
        │     └─────────────────────────────────┘       │
        │                                              │
        │  6. Cleanup staging_dir                       │
        └─────────────────────────────────────────────┘
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/data_uploader/model.py` | Modify | Add `upload_as_csv: bool = False` to `FileEntry`; read in `from_toml()` |
| `src/data_uploader/uploader.py` | Modify | Add `_convert_to_parquet()`; add conversion loop before compliance; reorder pipeline; wire `keep_csv` |
| `src/data_uploader/repo_compliance.py` | Modify | Add `staging_dir` param to `build_schema_report`; add Parquet-reading path with type mapping |
| `src/data_uploader/cli.py` | Modify | Add `--keep-csv` flag to `upload` subparser; pass to `upload()` |
| `pyproject.toml` | Modify | Add `pyarrow>=14.0` to `dependencies` |
| `tests/test_parquet_conversion.py` | Create | Conversion + keep-csv + pipeline + model tests |
| `tests/test_repo_compliance.py` | Modify | Add Parquet-aware schema tests |

## Interfaces / Contracts

### `_convert_to_parquet` (uploader.py)

```python
def _convert_to_parquet(
    csv_path: Path,
    staging_dir: Path,
) -> Path | None:
```

Returns the Parquet path on success, `None` on failure (warning already printed).

### `build_schema_report` (repo_compliance.py) — new parameter

```python
def build_schema_report(
    cfg: DatasetConfig,
    csv_delimiter: str | None = None,
    csv_encoding: str = "utf-8-sig",
    staging_dir: Path | None = None,          # NEW
) -> list[ColumnSchema]:
```

When `staging_dir` is set and a matching `.parquet` exists for a CSV entry:
read column names and types from `parquet_file.schema_arrow`, physical types
mapped via the table in § 3.2 of the delta spec. Falls back to CSV for
`upload_as_csv=True` or missing Parquet files.

### `upload()` signature change

```python
def upload(cfg: DatasetConfig, keep_csv: bool = False) -> int:
```

### Parquet physical type → `ColumnSchema.dtype` mapping

| Parquet physical type | `dtype` |
|-----------------------|---------|
| `INT{8,16,32,64}`, `FLOAT`, `DOUBLE`, `DECIMAL` | `"numeric"` |
| `BOOLEAN`, `BYTE_ARRAY`, `STRING`, `LARGE_STRING`, `ENUM`, `TIMESTAMP`, `DATE`, `TIME` | `"categorical/text"` |
| `LIST`, `MAP`, `STRUCT` | `"unknown"` |

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `_convert_to_parquet` | Round-trip CSV→Parquet via `tmp_path`; verify row count, column names, types; corrupt CSV returns `None`; warning captured via `capsys` |
| Unit | `build_schema_report` with `staging_dir` | Write Parquet files via `pyarrow.Table.from_pydict` + `write_table`; verify type mapping (int64→numeric, string→categorical/text, bool→categorical/text); verify disambiguation uses `.parquet` prefix |
| Unit | `from_toml` with `upload_as_csv` | TOML with and without `upload_as_csv` field; verify default `False` |
| Pipeline | `upload()` conversion integration | Mock `subprocess.Popen` for HF calls; verify conversion called for CSV entries; verify skipped for `upload_as_csv=True` and existing `.parquet`; verify `keep_csv=True` uploads both paths |

## Migration / Rollout

No migration required. Existing datasets without `upload_as_csv` in their TOML
will now upload Parquet instead of CSV — this is the intended behaviour change.
Existing uploaded repos on HF are untouched.

## Open Questions

- [x] **pyarrow version**: Spec says `>=14.0` (minimum with stable CSV→Parquet
  round-trip). Orchestrator design points say `>=15.0`. **Recommendation**: use
  `>=14.0` as specified in the detailed spec, which has documented reasoning.
- [x] **Test file location**: Orchestrator list mentions `tests/test_uploader.py
  (Modify)`, but the conversion spec § 11.2 specifies `tests/test_parquet_conversion.py`
  (Create). **Recommendation**: follow the spec — create `test_parquet_conversion.py`
  to keep conversion tests separate from upload orchestration tests.
