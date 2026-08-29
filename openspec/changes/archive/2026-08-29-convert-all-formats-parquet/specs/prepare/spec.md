# Delta for prepare

## MODIFIED Requirements

### Requirement: CSV→Parquet conversion preserved in output dir (PRP-02)

`prepare` SHALL convert every eligible entry among `.csv/.tsv/.xlsx/.jsonl` to Parquet and write the result into the output directory at the **normalized** remote-relative path (extension replaced with `.parquet`; for `.xlsx` with N sheets, N files at `stem__{sanitized}.parquet`). Eligibility: NOT `recursive`, suffix in convertible set, `convert_to_parquet != false` (alias `upload_as_csv` honored for csv with deprecation warning), `local` exists. `.parquet` entries SHALL be passthrough. `prepare._check_local_overwrite` and `_validate_case_fold_collisions` (via `_mirror`) MUST scan all convertible suffixes on normalized keys (`normalize_parquet_remote(...).lower()`), not just `.csv`. Conversion MUST use `config.PARQUET_COMPRESSION` and `config.PARQUET_ROW_GROUP_SIZE`; no hardcoded compression/row-group literals.

(Previously: only `.csv` eligible; `.tsv/.xlsx/.jsonl` staged as-is via `copy_to_mirror`; overwrite/collision gates scanned only `.csv`.)

#### Scenario: Converted parquets mirror normalized remote layout
- GIVEN entries `remote="data/PROV/train.csv"` and `remote="data/DPTO/train.TSV"`
- WHEN `prepare` completes
- THEN `data/prov/train.parquet` and `data/dpto/train.parquet` SHALL exist in output

#### Scenario: XLSX multi-sheet expanded
- GIVEN `remote="Report.XLSX"` with sheets `Ventas`, `Costos`
- WHEN `prepare` completes
- THEN `report__ventas.parquet` and `report__costos.parquet` SHALL exist (flat `__`)

#### Scenario: convert_to_parquet=false keeps original suffix
- GIVEN `[[file]] remote="raw.xlsx" convert_to_parquet=false`
- WHEN `prepare` completes
- THEN no Parquet SHALL be generated for that entry and `raw.xlsx` SHALL be staged at its declared remote

#### Scenario: upload_as_csv alias still honored for csv
- GIVEN `[[file]] remote="raw.csv" upload_as_csv=true`
- WHEN `prepare` completes
- THEN deprecation warning SHALL be printed, no Parquet SHALL be generated, and `raw.csv` SHALL be staged

#### Scenario: Conversion failure falls back to original for any format
- GIVEN `bad.tsv` that fails to parse
- WHEN `prepare` runs the conversion loop
- THEN warning SHALL be printed naming `bad.tsv` and original `bad.tsv` SHALL be staged at its remote

#### Scenario: Overwrite protection covers all convertible suffixes normalized
- GIVEN `data/prov/train.parquet` already exists in output from prior run and a `train.tsv` entry maps to same normalized key
- WHEN `sofer prepare` executes without `--force`
- THEN error naming the existing `data/prov/train.parquet` SHALL be printed and exit SHALL be 1

#### Scenario: Case-fold collision on normalized remotes refused before write
- GIVEN entries `Data/Prov/Train.CSV` and `data/prov/train.tsv` normalizing to same `data/prov/train.parquet`
- WHEN `prepare` validates
- THEN hard error naming both remotes SHALL be emitted and exit SHALL be 1 before any staging write

### Requirement: Cross-file schema and parity for all formats (PRP-02a)

`prepare` SHALL run cross-file schema assertion and per-format parity on all converted parquets (`.csv/.tsv/.xlsx/.jsonl`). CSV/TSV parity checks row/col/name and soft value-altered warning; XLSX checks row/col/name per sheet; JSONL checks key-union vs column names and row count. Thresholds for sample sizes and shard warnings SHALL be read from `config.py` (`SCHEMA_SAMPLE_SIZE`, `PARQUET_SHARD_WARNING_MB`).

(Previously: cross-file schema and parity covered only converted `.csv`.)

#### Scenario: Cross-file grouping includes tsv
- GIVEN `a.csv` and `b.tsv` with disjoint column sets now both converted
- WHEN cross-file schema assertion runs
- THEN grouping SHALL include both parquets without spurious collision from hardcoded csv-only filter

## ADDED Requirements

### Requirement: Normalization precedes overwrite and collision gates (PRP-02b)

The system MUST normalize every convertible remote via `normalize_parquet_remote` BEFORE checking `_check_local_overwrite` and `_validate_case_fold_collisions`. Raw `entry.remote` values SHALL NOT be compared directly for convertible files.

#### Scenario: Normalized collision not missed due to accents
- GIVEN remotes `DATA GÖT Año.csv` and `data_got_ano.tsv` both normalizing to `data_got_ano.parquet`
- WHEN validation runs
- THEN collision error SHALL be emitted naming both originals
