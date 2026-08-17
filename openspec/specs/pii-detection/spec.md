# PII Detection Specification

## Purpose

Heuristic detection of personally identifiable information (PII) in dataset
columns. Findings are always advisory — a detector MAY flag a column as
"possible" PII but MUST NOT assert it contains PII, so the tool never states a
categorical conclusion it cannot prove.

## Requirements

### Requirement: PII detector contract (PII-01)

The system SHALL define a `PiiDetector` base exposing a `detect(values)` method
that returns a PII finding when the column may contain PII, or `None` otherwise.

#### Scenario: Matching column yields a finding

- GIVEN a PII detector and a column that may contain PII
- WHEN `detect(values)` is called
- THEN a finding SHALL be returned

#### Scenario: Non-matching column yields None

- GIVEN a PII detector and a column with no PII signal
- WHEN `detect(values)` is called
- THEN `None` SHALL be returned

### Requirement: PII finding shape (PII-02)

The system SHALL model a PII finding as `{label, confidence, note}` where `note`
is always the literal `"possible_pii"`.

#### Scenario: Finding carries label, confidence, note

- GIVEN a positive PII finding
- WHEN the finding is inspected
- THEN `label`, `confidence`, and `note` SHALL all be present

### Requirement: Note is always "possible", never categorical (PII-03)

The system SHALL always set `note = "possible_pii"`. It MUST NOT emit an
affirmative note such as `"contains_pii"` or any categorical verdict.

#### Scenario: Note never asserts containment

- GIVEN any positive PII finding
- WHEN the finding is produced
- THEN `note` SHALL equal `"possible_pii"`
- AND `note` SHALL NOT equal any `"contains_pii"`-style affirmative value

### Requirement: EmailPiiDetector (PII-04)

The system SHALL provide an `EmailPiiDetector` that flags columns whose values
match the email pattern as possible PII.

#### Scenario: Email column flagged as possible PII

- GIVEN a column whose values match the email pattern
- WHEN `EmailPiiDetector.detect(values)` is called
- THEN a finding SHALL be returned with `note = "possible_pii"`

#### Scenario: Non-PII column not flagged

- GIVEN a column with no email pattern
- WHEN `EmailPiiDetector.detect(values)` is called
- THEN `None` SHALL be returned
