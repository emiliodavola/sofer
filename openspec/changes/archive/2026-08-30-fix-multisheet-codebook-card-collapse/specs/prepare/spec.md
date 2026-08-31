# Delta for prepare

## ADDED Requirements

### Requirement: Prepare inherits multisheet codebook N-files (PRP-10)

When `prepare` invokes codebook generation with `--all-files` (via `generate_all(..., output_dir=build_dir)`), it MUST inherit CB-R09's N-files behavior: a multisheet `.xlsx` SHALL produce N codebooks `build/codebooks/<stem>__<sanitized>.md` (single sheet → `stem.md`), reusing `sanitize_sheet_name`/`seen` dedup identical to Parquet conversion. Staged Parquets already per-sheet; codebooks SHALL mirror them 1:1 (`sheet → stem_sheet.parquet → stem__sheet.md`). `prepare` SHALL NOT reimplement sanitization; it SHALL delegate to `codebook.generate_all`.

#### Scenario: PRP-10.01 multisheet XLSX yields N Parquets and N codebooks in build

- GIVEN `DATA_GOT_ALL.xlsx` with sheets `aristas` and `nodos`
- WHEN `sofer prepare --all-files` completes
- THEN `build/` SHALL contain `data_got_all_aristas.parquet` and `data_got_all_nodos.parquet`
- AND `build/codebooks/DATA_GOT_ALL__aristas.md` and `build/codebooks/DATA_GOT_ALL__nodos.md` SHALL both exist (or normalized `__` stems)

#### Scenario: PRP-10.02 single-sheet unchanged

- GIVEN `dataset.xlsx` with one sheet
- WHEN `prepare --all-files` completes
- THEN exactly one `build/<stem>.parquet` and one `build/codebooks/<stem>.md` SHALL exist

#### Scenario: PRP-10.03 no extra conversion logic in prepare

- GIVEN a multisheet XLSX
- WHEN `prepare` stages codebooks
- THEN no XLSX sheet iteration SHALL exist in `prepare.py` beyond the `generate_all` delegation (provenance stays in `codebook.py`/`_converters.py`)
