# Profile Specification

## Purpose

The `profile` command introspects a dataset read-only and emits a `metadata.yaml`
document. It is the entry point for sofer v2's documentation pipeline and never
modifies its input.

## Requirements

### Requirement: profile command surface (PRF-01)

The system SHALL register a `sofer profile <dataset>` subcommand accepting the
dataset path as its positional argument.

#### Scenario: profile accepts dataset path

- GIVEN `sofer profile dataset.csv`
- WHEN the command executes
- THEN the profile handler SHALL run with `dataset.csv` as its input

### Requirement: profile orchestration (PRF-02)

The `profile` command SHALL detect the dataset format, read the dataset, infer a
coarse schema, run semantic inference (Email only) and PII detection (Email
only), assemble a `metadata.yaml` document, and report missing human-input
fields.

The coarse schema's `unique` statistic for each column SHALL count DISTINCT
NON-MISSING values only: missing-value sentinels ("", "NA", "NULL", "N/A") and
null/None MUST NOT be counted as distinct values. This aligns `profile.py` with
the corrected unique-count semantics in the schema report and codebook.

(Previously: `unique=len(set(values))` counted sentinels as values, even though
`_is_missing` was already used for missing% and example selection in the same
function.)

#### Scenario: profile CSV writes metadata.yaml

- GIVEN a CSV dataset with an email-bearing column
- WHEN `sofer profile dataset.csv` executes
- THEN a `metadata.yaml` SHALL be written next to the dataset
- AND it SHALL contain the detected schema and the email semantic type

#### Scenario: profile detects email semantic type

- GIVEN a CSV dataset with an email column
- WHEN `sofer profile dataset.csv` executes
- THEN `metadata.yaml` SHALL record `email` as the column's semantic type with a status

#### Scenario: profile flags possible PII

- GIVEN a CSV dataset with an email column
- WHEN `sofer profile dataset.csv` executes
- THEN `metadata.yaml` SHALL flag the column with `note = "possible_pii"`

#### Scenario: profile reports missing human fields

- GIVEN a CSV dataset with no description, license, or source
- WHEN `sofer profile dataset.csv` executes
- THEN the command SHALL report `description`, `license`, and `source` as missing
- AND `metadata.yaml` SHALL list them in `documentation.missing_fields`

#### Scenario: Sentinels excluded from unique counts

- GIVEN a CSV dataset with a column whose values are ["A", "", "NA", "B"]
- WHEN `sofer profile dataset.csv` executes
- THEN that column's `unique` statistic in `metadata.yaml` SHALL be 2

### Requirement: read-only (PRF-03)

The `profile` command SHALL NOT modify its input dataset in any way.

#### Scenario: Input dataset untouched

- GIVEN a dataset file
- WHEN `sofer profile` runs on it
- THEN the input file's bytes SHALL be unchanged

### Requirement: Unsupported format errors cleanly (PRF-04)

The `profile` command SHALL fail with a clear, non-traceback error message and a
non-zero exit code when the dataset format is unsupported.

#### Scenario: Unsupported format

- GIVEN a dataset file with an unsupported extension
- WHEN `sofer profile file.xyz` executes
- THEN a clear error message SHALL be printed
- AND the exit code SHALL be non-zero
- AND no `metadata.yaml` SHALL be written

---

### Requirement: Batch profile via --all-files (PRF-05)

