# Delta for scan

## MODIFIED Requirements

### Requirement: Source Layout and Move-to-Raw (SCN-07)

System MUST enforce `raw/` (tracked) → `cache/` (`OUTPUT_DIR`, gitignored) → `build/` (gitignored) with diagram `raw/DPTO.csv→cache/DPTO.csv→build/*.parquet`. `scan` MUST create `raw/` (`mkdir -p`) if missing, then MOVE supported files (`.csv`, `.tsv`, `.xlsx`, `.jsonl`, `.parquet`) not already under `raw/`/`cache/`/`EXCLUSIONS` into `raw/` preserving `relative_to(base_dir)` tree via `shutil.move` (`dest = raw_dir / rel`, lazy `mkdir -p` parent), then copy `raw/`→`cache/` via `flatten_first_level` using `shutil.copy2`. System MUST check raw-dest collisions before any move and fail atomically; MUST honor `--dry-run` (preview only), `--force` (skip prompt), else `[y/N]` abort with no partial moves on `N`.

(Previously: copy-only to cache via flatten_first_level, sources untouched, no raw MOVE.)

#### Scenario: Move preserves tree and removes source

- GIVEN loose `a.csv` at `base_dir/` and `sub/b.xlsx` at `base_dir/sub/b.xlsx`
- WHEN `sofer scan --force` executes
- THEN `raw/a.csv` and `raw/sub/b.xlsx` SHALL exist, originals SHALL NOT, and `cache/` copies SHALL exist

#### Scenario: Supported extensions only

- GIVEN `a.csv`, `b.tsv`, `c.xlsx`, `d.jsonl`, `e.parquet`, `f.txt` loose
- WHEN `scan` discovers
- THEN the 5 supported SHALL be moved, `f.txt` SHALL remain untouched

#### Scenario: Excluded dirs never moved

- GIVEN `.venv/lib/data.csv` and `node_modules/pkg/data.csv`
- WHEN `scan` executes
- THEN neither SHALL be moved nor appear in `raw/`

#### Scenario: Dry-run previews without mutation

- GIVEN loose `a.csv` and `sub/b.parquet`
- WHEN `sofer scan --dry-run` executes
- THEN output SHALL list `-> raw/a.csv` and `-> raw/sub/b.parquet`
- AND no file SHALL be moved, no `cache/` write, TOML unchanged

#### Scenario: Collision fails before any move

- GIVEN `raw/a.csv` exists and loose `a.csv` maps to `raw/a.csv`
- WHEN `scan` executes
- THEN error SHALL name both source and dest, exit 1, no file moved, TOML unchanged

#### Scenario: Interactive abort is atomic

- GIVEN 2 loose files and prompt answered `N`
- WHEN `sofer scan` (no `--force`) executes
- THEN no file SHALL be moved and TOML SHALL be unchanged

#### Scenario: Idempotency when already under raw

- GIVEN all files already under `raw/` and no loose files
- WHEN `scan --force` runs twice with no FS change
- THEN second run SHALL produce byte-identical TOML and move 0 files

#### Scenario: Docs show diagram

- GIVEN user views Directory layout
- WHEN layout rendered
- THEN `raw/→cache/→build/` and `raw/DPTO.csv→cache/DPTO.csv` SHALL appear
