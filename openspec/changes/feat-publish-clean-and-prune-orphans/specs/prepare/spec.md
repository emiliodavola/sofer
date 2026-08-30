# Delta for prepare

## ADDED Requirements

### Requirement: Orphan pruning on force prepare (PRP-09)

`prepare(force=True)` MUST prune orphan files under `output_dir` after staging (converted parquets, codebooks). The allowlist MUST be `allowed_output_remotes = expanded_planned_remotes(cfg, keep_csv, output_dir) ∪ {README.md, LICENSE, codebook.md, codebooks/**} ∪ keep_csv CSV remotes`. `expanded_planned_remotes` MUST reuse `sanitize_sheet_name`/`normalize_parquet_remote` with dual `__`/`_` guard identical to `prepare.py:615-622`, so single-underscore sheets (e.g., `DATA_GOT_ALL.xlsx` → `data_got_all_aristas.parquet`, `data_got_all_nodos.parquet`) are recognized as owned, not orphan. Pruning MUST be idempotent and MUST NOT run when `force` is false.

#### Scenario: Single-underscore orphan deleted on force

- GIVEN `build/` contains `data_got_all_aristas.parquet` but TOML no longer declares that sheet
- WHEN `prepare(force=True)` completes
- THEN that orphan file SHALL be removed and only `expanded_planned_remotes` members SHALL remain

#### Scenario: Stale file from removed TOML entry pruned

- GIVEN a prior `[[file]]` entry was removed leaving `old.parquet` in `build/`
- WHEN `prepare(force=True)` completes
- THEN `old.parquet` SHALL be removed

#### Scenario: Compliance auto-generated files retained

- GIVEN `build/` contains `README.md`, `LICENSE`, `codebook.md`, `codebooks/a.md`
- WHEN `prepare(force=True)` completes
- THEN all compliance files SHALL remain (not treated as orphans)

#### Scenario: keep_csv originals retained

- GIVEN `keep_csv=true` and `build/` contains `data/foo.csv` alongside `data/foo.parquet`
- WHEN `prepare(force=True)` completes
- THEN `data/foo.csv` SHALL remain

#### Scenario: Idempotent second force run

- GIVEN `prepare(force=True)` already pruned orphans
- WHEN `prepare(force=True)` runs again without config change
- THEN no further files SHALL be deleted and exit SHALL be 0

#### Scenario: Non-force run does not prune

- GIVEN an orphan `stale.parquet` exists in `build/`
- WHEN `prepare` runs without `--force`
- THEN `stale.parquet` SHALL remain and orphan scan SHALL not execute
