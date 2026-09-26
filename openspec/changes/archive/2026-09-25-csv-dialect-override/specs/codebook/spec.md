# Spec delta: 2026-09-25-csv-dialect-override (codebook)

> **Change:** `2026-09-25-csv-dialect-override` (GitHub #204) · branch
> `feat/204-csv-dialect-override`.
>
> CB-R11 (single-file reads through the resolved tool-wide config) is left intact;
> CB-R12 adds the **additive** explicit override above it. `codebook.generate` /
> `generate_all` parameter defaults are unchanged for direct library callers.

## ADDED Requirements

### Requirement: Explicit CSV dialect override wins over config (CB-R12)

`sofer codebook FILE` and `sofer codebook --all-files` SHALL accept optional
`--delimiter` / `--encoding`. The resolution order SHALL be **explicit flag →
resolved config (tool-wide or dataset, per the command's existing tier) → the
existing reader fallback**. For the single-file tier the configured value is the
post-reload `config.CSV_DELIMITER` / `config.CSV_ENCODING` (CB-R11); for
`--all-files` it is `cfg.csv_delimiter` / `cfg.csv_encoding` from the dataset
`[meta]` (CB-R03/CB-R10). The explicit value SHALL win over whichever tier applies.

`None` (the argparse default) SHALL be the only "not supplied" signal, and the
omitted path SHALL be byte-identical to the pre-change behaviour. `.tsv` files
SHALL remain tab-delimited by format; the explicit delimiter SHALL apply to `.csv`
and the explicit encoding SHALL apply to `.csv` and `.tsv`. When an explicit value
is supplied, the command SHALL echo it on stderr. `codebook.generate`'s and
`generate_all`'s parameter defaults SHALL remain unchanged.

#### Scenario: Explicit delimiter wins over a disagreeing tool-wide config

- GIVEN `[tool.sofer] csv_delimiter = ";"` and a `.csv` whose real delimiter is `,`
- WHEN `sofer codebook FILE --delimiter ,` runs
- THEN the codebook SHALL show the `,`-induced columns
- AND the explicit value SHALL NOT be ignored in favour of the configured `;`

#### Scenario: Explicit encoding wins over a disagreeing tool-wide config

- GIVEN `[tool.sofer] csv_encoding = "utf-8-sig"` and a file readable only as a supplied encoding
- WHEN `sofer codebook FILE --encoding <enc>` runs
- THEN the file SHALL be read under the explicit encoding first

#### Scenario: Omitted override is unchanged

- GIVEN the same file and `[tool.sofer]` config
- WHEN `sofer codebook FILE` runs without `--delimiter` / `--encoding`
- THEN the codebook SHALL be byte-identical to the pre-change run
- AND no explicit-dialect line SHALL be printed to stderr

#### Scenario: --all-files override wins over the dataset [meta]

- GIVEN a dataset whose `[meta] csv_delimiter` is `;` and CSV files using `,`
- WHEN `sofer codebook --all-files --delimiter ,` runs
- THEN every emitted codebook SHALL reflect the explicit `,`

#### Scenario: Explicit dialect is echoed

- GIVEN an explicit `--delimiter` and/or `--encoding` is supplied
- WHEN the command runs
- THEN the supplied override SHALL be echoed on stderr
- AND stdout SHALL remain the codebook markdown (single-file) or the batch report

#### Scenario: .tsv stays tab-delimited

- GIVEN a `.tsv` file and an explicit `--delimiter ,`
- WHEN the codebook is generated
- THEN the file SHALL still be read tab-delimited
- AND the explicit delimiter SHALL NOT change the `.tsv` column split
