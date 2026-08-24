# Spec: repo-compliance — Dataset Card, LICENSE, and Schema Documentation

- **Change:** hf-dataset-compliance
- **Capability:** `repo-compliance` (new)
- **Status:** Draft
- **Author:** sdd-spec executor
- **Date:** 2026-07-30

---

## 1. Overview

The `repo-compliance` capability generates the three files that turn a raw Hugging
Face dataset repository into a standards-compliant dataset: a **Dataset Card**
(`README.md` with YAML frontmatter), a **LICENSE** file, and an embedded **schema
report** inside the Dataset Card body.

These files are produced **before** any data files are pushed to the Hub, so the
repository is compliant from the moment its first commit lands.

### 1.1 Design constraints

- **Pure functions** — every public function in the module returns a string or
  structured data; none write files, make network calls, or mutate global state.
- **Backward-compatible TOML** — all new `[meta]` fields are optional.  Existing
  TOML files without them produce a valid (though minimal) Dataset Card.
- **`PyYAML` for YAML frontmatter** — the YAML metadata section is assembled as a
  Python `dict` and serialised via `yaml.safe_dump()`.  `PyYAML` is a standard
  choice available as a transitive dependency in most ML/Python environments,
  and unlike `tomli_w.dumps()` it outputs standard YAML (`key: value`) syntax
  that the Hub frontmatter parser expects.

---

## 2. Data Model — new `[meta]` fields

### 2.1 `DatasetConfig` additions

The following fields SHALL be added to the `DatasetConfig` dataclass in
`src/sofer/model.py`.  Every field MUST default to a value that produces
sensible output when the field is absent from the TOML.

| Field | Type | Default | YAML frontmatter key | Description |
|-------|------|---------|----------------------|-------------|
| `language` | `list[str]` | `field(default_factory=list)` | `language` | ISO 639-1 codes (e.g. `["es", "ay"]`). |
| `pretty_name` | `str` | `""` | `pretty_name` | Human-readable name shown on the Hub. Falls back to `DatasetConfig.name` when empty. |
| `task_categories` | `list[str]` | `field(default_factory=list)` | `task_categories` | HF task taxonomy tags (e.g. `["tabular-classification"]`). |
| `size_categories` | `str` | `""` | `size_categories` | HF size category string (e.g. `"10K<n<100K"`). |
| `citation` | `str` | `""` | (body only, not frontmatter) | BibTeX or APA citation string. |
| `collection_method` | `str` | `""` | (body only) | How the data was collected (survey, administrative, sensor, etc.). |
| `csv_delimiter` | `str` | `";"` | (not in frontmatter) | CSV delimiter character used by `build_schema_report`. |

Additionally, the existing `license` field's semantics SHALL be extended: when it
contains a known SPDX identifier (e.g. `"mit"`, `"cc0-1.0"`, `"apache-2.0"`), that
identifier SHALL be used directly in the YAML frontmatter `license` key AND used
to look up the embedded license template for the `LICENSE` file.

#### 2.1.1 TOML representation

```toml
[meta]
language = ["en"]
pretty_name = "Customer Survey 2025"
task_categories = ["tabular-classification"]
size_categories = "1K<n<10K"
citation = """
@techreport{survey2025,
  author = {Example Organization},
  title = {Annual Customer Satisfaction Survey},
  year = {2025}
}
"""
source = "Example Organization — Customer Experience Team"
collection_method = "Online survey — email invite"
csv_delimiter = ","
# csv_encoding = "utf-8-sig"  # override for Latin-1/Windows-1252 files
```

#### 2.1.2 Resolution rules

When any of the above fields is absent from the TOML (or empty), the Dataset Card
body SHALL use a placeholder string such as `"[Not specified]"` for that section.
The frontmatter SHALL omit the corresponding YAML key entirely rather than emit an
empty value, with these exceptions:

- `language` — omit the key when the list is empty.
- `pretty_name` — fall back to `cfg.name` when empty.
- `task_categories` — omit when the list is empty.
- `size_categories` — omit when empty.

### 2.2 `from_toml` changes

The `DatasetConfig.from_toml()` classmethod in `model.py` SHALL be updated to read
the new fields from the `[meta]` table.  The loading code MUST use `.get()` with
the default values listed above so that existing TOML files without these fields
continue to parse without error.

---

## 3. Module: `src/sofer/repo_compliance.py`

### 3.0 Module structure

```
repo_compliance.py
├── build_dataset_card(cfg, schema) -> str      # § 3.1
├── build_license_file(license_id) -> str       # § 3.2
├── build_schema_report(cfg, *, staging_dir=None) -> list[ColumnSchema]  # § 3.3
├── ColumnSchema(dataclass)                     # § 3.3.1
└── _LICENSE_TEMPLATES (module-level dict)      # § 3.2.1
```

All public functions MUST be pure: no network calls, no mutation of arguments.
File I/O is permitted only for paths received as explicit string parameters
(not embedded in config objects). The orchestrator (`upload()`) is responsible
for reading file contents and passing them as strings to pure functions.

