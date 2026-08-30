# Delta for scan

## ADDED Requirements

### Requirement: Source Layout and Copy-Only (SCN-07)
System MUST enforce `raw/` (tracked) → `cache/` (`OUTPUT_DIR`, gitignored) → `build/` (gitignored) with diagram `raw/DPTO.csv→cache/DPTO.csv→build/*.parquet`. `scan` MUST copy to `cache/` via `flatten_first_level` and SHALL NOT move/delete sources.

#### Scenario: Sources untouched
- GIVEN `raw/DPTO.csv` exists
- WHEN `scan` completes
- THEN `raw/DPTO.csv` unchanged and `cache/DPTO.csv` exists

#### Scenario: Docs show diagram
- GIVEN user views Directory layout
- WHEN layout rendered
- THEN `raw/→cache/→build/` and `raw/DPTO.csv→cache/DPTO.csv` SHALL appear

## MODIFIED Requirements

### Requirement: File Discovery (SCN-01)
System MUST discover supported extensions (`.csv`,`.tsv`,`.parquet`,`.xlsx`,`.jsonl`) from config dir. `EXCLUSIONS` (`.git`, `__pycache__`, `.venv`, `node_modules`, `dist`, `build`) MUST be skipped. `cache/` (`OUTPUT_DIR`) SHALL be excluded; `raw/` SHALL never be excluded. `flatten_first_level` drops first segment.
(Previously: generic `data/` destination, no explicit `raw/`/`cache/` exclusion.)

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

### Requirement: TOML Merge (SCN-02)
System MUST load TOML via `tomli`, merge `[[file]]` with `local=cache/<flat>` (`OUTPUT_DIR/<flat>`) and `remote=<flat>` posix, `tomli_w` write. Dedup by resolved absolute path and `remote`. Preserve `[dataset]`,`[meta]`,`[[check]]`,`[[quality]]`. Flatten first segment; root file keeps name.
(Previously: used `data/` prefix.)

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

### Requirement: File Copy (SCN-03)
System MUST copy to `cache/` (`OUTPUT_DIR`) flattening first segment (`raw/sub/data.csv→cache/sub/data.csv`, `x.csv→cache/x.csv`). Preserve subdirs beyond first. Use `shutil.copy2`. Sources untouched. Lazy mkdir.
(Previously: `data/` destination.)

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

### Requirement: Error Handling (SCN-06)
System MUST handle missing config, no files, conflicts, malformed TOML. Flatten collision SHALL fail before copy, naming all sources. Exit 1 for errors. No silent overwrite.
(Previously: collision message used `data/`.)

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
