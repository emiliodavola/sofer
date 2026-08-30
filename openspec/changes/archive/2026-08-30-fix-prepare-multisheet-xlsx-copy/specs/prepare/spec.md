# Delta for prepare

## MODIFIED Requirements

### Requirement: CSV→Parquet conversion preserved in output dir (PRP-02) — Universal (Modified 2026-08-30, fix-prepare-multisheet-xlsx-copy)

`prepare` SHALL convert every eligible `.csv/.tsv/.xlsx/.jsonl` entry to Parquet at the normalized remote (`normalize_parquet_remote(parquet_remote_for(remote))`). Eligible: NOT `recursive`, suffix in convertible set, `convert_to_parquet != false` (`upload_as_csv` alias for csv with deprecation warning), `local` exists; `.parquet` SHALL be passthrough. Converted keys use normalized form: `__+` → `_` collapses `stem__sheet` → `stem_sheet`, so multisheet XLSX with N sheets SHALL produce N files at `stem_{sanitized}.parquet` (single `_`). Guards (`is_converted` staging check, `_check_local_overwrite`, `_validate_case_fold_collisions`, `_assert_cross_file_schema`, `expanded_planned_remotes` fallback) SHALL match **both** `__` and `_` sheet suffixes. When any XLSX sheet converts, original `.xlsx` SHALL NOT be staged; `build/` SHALL contain only normalized `.parquet` per sheet. Single-sheet XLSX SHALL produce single `stem.parquet` (key == `norm_key`). Overwrite/collision gates MUST scan normalized keys. Conversion MUST use `config.PARQUET_COMPRESSION`/`PARQUET_ROW_GROUP_SIZE`; no hardcoded literals.

(Previously: guards checked `__` only; normalized keys collapse to `_`, so `prepare.py:848/603/364` missed multisheet sheets and leaked the workbook into `build/`.)

#### Scenario: Converted parquets mirror normalized remote layout

- GIVEN `data/PROV/train.csv` and `data/DPTO/train.TSV`
- WHEN `prepare` completes
- THEN `data/prov/train.parquet` and `data/dpto/train.parquet` SHALL exist

#### Scenario: XLSX multi-sheet expanded (normalized)

- GIVEN `Report.XLSX` with sheets `Ventas`, `Costos`
- WHEN `prepare` completes
- THEN `report_ventas.parquet` and `report_costos.parquet` SHALL exist (single `_`)
- AND `report.xlsx` SHALL NOT exist in output

#### Scenario: Multisheet stages only parquet — no source leak

- GIVEN `DATA_GOT_ALL.xlsx` with sheets `aristas`/`nodos`
- WHEN `sofer prepare` into clean `build/` completes
- THEN `build/` SHALL contain `data_got_all_aristas.parquet` and `data_got_all_nodos.parquet`
- AND `build/` SHALL contain no `*.xlsx`

#### Scenario: Single-sheet XLSX unchanged

- GIVEN `dataset.xlsx` with one sheet
- WHEN `prepare` completes
- THEN exactly one `dataset.parquet` SHALL exist
- AND no `dataset_*.parquet` sheet file SHALL exist

#### Scenario: convert_to_parquet=false keeps original suffix

- GIVEN `raw.xlsx` with `convert_to_parquet=false`
- WHEN `prepare` completes
- THEN no Parquet SHALL be generated and `raw.xlsx` SHALL be staged

#### Scenario: upload_as_csv alias still honored for csv

- GIVEN `raw.csv` with `upload_as_csv=true`
- WHEN `prepare` completes
- THEN deprecation warning SHALL be printed and `raw.csv` SHALL be staged

#### Scenario: Conversion failure falls back to original for any format

- GIVEN `bad.tsv` that fails to parse
- WHEN `prepare` runs the conversion loop
- THEN warning naming `bad.tsv` SHALL be printed and original `bad.tsv` SHALL be staged

#### Scenario: Overwrite protection covers all suffixes normalized (XLSX fallback)

- GIVEN `data/prov/train.parquet` exists and `train.tsv` maps to same normalized key
- WHEN `sofer prepare` without `--force` runs
- THEN error naming `data/prov/train.parquet` SHALL be printed and exit SHALL be 1
- AND GIVEN `report_ventas.parquet` (single `_`) exists from prior run
- WHEN new `Report.XLSX` covering that sheet runs without `--force`
- THEN guard SHALL detect via `_` fallback glob and refuse with exit 1; with `--force` it SHALL overwrite

#### Scenario: Case-fold collision on normalized remotes refused before write

- GIVEN `Data/Prov/Train.CSV` and `data/prov/train.tsv` both normalize to `data/prov/train.parquet`
- WHEN `prepare` validates
- THEN error naming both remotes SHALL be emitted and exit SHALL be 1 before write

#### Scenario: Cross-file schema grouping handles both underscore forms

- GIVEN converted keys include `data_got_all_aristas.parquet` (single `_`)
- WHEN `_assert_cross_file_schema` groups sheets for `DATA_GOT_ALL.xlsx`
- THEN it SHALL match via both `stem__*` and `stem_*` (excluding `norm_key`) so grouping works regardless of normalization

#### Scenario: Legacy CSV scenarios preserved

- GIVEN `data/PROV/train.csv` and `data/DPTO/train.csv`
- WHEN `prepare` completes
- THEN `data/prov/train.parquet` SHALL exist (normalized lowercase)

#### Scenario: upload_as_csv entries keep their CSV (legacy)

- GIVEN entry with `upload_as_csv=true`
- WHEN `prepare` completes
- THEN no Parquet SHALL be generated and original CSV SHALL be staged

#### Scenario: Conversion failure falls back to CSV (legacy)

- GIVEN CSV entry that fails to parse
- WHEN conversion loop runs
- THEN warning SHALL be printed and original CSV SHALL be staged