When `--all-files` is set the system MUST iterate `[[file]]` entries via `DatasetConfig.from_toml`; for each entry it MUST derive `rel_stem` as `local.relative_to(data_dir)` when inside `data_dir = base_dir / config.OUTPUT_DIR`, otherwise `local.relative_to(base_dir)`. For non-`.xlsx` and single-sheet `.xlsx` entries it MUST write one `metadata.yaml` namespaced by `rel_stem` under `profile_dir` as `<write_root>/profiles/<rel_stem>.metadata.yaml`, computed as `(profile_dir / rel_stem).with_suffix(PurePath.suffixes replacement)` (only last suffix → `.metadata.yaml`). For `.xlsx` with N>1 sheets it MUST read all sheets via `_read_xlsx_sheets`, sanitize each sheet name via `sanitize_sheet_name` (lower→NFKD→ascii→space→`_`→strip; empty/whitespace-only → `sheet`) with `seen` dedup `_{n}`, and write N files `profiles/<rel>/<stem>__<sanitized>.metadata.yaml`. The system MUST pre-compute the collision map over sheet-expanded outputs normalized via `re.sub(r"__+", "_", str(path))` (so `a__ventas`≈`a_ventas`) as `output → [sources]` before any write, MUST write non-colliding outputs first, then MUST raise `ValueError` naming every colliding source as `<path>::<sheet>` and MUST NOT write colliding outputs nor a root index. `--output` anchoring MUST follow Option B: relative dirs anchor to `cfg._base_dir`, writes go to `<output>/profiles/`, never mutating `cache/`. TOML without `[[file]]` MUST fail fast.

#### Scenario: Batch N-files

- GIVEN `dataset.toml` with `[[file]]` for `raw/a.csv` and `raw/b.csv`
- WHEN `sofer profile dataset.toml --all-files` executes
- THEN `<write_root>/profiles/a.metadata.yaml` and `b.metadata.yaml` SHALL exist

#### Scenario: Nested path preserved via rel_stem

- GIVEN `[[file]]` for `raw/Labels/etiquetas_a.csv`
- WHEN batch executes
- THEN `profiles/Labels/etiquetas_a.metadata.yaml` SHALL be generated

#### Scenario: Multisheet workbook 2 sheets yields 2 profiles

- GIVEN `report.xlsx` with sheets `Sales` (id,amount) and `Inventory` (sku,qty) under `raw/`
- WHEN `sofer profile dataset.toml --all-files` executes
- THEN `profiles/report__sales.metadata.yaml` and `profiles/report__inventory.metadata.yaml` SHALL exist
- AND each file's schema SHALL reflect only that sheet's headers and row counts

#### Scenario: Single-sheet xlsx stays suffix-less

- GIVEN an `.xlsx` with 1 sheet `Data`
- WHEN batch or `generate_all_profiles` processes it
- THEN exactly one file `profiles/<stem>.metadata.yaml` SHALL be written
- AND the file SHALL be byte-identical to the pre-change single-sheet output

#### Scenario: sanitize_sheet_name applied

- GIVEN sheets named `DATA GOT Año` and `Ventas 2024!`
- WHEN sanitized for the stem
- THEN results SHALL be `data_got_ano` and `ventas_2024`
- AND empty/whitespace-only names SHALL fallback to `sheet`

#### Scenario: Dedup via seen _{n}

- GIVEN an `.xlsx` with sheets `Ventas` and `VENTAS` (both → `ventas`)
- WHEN profiles are emitted
- THEN outputs SHALL be `__ventas.metadata.yaml` and `__ventas_2.metadata.yaml`
- AND a third duplicate SHALL be `__ventas_3.metadata.yaml`

#### Scenario: Sheet-aware collision via normalized __+→_

- GIVEN `data/a__ventas.xlsx` sheet `Ventas` (→ `profiles/a__ventas.metadata.yaml`) and `data/a_ventas.csv` (→ `profiles/a_ventas.metadata.yaml` normalized `__+`→`_`)
- WHEN `--all-files` expands sheets and builds the collision map
- THEN the normalized key SHALL collide
- AND system SHALL raise `ValueError` naming both sources with `::Ventas` suffix and write neither

#### Scenario: Same-stem collision errors after partial write

- GIVEN `raw/x.csv` and `raw/x.parquet` mapping to `profiles/x.metadata.yaml` plus `raw/ok.csv`
- WHEN batch executes
- THEN `profiles/ok.metadata.yaml` SHALL be written
- AND `ValueError` SHALL name both colliding sources and colliding path

#### Scenario: Custom --output anchoring (Option B)

- GIVEN `sofer profile dataset.toml --all-files --output /tmp/out`
- WHEN batch executes
- THEN outputs SHALL be under `/tmp/out/profiles/` and `cache/` SHALL be untouched

#### Scenario: Custom --output relative anchored to base_dir

