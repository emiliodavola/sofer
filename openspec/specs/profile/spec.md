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

When `--all-files` is set the system MUST iterate `[[file]]` entries via `DatasetConfig.from_toml`; for each entry it MUST write one `metadata.yaml` namespaced by `rel_stem` under `profile_dir` as `<write_root>/profiles/<rel_stem>.metadata.yaml`. `rel_stem` MUST be `local.relative_to(data_dir)` when inside `data_dir = base_dir / config.OUTPUT_DIR`, otherwise `local.relative_to(base_dir)`, with output computed as `(profile_dir / rel_stem).with_suffix(PurePath.suffixes replacement)` (only last suffix → `.metadata.yaml`). The system MUST pre-compute the collision map `output → [sources]` before any write, MUST write non-colliding outputs first, then MUST raise `ValueError` naming every colliding source and MUST NOT write colliding outputs nor a root index. `--output` anchoring MUST follow Option B: relative dirs anchor to `cfg._base_dir`, writes go to `<output>/profiles/`, never mutating `cache/`. TOML without `[[file]]` MUST fail fast.

#### Scenario: Batch N-files

- GIVEN `dataset.toml` with `[[file]]` for `raw/a.csv` and `raw/b.csv`
- WHEN `sofer profile dataset.toml --all-files` executes
- THEN `<write_root>/profiles/a.metadata.yaml` and `b.metadata.yaml` SHALL exist

#### Scenario: Nested path preserved via rel_stem

- GIVEN `[[file]]` for `raw/Labels/etiquetas_a.csv`
- WHEN batch executes
- THEN `profiles/Labels/etiquetas_a.metadata.yaml` SHALL be generated

#### Scenario: Same-stem collision errors after partial write

- GIVEN `raw/x.csv` and `raw/x.parquet` mapping to `profiles/x.metadata.yaml`
- WHEN batch executes
- THEN non-colliding outputs SHALL be written
- AND `ValueError` SHALL name both sources and colliding path

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
