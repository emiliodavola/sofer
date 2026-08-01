# Tasks: Parquet as Default Upload Format

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~385 (1 dep, 4 source files, 2 test files) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | auto-chain |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

## Phase 1: Model + Dependencies

- [x] 1.1 Add `pyarrow>=14.0` to `pyproject.toml` `dependencies`
- [x] 1.2 Add `upload_as_csv: bool = False` field to `FileEntry` dataclass in `model.py`
- [x] 1.3 Read `upload_as_csv` in `DatasetConfig.from_toml()` via `.get("upload_as_csv", False)`

## Phase 2: Conversion Engine

- [x] 2.1 Add `_convert_to_parquet(csv_path, staging_dir) -> Path | None` to `uploader.py` — reads CSV via `pyarrow.csv.read_csv`, writes Parquet via `pyarrow.parquet.write_table` with `compression='zstd'`, catches exceptions, prints warning on failure
- [x] 2.2 Add conversion loop in `upload()` before compliance: iterate `cfg.files`, convert CSV entries unless `upload_as_csv`, skip non-CSV and existing `.parquet`
- [x] 2.3 Update upload loop: point converted entries at staged `.parquet` file, replace remote `.csv` with `.parquet` extension
- [x] 2.4 Add `keep_csv: bool = False` param to `upload()` — when True and conversion succeeded, upload original CSV alongside Parquet

## Phase 3: Parquet-Aware Schema

- [x] 3.1 Add `staging_dir: Path | None = None` param to `build_schema_report()` in `repo_compliance.py`
- [x] 3.2 Add Parquet physical-type-to-dtype mapping: INT/FLOAT/DOUBLE/DECIMAL → `"numeric"`, BOOLEAN/STRING/BYTE_ARRAY/ENUM/TIMESTAMP/DATE/TIME → `"categorical/text"`, LIST/MAP/STRUCT → `"unknown"`
- [x] 3.3 Add Parquet-reading path: when `staging_dir` set and `.parquet` exists for a CSV entry (not `upload_as_csv`), read schema via `pq.ParquetFile.schema_arrow` and metadata; compute `unique`/`missing` from first row-group sample; use `.parquet` extension in disambiguation prefix
- [x] 3.4 Update `upload()` to pass `staging_dir=tmpdir` to `build_schema_report` (after conversion, before Dataset Card generation)

## Phase 4: CLI Wiring

- [x] 4.1 Add `--keep-csv` flag (`action="store_true"`) to `upload` subparser in `cli.py`
- [x] 4.2 Pass `keep_csv=args.keep_csv` from `_cmd_upload` to `run_upload(cfg, keep_csv=...)`

## Phase 5: Tests

- [x] 5.1 Create `tests/test_parquet_conversion.py` with `TestConvertToParquet` (round-trip, row count, column names), `TestConvertToParquetFallback` (corrupt CSV → `None`, warning), `TestConversionPipeline` (calls convert for CSV, skips for `upload_as_csv=True` and `.parquet`), `TestKeepCsv` (both files uploaded when True), `TestUploadFileSelection` (staging path used, remote extension changed), `TestFileEntryModel` (default `False`, TOML parse)
- [x] 5.2 Add to `tests/test_repo_compliance.py`: `TestBuildSchemaReportParquet` (native types from Parquet), `TestBuildSchemaReportParquetFallback` (no staging dir, missing Parquet, `upload_as_csv` override → CSV fallback), `TestBuildSchemaReportSampling` (unique/missing from row-group sample), `TestBuildSchemaReportDisambiguationParquet` (`.parquet` prefix in disambiguation)

## Phase 6: Verification

- [x] 6.1 Run `uv run pytest` — all tests pass
- [x] 6.2 Run `ruff check src/ tests/` — no lint errors
- [x] 6.3 Run `mypy src/` — no type errors