### 3.1 `build_dataset_card(cfg, schema) -> str`

#### 3.1.1 Signature

```python
def build_dataset_card(
    cfg: DatasetConfig,
    schema: list[ColumnSchema],
    recipe_content: str | None = None,
) -> str
```

#### 3.1.2 Behaviour

1. Build a YAML frontmatter block from `cfg` fields following the HF Dataset Card
   metadata specification.
2. Append a Markdown body with the following sections (all present, even if
   placeholder text is used):

   | Section | Source | Required |
   |---------|--------|----------|
   | **Dataset Description** | `cfg.description`, `cfg.source` | MUST |
   | **Raw Data Provenance** | `cfg.collection_method`, `cfg.source` | MUST |
   | **Tidy Data Description** | Auto-generated: row count per file, file list | MUST |
   | **Codebook / Variable Reference** | `schema` rendered as a Markdown table | MUST |
   | **Processing Recipe** | `recipe_content` (pre-loaded by orchestrator) — inline as a code block | SHOULD when present |
   | **Citation** | `cfg.citation` | SHOULD when present |
   | **License** | `cfg.license` | MUST |

3. Return the complete `README.md` content as a single string.

#### 3.1.3 YAML frontmatter generation

The frontmatter SHALL be produced by:

1. Building a Python `dict` with only the keys that have non-empty, non-default values.
2. Serialising via `yaml.safe_dump()` (from the `PyYAML` package) wrapped in `---\n{body}\n---\n`.

The mapping from `DatasetConfig` fields to YAML keys:

```python
{
    "language": cfg.language or None,         # omitted if empty
    "license": cfg.license or None,           # omitted if empty
    "pretty_name": cfg.pretty_name or cfg.name,
    "task_categories": cfg.task_categories or None,
    "size_categories": cfg.size_categories or None,
    "tags": cfg.tags or None,
}
```

#### 3.1.4 Scenarios

**Happy path — fully specified config**

```
GIVEN a DatasetConfig with language=["en"], pretty_name="Customer Survey 2025",
      license="cc0-1.0", task_categories=["tabular-classification"],
      size_categories="1K<n<10K", tags=["survey", "satisfaction"],
      and a schema with three ColumnSchema entries
WHEN build_dataset_card(cfg, schema) is called
THEN the returned string SHALL begin with valid YAML frontmatter
     bounded by `---` delimiters
  AND the frontmatter SHALL contain all the supplied metadata keys
  AND the body SHALL contain sections: Dataset Description,
     Raw Data Provenance, Tidy Data Description, Codebook,
     and License
  AND the Codebook section SHALL contain a Markdown table with
     one row per ColumnSchema entry
```

**Minimal config — only required fields**

```
GIVEN a DatasetConfig with only name="test", repo_id="u/test",
      a single FileEntry, and no meta fields
  AND an empty schema list
WHEN build_dataset_card(cfg, schema) is called
THEN the returned string SHALL contain valid YAML frontmatter
     with only the `pretty_name` key (falling back to cfg.name)
  AND the body SHALL contain all required sections with
     "[Not specified]" placeholders where data is missing
  AND the Codebook table SHALL state "No schema information available."
```

**No files configured**

```
GIVEN a DatasetConfig with files=[]
WHEN build_dataset_card(cfg, schema) is called
THEN the Tidy Data Description section SHALL state
     "No data files declared." instead of a file count.
```

**`recipe_content` provided**

```
GIVEN a DatasetConfig with recipe = "recipe.R"
  AND recipe_content = "library(tidyverse)\ndata <- read.csv(...)"
WHEN build_dataset_card(cfg, schema, recipe_content="library(tidyverse)...") is called
THEN the Processing Recipe section SHALL contain the recipe_content
     inside a fenced code block with language label 'r'
     (inferred from the file extension ".R")
```

**`recipe_content` is None**

```
GIVEN a DatasetConfig with recipe = "missing.R"
  AND recipe_content is None
WHEN build_dataset_card(cfg, schema, recipe_content=None) is called
THEN the Processing Recipe section SHALL state
     "Recipe file declared but not found: missing.R"
  AND the function SHALL NOT raise an exception.
```

---

### 3.2 `build_license_file(license_id) -> str`

#### 3.2.1 Signature

```python
def build_license_file(license_id: str) -> str
```

#### 3.2.2 Behaviour

1. Look up `license_id` (lowercased, stripped) in a module-level dictionary
   `_LICENSE_TEMPLATES` that maps SPDX identifiers to their short license text.
2. If found, return the license text as a string.
3. If not found but `license_id` is non-empty, return a descriptive fallback
   string: `"This dataset is shared under the following terms: {license_id}"`
   followed by a link to `choosealicense.com`.  This is a graceful degradation —
   the repo still gets a LICENSE file instead of crashing.
4. If `license_id` is empty or `"restricted"`, return a generic fallback string
   stating that no license was declared and link to `choosealicense.com`.

#### 3.2.3 Embedded templates

