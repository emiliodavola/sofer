# Codebook Specification

## Purpose

Automated markdown codebook generation from tabular data files. Documents
column name, inferred type, unique value count, missing percentage, and a
sample value. Supports single-file and batch (TOML-driven) generation.

## Requirements

### Requirement: Multi-Format Reading (CB-R01)

The system MUST read `.csv`, `.tsv`, `.parquet`, `.xlsx`, and `.jsonl` files
through format-appropriate readers that return uniform columnar data for
analysis. The existing string-based type inference logic MUST remain
unchanged for all formats. For typed formats (Parquet), the system SHOULD
surface the storage dtype alongside the inferred type.

#### Scenario: Read CSV with existing inference

- GIVEN a `.csv` file with numeric and text columns
- WHEN the codebook is generated
- THEN column types SHALL be inferred from string values as today

#### Scenario: Read Parquet with dtype display

- GIVEN a `.parquet` file with int64 and bool columns
- WHEN the codebook is generated
- THEN inferred types SHALL be computed from stringified values
- AND the storage dtype SHOULD appear as an extra column

#### Scenario: Read XLSX with multi-format

- GIVEN a `.xlsx` file with multiple columns
- WHEN the codebook is generated
- THEN column headers and values SHALL be extracted for analysis

---

### Requirement: Single-File Generation (CB-R02)

The existing `sofer codebook <file>` interface MUST remain functional
for all supported formats. Output SHALL go to stdout by default or to `-o
<file>`. The positional argument MUST retain the name `csv` with `metavar`
changed to `FILE` for backward compatibility.

#### Scenario: CSV backward compatibility

- GIVEN a `.csv` file from a prior workflow
- WHEN `sofer codebook data.csv` is called
- THEN the output SHALL be identical to the current implementation

#### Scenario: Parquet single-file

- GIVEN a `.parquet` file at `data/survey.parquet`
- WHEN `sofer codebook data/survey.parquet` is called
- THEN a markdown codebook SHALL be printed to stdout

#### Scenario: Output to file

- GIVEN any supported-format file
- WHEN `sofer codebook data.csv -o out.md` is called
- THEN the codebook SHALL be written to `out.md`

---

### Requirement: Batch Generation (CB-R03)

When `--all-files` is specified, the system MUST generate one codebook for every `[[file]]` entry in the TOML config that points to a supported-format file; for `.xlsx` with N sheets it MUST generate N codebooks per § CB-R09. Directories and unsupported formats MUST be skipped with a warning. Each codebook MUST be written to `codebooks/<rel-stem>.md` for single-table formats, or `codebooks/<rel>/<stem>__<sanitized>.md` per sheet for multisheet `.xlsx` (single sheet → `stem.md`). No format suffix SHALL be appended. The collision map MUST be built from sheet-expanded output paths; when two or more expanded outputs collide, the system MUST print an error naming each source file (including sheet suffix), MUST exit 1, and MUST NOT write a codebook for any colliding file; non-colliding files SHALL still be written before the error is raised.

(Previously: single output per TOML entry; collision key ignored sheet suffixes; `.xlsx` emitted only `wb.active`.)

#### Scenario: Batch from TOML config

- GIVEN `dataset.toml` with `[[file]]` entries for `data/a.csv`, `data/b.parquet`, and `data/c.docx`
- WHEN `sofer codebook --config dataset.toml --all-files` is called
- THEN `codebooks/a.md` SHALL be generated for `a.csv`
- AND `codebooks/b.md` SHALL be generated for `b.parquet`
- AND `c.docx` SHALL be skipped with a warning

#### Scenario: Directory entry skipped

- GIVEN a `[[file]]` entry pointing to a directory
- WHEN `--all-files` executes
- THEN a warning SHALL be emitted
- AND no codebook SHALL be generated for that entry

#### Scenario: Nested file keeps its relative path

- GIVEN a `[[file]]` entry for `data/Labels/etiquetas_a.csv`
- WHEN `--all-files` executes
- THEN `codebooks/Labels/etiquetas_a.md` SHALL be generated

#### Scenario: Same-stem collision errors

- GIVEN `data/PROV.csv` and `data/PROV.parquet` in the same folder (both map to `codebooks/PROV.md`)
- WHEN `--all-files` executes
- THEN an error SHALL be printed naming both `PROV.csv` and `PROV.parquet`
- AND exit code SHALL be 1
- AND no codebook SHALL be written for either file

#### Scenario: Sheet-aware collision via expanded keys

