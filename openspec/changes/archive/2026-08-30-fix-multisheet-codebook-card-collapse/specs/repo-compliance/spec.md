# Delta for repo-compliance

## ADDED Requirements

### Requirement: Collapsible Data Fields per sheet with threshold (RC-R21)

The system MUST render the Dataset Card's Data Fields as per-sheet collapsible tables. `build_dataset_card(cfg, schema, row_counts)` SHALL group `ColumnSchema` entries by `origin` sheet fragment (derived from `origin`/`staging_dir` normalized `stem__sheet.parquet` key; when grouping yields one label it is the file stem). Each group SHALL be rendered as its own `<details><summary>Data Fields -- <label> (N columns)</summary>` block containing that group's `| Column | Type | File | … |` table, with a **blank line after `</summary>`** so HF/GFM renders the table inside the details (HF `<details>` requirement). Wrapping SHALL be gated by `config.CARD_COLLAPSE_THRESHOLD` (default 15) via dynamic `config` read at call time:

- Collapse a group WHEN `len(group.columns) > threshold` (per-table threshold) **OR** `len(groups) > 1` (multisheet/multi-file → always per-sheet collapsibles, each independent).
- Single-group (`len(groups)==1`) with `len(columns) <= threshold` SHALL render an unwrapped `### Data Fields` table (backward compat, no `<details>`).
- Single-group above threshold SHALL also wrap in one `<details>` (per-table threshold applies even for single-file).
- `dataset_info.features` SHALL stay flat (no collapse); collapse affects only the body Data Fields section.
- Section titles MUST match staged artifact stems `__<sanitized>` (post-sanitize, using same `sanitize_sheet_name` contract as codebook/prepare), and both sheets MUST appear when multisheet data is present.

#### Scenario: RC-R21.01 single-file below threshold stays unwrapped

- GIVEN one file `a.csv` with 8 columns and `card_collapse_threshold=15`
- WHEN `build_dataset_card` runs
- THEN output SHALL contain `### Data Fields` with a single flat table
- AND SHALL NOT contain `<details>`

#### Scenario: RC-R21.02 single-file above threshold collapses even when alone

- GIVEN one file `a.csv` with 20 columns and `threshold=15`
- WHEN `build_dataset_card` runs
- THEN output SHALL contain one `<details><summary>Data Fields -- a (20 columns)</summary>`
- AND the table SHALL be inside the `<details>` with a blank line after `</summary>`

#### Scenario: RC-R21.03 multi-sheet yields per-table details — cada tabla por separado

- GIVEN `Report.xlsx` producing `report__ventas.parquet` (4 cols) and `report__costos.parquet` (3 cols)
- WHEN the card is generated (`len(groups)==2`)
- THEN output SHALL contain two independent blocks: `<details><summary>Data Fields -- ventas (4 columns)</summary>` and `<details><summary>Data Fields -- costos (3 columns)</summary>`
- AND there SHALL be exactly 2 `<details>` elements (not one mega wrapper)
- AND each block SHALL contain a blank line after its `</summary>` before the `| Column |` header
- AND both `ventas` and `costos` SHALL appear (no sheet dropped)

#### Scenario: RC-R21.04 section titles match staged stems __sanitized

- GIVEN staged Parquets `data_got_all_aristas.parquet` and `data_got_all_nodos.parquet` (from `DATA_GOT_ALL.xlsx`)
- WHEN the card is generated
- THEN summaries SHALL be `Data Fields -- aristas (N columns)` and `Data Fields -- nodos (M columns)` matching the `__<sanitized>` stems
- AND the File column inside each table SHALL show the corresponding `origin` (`data_got_all_aristas.parquet` / `data_got_all_nodos.parquet`)

#### Scenario: RC-R21.05 HF blank-line requirement

- GIVEN any collapsed group
- WHEN its `<details>` is rendered
- THEN bytes SHALL contain `</summary>\n\n| Column |`
- AND HF viewer SHALL render the table inside the collapsed block (not as raw text)

#### Scenario: RC-R21.06 backward compat — single-file dataset card unchanged

- GIVEN a dataset with one CSV of 10 columns, `threshold=15`, no XLSX sheets
- WHEN the card is generated
- THEN the Data Fields section SHALL be identical to the pre-change flat table (no `<details>`, File column populated per RC-R06)

#### Scenario: RC-R21.07 threshold boundary

- GIVEN one file with exactly 15 columns and `threshold=15`
- WHEN the card is generated
- THEN the table SHALL NOT be collapsed (collapse only when `>` threshold; `len(groups)==1`)

#### Scenario: RC-R21.08 mixed small sheets still per-sheet collapse via group count

- GIVEN two sheets each with 5 columns (both below threshold) and `threshold=15`
- WHEN the card is generated
- THEN both tables SHALL still be wrapped (each in its own `<details>`) because `len(groups)>1`