The `_LICENSE_TEMPLATES` dict SHALL embed short-form templates for at least these
identifiers (OSI-approved or commonly used for data):

| Key | License |
|-----|---------|
| `"cc0-1.0"` | Creative Commons Zero v1.0 Universal |
| `"cc-by-4.0"` | Creative Commons Attribution 4.0 |
| `"cc-by-sa-4.0"` | Creative Commons Attribution-ShareAlike 4.0 |
| `"mit"` | MIT License |
| `"apache-2.0"` | Apache License 2.0 |
| `"unlicense"` | The Unlicense |
| `"pddl"` | Open Data Commons Public Domain Dedication and License |

Each template SHALL be a complete, legally-valid short-form notice that an end
user can copy verbatim as the repository's `LICENSE` file.  Templates SHALL be
stored as triple-quoted strings inside the module; the module size impact is
acceptable because these are short-form templates, not the full legal text for
every variant.

#### 3.2.4 Scenarios

**Known SPDX identifier**

```
GIVEN license_id = "cc0-1.0"
WHEN build_license_file(license_id) is called
THEN the returned string SHALL contain "Creative Commons Zero v1.0 Universal"
```

**Unknown identifier**

```
GIVEN license_id = "made-up-1.0"
WHEN build_license_file(license_id) is called
THEN the returned string SHALL contain "This dataset is shared under the following terms: made-up-1.0"
  AND the function SHALL NOT raise an exception
```

**Empty identifier**

```
GIVEN license_id = ""
WHEN build_license_file(license_id) is called
THEN the returned string SHALL be a fallback message that explains
     no LICENSE file was generated
  AND the function SHALL NOT raise an exception
```

**Identifier `"restricted"`**

```
GIVEN license_id = "restricted"
WHEN build_license_file(license_id) is called
THEN the returned string SHALL be the same fallback message
     as for the empty-identifier case
```

---

### 3.3 `build_schema_report(cfg) -> list[ColumnSchema]`

#### 3.3.1 `ColumnSchema` dataclass

```python
@dataclass
class ColumnSchema:
    """Describes a single column in the dataset.

    Attributes:
        name:     Column header as it appears in the CSV.
        dtype:    Inferred data type (one of "numeric", "categorical/text",
                  "mixed (mostly numeric)", "unknown").
        nullable: Whether missing values were observed in the sample.
        example:  A non-missing example value (string).
        unique:   Number of unique values observed in the sample, excluding missing-value sentinels (`""`, `"NA"`, `"NULL"`, `"N/A"`, etc.).
        missing:  Percentage of rows with missing values (float 0.0–100.0).
    """

    name: str
    dtype: str
    nullable: bool
    example: str
    unique: int
    missing: float
```

#### 3.3.2 Signature

```python
def build_schema_report(
    cfg: DatasetConfig,
    csv_delimiter: str | None = None,
    csv_encoding: str = "utf-8-sig",
    staging_dir: Path | None = None,
) -> list[ColumnSchema]:
```

#### 3.3.3 Behaviour

1. Iterate over `cfg.files`.
2. For each `FileEntry` whose `remote` path ends with `.csv` (case-insensitive),
   and that is NOT marked `recursive`:

   a. **Parquet path** — used when `staging_dir` is provided AND the entry does
      NOT have `upload_as_csv = True`:
      - Look for `staging_dir / <stem>.parquet` (same stem as the CSV file).
      - If the Parquet file exists:
        - Open via `pyarrow.parquet.ParquetFile(parquet_path)`.
        - Read column names from `schema_arrow.field(i).name`.
        - Derive `dtype` from the Parquet physical type using the mapping in
          § 3.3.5 (e.g. INT64 → `"numeric"`, BYTE_ARRAY → `"categorical/text"`).
        - Read `nullable` from `schema_arrow.field(i).nullable`.
        - Sample the first row group (up to `_SCHEMA_SAMPLE_SIZE` rows) to
          compute `example`, `unique`, and `missing` — same heuristic logic
          as the CSV path.
        - Use the Parquet file stem with `.parquet` extension in disambiguation
          prefixes (e.g. `"survey.parquet::age"`).
      - If the Parquet file does not exist, fall back to the CSV path (step 2b).

   b. **CSV fallback path** — used when no `staging_dir`, or `upload_as_csv = True`,
      or the matching `.parquet` is missing:
      - Resolve the local path via `entry.resolve(cfg._base_dir)`.
      - Open the file with `encoding=csv_encoding` (default `"utf-8-sig"`) and
        `delimiter=csv_delimiter` (default `";"`).  When the header produces
        fewer than 2 columns with the default delimiter, fall back to
        `csv.Sniffer().sniff()` on a sample of rows as heuristic auto-detection.
      - Read the header row.
      - Read up to 10 000 data rows (`_SCHEMA_SAMPLE_SIZE`) for type inference.
      - For each column, compute `dtype` via `codebook.infer_column_type` and
        `example`, `unique`, `missing` from the sample.

