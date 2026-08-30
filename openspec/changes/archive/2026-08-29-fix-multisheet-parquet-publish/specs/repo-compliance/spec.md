# Delta for repo-compliance

## MODIFIED Requirements

### Requirement: Card data_files universal normalized remotes (RC-Universal-Card)

`build_dataset_card` MUST list `configs.data_files` and `Dataset Structure` via `expanded_planned_remotes` when staging directory is available, otherwise via `planned_remotes` fallback. TSV/XLSX/JSONL SHALL appear as normalized `.parquet` remotes; `report.xlsx` with N sheets SHALL appear as N `stem__sheet.parquet` entries. No local-disk paths SHALL leak. `num_examples` row-count dict SHALL remain keyed by verbatim `entry.remote`; `configs.data_files` SHALL be keyed by normalized remotes.

(Previously: `build_dataset_card` called `planned_remotes` directly, emitting single `report.parquet` phantom for multi-sheet xlsx.)

#### Scenario: tsv as parquet
- GIVEN `data/x.tsv`
- WHEN card generated
- THEN lists `data/x.parquet` not `x.tsv`

#### Scenario: xlsx N entries
- GIVEN `report.xlsx` staged 2 sheets
- WHEN card generated
- THEN data_files has both `__` remotes

#### Scenario: Structure expanded
- GIVEN `report.xlsx` 2 sheets
- WHEN card with staging
- THEN Structure lists both, no local path

#### Scenario: Fallback before prepare
- GIVEN `report.xlsx`, `staging=None`
- WHEN card generated
- THEN lists `report.parquet`

#### Scenario: configs==Structure
- GIVEN `report.xlsx` 2 sheets
- WHEN card with staging
- THEN data_files equals Structure
