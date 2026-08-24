# Publish Specification

## Purpose

Delivery of a prepared dataset package to a target. `publish` pushes the
prepared package to the Hugging Face Hub via a single `upload_folder` call
(`--target hf`, default) or writes it to a local directory (`--target local`).
It auto-prepares when artifacts are stale or missing, and can dry-run, force,
verify, and keep CSVs.

## Requirements

### Requirement: hf target uploads via upload_folder (PUB-01)

`publish --target hf` SHALL ensure the repository exists, run the quality gate,
and push the package in a single `HfApi.upload_folder()` call. It SHALL print
the repo diff summary before pushing and the split report after. Files missing
on disk SHALL be reported as NOT FOUND and skipped. Delivery SHALL be blocked
when the quality gate fails (preserved from `upload`).

#### Scenario: Full hf publish

- GIVEN a prepared output directory and a valid config
- WHEN `sofer publish dataset.toml` executes
- THEN the repository SHALL be ensured
- AND the diff summary SHALL be printed
- AND `upload_folder` SHALL be called exactly once
- AND the post-upload split report SHALL be printed
- AND the exit code SHALL be 0

#### Scenario: Quality gate blocks delivery

- GIVEN a config whose quality checks fail
- WHEN `publish` executes
- THEN the failed-checks report SHALL be printed
- AND no upload SHALL occur
- AND the exit code SHALL be 1

#### Scenario: upload_folder failure

- GIVEN `HfApi.upload_folder()` raises an exception
- WHEN `publish` runs the batch upload
- THEN the error SHALL be printed
- AND the exit code SHALL be 1

#### Scenario: Missing files reported, never uploaded

- GIVEN a declared file absent from the prepared package
- WHEN `publish` stages
- THEN the file SHALL be reported as NOT FOUND
- AND it SHALL NOT be included in the upload

---

### Requirement: local target writes a complete package (PUB-02)

`publish --target local` SHALL write the complete package — Parquet files,
README.md, LICENSE, and codebooks — to `--output` with no network calls and no
Hub access. When `--output` is omitted, the prepared output directory SHALL be
the destination (in-place assembly).

#### Scenario: Package written to --output

- GIVEN a prepared package and `sofer publish dataset.toml --target local --output ./out/`
- WHEN the command executes
- THEN `./out/` SHALL contain the parquet tree, README.md, LICENSE, and codebooks
- AND no network request SHALL be made

#### Scenario: Local target runs offline

- GIVEN no network connectivity
- WHEN `publish --target local` executes
- THEN the command SHALL complete successfully

---

### Requirement: Auto-prepare when artifacts are stale or missing (PUB-03)

`publish` SHALL run `prepare` automatically before delivering when the output
directory has no Parquet files, or when the TOML's modification time OR any
declared source file's modification time (for ALL supported formats — CSV,
TSV, Parquet, Excel, JSONL) is newer than the newest Parquet file. The TOML and
source files SHALL be the source of truth; Parquet existence is the fallback
check.

Auto-prepare SHALL run with the all-files behavior ENABLED (equivalent to
`prepare --all-files`): the prepared package SHALL include per-file codebooks
(`codebooks/**/*.md`) and the root `codebook.md` index, so that a bare
`sofer publish dataset.toml` delivers a complete package — data + README +
LICENSE + codebooks.

(Previously: auto-prepare ran plain `prepare(cfg, source, force=True)` with
all-files disabled, so published packages never contained codebooks and nothing
warned about it.)

#### Scenario: Parquet missing triggers prepare

- GIVEN a config whose output directory contains no `.parquet` files
- WHEN `publish` executes
- THEN `prepare` SHALL run first
- AND the freshly prepared package SHALL be delivered

#### Scenario: TOML newer than parquet triggers prepare

- GIVEN `dataset.toml` modified after the last Parquet write
- WHEN `publish` executes
- THEN `prepare` SHALL run first

#### Scenario: Source file newer than parquet triggers prepare

- GIVEN a declared source CSV (or any supported format) modified after the
  last Parquet write, even when the TOML is unchanged
- WHEN `publish` executes
- THEN `prepare` SHALL run first

#### Scenario: Up-to-date package skips prepare

- GIVEN Parquet files exist AND the TOML and all source files are older than them
- WHEN `publish` executes
- THEN no `prepare` SHALL run
- AND the existing package SHALL be delivered

#### Scenario: Auto-prepare generates codebooks

- GIVEN a stale build directory (sources newer than Parquet)
- WHEN `publish` executes and auto-prepare runs
- THEN the delivered package SHALL include `codebooks/**/*.md` and root `codebook.md`
- AND the pinned test asserting "bare prepare stages no codebooks" SHALL be reversed

---

### Requirement: --dry-run shows the diff without publishing (PUB-04)

`--dry-run` SHALL print the repo diff summary and split report without pushing
any files and without mutating the output directory.

#### Scenario: Dry-run does not upload

- GIVEN a valid config and `sofer publish dataset.toml --dry-run`
- WHEN the command executes
- THEN the diff summary SHALL be printed
- AND no `upload_folder` call SHALL be made
- AND the exit code SHALL be 0

---

### Requirement: --force bypasses overwrite protection (PUB-05)

Auto-generated files — `README.md`, `LICENSE`, `codebook.md`, and
`codebooks/**/*.md` — SHALL always overwrite remote files without prompting,
even without `--force`. For all other remote files, overwrite protection SHALL
apply unless `--force` is given.

#### Scenario: Auto-generated files always overwrite

- GIVEN `README.md` and `LICENSE` already exist on the Hub
- AND no `--force`
- WHEN `publish` executes
- THEN both SHALL be uploaded unconditionally
- AND no prompt SHALL block them

#### Scenario: Protected file needs --force

- GIVEN a data file already exists on the Hub and no `--force`
- WHEN `publish` executes
- THEN overwrite protection SHALL refuse the file
- AND with `--force` the file SHALL be overwritten

---

### Requirement: --keep-csv uploads CSVs alongside parquet (PUB-07)

For the `hf` target, `--keep-csv` SHALL include each converted entry's original
CSV in the upload at its original remote path, alongside the Parquet. For the
`local` target, `--keep-csv` SHALL have no effect.

#### Scenario: CSV kept alongside parquet on hf

- GIVEN `sofer publish dataset.toml --keep-csv`
- WHEN the hf upload completes
- THEN `data/PROV/train.csv` SHALL be uploaded alongside `data/PROV/train.parquet`

#### Scenario: --keep-csv ignored for local target

- GIVEN `sofer publish dataset.toml --target local --keep-csv`
- WHEN the command executes
- THEN the local package SHALL contain only the default artifacts

---

### Requirement: Codebook-absence warning before delivery (PUB-08)

> Added by change `publish-readme-bugs` (archived 2026-08-24).

When delivering to the `hf` target, if the build directory contains NO codebooks
(neither `codebook.md` nor `codebooks/**/*.md`) at delivery time, `publish`
SHALL print a warning advising how to generate them. The warning MUST NOT block
delivery — the upload SHALL proceed for all other files.

(Previously: absence was silent — the repo diff simply omitted the codebook
entries.)

#### Scenario: Build without codebooks warns but delivers

- GIVEN an up-to-date build directory containing no codebook files
- WHEN `publish` executes against hf
- THEN a codebook-missing warning SHALL be printed before upload
- AND the remaining package SHALL still be delivered (exit 0)

#### Scenario: Complete package does not warn

- GIVEN a build directory that includes codebooks
- WHEN `publish` executes
- THEN no codebook-missing warning SHALL be printed