3. Return the aggregated list of `ColumnSchema` objects — one per column across
   ALL CSV (or Parquet) files.  Include the source filename as a prefix in the
   column name when the same column name appears in multiple files:
   `"file1.csv::col_A"`, `"file2.csv::col_A"`.  When read from Parquet, the
   prefix uses the Parquet filename (e.g. `"survey.parquet::age"`).
4. If no CSV files are found (or none are parseable), return an empty list.

#### 3.3.4 Scenarios

**Single CSV with numeric and text columns**

```
GIVEN a DatasetConfig with one FileEntry pointing to a CSV with
      headers ["id", "name", "age"] and three rows of data
WHEN build_schema_report(cfg) is called
THEN the returned list SHALL contain three ColumnSchema entries
  AND the entry for "age" SHALL have dtype "numeric"
  AND the entry for "name" SHALL have dtype "categorical/text"
  AND the entry for "id" SHALL have dtype "numeric"
```

**CSV with missing values**

```
GIVEN a CSV column where 2 out of 4 data rows are empty or "NA"
  AND the 2 non-missing rows have values "A", "B"
WHEN build_schema_report(cfg) is called
THEN the corresponding ColumnSchema SHALL have
     nullable=True, missing=50.0
  AND unique SHALL be 2 (excluding "" and "NA" sentinels)
```

**No CSV files in config**

```
GIVEN a DatasetConfig with only recursive directory entries
      (no direct .csv file entries)
WHEN build_schema_report(cfg) is called
THEN an empty list SHALL be returned
```

**Column name collision across files**

```
GIVEN a DatasetConfig with two CSV files that both contain a column "value"
WHEN build_schema_report(cfg) is called
THEN the returned list SHALL contain two entries for "value"
     with the filename prefix disambiguation:
     "file_a.csv::value" and "file_b.csv::value"
```

**File not found on disk**

```
GIVEN a DatasetConfig with a FileEntry whose local path does not exist
WHEN build_schema_report(cfg) is called
THEN the function SHALL skip that file (no exception)
  AND the returned list SHALL contain entries only from files
     that were successfully read
```

#### 3.3.5 Parquet Physical-Type → `dtype` Mapping

When reading from Parquet, the `dtype` field SHALL be derived from the Parquet
physical type instead of `codebook.infer_column_type`:

| Parquet physical type | `ColumnSchema.dtype` |
|-----------------------|----------------------|
| `INT{8,16,32,64}` | `"numeric"` |
| `FLOAT`, `DOUBLE` | `"numeric"` |
| `DECIMAL` | `"numeric"` |
| `BOOLEAN` | `"categorical/text"` |
| `BYTE_ARRAY` (string-like) | `"categorical/text"` |
| `FIXED_LEN_BYTE_ARRAY` | `"categorical/text"` |
| `STRING` | `"categorical/text"` |
| `LARGE_STRING` | `"categorical/text"` |
| `ENUM` | `"categorical/text"` |
| `TIMESTAMP`, `DATE`, `TIME` | `"categorical/text"` |
| `INT{32,64}` with `isAdjustedToUTC` / logical timestamp | `"categorical/text"` |
| `LIST`, `MAP`, `STRUCT` | `"unknown"` |

The exact Parquet physical type is not preserved in `ColumnSchema` in P0.
The mapping is lossless because `ColumnSchema.dtype` is a simplified category
for the Dataset Card's Codebook table.

#### 3.3.6 Parquet-specific Scenarios

**Schema from Parquet — happy path**

```
GIVEN a DatasetConfig with one CSV file entry "survey.csv"
  AND prepare(cfg) is called, producing the staging directory
  AND conversion succeeds (survey.parquet is in staging_dir)
WHEN build_schema_report(cfg, staging_dir=tmpdir) is called
THEN the function SHALL read survey.parquet from staging_dir
  AND the dtype for an INT64 column SHALL be "numeric"
  AND the dtype for a BYTE_ARRAY column SHALL be "categorical/text"
  AND the nullable field SHALL match parquet_schema.field(i).nullable
  AND unique and missing fields SHALL be computed from a row-group sample
```

**Schema from CSV — no staging dir (backward compat)**

```
GIVEN a DatasetConfig with one CSV file entry
  AND build_schema_report(cfg) is called (no staging_dir)
THEN the function SHALL read the CSV file directly
  AND use infer_column_type for dtype
  AND behave identically to the parent spec's § 3.3
```

**Schema from CSV — upload_as_csv override**

```
GIVEN a DatasetConfig with upload_as_csv = true for a CSV entry
  AND staging_dir=tmpdir is provided
WHEN build_schema_report processes that entry
THEN the function SHALL read the original CSV (not the Parquet)
  AND use infer_column_type for dtype
```

**Schema from CSV — Parquet file missing from staging**

```
GIVEN a CSV entry that was NOT marked upload_as_csv
  BUT the .parquet file is missing from staging_dir
  (e.g., conversion failed silently)
WHEN build_schema_report processes that entry
THEN the function SHALL fall back to reading the original CSV
  AND use infer_column_type for dtype
```

**Schema from Parquet — column name disambiguation**

