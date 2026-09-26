# Spec delta: 2026-09-25-csv-dialect-override (mcp-server)

> **Change:** `2026-09-25-csv-dialect-override` (GitHub #204) · branch
> `feat/204-csv-dialect-override`.
>
> MSP-R06 (scan non-interactivity) is untouched. MSP-R18 adds the optional dialect
> parameters to the four CSV-reading tools. The issue's "scan tools" mention is
> realized by the `profile` family: the scan tools never read CSV bytes, so a
> dialect parameter there would be inert (design D6/non-goal).

## ADDED Requirements

### Requirement: Optional explicit CSV dialect parameters (MSP-R18)

`sofer_codebook`, `sofer_codebook_all`, `sofer_profile`, and `sofer_profile_all`
SHALL each expose optional `delimiter` / `encoding` parameters defaulting to
`None` ("not supplied"). Their descriptions SHALL state that the configured value
applies when omitted. Resolution SHALL be **explicit parameter → resolved config
(tool-wide post-reload `config.CSV_*` for `sofer_codebook` / `sofer_profile`;
dataset `[meta] cfg.csv_*` for `sofer_codebook_all`; tool-wide for
`sofer_profile_all`) → the existing reader fallback**. The explicit value SHALL
win. `None` SHALL be the only "not supplied" signal, and the omitted path SHALL be
byte-identical to the pre-change tool output.

When at least one explicit parameter is supplied, the tool SHALL add a `dialect`
key to its **successful** return envelope (e.g. `{"delimiter": ",", "encoding":
null}`) echoing the supplied override, so the result is traceable. The key SHALL
be declared in the tool's `output_schema` (so FastMCP validation does not drop it)
and SHALL be `null` when neither parameter is supplied — the dialect resolution
itself is unchanged in that case. Error/refusal envelopes are not required to
carry it (the read may never have happened). No parameter SHALL be
required, and MSP-R06's non-interactivity contract SHALL hold — an omitted
optional parameter is not a prompt. `.tsv` SHALL remain tab-delimited; the
explicit delimiter SHALL apply to `.csv`.

#### Scenario: explicit delimiter wins over config

- GIVEN `csv_delimiter = ";"` in `[tool.sofer]` and a `.csv` using `,`
- WHEN `sofer_codebook(path, delimiter=",")` runs
- THEN the codebook SHALL reflect the explicit `,`

#### Scenario: omitted parameters are unchanged

- GIVEN the same file and config
- WHEN `sofer_codebook(path)` runs without the parameters
- THEN the resolved dialect SHALL be the configured one
- AND the envelope `dialect` SHALL be `null`

#### Scenario: dialect echo when supplied

- GIVEN an explicit `delimiter` and/or `encoding`
- WHEN any of the four tools runs
- THEN its envelope SHALL carry a `dialect` object echoing the supplied value(s)
- AND `dialect` SHALL be `null` when neither is supplied

#### Scenario: batch parameter wins over dataset [meta]

- GIVEN a dataset whose `[meta] csv_delimiter` is `;` and CSV files using `,`
- WHEN `sofer_codebook_all(config, delimiter=",")` runs
- THEN every emitted codebook SHALL reflect the explicit `,`

#### Scenario: every parameter has a description

- GIVEN `tools/list` for the four tools
- WHEN the input schemas are inspected
- THEN `delimiter` and `encoding` SHALL each carry a description stating the fallback
- AND neither SHALL be in the `required` list

#### Scenario: scan tools gain no inert parameter

- GIVEN `tools/list` for `sofer_scan_dry_run` / `sofer_scan_apply`
- WHEN the input schemas are inspected
- THEN neither SHALL expose `delimiter` or `encoding`
- AND their behaviour SHALL be unchanged
