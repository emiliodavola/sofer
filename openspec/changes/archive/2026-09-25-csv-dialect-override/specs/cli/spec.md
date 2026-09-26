# Spec delta: 2026-09-25-csv-dialect-override (cli)

> **Change:** `2026-09-25-csv-dialect-override` (GitHub #204) · branch
> `feat/204-csv-dialect-override`.
>
> CLI-R02 / CLI-R04 (help accuracy) are left intact; CLI-R12 adds the optional
> dialect-flag surface on the two CSV-reading commands.

## ADDED Requirements

### Requirement: Optional explicit CSV dialect flags (CLI-R12)

`sofer codebook` and `sofer profile` SHALL accept optional `--delimiter` /
`--encoding` arguments on both their single-file and `--all-files` forms, defaulting
to `None` ("not supplied"). When supplied, the explicit value SHALL win over the
applicable configured value (single-file: the post-reload tool-wide
`config.CSV_DELIMITER` / `config.CSV_ENCODING`; `codebook --all-files`: the dataset
`[meta]`). When omitted, behaviour SHALL be byte-identical to the pre-change
command — no new line, no changed output.

When at least one explicit value is supplied, the command SHALL echo the supplied
override on **stderr** in a single informational line naming only the supplied
keys (e.g. `  i  Explicit dialect: delimiter=',' encoding='utf-8'`), so the
single-file codebook's stdout stays pure markdown. The `.tsv` format SHALL remain
tab-delimited; the explicit delimiter SHALL apply to `.csv` only.

The `codebook` and `profile` `help=` / `description=` strings SHALL document the new
flags and their "explicit wins over config" precedence.

#### Scenario: flags are listed in help

- GIVEN `sofer codebook --help`
- WHEN rendered
- THEN `--delimiter` and `--encoding` SHALL be listed
- AND the `profile` help SHALL likewise list both flags

#### Scenario: explicit value wins over config

- GIVEN `[tool.sofer] csv_delimiter = ";"` and a `.csv` using `,`
- WHEN `sofer codebook FILE --delimiter ,` runs
- THEN the codebook SHALL reflect the explicit `,`

#### Scenario: omitted flags preserve behaviour

- GIVEN the same invocation without `--delimiter` / `--encoding`
- WHEN it runs
- THEN the output SHALL be byte-identical to the pre-change command
- AND stderr SHALL carry no explicit-dialect line

#### Scenario: explicit dialect echoed on stderr

- GIVEN an explicit `--delimiter` and/or `--encoding` is supplied
- WHEN the command runs
- THEN stderr SHALL carry one line naming the supplied key(s)
- AND stdout SHALL NOT carry the echo

#### Scenario: both commands accept the flags

- GIVEN `sofer profile DATASET --delimiter , --encoding utf-8`
- WHEN it runs
- THEN both explicit values SHALL be applied to the CSV/TSV read
