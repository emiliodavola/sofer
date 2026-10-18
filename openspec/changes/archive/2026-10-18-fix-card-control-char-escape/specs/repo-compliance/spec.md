# Delta for repo-compliance

> **Change** `2026-10-18-fix-card-control-char-escape` (issue **#348**) · branch
> `fix/348-card-control-char-escape` from `dev@c68e090` · store **hybrid**.
>
> **One modified requirement, two added scenarios.** RC-R21 gains the rendering
> rule for data-derived cells.
>
> **Rule-6 resolution.** `repo-compliance` is a permanent declared-backlog spec
> (`openspec/test-mapping-registry.md:40`), so the new scenarios are unmapped and
> the registry is not edited; `scripts/check_test_mapping.py` still exits 0.

## MODIFIED Requirements

### Requirement: Collapsible Data Fields per sheet with threshold (RC-R21) — Modified 2026-10-18, fix-card-control-char-escape

The system MUST render the Dataset Card's Data Fields as per-sheet collapsible tables. `build_dataset_card(cfg, schema, row_counts)` SHALL group `ColumnSchema` entries by `origin` sheet fragment (derived from `origin`/`staging_dir` normalized `stem__sheet.parquet` key; when grouping yields one label it is the file stem). Each group SHALL be rendered as its own `<details><summary>Data Fields -- <label> (N columns)</summary>` block containing that group's `| Column | Type | File | … |` table, with a **blank line after `</summary>`** so HF/GFM renders the table inside the details (HF `<details>` requirement). Wrapping SHALL be gated by `config.CARD_COLLAPSE_THRESHOLD` (default 15) via dynamic `config` read at call time:

- Collapse a group WHEN `len(group.columns) > threshold` (per-table threshold) **OR** `len(groups) > 1` (multisheet/multi-file → always per-sheet collapsibles, each independent).
- Single-group (`len(groups)==1`) with `len(columns) <= threshold` SHALL render an unwrapped `### Data Fields` table (backward compat, no `<details>`).
- Single-group above threshold SHALL also wrap in one `<details>` (per-table threshold applies even for single-file).
- `dataset_info.features` SHALL stay flat (no collapse); collapse affects only the body Data Fields section.
- Section titles MUST match staged artifact stems `__<sanitized>` (post-sanitize, using same `sanitize_sheet_name` contract as codebook/prepare), and both sheets MUST appear when multisheet data is present.
- Grouping for display SHALL be by `origin` (one block per table), NEVER by config group: two origins that share one column signature still render one independent block each, so every table's own columns stay visible (`2026-10-15-fix-schema-relation-map`, issue #304).
- Every data-derived string cell of those tables (the column name, the File cell and the Example cell, in both the flat and the per-sheet branches) SHALL be rendered as printable text (`2026-10-18-fix-card-control-char-escape`, issue #348): a character in the Unicode `Cc` category SHALL be rendered as its `\xNN` escape, `|` SHALL be escaped as `\|` so it cannot split the row, and the code-span fence SHALL be one backtick, or two when the value itself contains a backtick. The generated card SHALL therefore contain no raw control byte other than the line breaks the generator itself writes, and the sampled value in the Parquet SHALL stay untouched.

#### Scenario: RC-R21.01 single-file below threshold stays unwrapped

- GIVEN one file `a.csv` with 8 columns and `card_collapse_threshold=15`
- WHEN `build_dataset_card` runs
- THEN output SHALL contain `### Data Fields` with a single flat table
- AND SHALL NOT contain `<details>`

#### Scenario: RC-R21.10 a control-character sample does not make the card binary (#348) — Added

- GIVEN one column whose sampled value is `"\x00"` (the corpus of #348: a one-row table whose only value is a NUL)
- WHEN `build_dataset_card` runs
- THEN the rendered card SHALL hold no `Cc` character other than `\n`/`\r`
- AND the value SHALL appear as the printable escape `\x00`

#### Scenario: RC-R21.11 a separator in a sample cannot split the row (#348) — Added

- GIVEN one column whose sampled value is `"a|b"` and another whose value contains a backtick
- WHEN `build_dataset_card` runs
- THEN the value SHALL be rendered as `a\|b` inside one cell and the backtick value SHALL be fenced with two backticks
- AND the row SHALL still carry exactly the table's seven cells
