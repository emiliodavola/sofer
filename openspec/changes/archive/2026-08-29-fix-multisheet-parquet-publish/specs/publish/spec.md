# Delta for publish

## ADDED Requirements

### Requirement: Expanded planned remotes via mirror scan (PUB-10)

The system MUST provide `expanded_planned_remotes(cfg, keep_csv, staging_dir)` in `_mirror.py`. It SHALL reuse `sanitize_sheet_name`/`normalize_parquet_remote` and SHALL NOT open workbooks. For convertible `.xlsx` (not recursive, `convert_to_parquet` true): if `staging_dir` exists it MUST glob `<dir>/<stem>__*.parquet`; on match it SHALL emit them else single `<stem>.parquet`. If absent it SHALL fallback to `planned_remotes`. Others equal `planned_remotes`. `keep_csv` SHALL remain CSV-only.

#### Scenario: Multi-sheet expands
- GIVEN `report.xlsx` staged as `report__ventas.parquet`, `report__costos.parquet`
- WHEN helper runs
- THEN both `__` remotes present, not `report.parquet`

#### Scenario: Single-sheet stays single
- GIVEN `single.xlsx` staged as `single.parquet`
- WHEN helper runs
- THEN exactly `single.parquet`

#### Scenario: Fallback and invariants
- GIVEN `staging_dir=None`, `recursive=true`
- WHEN helper runs
- THEN `planned_remotes` placeholder; recursive unchanged; no openpyxl

## MODIFIED Requirements

### Requirement: hf target uploads via upload_folder (PUB-01) — Universal

`publish --target hf` SHALL ensure repository exists, run quality gate, and push via single `upload_folder`. The system MUST derive remotes via `expanded_planned_remotes` when staging is resolvable else `planned_remotes`. `_repo_diff_summary`, `_copy_package`, `_check_overwrite_protection`, `_print_split_mapping_validation`/`detect_splits`, and dry-run MUST share the expanded set. `keep_csv` SHALL remain CSV-only.

(Previously: only `_copy_package` globbed; diff/protection/splits hid sheets behind single `stem.parquet`.)

#### Scenario: Diff universal remotes
- GIVEN `DATA/GOT Ano.csv`, `Data/B.tsv`
- WHEN diff runs
- THEN reports `data/got_ano.parquet`, `data/b.parquet`

#### Scenario: Copy stages parquets
- GIVEN `report__ventas.parquet` staged
- WHEN copy stages
- THEN includes it; expanded==staged

#### Scenario: keep_csv CSV-only
- GIVEN `a.csv->parquet`, `b.xlsx->b__s1.parquet`, `--keep-csv`
- WHEN staging
- THEN `a.csv` added; `b.xlsx` not

#### Scenario: Full hf publish
- GIVEN prepared output valid
- WHEN `publish dataset.toml` runs
- THEN repo ensured, diff, upload_folder once, split report, exit 0

#### Scenario: Quality gate blocks
- GIVEN quality fail
- WHEN publish runs
- THEN report, no upload, exit 1

#### Scenario: upload failure
- GIVEN upload_folder raises
- WHEN publish runs
- THEN error, exit 1

#### Scenario: Missing files
- GIVEN absent file
- WHEN staging
- THEN NOT FOUND, not included

#### Scenario: Multi-sheet diff and per-sheet protection
- GIVEN `report.xlsx` 2 sheets, Hub has `report__ventas.parquet`
- WHEN diff/protection
- THEN diff lists 2; only `ventas` protected w/o --force

#### Scenario: Split counts expanded
- GIVEN `report.xlsx` 2 sheets
- WHEN detect_splits
- THEN count 2

### Requirement: Publish delegation invariant (PUB-09)

`expanded_planned_remotes`, diff, and copy MUST share ONE eligibility: `{.csv,.tsv,.xlsx,.jsonl}`+`convert!=false`+NOT `recursive` → normalized `parquet_remote_for` (xlsx→`__` set) else passthrough. Collisions MUST error identically. Diff vs staged divergence SHALL be a bug. `planned_remotes` is logical; expanded is ground truth.

(Previously: invariant only for `planned_remotes`; expansion diverged.)

#### Scenario: Diff and copy agree
- GIVEN mixed csv/tsv/xlsx/jsonl/parquet
- WHEN diff and copy compute
- THEN sets identical

#### Scenario: Collision error
- GIVEN `data/report.xlsx` vs `DATA/REPORT.XLSX`
- WHEN dry-run validates
- THEN error both, no upload
