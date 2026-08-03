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

When `--all-files` is specified, the system MUST generate a codebook for
every `[[file]]` entry in the TOML config that points to a supported-format
file. Directories and unsupported formats MUST be skipped with a warning.
Each codebook MUST be placed alongside its data file as `codebook.md`.

#### Scenario: Batch from TOML config

- GIVEN `dataset.toml` with `[[file]]` entries for `data/a.csv`,
  `data/b.parquet`, and `data/c.docx`
- WHEN `sofer codebook --config dataset.toml --all-files` is called
- THEN `data/codebook.md` SHALL be generated alongside `a.csv`
- AND `data/codebook.md` SHALL be generated alongside `b.parquet`
- AND `c.docx` SHALL be skipped with a warning

#### Scenario: Directory entry skipped

- GIVEN a `[[file]]` entry pointing to a directory
- WHEN `--all-files` executes
- THEN a warning SHALL be emitted
- AND no codebook SHALL be generated for that entry

---

### Requirement: Root Index (CB-R04)

When `--all-files` is used, the system MUST generate a root `codebook.md` in
the TOML config's directory containing a table of contents with relative
links to each generated codebook and a dataset summary.

#### Scenario: Root index after batch generation

- GIVEN `dataset.toml` in `/proj/` with files in `data/a.csv` and
  `data/b.parquet`
- WHEN `sofer codebook --config dataset.toml --all-files` completes
- THEN `/proj/codebook.md` SHALL exist
- AND SHALL contain links to each generated per-file codebook

---

### Requirement: Output Collision (CB-R05)

When multiple supported files share the same parent directory, the system
MUST use format-specific suffixes (`codebook_<fmt>.md`) and emit a warning.

#### Scenario: Same-dir multi-format collision

- GIVEN `data/PROV.parquet` and `data/PROV.csv` in the same directory
- WHEN `--all-files` generates codebooks
- THEN `data/codebook_parquet.md` SHALL be written for the parquet file
- AND `data/codebook_csv.md` SHALL be written for the CSV file
- AND a warning SHALL be emitted about the collision

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
