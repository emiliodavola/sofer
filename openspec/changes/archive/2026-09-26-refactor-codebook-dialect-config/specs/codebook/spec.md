# Delta for codebook

> **Change** `2026-09-26-refactor-codebook-dialect-config` (GitHub #260) · branch
> `refactor/260-codebook-dialect-config` · store **hybrid** (this file + Engram mirror).
>
> **Two modifications, no additions.** CB-R11 and CB-R12 each carry a sentence that pins the
> hardcoded `";"` / `"utf-8-sig"` parameter defaults in `codebook.generate` as immutable. GitHub
> #260 retires those literals — the parameters become **required** keyword arguments, so no caller
> can silently inherit a dialect — and the two sentences are amended. Every scenario of both
> requirements is retained byte-for-byte; CB-R11 gains one scenario pinning the fail-closed
> contract. The `codebook` capability has no `## Test Mapping` table (declared backlog in
> `openspec/test-mapping-registry.md`), so no mapping row changes.

## MODIFIED Requirements

### Requirement: Single-file codebook reads through the resolved tool-wide config (CB-R11)

> Added by change `2026-09-14-fix-cli-codebook-config` (GitHub #182). Amended by change
> `2026-09-26-refactor-codebook-dialect-config` (GitHub #260): the literal defaults in
> `codebook.generate` are removed, so the parameters are required and the invocation passes the
> configured value by construction.

The `sofer codebook FILE` path SHALL pass the resolved tool-wide `config.CSV_DELIMITER` and
`config.CSV_ENCODING` into `codebook.generate`, resolved at call time after the invocation's single
tool-config reload (TC-04) — the same source MSP-R10 requires of the MCP codebook tools. The
dialect parameters of `codebook.generate` and of its readers (`_read_csv`, `_read_tsv`,
`_read_file`) SHALL be required arguments with no literal `";"` / `"utf-8-sig"` default, so a call
that omits them SHALL fail closed (`TypeError`) rather than silently assume a dialect; every
production call site SHALL pass the configured value for its tier.

When the input cannot be read — the configured encoding and the repository's fallback chain are
exhausted (`ValueError`), or the configured encoding names a codec that does not exist (`LookupError`,
reachable per TC-13) — the command SHALL print `Error: <message>` on stderr and SHALL exit non-zero.
It SHALL NOT emit an uncaught traceback, and it SHALL NOT retry `latin-1`/`cp1252`: the fallback
policy remains the repository's existing `utf-8-sig → utf-8` (`src/sofer/_csv_reader.py:27-31`), with
a configured non-UTF-8 encoding honoured first. `generate_all`'s `None` sentinel and its
dataset-`[meta]` resolution (`codebook.py:522-523`) SHALL remain unchanged, as the `--all-files`
tier's configured source.

#### Scenario: Configured delimiter and encoding are what the codebook reflects

- GIVEN `[tool.sofer] csv_delimiter = ","` (and, separately, a non-default `csv_encoding`) and a file matching that configuration
- WHEN `sofer codebook FILE` runs with no `--config`
- THEN the codebook SHALL show the columns induced by the configured delimiter (two columns for a two-field header)
- AND the file SHALL be read under the configured encoding, not a literal `";"` / `"utf-8-sig"` default

#### Scenario: CLI and MCP agree on the same input

- GIVEN the same tool-wide config and the same file
- WHEN the CLI single-file command and the MCP single-file tool both run
- THEN both SHALL produce the same column structure for that file
- AND no MCP source or MCP test SHALL be modified by this change

#### Scenario: Undecodable input yields a diagnostic, never a traceback

- GIVEN a file that cannot be decoded under the configured encoding nor under `utf-8-sig → utf-8`
- WHEN `sofer codebook FILE` runs
- THEN it SHALL print `Error: <message>` on stderr
- AND it SHALL exit non-zero, with no uncaught traceback

#### Scenario: Unknown codec name yields the same diagnostic

- GIVEN `[tool.sofer] csv_encoding` naming a codec that does not exist (valid as a non-empty string under TC-13)
- WHEN `sofer codebook FILE` runs
- THEN the same `Error: <message>` diagnostic SHALL be printed on stderr with a non-zero exit
- AND no traceback SHALL escape the command

#### Scenario: The fallback policy is the existing one, not a new one

- GIVEN the configured encoding is honoured first and then exhausted
- WHEN the readers fall back
- THEN only `utf-8-sig → utf-8` SHALL be tried
- AND `latin-1`/`cp1252` SHALL NOT be added as retries

#### Scenario: Omitting the dialect fails closed

- GIVEN `codebook.generate`, `_read_csv`, `_read_tsv`, or `_read_file`
- WHEN a caller omits the required delimiter/encoding argument
- THEN the call SHALL raise `TypeError`
- AND it SHALL NOT fall back to a hardcoded `";"` / `"utf-8-sig"` default (issue #260, AGENTS.md rule 3)

---

### Requirement: Explicit CSV dialect override wins over config (CB-R12)

> Added by change `2026-09-25-csv-dialect-override` (GitHub #204). Amended by change
> `2026-09-26-refactor-codebook-dialect-config` (GitHub #260): `codebook.generate`'s dialect
> parameters are now required keyword arguments, so the "defaults unchanged" clause no longer
> applies to them; only `generate_all`'s `None` sentinel remains.

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
is supplied, the command SHALL echo it on stderr. `generate_all`'s `None` sentinel
SHALL remain unchanged; `codebook.generate`'s dialect parameters SHALL be required
keyword arguments (CB-R11, issue #260), so every call site passes a resolved value
and no literal default exists to inherit.

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
