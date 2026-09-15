# Delta for tool-config

> Change `2026-09-14-fix-prepare-csv-config-tier` (issue #181). Canonical target:
> `openspec/specs/tool-config/spec.md`, requirement **TC-04**. This file carries
> only the pointer that makes the note true; the normative precedence clause lives
> in `parquet-conversion` **PC-U01**, which owns the reader table naming the caller.

## MODIFIED Requirements

### Requirement: One reload per CLI invocation after the config path resolves (TC-04)

The CLI entry point SHALL trigger exactly one tool-config resolution per
invocation, once the effective `--config` path is known. After resolution,
module-level config constants SHALL reflect the newly resolved values for all
subsequent reads within that invocation.

#### Scenario: Override honored within the same invocation

- GIVEN a working tree whose `pyproject.toml` sets `csv_delimiter = ","`
- WHEN `sofer profile data.csv` runs with the current working directory inside that tree
- THEN the CSV is read with `,` during that same invocation

(Note: the tool-wide `csv_delimiter` consumer is `sofer profile`, whose reader
defaults flow through `stream_csv`. The `prepare` command uses the
DATASET-level `[meta] csv_delimiter`/`csv_encoding` when the dataset declares
them, and falls back to this tool-wide `csv_delimiter` key and
`config.CSV_ENCODING` only when it declares neither — the resolution order is
normative in `parquet-conversion` **PC-U01**.)

(Previously: the note stated flatly that `prepare` uses the dataset-level key "not this tool-wide key", contradicting PC-U01's reader table and leaving the fallback undocumented.)

#### Scenario: Single-file commands without a dataset TOML

- GIVEN `sofer codebook FILE` is invoked with no `--config`
- WHEN tool-config resolution occurs
- THEN discovery anchors on the current working directory per TC-02

## Evidence (AGENTS.md rule 6)

| Scenario | Test file |
|----------|-----------|
| Override honored within the same invocation | `tests/test_config.py` (existing tool-config resolution test; unchanged) |
| Single-file commands without a dataset TOML | `tests/test_cli.py` (existing; unchanged) |

This delta changes no config tier and no anchoring; it is a text reconciliation,
so both scenarios stay evidenced by their existing tests.
