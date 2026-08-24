# Render Specification

## Purpose

The `render` command turns a `metadata.yaml` document into a human-readable
`README.md`. It renders strictly from the metadata document and never presents
inference as fact.

## Requirements

### Requirement: render command surface (RND-01)

The system SHALL register a `sofer render <package>` subcommand accepting a
package path as its positional argument. The path MAY be a directory
(containing a `metadata.yaml`) or a direct path to a `metadata.yaml` file. The
handler SHALL resolve the argument as follows: if the path is a directory, read
`<dir>/metadata.yaml`; if it is a file, read that file directly; if neither
resolves to a readable `metadata.yaml`, fail with a clear, non-traceback error
and a non-zero exit code.

#### Scenario: render accepts a directory

- GIVEN `sofer render ./build/` where `./build/metadata.yaml` exists
- WHEN the command executes
- THEN the handler SHALL read `./build/metadata.yaml`

#### Scenario: render accepts a direct metadata.yaml path

- GIVEN `sofer render ./build/metadata.yaml`
- WHEN the command executes
- THEN the handler SHALL read `./build/metadata.yaml` directly

#### Scenario: missing metadata.yaml errors cleanly

- GIVEN `sofer render ./` where `./metadata.yaml` does not exist
- WHEN the command executes
- THEN a clear error message SHALL be printed
- AND the exit code SHALL be non-zero

### Requirement: README rendered from metadata (RND-02)

The `render` command SHALL read `metadata.yaml` and generate `README.md` from its
contents — never from a hand-written template that ignores the metadata.

#### Scenario: render produces README from metadata

- GIVEN a valid `metadata.yaml`
- WHEN `sofer render` executes
- THEN a `README.md` SHALL be written
- AND its content SHALL reflect the metadata document's fields

### Requirement: Inference states rendered distinctly (RND-03)

The `render` command SHALL render inference states distinctly: `confirmed` as a
plain label, `inferred` as `"<type> (inferred, NN%)"` with the confidence
percentage, and `unknown` as `"unknown"`. The percentage SHALL be computed as
`round(confidence × 100)` — rounded to the nearest integer percent using
Python's `round()` (round-half-to-even), never truncated (no `int()`/floor),
so e.g. `confidence = 0.78` renders as `78%`.

#### Scenario: Confirmed renders plain

- GIVEN a column with semantic status `confirmed`
- WHEN README is rendered
- THEN the column's type SHALL appear as a plain label with no qualifier

#### Scenario: Inferred renders with confidence

- GIVEN a column with semantic status `inferred` and `confidence = 0.78`
- WHEN README is rendered
- THEN the column's type SHALL render as `email (inferred, 78%)`

#### Scenario: Unknown renders as unknown

- GIVEN a column with no semantic type (status `unknown`)
- WHEN README is rendered
- THEN the field SHALL render as `unknown` — not blank and not fabricated
