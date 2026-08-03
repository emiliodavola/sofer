# Proposal: Parquet as Default Upload Format

## Intent

CSV is the default upload format today — but Parquet is the standard for tabular data on Hugging Face Hub (smaller, typed, faster). This change makes Parquet the automatic upload format while keeping CSV as an explicit opt-in per file. Reduces storage, preserves column types, and aligns with Hub conventions.

## Scope

### In Scope
- Automatic CSV → Parquet conversion before upload (via pyarrow)
- `--keep-csv` flag: original CSV stays on disk, only Parquet uploaded
- `upload_as_csv = true` per `[[file]]` entry to skip conversion
- Existing `.parquet` files upload directly, no conversion
- `build_schema_report` reads from converted Parquet (more accurate types)
- Graceful fallback: conversion failure → upload as CSV + printed warning
- Document pyarrow type-conversion limitations

### Out of Scope
- Partitioned / multi-file Parquet datasets (single-file P0)
- Custom compression selection (pyarrow default: zstd)
- Reverse conversion (Parquet → CSV on upload)

## Capabilities

### New Capabilities
- `parquet-conversion`: Automatic CSV-to-Parquet conversion in staging, before upload. Covers conversion, staging, type preservation, encoding handling, error fallback.

### Modified Capabilities
- `repo-compliance`: `build_schema_report` now reads from the converted Parquet file (when available) instead of the raw CSV. Schema is generated after conversion, not before.

## Approach

1. **Dependency**: `pyarrow` (mandatory, ~40 MB).
2. **FileEntry** gains `upload_as_csv: bool = False` in `model.py`; TOML parser reads `upload_as_csv` per `[[file]]`.
3. **`uploader.upload()` pipeline**: after compliance generation and before the upload loop, iterate files. For each CSV **not** marked `upload_as_csv`: read via `pyarrow.csv.read_csv()`, write via `pyarrow.parquet.write_table()` into the staging tempdir. Point the upload at the `.parquet` file instead of the original CSV.
4. **`build_schema_report`** reads from the staged Parquet file (available in tempdir) — `pyarrow.parquet.read_schema()` for column names and dtypes, row count from metadata.
5. **Conversion failure**: catch `pyarrow.ArrowException`, print warning, upload as CSV (original fallback).
6. **`--keep-csv`**: CLI flag that stages the original CSV alongside the Parquet (uploaded as a separate file). Default: CSV not uploaded.
7. **`cli.py`**: `upload` subparser gains `--keep-csv` flag passed to `upload()`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `pyproject.toml` | Modified | Add `pyarrow` dependency |
| `src/sofer/model.py` | Modified | Add `upload_as_csv` to `FileEntry`; TOML parsing |
| `src/sofer/uploader.py` | Modified | Conversion loop in `upload()` before file upload |
| `src/sofer/cli.py` | Modified | Add `--keep-csv` to upload subparser |
| `src/sofer/repo_compliance.py` | Modified | `build_schema_report` reads Parquet when available |
| `openspec/specs/repo-compliance/spec.md` | Modified | Delta spec for schema-report behavior change |
| `tests/` | New/Modified | Tests for conversion, fallback, type fidelity |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| pyarrow type-conversion gaps | Medium | Document limitations; fall back to CSV with warning |
| ~40 MB install size | High | Accept tradeoff — pyarrow is the standard Parquet library |
| `build_schema_report` depends on Parquet | Low | Schema report runs after conversion; tempdir has the staged file |

## Rollback Plan

Remove `pyarrow` from `pyproject.toml`, revert `upload()` conversion loop, restore `build_schema_report` to read-only CSV. Existing uploaded Parquet repos stay untouched.

## Dependencies

- `pyarrow` ≥ 14.0 (minimum stable with round-trip CSV → Parquet cast support)

## Success Criteria

- [ ] CSV file uploaded as `.parquet` without manual flags
- [ ] `--as-csv` per `[[file]]` skips conversion, uploads raw CSV
- [ ] Existing `.parquet` in `[[file]]` uploads directly without change
- [ ] `--keep-csv` preserves original CSV on disk (not uploaded)
- [ ] Schema report reads column names and row count from Parquet correctly
- [ ] Corrupt CSV triggers warning + CSV upload fallback (no crash)
- [ ] All existing tests pass with `pyproject.toml` updated