```
GIVEN two CSV files: "a.csv" and "b.csv"
  AND both have a column named "value"
  AND both are converted to Parquet
WHEN build_schema_report(cfg, staging_dir=tmpdir) is called
THEN the returned list SHALL contain
  "a.parquet::value" and "b.parquet::value"
  (filename prefix uses the Parquet filename)
```

#### 3.3.7 Duplicate column summary threshold (RC-R02)

`build_schema_report()` SHALL emit warnings for duplicate column names across files. A new `schema_dup_threshold` config key (default `3`) in `[tool.sofer]` SHALL govern the output format:

- When duplicate count ≤ `schema_dup_threshold`: individual `[!]` warnings per duplicate.
- When duplicate count > `schema_dup_threshold`: a single `[i]` summary with the top 5 most-duplicated columns, a contextual message, and a tip referencing `include_in_schema` as an opt-out.

##### Scenario: Default threshold — 1 duplicate (below limit)
- GIVEN `schema_dup_threshold = 3` and 1 duplicate column detected
- WHEN `build_schema_report()` emits duplicate warnings
- THEN a single `[!]` warning SHALL be printed

##### Scenario: Default threshold — 3 duplicates (at limit)
- GIVEN `schema_dup_threshold = 3` and 3 duplicate columns detected
- WHEN `build_schema_report()` emits duplicate warnings
- THEN 3 individual `[!]` warnings SHALL be printed

##### Scenario: Default threshold — 4 duplicates (above limit)
- GIVEN `schema_dup_threshold = 3` and 4 duplicate columns detected
- WHEN `build_schema_report()` emits duplicate warnings
- THEN a single `[i]` summary SHALL be printed with top 5 columns, a contextual message, and a tip referencing `include_in_schema`

##### Scenario: Custom threshold — 8 duplicates (below limit)
- GIVEN `schema_dup_threshold = 10` and 8 duplicate columns detected
- THEN 8 individual `[!]` warnings SHALL be printed

##### Scenario: Custom threshold — 11 duplicates (above limit)
- GIVEN `schema_dup_threshold = 10` and 11 duplicate columns detected
- THEN a single `[i]` summary SHALL be printed

##### Scenario: No duplicates
- GIVEN no duplicate column names across files
- WHEN `build_schema_report()` completes
- THEN no duplicate-related warnings SHALL be emitted

#### 3.3.8 Per-file schema inclusion (RC-R03)

Each `[[file]]` entry SHALL support an optional `include_in_schema` boolean, defaulting to `true`. When `false`, `build_schema_report()` SHALL skip that file — its columns SHALL NOT appear in the Dataset Card's Codebook table. The file SHALL still be uploaded and listed in `configs`/`data_files`.

When all configured files have `include_in_schema = false`, `build_schema_report()` SHALL emit a warning and return an empty list.

##### Scenario: File excluded from schema
- GIVEN a `[[file]]` entry with `include_in_schema = false`
- WHEN `build_schema_report()` processes the file list
- THEN the file's columns SHALL NOT appear in the returned ColumnSchema list
- AND the file SHALL still be uploaded

##### Scenario: Field absent — default behavior preserved
- GIVEN a `[[file]]` entry without an `include_in_schema` field
- WHEN `build_schema_report()` processes the file list
- THEN the file SHALL contribute columns normally (default `true`)

##### Scenario: All files excluded from schema
- GIVEN all `[[file]]` entries have `include_in_schema = false`
- WHEN `build_schema_report()` processes the file list
- THEN a warning "All files excluded from schema" SHALL be emitted
- AND an empty list SHALL be returned

##### Scenario: Mixed inclusion — only true files contribute
- GIVEN some files with `include_in_schema = true` and some with `false`
- WHEN `build_schema_report()` processes the file list
- THEN only files with `include_in_schema = true` SHALL contribute columns

---

## 4. Pipeline orchestration

### 4.4 Placeholder Rejection in Validation (RC-R01)

The `validate()` function SHALL reject `repo_id` values containing known
placeholder patterns that indicate the user has not configured a real Hugging
Face repository. Rejected patterns include case-insensitive matches for
`YOUR_USER`, `YOUR_ORG`, `your-username`, and `YOUR_ORGANIZATION`. The system
MUST print a clear error message identifying the rejected placeholder to
stderr and return with exit code 1. Valid `user/dataset` repo_ids that do not
match any placeholder pattern SHALL continue to pass validation unchanged.

#### 4.4.1 Scenarios

**YOUR_USER placeholder rejected**

- GIVEN a DatasetConfig with `repo_id = "YOUR_USER/dataset"`
- WHEN `validate()` is called
- THEN an error SHALL be returned identifying `YOUR_USER` as a placeholder
- AND the message SHALL instruct the user to replace it with their actual HF username

**YOUR_ORG placeholder rejected**

- GIVEN a DatasetConfig with `repo_id = "YOUR_ORG/dataset"`
- WHEN `validate()` is called
- THEN an error SHALL be returned identifying `YOUR_ORG` as a placeholder

**Lowercase your-username placeholder rejected**

