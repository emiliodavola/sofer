# Scan Specification

## Purpose

Automated data-file discovery, copy, and TOML registration. The `scan` command
eliminates manual `[[file]]` maintenance by discovering supported formats,
copying them to `cache/` (`OUTPUT_DIR`, gitignored), and writing the updated config.

## Requirements

### Requirement: File Discovery (SCN-01)

System MUST discover supported extensions (`.csv`,`.tsv`,`.parquet`,`.xlsx`,`.jsonl`) from config dir. `EXCLUSIONS` (`.git`, `__pycache__`, `.venv`, `node_modules`, `dist`, `build`) MUST be skipped. `cache/` (`OUTPUT_DIR`) SHALL be excluded; `raw/` SHALL never be excluded. `flatten_first_level` drops first segment.

#### Scenario: Discover supported
- GIVEN `raw/survey.csv`, `raw/notes.txt`, `archive/data.parquet`
- WHEN `scan` executes
- THEN `survey.csv`/`data.parquet` SHALL be discovered, `notes.txt` excluded

#### Scenario: Excluded dirs skipped
- GIVEN `.venv/lib/data.csv` and `node_modules/pkg/data.jsonl`
- WHEN `scan` executes
- THEN neither SHALL appear

#### Scenario: --ext filters
- GIVEN `a.csv`, `b.parquet`, `c.jsonl`
- WHEN `scan --ext .csv`
- THEN only `a.csv` SHALL be discovered

#### Scenario: raw discovered, cache excluded
- GIVEN `raw/a.csv` and `cache/a.csv`
- WHEN `scan` executes
- THEN `raw/a.csv` SHALL be discovered, `cache/a.csv` SHALL NOT

---

### Requirement: TOML Merge (SCN-02)

System MUST load TOML via `tomli`, merge `[[file]]` with `local=cache/<flat>` (`OUTPUT_DIR/<flat>`) and `remote=<flat>` posix, `tomli_w` write. Dedup by resolved absolute path and `remote`. Preserve `[dataset]`,`[meta]`,`[[check]]`,`[[quality]]`. Flatten first segment; root file keeps name.

#### Scenario: Merge new files
- GIVEN `dataset.toml` with 2 `[[file]]` + `[dataset]`/`[meta]`
- AND discovered `raw/new.csv`
- WHEN write
- THEN `[dataset]`/`[meta]` unchanged, `[[file]]` = 3

#### Scenario: Duplicate skipped
- GIVEN existing `local="cache/survey.csv"` → `/abs/cache/survey.csv`
- AND discovered `/abs/raw/survey.csv`
- WHEN merge
- THEN no duplicate SHALL be created

#### Scenario: No loss
- GIVEN `dataset.toml` with `[[check]]`,`[[quality]]`
- WHEN scan writes
- THEN all `[[check]]`/`[[quality]]` SHALL survive

#### Scenario: Flattened paths
- GIVEN `raw/DPTO.csv` and `raw/Labels/etiquetas_a.csv`
- WHEN merge
- THEN `local="cache/DPTO.csv"`/`remote="DPTO.csv"` and `local="cache/Labels/etiquetas_a.csv"`/`remote="Labels/etiquetas_a.csv"`

#### Scenario: Root file
- GIVEN `x.csv` at root
- WHEN merge
- THEN `local="cache/x.csv"`, `remote="x.csv"`

---

### Requirement: File Copy (SCN-03)

System MUST copy to `cache/` (`OUTPUT_DIR`) flattening first segment (`raw/sub/data.csv→cache/sub/data.csv`, `x.csv→cache/x.csv`). Preserve subdirs beyond first. Use `shutil.copy2`. Sources untouched. Lazy mkdir.

#### Scenario: Flatten copy
- GIVEN `raw/sub/data.csv`
- WHEN copy
- THEN `cache/sub/data.csv` exists, source unchanged

#### Scenario: Root copy
- GIVEN `x.csv` at root
- WHEN copy
- THEN `cache/x.csv` exists

#### Scenario: Nested preserved
- GIVEN `raw/Labels/etiquetas_a.csv`
- WHEN copy
- THEN `cache/Labels/etiquetas_a.csv` exists

#### Scenario: Dry-run
- GIVEN 3 files
- WHEN `scan --dry-run`
- THEN report lists flattened `cache/` dests, no files created, TOML unchanged

---

### Requirement: CLI Interface (SCN-04)

The system MUST provide `sofer scan [config.toml] [--dry-run] [--force] [--ext .ext]`.
Default config SHALL be `dataset.toml` in the current directory. `--dry-run`
MUST report without filesystem changes. `--force` MUST skip the confirmation
prompt. Exit code 0 on success, 1 on error.

#### Scenario: Default config and interactive confirm

- GIVEN `dataset.toml` in the working directory
- WHEN `sofer scan` is called
- THEN `dataset.toml` SHALL be used as config
- AND the user SHALL be prompted before files are copied

#### Scenario: --force skips confirmation

- GIVEN discovered files and `dataset.toml`
- WHEN `sofer scan --force` is called
- THEN files SHALL be copied without prompting

#### Scenario: Explicit config path

- GIVEN `my-project/config.toml` exists
- WHEN `sofer scan my-project/config.toml` is called
- THEN that file SHALL be used as the TOML source

---

### Requirement: Idempotency (SCN-05)

The system MUST produce identical TOML output on repeated runs with the same
filesystem state. Two consecutive `scan` invocations with no file changes SHALL
yield byte-identical `dataset.toml`.

#### Scenario: Repeated scan with no file changes

- GIVEN `dataset.toml` after a successful `scan`
- AND no files added/removed
- WHEN `scan` is called a second time
- THEN the resulting TOML SHALL be identical to the first run's output

---

### Requirement: Error Handling (SCN-06)

System MUST handle missing config, no files, conflicts, malformed TOML. Flatten collision SHALL fail before copy, naming all sources. Exit 1 for errors. No silent overwrite.

#### Scenario: Config missing
- GIVEN no `dataset.toml`
- WHEN `scan`
- THEN error printed, exit 1

#### Scenario: No files
- GIVEN only `.txt`/`.md`
- WHEN `scan`
- THEN warning "no supported files" and exit 0

#### Scenario: Dest exists
- GIVEN `cache/raw.csv` exists
- WHEN copy `raw.csv`
- THEN prompt; `--force` overwrites silently

#### Scenario: Malformed TOML
- GIVEN invalid TOML
- WHEN `scan`
- THEN parse error with line, exit 1

#### Scenario: Flatten collision
- GIVEN `A/x.csv` and `B/x.csv` → `x.csv`
- WHEN `scan`
- THEN error names both, exit 1, no copy

---

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
