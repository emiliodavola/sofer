# Scan Specification

## Purpose

Automated data-file discovery, copy, and TOML registration. The `scan` command
eliminates manual `[[file]]` maintenance by discovering supported formats,
copying them to `data/`, and writing the updated config.

## Requirements

### Requirement: File Discovery (SCN-01)

The system MUST recursively discover files with supported extensions from the
config directory. Supported formats SHALL come from an extensible registry:
`.csv`, `.tsv`, `.parquet`, `.xlsx`, `.jsonl`. Standard exclusion directories
MUST be skipped: `.git/`, `__pycache__/`, `.venv/`, `node_modules/`, `dist/`,
`build/`.

#### Scenario: Discover supported files in a project tree

- GIVEN a directory with `raw/survey.csv`, `raw/notes.txt`, `archive/data.parquet`
- WHEN `scan` executes
- THEN `survey.csv` and `data.parquet` SHALL be discovered
- AND `notes.txt` SHALL be excluded (unsupported extension)

#### Scenario: Excluded directories are never traversed

- GIVEN a `.venv/lib/data.csv` and `node_modules/pkg/data.jsonl`
- WHEN `scan` executes
- THEN neither file SHALL appear in results
- AND `.venv/` and `node_modules/` subtrees SHALL be skipped entirely

#### Scenario: `--ext .ext` filters to a single extension

- GIVEN files `a.csv`, `b.parquet`, `c.jsonl`
- WHEN `scan --ext .csv` executes
- THEN only `a.csv` SHALL be discovered

---

### Requirement: TOML Merge (SCN-02)

The system MUST load the existing TOML via `tomli`, merge discovered files as
`[[file]]` entries (with `local` pointing to `data/`-relative paths and `remote`
using `PurePosixPath`), and write via `tomli_w`. Entries SHALL be deduplicated
by resolved absolute path. Non-`[[file]]` sections (`[dataset]`, `[meta]`,
`[[check]]`, `[[quality]]`) MUST be preserved.

#### Scenario: Merge new files into existing TOML

- GIVEN `dataset.toml` with 2 existing `[[file]]` entries and `[dataset]`/`[meta]` sections
- AND discovered files `raw/new.csv` and `raw/existing.csv`
- WHEN `scan` writes TOML
- THEN `[dataset]` and `[meta]` SHALL be unchanged
- AND `[[file]]` SHALL contain 3 entries (2 existing + 1 new)

#### Scenario: Duplicate by resolved path is skipped

- GIVEN an existing `[[file]]` entry with `local = "data/survey.csv"` (resolves to `/abs/data/survey.csv`)
- AND the discovered file `/abs/raw/survey.csv`
- WHEN `scan` merges
- THEN no duplicate `[[file]]` entry SHALL be created

#### Scenario: No `[[file]]` loss on merge

- GIVEN `dataset.toml` with `[[file]]`, `[[check]]`, and `[[quality]]` sections
- WHEN `scan` produces output
- THEN all `[[check]]` and `[[quality]]` entries SHALL survive the round-trip

---

### Requirement: File Copy (SCN-03)

The system MUST copy discovered files to `data/` preserving relative subdirectory
structure. `shutil.copy2` SHALL be used for metadata preservation. Source files
MUST remain untouched. Directory creation SHALL be lazy (only when needed).

#### Scenario: Copy preserves subdirectory structure

- GIVEN discovered file `raw/sub/data.csv` configured to `./data/`
- WHEN `scan` copies files
- THEN `data/sub/data.csv` SHALL exist
- AND `raw/sub/data.csv` SHALL be unchanged

#### Scenario: Dry-run reports without copying

- GIVEN 3 discovered files
- WHEN `scan --dry-run` executes
- THEN a report SHALL list all planned copies
- AND no files SHALL be created under `data/`
- AND `dataset.toml` SHALL NOT be modified

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

The system MUST handle errors gracefully: missing config, no discovered files,
destination conflicts, and malformed TOML. All errors SHALL produce exit code 1.

#### Scenario: Config file not found

- GIVEN `dataset.toml` does not exist
- WHEN `sofer scan` is called
- THEN an error message SHALL be printed
- AND exit code SHALL be 1

#### Scenario: No supported files discovered

- GIVEN a directory with only `.txt` and `.md` files
- WHEN `scan` executes
- THEN a warning SHALL state "no supported files found"
- AND exit code SHALL be 0 (not an error)

#### Scenario: Destination file already exists

- GIVEN `data/raw.csv` already exists (from prior copy)
- WHEN `scan` attempts to copy `raw.csv` (with different source)
- THEN the user SHALL be prompted to overwrite
- AND with `--force`, the file SHALL be overwritten silently

#### Scenario: Malformed TOML cannot be read

- GIVEN `dataset.toml` containing invalid TOML syntax
- WHEN `scan` is called
- THEN a parse error SHALL be reported with line number
- AND exit code SHALL be 1
