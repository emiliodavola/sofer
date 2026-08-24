# Delta for publish — PUB-03 auto-prepare produces a complete package

## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Codebook-absence warning before delivery (PUB-08)

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
