# Delta for repo-compliance

## MODIFIED Requirements

### Requirement: Schema report via staged Parquet for all convertible formats (RC-Universal)

`build_schema_report(cfg, staging_dir)` MUST include columns from every convertible entry (`.csv/.tsv/.xlsx/.jsonl`) that is not `recursive` and not excluded by `include_in_schema=false`, reading staged Parquet when present at normalized key `staging_dir / normalize_parquet_remote(parquet_remote_for(entry.remote))` else falling back to original file. For `.xlsx`, each sheet-produced Parquet contributes columns with `origin` set to its normalized `stem__sheet.parquet` key. `ColumnSchema.dtype/nullable/unique/missing` semantics unchanged; sample size governed by `config.SCHEMA_SAMPLE_SIZE`. Types for XLSX/JSONL-derived Parquets map via existing Parquet physical-type → `dtype` table.

(Previously: only `.csv` remotes contributed; `.tsv/.xlsx/.jsonl` skipped via `if not remote.endswith(".csv"): continue`; parquet branch keyed by `staging_dir / <stem>.parquet` ignoring normalized remotes and multi-sheet.)

#### Scenario: TSV contributes via its Parquet
- GIVEN `data/b.tsv` converted to `data/b.parquet` in staging
- WHEN `build_schema_report(cfg, staging_dir=...)` runs
- THEN returned list SHALL contain columns from `b.parquet` with origin `data/b.parquet`

#### Scenario: XLSX multi-sheet contributes per-sheet
- GIVEN `report.xlsx` producing `report__ventas.parquet` and `report__costos.parquet`
- WHEN schema report runs
- THEN columns from both sheets SHALL appear with distinct origins `report__ventas.parquet` and `report__costos.parquet`

#### Scenario: JSONL contributes via staged Parquet
- GIVEN `data/c.jsonl` converted to `data/c.parquet`
- WHEN schema report runs
- THEN columns SHALL be read from `data/c.parquet` (key-union derived)

#### Scenario: Fallback to original when Parquet missing or opt-out
- GIVEN entry `raw.xlsx` with `convert_to_parquet=false` or missing staged Parquet
- WHEN schema report runs
- THEN columns SHALL be read via `_read_file` fallback (CSV/TSV/XLSX/JSONL readers) and origin SHALL be declared remote

#### Scenario: Same-stem nested remotes resolve independently via normalized keys
- GIVEN remotes `survey.csv` and `data/survey.tsv` each with distinct staged Parquets
- WHEN schema report builds
- THEN each SHALL resolve to its own normalized Parquet (`survey.parquet` vs `data/survey.parquet`) without cross-contamination

#### Scenario: Missing staged Parquet warns once then falls back
- GIVEN eligible `a.tsv` whose `a.parquet` is absent under normalized key
- WHEN schema report builds
- THEN exactly one `[!]` warning naming `a.parquet` SHALL be emitted and columns SHALL come from TSV fallback

## ADDED Requirements

### Requirement: Card data_files reflect universal normalized remotes (RC-Universal-Card)

`build_dataset_card` MUST list `configs.data_files` via `_mirror.planned_remotes` so TSV/XLSX/JSONL appear as their normalized `.parquet` remotes (and `report.xlsx` as N entries). `Dataset Structure` section MUST list only normalized repo-relative delivered paths. No local-disk paths SHALL leak. `num_examples` (row-count dict) MUST key by verbatim `entry.remote` for original counts but `configs.data_files` MUST key by normalized parquet remotes; cross-link not required.

#### Scenario: Card lists converted tsv as parquet
- GIVEN `data/x.tsv` without opt-out
- WHEN card is generated
- THEN `configs.data_files` SHALL list `data/x.parquet` (normalized) and SHALL NOT list `data/x.tsv`

#### Scenario: Card lists xlsx as N parquet entries
- GIVEN `report.xlsx` with 2 sheets
- WHEN card is generated
- THEN `configs.data_files` SHALL contain `report__ventas.parquet` and `report__costos.parquet`