- GIVEN `dataset.toml` in `/proj/` and `--output rel/out`
- WHEN batch executes
- THEN writes SHALL go to `/proj/rel/out/profiles/` not CWD

#### Scenario: Config override to docs/profiles

- GIVEN `pyproject.toml` sets `profile_dir = "docs/profiles"`
- WHEN batch executes
- THEN outputs SHALL be under `docs/profiles/<rel_stem>.metadata.yaml`

#### Scenario: TOML without [[file]] fails

- GIVEN TOML with no `[[file]]`
- WHEN `--all-files` executes
- THEN system SHALL fail with non-zero exit and message mentioning `[[file]]`

#### Scenario: MCP containment for profile_dir

- GIVEN MCP `sofer_profile` with `output` escaping server root via `profile_dir`
- WHEN `_validate_output_targets` runs
- THEN request SHALL be rejected without writing

### Requirement: Single-file force guard (PRF-06)

Single-file `sofer profile <dataset>` MUST check `dest.exists()` before write; without `--force` it MUST raise `FileExistsError` with message containing `use --force to overwrite` and the destination path; with `--force` it MUST overwrite.

#### Scenario: Guard without --force

- GIVEN `out/profiles/a.metadata.yaml` exists
- WHEN `sofer profile raw/a.csv --output out` without `--force` runs
- THEN `FileExistsError` SHALL be raised and file SHALL be unchanged

#### Scenario: Overwrite with --force

- GIVEN same existing dest
- WHEN `sofer profile raw/a.csv --output out --force` runs
- THEN file SHALL be overwritten and exit 0

### Requirement: Explicit CSV dialect override for profile (PRF-07)

> Added by change `2026-09-25-csv-dialect-override` (GitHub #204).

`sofer profile DATASET` and `sofer profile --all-files` SHALL accept optional
`--delimiter` / `--encoding`. The resolution order SHALL be **explicit flag →
resolved config (tool-wide `config.CSV_DELIMITER` / `config.CSV_ENCODING` for the
single-file tier; the batch tier resolves the tool-wide values too) → the existing
`stream_csv` encoding fallback chain**. The explicit value SHALL win.

`None` SHALL be the only "not supplied" signal; the omitted path SHALL be
byte-identical to the pre-change behaviour. `.tsv` files SHALL remain
tab-delimited by format (the explicit delimiter SHALL apply to `.csv`; the explicit
encoding SHALL apply to `.csv` and `.tsv`). Non-streamed formats
(`.parquet`/`.xlsx`/`.jsonl`) SHALL ignore the explicit pair exactly as they do
today. The `metadata.yaml` `file.encoding` / `file.delimiter` fields SHALL record
the values actually used. When an explicit value is supplied, the command SHALL
echo it on stderr.

#### Scenario: Explicit delimiter wins over a disagreeing tool-wide config

- GIVEN `[tool.sofer] csv_delimiter = ";"` and a `.csv` whose real delimiter is `,`
- WHEN `sofer profile DATASET --delimiter ,` runs
- THEN the recorded schema SHALL reflect the `,`-split columns
- AND `metadata.yaml` `file.delimiter` SHALL equal the explicit value

#### Scenario: Explicit encoding wins

- GIVEN a file readable only under a supplied encoding
- WHEN `sofer profile DATASET --encoding <enc>` runs
- THEN the file SHALL be read under the explicit encoding first
- AND `metadata.yaml` `file.encoding` SHALL equal the explicit value

#### Scenario: Omitted override is unchanged

- GIVEN the same dataset and tool-wide config
- WHEN `sofer profile DATASET` runs without the new flags
- THEN the emitted `metadata.yaml` SHALL be byte-identical to the pre-change run
- AND no explicit-dialect line SHALL be printed to stderr

#### Scenario: .tsv stays tab-delimited

- GIVEN a `.tsv` file and an explicit `--delimiter ,`
- WHEN it is profiled
- THEN the file SHALL still be read tab-delimited

#### Scenario: Explicit dialect is echoed

- GIVEN an explicit `--delimiter` and/or `--encoding` is supplied
- WHEN the command runs
- THEN the supplied override SHALL be echoed on stderr
