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
