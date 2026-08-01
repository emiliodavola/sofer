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
`src/data_uploader/model.py`.  Every field MUST default to a value that produces
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

## 3. Module: `src/data_uploader/repo_compliance.py`

### 3.0 Module structure

```
repo_compliance.py
├── build_dataset_card(cfg, schema) -> str      # § 3.1
├── build_license_file(license_id) -> str       # § 3.2
├── build_schema_report(cfg) -> list[ColumnSchema]  # § 3.3
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
def build_schema_report(cfg: DatasetConfig, csv_delimiter: str | None = None, csv_encoding: str = "utf-8-sig") -> list[ColumnSchema]
```

#### 3.3.3 Behaviour

1. Iterate over `cfg.files`.
2. For each `FileEntry` whose `remote` path ends with `.csv` (case-insensitive),
   and that is NOT marked `recursive`:
   - Resolve the local path via `entry.resolve(cfg._base_dir)`.
   - Open the file with `encoding=csv_encoding` (default `"utf-8-sig"`) and `delimiter=csv_delimiter` (default `";"`).  When the header produces fewer than 2 columns with the default delimiter, fall back to `csv.Sniffer().sniff()` on a sample of rows as a heuristic auto-detection.
   - Read the header row.
   - Read up to 10 000 data rows (configurable via a module-level constant
     `_SCHEMA_SAMPLE_SIZE`) for type inference.
   - For each column, compute the fields described in `ColumnSchema` using the
      same type-inference logic as `codebook.infer_column_type`.
3. Return the aggregated list of `ColumnSchema` objects — one per column across
   ALL CSV files.  Include the source filename as a prefix in the column name
   when the same column name appears in multiple files: `"file1.csv::col_A"`,
   `"file2.csv::col_A"`.
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

---

## 4. Pipeline orchestration

### 4.1 `uploader.upload()` changes

The `upload()` function in `src/data_uploader/uploader.py` SHALL be modified to
call the compliance module **after** validation passes and **before** pushing any
files to Hugging Face Hub.

New sequence inside `upload()`:

```
1. _ensure_repo(cfg)             # same as today
2. compliance files generation:  # NEW
   a. schema = build_schema_report(cfg)        # reads CSVs locally
   b. readme  = build_dataset_card(cfg, schema)
   c. license = build_license_file(cfg.license)
3. Write compliance files to a temporary staging area
4. Upload compliance files first (README.md, LICENSE)
5. Upload data files (same loop as today)
```

#### 4.1.1 Staging strategy

The compliance files SHALL be written to a temporary directory created via
`tempfile.mkdtemp()`.  Each file is uploaded via the existing
`huggingface-cli upload` mechanism.  The temporary directory SHALL be cleaned up
after upload regardless of success or failure (use `try/finally`).

#### 4.1.2 Upload ordering

1. `README.md` — uploaded first so the Dataset Card is visible immediately.
2. `LICENSE` — uploaded second.
3. Data files — uploaded in their declared order (existing loop).

This ordering ensures that the Hub recognises the repository as a dataset from the
moment the first file lands.

#### 4.1.3 User feedback

The `upload()` function SHALL print progress lines for each compliance step:

```
  📄  Generating Dataset Card …
  📄  Generating LICENSE …
  ↑  README.md  →  README.md
  ✓  README.md
  ↑  LICENSE  →  LICENSE
  ✓  LICENSE
  ↑  data.csv  →  data.csv
  ✓  data.csv
```

#### 4.1.4 Scenarios

**Normal upload with compliance**

```
GIVEN a valid DatasetConfig with license="cc0-1.0" and
      two CSV file entries
WHEN upload(cfg) is called
THEN build_schema_report SHALL be called first
  AND build_dataset_card SHALL be called with the schema
  AND build_license_file SHALL be called with "cc0-1.0"
  AND README.md SHALL be uploaded before LICENSE
  AND LICENSE SHALL be uploaded before data files
  AND the function SHALL return 0
```

**Compliance failure — schema raises**

```
GIVEN a DatasetConfig pointing to a CSV with an unreadable encoding
WHEN upload(cfg) is called
THEN the exception SHALL propagate to the caller
  AND no files SHALL be uploaded to HF
  AND the temp directory SHALL be cleaned up
```

**Compliance with no license declared**

```
GIVEN a DatasetConfig with license="" (empty)
WHEN upload(cfg) is called
THEN build_license_file("") SHALL return a fallback message
  AND that message SHALL be written to LICENSE
  AND the upload SHALL proceed normally (no error)
```

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

---

## 6. Testing

### 6.1 New test file

A new file `tests/test_repo_compliance.py` SHALL be created with tests for:

| Test class / area | Tests |
|-------------------|-------|
| `TestBuildDatasetCard` | Happy path with full meta; minimal config; empty schema; recipe inlined; recipe missing; all sections present. |
| `TestBuildLicenseFile` | Known SPDX identifiers return correct text; non-SPDX returns descriptive fallback; empty/restricted returns generic fallback. |
| `TestBuildSchemaReport` | Single CSV; multiple CSVs; missing values; no CSV files; column name collision; file not found skipped. |
| `TestColumnSchema` | Dataclass default values; field types. |
| `TestUploadCompliance` | (integration-level, mocked) Compliance called before upload; upload ordering; temp dir cleanup; exception propagation. |

### 6.2 Test conventions

Tests SHALL follow the project's existing patterns:

- Use `tmp_path` for temporary files.
- Pure-function tests need no mocking.
- Upload-order tests MAY mock `build_schema_report`/`build_dataset_card`/`build_license_file` and verify call order via `unittest.mock.Mock` call tracking.
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
| `src/data_uploader/repo_compliance.py` | New module with `build_dataset_card`, `build_license_file`, `build_schema_report`, `ColumnSchema`. |
| `tests/test_repo_compliance.py` | Full test suite for the new module. |

### 7.2 Files to modify

| File | Change |
|------|--------|
| `src/data_uploader/model.py` | Add new `[meta]` fields to `DatasetConfig` + update `from_toml()`. |
| `src/data_uploader/codebook.py` | Rename `_infer_type` to public `infer_column_type` for cross-module reuse. |
| `src/data_uploader/uploader.py` | Call compliance module before file push in `upload()`. |
| `pyproject.toml` | Replace `tomli-w` dependency with `PyYAML`. |

### 7.3 Files unchanged

| File | Reason |
|------|--------|
| `src/data_uploader/cli.py` | No CLI changes in P0; upload command already calls `uploader.upload()`. |
| `src/data_uploader/checks.py` | Compliance is not validation — separate concern. |
| `src/data_uploader/__init__.py` | No public API changes for P0. |

---

## 8. Open questions / future work

- **`_LICENSE_TEMPLATES` maintenance**: when a new SPDX identifier is needed, it
  SHALL be added to the dict and the test updated.  No module-level changes beyond
  that.
- **User-overridable Dataset Card body**: should be deferred to a later change
  where users supply a custom template.
- **Parquet support** (`build_schema_report`): deferred — P0 reads only CSV.
  Parquet will be supported when the P1 conversion capability is added.