- GIVEN a DatasetConfig with `repo_id = "your-username/dataset"`
- WHEN `validate()` is called
- THEN an error SHALL be returned identifying `your-username` as a placeholder

**Valid user/dataset still passes**

- GIVEN a DatasetConfig with `repo_id = "alice/my-dataset"`
- WHEN `validate()` is called
- THEN validation SHALL pass without error

**_cmd_codebook calls validate before generation**

- GIVEN a TOML config with `repo_id = "YOUR_USER/dataset"`
- WHEN `sofer codebook --config dataset.toml --all-files` executes
- THEN `validate()` SHALL be called before `generate_all_codebooks()`
- AND the command SHALL exit with code 1
- AND the error message SHALL print to stderr

---

### 4.5 Recursive entries stage correctly (RC-R04)

Staging SHALL handle `recursive = true` entries without crashing. A
`recursive` entry pointing to a directory SHALL have its tree staged under the
entry's remote prefix by copying each file individually (or via
`shutil.copytree`); the directory itself SHALL NEVER be passed to
`shutil.copy2`. Passing a directory to `shutil.copy2` raises `PermissionError`
on Windows and `IsADirectoryError` on POSIX — this MUST NOT occur. Empty
directories SHALL stage zero files without error.

#### Scenario: Recursive directory stages its files

- GIVEN a `[[file]]` entry with `recursive = true` pointing to a directory containing `train.csv` and `test.csv`
- WHEN the staging step runs
- THEN both files SHALL be staged under the entry's remote prefix
- AND no exception SHALL be raised

#### Scenario: Nested subdirectories preserved

- GIVEN a recursive directory containing `Labels/etiquetas_a.csv`
- WHEN the staging step runs
- THEN `Labels/etiquetas_a.csv` SHALL be staged under the remote prefix

#### Scenario: Empty recursive directory is a no-op

- GIVEN a `recursive` entry pointing to an empty directory
- WHEN the staging step runs
- THEN zero files SHALL be staged
- AND no exception SHALL be raised

---

### 4.6 Column origin attribution (RC-R05)

> Added by change `publish-readme-bugs` (archived 2026-08-24).

`ColumnSchema` SHALL gain an optional `origin: str = ""` field holding the
source file's basename (e.g. `"survey.csv"` or `"survey.parquet"`).
`build_schema_report()` SHALL populate `origin` for every collected column, on both
the Parquet and CSV paths. Duplicate-name resolution remains first-occurrence-wins:
a column name appearing in several files SHALL yield ONE entry attributed to its
first source file via `origin`, and the duplicate warnings of § 3.3.7 remain
unchanged.

(Previously: the flat list carried no provenance — duplicate cross-file columns were
dropped silently with no way to tell which file a column came from.)

#### Scenario: Multi-file dataset exposes origin

- GIVEN a DatasetConfig with two CSV files, each contributing columns
- WHEN `build_schema_report()` runs
- THEN every returned ColumnSchema SHALL carry `origin` set to its source file's name

#### Scenario: Duplicate name keeps first occurrence with its origin

- GIVEN two files that both contain a column "value"
- WHEN `build_schema_report()` runs
- THEN exactly one "value" entry SHALL be returned
- AND its `origin` SHALL be the first file that provided the column

### 4.7 Data Fields renders per-file attribution (RC-R06)

> Added by change `publish-readme-bugs` (archived 2026-08-24). Supersedes the
> `file::` disambiguation prefixes described in § 3.3.3 step 3.

The Dataset Card's "Data Fields" table SHALL include a **File** column whose cell
contains the column's `origin`. The card MUST NOT drop any included column, and
column names SHALL be displayed without the `file::` disambiguation prefix, since
attribution is now structural.

Design decision — File column over grouped-by-file sections: because duplicate
names collapse to their first occurrence, at most one row exists per distinct
column name, so one flat table with an explicit File column stays accurate;
grouped sections would visually imply each file exclusively owns its rows and
would repeat table headers per group.

(Previously: one undifferentiated table mixing columns across files with no
attribution.)

#### Scenario: Multi-file card shows file attribution

- GIVEN a schema built from two files
- WHEN `build_dataset_card(cfg, schema)` runs
- THEN every Data Fields row SHALL show its source file in the File column
- AND the number of rows SHALL equal the number of schema entries (no silent drops)

#### Scenario: Single-file card still attributes

- GIVEN a schema built from one file
- WHEN the card is rendered
- THEN the File column SHALL be present and populated for every row

### 4.8 Real num_examples in YAML splits (RC-R07)

> Added by change `publish-readme-bugs` (archived 2026-08-24).

The card's single train split's `num_examples` SHALL equal the actual number of
data rows backing that split — the SUM of exact per-file row counts (Parquet:
each file's Parquet metadata row count via `pf.metadata.num_rows`; CSV: counted
data rows via `len(rows)` on the fully loaded file). Row counts are EXACT —
they are NOT capped by any sample size. This replaces the previous value,
which was the sum of `unique` values across columns.