- GIVEN `data/a__ventas.xlsx` sheet `Ventas` (→ `codebooks/a__ventas.md`) and `data/a_ventas.csv` (→ `codebooks/a_ventas.md` normalized via `normalize_parquet_remote` `__+`→`_`)
- WHEN `--all-files` executes and both resolve to the same normalized key
- THEN the collision map SHALL treat them as colliding on the expanded key
- AND the error SHALL name both sources and no file SHALL be written for either

---

### Requirement: Root Index (CB-R04)

When `--all-files` is used, the system MUST generate the root `codebook.md` at `write_root / "codebook.md"`: the CLI `codebook --all-files` SHALL resolve `write_root` to the package `build_dir` (or `--output` override), matching `sofer_codebook_all` and where `publish` collects codebooks; the `generate_all` domain function with `output_dir is None` SHALL still write `cache/codebook.md` (Option B only when `output_dir` is set). The index SHALL contain a TOC with relative links under `codebooks/` prefix (matching uploader's HF staging), not `data/codebooks/`, colocated with per-file `codebooks/<rel-stem>.md` (or per-sheet `codebooks/<rel>/<stem>__<sanitized>.md`). System MUST NOT write `base_dir/codebook.md` in standalone mode. `**Tables:**` SHALL count sheets (one per codebook file), and `**Total columns:**` SHALL sum columns across all emitted codebooks.

(Previously: Tables counted TOML entries, not sheets; only `stem.md` links. `codebook --all-files` wrote to `cache/codebook.md` instead of the package `build_dir`.)

#### Scenario: Standalone batch writes to build_dir

- GIVEN `dataset.toml` in `/proj/` with `raw/a.csv` and `raw/b.parquet`
- WHEN `sofer codebook --config dataset.toml --all-files` completes
- THEN `/proj/build/codebook.md` SHALL exist, `/proj/build/codebooks/a.md` and `b.md` SHALL exist
- AND `/proj/cache/codebook.md` SHALL NOT exist, links SHALL be `codebooks/a.md` and `codebooks/b.md`

#### Scenario: Prepare mode writes to build

- GIVEN `generate_all` called with `output_dir=/proj/build`
- WHEN `--all-files` executes via prepare
- THEN `/proj/build/codebook.md` and `/proj/build/codebooks/*.md` SHALL exist

#### Scenario: Nested subdirectories preserved in links

- GIVEN `[[file]]` for `raw/Labels/etiquetas_a.csv`
- WHEN standalone batch generates index
- THEN link SHALL be `codebooks/Labels/etiquetas_a.md` (and file at `build/codebooks/Labels/etiquetas_a.md`)

#### Scenario: Index links are relative paths

- GIVEN generated `cache/codebook.md`
- WHEN any codebook link is extracted
- THEN path SHALL be relative (e.g., `codebooks/DPTO.md`) and MUST NOT be an absolute path

#### Scenario: Multisheet index lists per-sheet links

- GIVEN `Report.xlsx` with sheets `Ventas`, `Costos` under `data/`
- WHEN index is generated
- THEN it SHALL contain `codebooks/Report__ventas.md — N columns` and `codebooks/Report__costos.md — M columns`
- AND `**Tables:** 2` SHALL be shown

---

### Requirement: Error Handling (CB-R06)

The system MUST handle unsupported formats (skip + warn), missing files (skip
+ warn), empty files (generate minimal codebook), unreadable files (skip +
error), and missing/malformed TOML (error + exit 1).

#### Scenario: Unsupported format

- GIVEN a file `data/notes.txt`
- WHEN codebook generation is attempted
- THEN a warning SHALL be emitted and the file SHALL be skipped

#### Scenario: Missing file

- GIVEN a `[[file]]` entry pointing to a non-existent path
- WHEN `--all-files` executes
- THEN a warning SHALL be emitted and the file SHALL be skipped

#### Scenario: Empty file

- GIVEN a supported-format file with headers but zero data rows
- WHEN the codebook is generated
- THEN a minimal codebook with column names and "unknown" types SHALL be
  produced

#### Scenario: Malformed TOML

- GIVEN `dataset.toml` with invalid TOML syntax
- WHEN `--all-files` is called
- THEN an error message SHALL be printed
- AND exit code SHALL be 1

---

### Requirement: Unique counts exclude missing sentinels (CB-R07)

> Added by change `publish-readme-bugs` (archived 2026-08-24).

For every format, the per-column `unique` statistic SHALL count DISTINCT
NON-MISSING values only. Missing-value sentinels ("", "NA", "NULL", "N/A", and
null/None) MUST NOT be counted as distinct values. This aligns `codebook.py`
with its own missing-percentage computation (which already filters sentinels)
and with the documented behavior of the Dataset Card's schema report.

(Previously: `n_unique = len(set(col_values))` counted sentinels as values,
so a column of ["A", "", "NA"] reported unique=3 while missing% excluded them —
inconsistent within the same output table.)

#### Scenario: Sentinels not counted as values

- GIVEN a column whose values are ["A", "", "NA", "B", "NULL"]
- WHEN the codebook is generated
- THEN unique SHALL be 2
- AND missing percentage SHALL reflect the 3 missing rows

#### Scenario: Column without sentinels unchanged

- GIVEN a column whose values are all non-missing
- WHEN the codebook is generated
- THEN unique SHALL equal the count of distinct values, as today

---

### Requirement: --max-sample default from config (CB-R08)

> Added by change `publish-readme-bugs` (archived 2026-08-24).

The `codebook` command's `--max-sample` default SHALL come from the
`CODEBOOK_MAX_SAMPLE` constant loaded from `[tool.sofer] codebook_max_sample`
(default `100_000`) via `config.py`. The CLI parser MUST NOT embed a numeric
literal default; the argparse help text SHALL state the configured value.

(Previously: `cli.py` hardcoded `default=100_000`, bypassing the user's TOML
config — AGENTS rule 1.)

#### Scenario: TOML override respected by CLI default

- GIVEN `[tool.sofer] codebook_max_sample = 50000`
- WHEN `sofer codebook data.csv` runs without `--max-sample`
- THEN sampling SHALL cap at 50000 rows

#### Scenario: Explicit flag still wins

- GIVEN any configured value
- WHEN `sofer codebook data.csv --max-sample 1000` runs
- THEN sampling SHALL cap at 1000 rows

---

### Requirement: Multisheet XLSX codebook per sheet (CB-R09)

The system MUST support `.xlsx` files with multiple sheets by emitting one codebook per sheet at `codebooks/<rel>/<stem>__<sanitized>.md`, reusing `sanitize_sheet_name` verbatim with `seen` dedup (`_<n>`). Single-sheet `.xlsx` MUST remain `codebooks/<rel>/<stem>.md`. Every sheet MUST be read via a shared `_read_xlsx_sheets` helper; `generate()` MUST stay backward compatible (single-sheet path). Empty/header-only sheets MUST emit a placeholder codebook, not crash.

#### Scenario: CB-R09.01 single-sheet stays stem.md

- GIVEN an `.xlsx` with 1 sheet
- WHEN `generate()` or `generate_all()` processes it
- THEN exactly one file `codebooks/<stem>.md` SHALL be written
- AND the file SHALL be identical to the pre-change single-sheet output

#### Scenario: CB-R09.02 multisheet 2 sheets yields 2 files

- GIVEN `Report.xlsx` with sheets `Ventas` and `Costos`
- WHEN `generate_all()` runs
- THEN `codebooks/Report__ventas.md` and `codebooks/Report__costos.md` SHALL both exist
- AND each file's title/table SHALL reflect only that sheet's headers/columns/dtypes

#### Scenario: CB-R09.03 dedup via sanitize_sheet_name + seen

- GIVEN an `.xlsx` with sheets `Ventas` and `VENTAS` (both sanitize to `ventas`)
- WHEN codebooks are emitted
- THEN outputs SHALL be `__ventas.md` and `__ventas_2.md`
- AND a third duplicate SHALL be `__ventas_3.md`

#### Scenario: CB-R09.04 batch --all-files expands to N

- GIVEN `dataset.toml` with `[[file]]` for `data/a.csv` and `data/report.xlsx` (2 sheets)
- WHEN `sofer codebook --all-files` runs
- THEN 3 codebooks SHALL be counted (1 + 2 sheets) plus the root index

#### Scenario: CB-R09.05 index counts sheets

- GIVEN the previous batch
- WHEN the root `codebook.md` is written
- THEN `**Tables:** 3 | **Total columns:** <sum across all sheets>` SHALL be shown
- AND `## Contents` SHALL list one link per sheet file relative to `write_root`

#### Scenario: CB-R09.06 empty sheet placeholder

- GIVEN an `.xlsx` where sheet 2 has no rows or `header_row is None`
- WHEN its codebook is built
- THEN the file SHALL contain `**No data rows found**`
- AND the command SHALL NOT raise

#### Scenario: CB-R09.07 sanitize reuse invariant

- GIVEN any sheet name (e.g. `DATA GOT Ano`, `a__b`, `""` → `sheet`)
- WHEN sanitized for the codebook stem
- THEN the result SHALL equal `sanitize_sheet_name` from `_converters.py` with identical collapse/strip/fallback
- AND dedup logic SHALL match `_convert_xlsx_to_parquet` (`seen` dict, `_<n>` suffix)
