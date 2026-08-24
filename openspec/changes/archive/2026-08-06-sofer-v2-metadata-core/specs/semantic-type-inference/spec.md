# Semantic Type Inference Specification

## Purpose

Coarse-to-semantic column typing for sofer v2. Detectors map a column's values
to a semantic type with a deterministic confidence, and every result carries a
machine-readable status (`confirmed` / `inferred` / `unknown`). Confidence is
derived from config, never hardcoded, so inference is reproducible and never
presented as fact.

## Requirements

### Requirement: Detector contract (STI-01)

The system SHALL define a `SemanticDetector` abstract base exposing a single
`detect(values)` method that returns a `Detection` when the column matches the
detector's type, or `None` when it does not. A detector computes `match_rate`
as the fraction of **non-missing** values that match the detector's pattern;
missing values (whitespace-only or equal to a sentinel such as `""` or `"NA"`)
are excluded from both numerator and denominator. A detector SHALL return
`None` when `match_rate` is below the config-driven `detect_threshold`, and a
`Detection` otherwise.

#### Scenario: Matching column yields a Detection

- GIVEN a detector and a column whose values match the detector's type
- WHEN `detect(values)` is called
- THEN a `Detection` SHALL be returned
- AND its `type` SHALL equal the detector's semantic type

#### Scenario: Non-matching column yields None

- GIVEN a detector and a column whose values do not match the type
- WHEN `detect(values)` is called
- THEN `None` SHALL be returned

#### Scenario: Weak match below detect_threshold yields None

- GIVEN a detector and a column whose `match_rate` is below `detect_threshold`
- WHEN `detect(values)` is called
- THEN `None` SHALL be returned
- AND no `Detection` SHALL be produced — this is the "not this type" signal,
  distinct from the `unknown` status, which only applies to a returned
  `Detection`

### Requirement: Detection result shape (STI-02)

The system SHALL model a detection result as a `Detection` carrying `type`,
`match_rate`, `confidence`, and `status` fields.

#### Scenario: Detection carries full result

- GIVEN a successful detection
- WHEN the result is inspected
- THEN `type`, `match_rate`, `confidence`, and `status` SHALL all be present

### Requirement: Confidence is match_rate times config prior (STI-03)

The system SHALL compute `confidence = match_rate × prior`, where `prior` is
read from `[tool.sofer] semantic_priors` in config. Detectors MUST NOT hardcode
a prior. Before the confidence is stored or serialized, the system SHALL round
it to the config-driven precision `confidence_round_digits` (default `4`) using
Python's `round()` (round-half-to-even), so IEEE-754 artefacts such as
`0.8 × 0.9 = 0.7200000000000001` never leak into the metadata document.

#### Scenario: Prior read from config, not magic

- GIVEN a config whose `semantic_priors` sets `email = 0.9` and whose
  `confidence_round_digits` is `4`
- WHEN an email column with `match_rate = 0.8` is detected
- THEN `confidence` SHALL be `round(0.8 × 0.9, 4)`, i.e. `0.72`
- AND tests SHALL assert it with `pytest.approx(0.72)` — never exact float
  equality

#### Scenario: Confidence is deterministic on the same input

- GIVEN the same column values and the same config
- WHEN detection runs twice
- THEN `confidence` SHALL be identical across runs

### Requirement: Status thresholds are config-driven (STI-04)

The system SHALL derive `status` from `confidence` against two config
thresholds: `confirmed` when `confidence ≥ confirm_threshold`, `inferred` when
`min_threshold ≤ confidence < confirm_threshold`, and `unknown` otherwise. Both
thresholds MUST come from config. `status` applies only to a returned
`Detection`; a column whose `match_rate` falls below `detect_threshold` (STI-01)
produces no `Detection` and therefore no status at all — a qualitatively
different outcome from a `Detection` whose `status` is `unknown`.

#### Scenario: High confidence is confirmed

- GIVEN `confirm_threshold = 0.8` and a detection with `confidence = 0.9`
- WHEN status is computed
- THEN status SHALL be `confirmed`

#### Scenario: Mid confidence is inferred

- GIVEN `min_threshold = 0.5`, `confirm_threshold = 0.8`, and `confidence = 0.6`
- WHEN status is computed
- THEN status SHALL be `inferred`

#### Scenario: Low confidence is unknown

- GIVEN `min_threshold = 0.5` and `confidence = 0.3`
- WHEN status is computed
- THEN status SHALL be `unknown`

### Requirement: EmailDetector (STI-05)

The system SHALL provide an `EmailDetector` that detects email columns using a
regex pattern, with its prior read from `[tool.sofer] semantic_priors.email`.

#### Scenario: Email column detected

- GIVEN a column where most values match the email pattern
- WHEN `EmailDetector.detect(values)` is called
- THEN a `Detection` with `type = "email"` SHALL be returned

#### Scenario: Non-email column not detected

- GIVEN a column of plain text with no email pattern
- WHEN `EmailDetector.detect(values)` is called
- THEN `None` SHALL be returned