(Previously: `num_examples` was `sum(s.unique)` across all columns and files,
producing absurd values like 13 for a 5-row dataset.)

#### Scenario: num_examples equals actual rows

- GIVEN a 5-row dataset whose columns hold 13 distinct values in total
- WHEN the card's YAML frontmatter is generated
- THEN `dataset_info.splits[0].num_examples` SHALL be 5

#### Scenario: Multi-file splits sum per-file row counts

- GIVEN two files with 30 and 40 rows respectively feeding one train split
- WHEN splits are computed
- THEN the single train split's `num_examples` SHALL equal the sum of per-file
  row counts (30+40=70)

### 4.9 Data Structure lists delivered repo-relative paths only (RC-R08)

> Added by change `publish-readme-bugs` (archived 2026-08-24).

The card's "Dataset Structure" section SHALL list ONLY repo-relative DELIVERED
paths, derived from the SAME conversion/mirroring mapping the upload pipeline
uses (reuse `planned_remotes` semantics — no duplicated logic):

- eligible CSV entries → their converted `.parquet` remote path
- the original CSV additionally listed only when `keep_csv` is set
- `upload_as_csv` entries → their declared `.csv` remote path
- `recursive` entries → the staged tree under the remote prefix

The section MUST NOT contain local disk paths (`e.local`) or absolute paths.

(Previously: rendered `{local disk path} -> {declared remote}` verbatim, ignoring
conversion, `upload_as_csv`, `recursive`, and `keep_csv` — leaking the publisher's
private filesystem into a public artifact.)

#### Scenario: Converted CSV listed as .parquet

- GIVEN a CSV entry eligible for Parquet conversion and `keep_csv` unset
- WHEN the card is generated
- THEN Dataset Structure SHALL list `data/x.parquet` and SHALL NOT list `data/x.csv`
- AND no local path fragment SHALL appear anywhere in the card

#### Scenario: keep_csv lists both artifacts

- GIVEN the same entry published with `--keep-csv`
- WHEN the card is generated
- THEN both the `.parquet` and the original `.csv` repo-relative paths SHALL be listed

#### Scenario: Recursive entry lists its staged tree

- GIVEN a `recursive` directory entry staging `Labels/a.csv`
- WHEN the card is generated
- THEN the section SHALL list the staged remote path for `Labels/a.csv`
  (recursive entries render the staged tree ROOT path)

### 4.10 Config-driven schema sample size (RC-R09)

> Added by change `publish-readme-bugs` (archived 2026-08-24). Replaces the
> `_SCHEMA_SAMPLE_SIZE` module constant referenced in § 3.3.3.

A new `[tool.sofer] schema_sample_size` key (default `10_000`), exposed through
`config.py`, SHALL govern every sample-size limit in `build_schema_report()`
(Parquet row-group slice and CSV slice). No numeric literal SHALL remain in the
function bodies. The card's statistics footnote SHALL be GENERATED from the
configured value and state it (e.g. "... based on a 10,000-row sample").

