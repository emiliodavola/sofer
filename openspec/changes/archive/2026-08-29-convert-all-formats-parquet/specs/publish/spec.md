# Delta for publish

## MODIFIED Requirements

### Requirement: hf target uploads via upload_folder (PUB-01)

`publish --target hf` SHALL ensure the repository exists, run the quality gate, and push via single `HfApi.upload_folder`. It MUST compute planned remotes by delegating to `_mirror.planned_remotes(cfg, keep_csv)` which SHALL respect normalized remotes (`normalize_parquet_remote`) and `convert_to_parquet` (and deprecated `upload_as_csv` for csv). `_repo_diff_summary` and `_copy_package` MUST delegate to `_mirror.planned_remotes` instead of duplicating gate logic. `keep_csv` SHALL remain CSV-only: only converted `.csv` entries add their original `.csv` alongside `.parquet`; `.tsv/.xlsx/.jsonl` originals SHALL NOT be kept even with `keep_csv=true`.

(Previously: `_repo_diff_summary` and `_copy_package` duplicated the `endswith(".csv")` gate instead of delegating; non-csv formats were passthrough.)

#### Scenario: Diff reflects normalized universal remotes
- GIVEN entries `A.CSV` remoted as `DATA/GÖT Año.csv` and `b.tsv` remoted as `Data/B.tsv`
- WHEN `_repo_diff_summary` runs
- THEN it SHALL delegate to `planned_remotes` and report `data/got_ano.parquet` and `data/b.parquet` as planned uploads

#### Scenario: Copy package stages normalized parquets
- GIVEN a prepared output with `report__ventas.parquet` from `Report.XLSX`
- WHEN `_copy_package` stages for hf upload
- THEN staging SHALL include `report__ventas.parquet` at normalized remote and `_mirror.planned_remotes` output SHALL match staged set

#### Scenario: keep_csv CSV-only semantics preserved
- GIVEN converted `a.csv→a.parquet` and `b.xlsx→b__s1.parquet` with `--keep-csv`
- WHEN hf staging runs
- THEN `a.csv` SHALL be additionally staged; `b.xlsx` SHALL NOT

### Requirement: local target writes a complete package (PUB-02)

`publish --target local` SHALL delegate remote planning to `_mirror.planned_remotes` with normalization and `convert_to_parquet` handling, writing the complete package (normalized parquets, `README.md`, `LICENSE`, codebooks) to `--output` with no network calls. No duplication of gate logic.

(Previously: local path used same duplicated gate.)

#### Scenario: Local output uses normalized universal remotes
- GIVEN `remote="DATA GÖT Año.XLSX"` multi-sheet with `--target local --output ./out/`
- WHEN command executes
- THEN `./out/report__ventas.parquet` (normalized) SHALL exist and no network request SHALL be made

## ADDED Requirements

### Requirement: Publish delegation invariant (PUB-09)

`planned_remotes`, `_repo_diff_summary`, and `_copy_package` MUST share ONE definition of eligibility and normalization: suffix in `{.csv,.tsv,.xlsx,.jsonl}` AND `convert_to_parquet != false` (alias honored for `.csv`) AND NOT `recursive` → normalized `parquet_remote_for` else passthrough via `normalize_parquet_remote` for passthrough remotes as well. Case-fold collisions on normalized keys MUST error identically in `prepare` and `publish` validation. Any divergence between `_repo_diff_summary` and actual staged files SHALL be treated as a bug.

#### Scenario: Diff and copy agree for universal set
- GIVEN mixed `csv/tsv/xlsx/jsonl/parquet` entries
- WHEN diff summary and copy package both compute planned remotes
- THEN the sets SHALL be identical (both via `_mirror.planned_remotes`)

#### Scenario: Collision error surfaces in publish validation
- GIVEN colliding normalized remotes `data/report.xlsx` and `DATA/REPORT.XLSX`
- WHEN `publish --dry-run` validates
- THEN error naming both colliding normalized `.parquet` keys SHALL be emitted and no upload SHALL occur
