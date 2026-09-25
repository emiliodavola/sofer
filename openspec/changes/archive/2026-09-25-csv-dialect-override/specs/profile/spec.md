# Spec delta: 2026-09-25-csv-dialect-override (profile)

> **Change:** `2026-09-25-csv-dialect-override` (GitHub #204) · branch
> `feat/204-csv-dialect-override`.
>
> PRF-02's config-driven read is left intact; PRF-07 adds the **additive**
> explicit override above it for the CSV/TSV read path.

## ADDED Requirements

### Requirement: Explicit CSV dialect override for profile (PRF-07)

`sofer profile DATASET` and `sofer profile --all-files` SHALL accept optional
`--delimiter` / `--encoding`. The resolution order SHALL be **explicit flag →
resolved config (tool-wide `config.CSV_DELIMITER` / `config.CSV_ENCODING` for the
single-file tier; dataset `[meta] cfg.csv_delimiter` / `cfg.csv_encoding` is not
used by the batch tier today, so the tool-wide values apply) → the existing
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
