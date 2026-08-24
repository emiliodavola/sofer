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

When `--all-files` is specified, the system MUST generate one codebook for
every `[[file]]` entry in the TOML config that points to a supported-format
file. Directories and unsupported formats MUST be skipped with a warning.
Each codebook MUST be written to `data/codebooks/<rel-stem>.md`, where
`<rel-stem>` is the file's path relative to the `data/` directory with the
extension replaced by `.md` (e.g. `data/DPTO.csv` → `data/codebooks/DPTO.md`;
`data/Labels/etiquetas_a.csv` → `data/codebooks/Labels/etiquetas_a.md`). No
format suffix SHALL be appended. When two or more files resolve to the same
codebook path, the system MUST print an error naming each source file, MUST
exit 1, and MUST NOT write a codebook for any colliding file.

#### Scenario: Batch from TOML config

- GIVEN `dataset.toml` with `[[file]]` entries for `data/a.csv`,
  `data/b.parquet`, and `data/c.docx`
- WHEN `sofer codebook --config dataset.toml --all-files` is called
- THEN `data/codebooks/a.md` SHALL be generated for `a.csv`
- AND `data/codebooks/b.md` SHALL be generated for `b.parquet`
- AND `c.docx` SHALL be skipped with a warning

#### Scenario: Directory entry skipped

- GIVEN a `[[file]]` entry pointing to a directory
- WHEN `--all-files` executes
- THEN a warning SHALL be emitted
- AND no codebook SHALL be generated for that entry

#### Scenario: Nested file keeps its relative path

- GIVEN a `[[file]]` entry for `data/Labels/etiquetas_a.csv`
- WHEN `--all-files` executes
- THEN `data/codebooks/Labels/etiquetas_a.md` SHALL be generated

#### Scenario: Same-stem collision errors

- GIVEN `data/PROV.csv` and `data/PROV.parquet` in the same folder (both map to `data/codebooks/PROV.md`)
- WHEN `--all-files` executes
- THEN an error SHALL be printed naming both `PROV.csv` and `PROV.parquet`
- AND exit code SHALL be 1
- AND no codebook SHALL be written for either file

---

### Requirement: Root Index (CB-R04)

When `--all-files` is used, the system MUST generate a root `codebook.md` in
the TOML config's directory containing a table of contents with relative links
to each generated codebook and a dataset summary. The links SHALL point to the
per-file codebook paths under the `codebooks/` prefix (matching the uploader's
HF repository staging layout), not under `data/codebooks/`.

(Previously: links pointed to `data/codebooks/` — produced 404 on Hugging Face
Hub because the uploader stages codebooks under `codebooks/`.)

#### Scenario: Root index after batch generation

- GIVEN `dataset.toml` in `/proj/` with files in `data/a.csv` and
  `data/b.parquet`
- WHEN `sofer codebook --config dataset.toml --all-files` completes
- THEN `/proj/codebook.md` SHALL exist
- AND SHALL contain links to `codebooks/a.md` and `codebooks/b.md`

#### Scenario: Nested subdirectories preserved in links

- GIVEN a `[[file]]` entry for `data/Labels/etiquetas_a.csv`
- WHEN `--all-files` generates the root index
- THEN the link SHALL point to `codebooks/Labels/etiquetas_a.md`

#### Scenario: Index links are relative paths

- GIVEN generated root index `codebook.md`
- WHEN any codebook link is extracted from the index
- THEN the path SHALL be a relative path (e.g., `codebooks/DPTO.md`)
- AND MUST NOT be an absolute path

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
