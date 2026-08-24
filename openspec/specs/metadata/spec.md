# Metadata Specification

## Purpose

`metadata.yaml` is the source of truth for dataset documentation in sofer v2.
This spec defines its schema skeleton, deterministic serialization, the
`InferenceStatus` vocabulary, and the read-only guarantee that producing it never
mutates the source dataset.

## Requirements

### Requirement: metadata.yaml schema skeleton (MTA-01)

The system SHALL define a `metadata.yaml` schema whose top-level sections are
`dataset`, `file`, `structure` (with `schema[]`), `quality`, `documentation`
(with `missing_fields`), and `generated`.

#### Scenario: Skeleton sections present

- GIVEN a serialized metadata document
- WHEN the document is inspected
- THEN the sections `dataset`, `file`, `structure`, `quality`,
  `documentation`, and `generated` SHALL be present
- AND `structure.schema` SHALL be a list
- AND `documentation.missing_fields` SHALL be a list

### Requirement: metadata_version field (MTA-02)

The system SHALL include a `metadata_version` field in every serialized metadata
document. The value SHALL be sourced from the module constant
`METADATA_VERSION` (defined in `metadata.py`, value `"1"`), never an inline
literal at the call site.

#### Scenario: Version present

- GIVEN a serialized metadata document
- WHEN the document is inspected
- THEN `metadata_version` SHALL be present and non-empty
- AND `metadata_version` SHALL equal the `METADATA_VERSION` constant

### Requirement: Deterministic serialization (MTA-03)

The system SHALL serialize metadata deterministically — keys sorted and output
order stable — so the same input produces byte-identical YAML across runs.

#### Scenario: Same input yields identical YAML

- GIVEN two serializations of the same metadata object
- WHEN both documents are compared
- THEN the YAML SHALL be byte-identical

#### Scenario: YAML round-trips

- GIVEN a metadata document serialized to YAML
- WHEN the YAML is loaded back
- THEN the loaded document SHALL equal the original

### Requirement: InferenceStatus machine (MTA-04)

The system SHALL define `InferenceStatus` with exactly three values:
`confirmed`, `inferred`, and `unknown`.

#### Scenario: Status vocabulary fixed

- GIVEN the `InferenceStatus` type
- WHEN its values are enumerated
- THEN they SHALL be exactly `confirmed`, `inferred`, and `unknown`

### Requirement: Read-only, never modifies source (MTA-05)

Metadata generation SHALL NOT modify the source dataset file in any way.

#### Scenario: Source dataset untouched

- GIVEN a source dataset file
- WHEN metadata is generated for it
- THEN the source file's bytes SHALL be unchanged

### Requirement: Per-column schema contract (MTA-06)

The system SHALL model each entry of `structure.schema[]` with exactly these
fields:

- `name` — the column name (string).
- `storage_type` — the coarse storage type from existing inference
  (`codebook.infer_column_type`): one of `numeric`, `categorical/text`,
  `mixed (mostly numeric)`, or `unknown`.
- `semantic_type` — a mapping carrying the NEW semantic inference result:
  - `type` — the detected semantic type (e.g. `"email"`).
  - `status` — one of `confirmed`, `inferred`, `unknown`.
  - `confidence` — the rounded `confidence` (float).
  - `basis` — the detector name that produced the result (e.g. `"email"`).
- `pii` — a mapping carrying the PII finding:
  - `label` — the PII label (e.g. `"email"`).
  - `confidence` — the finding confidence (float).
  - `note` — always the literal `"possible_pii"`.

When no semantic detector matches, `semantic_type` SHALL carry
`status = "unknown"` with `type`, `confidence`, and `basis` omitted (or `null`)
— never a fabricated type. `storage_type` is the coarse pre-existing vocabulary
and MUST NOT be merged with `semantic_type`: they answer different questions
("how is it stored" vs "what does it mean").

#### Scenario: One column entry fully rendered

- GIVEN an email column named `user_email` with coarse type `categorical/text`,
  semantic type `email` (inferred, confidence `0.72`, basis `email`), and
  flagged as possible PII
- WHEN the metadata document is serialized
- THEN the column entry SHALL match:

    ```yaml
    structure:
      schema:
        - name: user_email
          storage_type: categorical/text
          semantic_type:
            type: email
            status: inferred
            confidence: 0.72
            basis: email
          pii:
            label: email
            confidence: 0.72
            note: possible_pii
    ```