(Previously: `_SCHEMA_SAMPLE_SIZE = 10_000` was hardcoded and the footnote was a
literal string, diverging from the codebook's configurable `codebook_max_sample`.)

#### Scenario: Custom sample size reflected in footnote

- GIVEN `schema_sample_size = 5000` in `[tool.sofer]`
- WHEN the card is generated
- THEN the footnote SHALL state a 5,000-row sample
- AND sampling SHALL cap at 5000 rows

#### Scenario: Default applies when key is absent

- GIVEN a TOML without `schema_sample_size`
- WHEN the card is generated
- THEN sampling SHALL cap at 10,000 rows and the footnote SHALL say 10,000

### 4.11 Unique counts exclude missing sentinels everywhere (RC-R10)

> Added by change `publish-readme-bugs` (archived 2026-08-24).

In BOTH the Parquet and CSV paths, `ColumnSchema.unique` SHALL equal the count of
DISTINCT NON-MISSING sample values (`len(set(non_missing))`). Missing-value
sentinels ("", "NA", "NULL", "N/A", and null/None) MUST NOT be counted. This makes
the code match the field's documented contract.

(Previously: `unique = len(set(col_values))` counted sentinels/nulls as values,
contradicting the docstring and the CSV-path scenario of § 3.3.4.)

#### Scenario: Sentinels excluded on the CSV path

- GIVEN a column whose sample values are ["A", "", "NA", "B", "NULL"]
- WHEN `build_schema_report()` computes stats
- THEN `unique` SHALL be 2

#### Scenario: Nulls excluded on the Parquet path

- GIVEN a Parquet string column with values ["x", null, "y"]
- WHEN the Parquet path computes stats
- THEN `unique` SHALL be 2

---

## 5. Backward compatibility

### 5.1 TOML schema

All new `[meta]` fields defined in § 2.1 are OPTIONAL.  A TOML file that lacks
every new field SHALL:

- Parse successfully (existing tests pass unchanged).
- Produce a Dataset Card with minimal frontmatter (only `pretty_name` from
  `dataset.name`).
- Produce a `LICENSE` file with the fallback "no license" message.
- Produce an empty schema report if no CSV files are declared.

### 5.2 Existing upload behaviour

An upload with a minimal TOML (no new meta fields) SHALL behave identically to
today EXCEPT that `README.md` and `LICENSE` files are now pushed alongside the
data files.  This is additive — no existing upload is broken, but repos become
slightly more compliant.

### 5.3 `DatasetConfig()` direct construction

Callers that construct `DatasetConfig(...)` directly (as the test suite does)
SHALL NOT need to change.  All new fields have defaults that produce the same
behaviour as before.

### 5.4 Parquet-aware schema report

Callers that invoke `build_schema_report(cfg)` without `staging_dir` SHALL
receive identical behaviour to the previous spec (CSV-only path).  Callers
that pass `staging_dir` SHALL get the new Parquet-reading behaviour.  The
return type (`list[ColumnSchema]`) is unchanged.  `build_dataset_card` and
`build_license_file` are unaffected — their inputs are unchanged.

---

## 6. Testing

### 6.1 New test file

A new file `tests/test_repo_compliance.py` SHALL be created with tests for:

| Test class / area | Tests |
|-------------------|-------|
| `TestBuildDatasetCard` | Happy path with full meta; minimal config; empty schema; recipe inlined; recipe missing; all sections present. |
| `TestBuildLicenseFile` | Known SPDX identifiers return correct text; non-SPDX returns descriptive fallback; empty/restricted returns generic fallback. |
| `TestBuildSchemaReport` | Single CSV; multiple CSVs; missing values; no CSV files; column name collision; file not found skipped. |
| `TestBuildSchemaReportParquet` | Happy path from Parquet; native type mapping for int, float, string, bool; nullable from schema; column name read from Parquet. |
| `TestBuildSchemaReportParquetFallback` | No staging_dir → CSV; staging_dir but .parquet missing → CSV; upload_as_csv override → CSV. |
| `TestBuildSchemaReportSampling` | Unique and missing computed from Parquet row-group sample; example from first non-null value. |
| `TestBuildSchemaReportDisambiguationParquet` | Column name collision across Parquet files with `.parquet` filename prefix. |
| `TestColumnSchema` | Dataclass default values; field types. |
| `TestUploadCompliance` | (integration-level, mocked) Compliance called before upload; upload ordering; temp dir cleanup; exception propagation. |

### 6.2 Test conventions

Tests SHALL follow the project's existing patterns:

- Use `tmp_path` for temporary files.
- Pure-function tests need no mocking.
- Upload-order tests MAY mock `build_schema_report`/`build_dataset_card`/`build_license_file` and verify call order via `unittest.mock.Mock` call tracking.
- Parquet tests SHALL write small Parquet files programmatically with `pyarrow.Table.from_pydict()` and `pyarrow.parquet.write_table()`.
- Existing CSV-based tests SHALL continue to pass unchanged.
- No integration tests against the real Hugging Face Hub.

### 6.3 Coverage target

All new code in `repo_compliance.py` SHALL have unit-test coverage of at least
90% (branch coverage).  The upload orchestration code in `uploader.py` SHALL have
at least 80% coverage via mocked compliance calls.

---

## 7. File checklist

### 7.1 Files to create

| File | Purpose |
|------|---------|
| `src/sofer/repo_compliance.py` | New module with `build_dataset_card`, `build_license_file`, `build_schema_report`, `ColumnSchema`. |
| `tests/test_repo_compliance.py` | Full test suite for the new module. |

### 7.2 Files to modify

| File | Change |
|------|--------|
| `src/sofer/model.py` | Add new `[meta]` fields to `DatasetConfig` + update `from_toml()`. |
| `src/sofer/codebook.py` | Rename `_infer_type` to public `infer_column_type` for cross-module reuse. |
| `src/sofer/repo_compliance.py` | Add `staging_dir` parameter to `build_schema_report`; add Parquet-reading logic with type mapping. |
| `src/sofer/uploader.py` | Add conversion loop before compliance; pass `staging_dir=tmpdir` to `build_schema_report`. |
| `pyproject.toml` | Replace `tomli-w` dependency with `PyYAML`. |
| `tests/test_repo_compliance.py` | Add Parquet-based schema tests (happy path, fallback, sampling, disambiguation). |

### 7.3 Files unchanged

| File | Reason |
|------|--------|
| `src/sofer/cli.py` | No CLI changes in P0; upload command already calls `uploader.upload()`. |
| `src/sofer/checks.py` | Compliance is not validation — separate concern. |
| `src/sofer/__init__.py` | No public API changes for P0. |
| `src/sofer/codebook.py` | `infer_column_type` unchanged — still used by CSV-fallback path. |

---

## 8. Open questions / future work

- **`_LICENSE_TEMPLATES` maintenance**: when a new SPDX identifier is needed, it
  SHALL be added to the dict and the test updated.  No module-level changes beyond
  that.
- **User-overridable Dataset Card body**: should be deferred to a later change
  where users supply a custom template.
