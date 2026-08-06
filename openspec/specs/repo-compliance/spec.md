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
  AND upload(cfg) is called
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

---

## 4. Pipeline orchestration

### 4.1 `uploader.upload()` changes

The `upload()` function in `src/sofer/uploader.py` SHALL be modified to
call the compliance module **after** validation passes and **before** pushing any
files to Hugging Face Hub. When Parquet conversion is enabled, the conversion
step SHALL run **before** compliance so `build_schema_report` reads the
converted Parquet files.

New sequence inside `upload()`:

```
1. _ensure_repo(cfg)             # same as today
2. VALIDATION:                   # remote paths, overwrite protection, diff summary
3. CONVERSION:                   # runs before compliance
   convert CSVs to Parquet in tmpdir
4. COMPLIANCE:                   # reads Parquet when available
   a. schema = build_schema_report(cfg, staging_dir=tmpdir)
   b. readme  = build_dataset_card(cfg, schema)
   c. license = build_license_file(cfg.license)
5. STAGING:                      # mirror HF repo layout under staging_root/
   a. Copy converted Parquet files to staging_root/<remote-path>/
   b. Copy non-converted files to staging_root/<remote>/
   c. Move compliance files (README.md, LICENSE) to staging_root/
   d. Copy codebooks to staging_root/codebooks/ and staging_root/codebook.md
6. BATCH UPLOAD:                 # single atomic upload
   HfApi.upload_folder(staging_root, ...)
```

#### 4.1.1 Staging strategy — mirror HF repository structure

The staging directory `tmpdir` SHALL contain a subdirectory `repo/` (staging_root)
that mirrors the HF repository layout. ALL files — data (.parquet), compliance
(README.md, LICENSE), codebooks, and original CSVs (keep_csv mode) — SHALL be
staged under `staging_root/` with their exact remote-relative paths before the
single `upload_folder()` call.

| File type | Staging path | Example |
|-----------|-------------|---------|
| Converted Parquet | `staging_root/<remote-path>/*.parquet` | `staging_root/data/PROV/train.parquet` |
| Non-converted files | `staging_root/<remote>` | `staging_root/data/direct.parquet` |
| Compliance | `staging_root/README.md`, `staging_root/LICENSE` | (root) |
| Codebooks | `staging_root/codebooks/<relative-path>.md` | `staging_root/codebooks/DPTO.md` |
| Root codebook index | `staging_root/codebook.md` | (root) |
| Original CSVs (keep_csv) | `staging_root/<original-remote>` | `staging_root/data/PROV/train.csv` |

The temporary directory SHALL be cleaned up after upload regardless of success
or failure (use `try/finally` with `shutil.rmtree`).

##### Requirement: tmpdir mirrors the HF repository structure

The staging directory `tmpdir` SHALL contain ALL files to be uploaded, organized
with the same directory structure they will have on the Hugging Face Hub. Data
files go in their remote-relative paths, compliance files at root, and codebooks
under `codebooks/`.

###### Scenario: tmpdir structure matches remote layout

- GIVEN a DatasetConfig with `remote = "data/PROV/train.csv"` and `remote = "data/DPTO/train.csv"`
- AND both CSV files are converted to .parquet
- WHEN staging is complete
- THEN `tmpdir/repo/data/PROV/train.parquet` SHALL exist
- AND `tmpdir/repo/data/DPTO/train.parquet` SHALL exist
- AND `tmpdir/repo/README.md` SHALL exist
- AND `tmpdir/repo/LICENSE` SHALL exist

#### 4.1.2 Batch upload via `upload_folder`

Instead of uploading files individually via `HfApi.upload_file()`, all staged
files SHALL be uploaded in a single `HfApi.upload_folder(staging_root,
repo_id=cfg.repo_id, repo_type=cfg.repo_type, path_in_repo="")` call. The
`upload_folder` function is resumable — interrupted uploads skip already-uploaded
files on retry. A built-in progress bar (via `hf_xet`) replaces individual
per-file progress lines.

#### 4.1.3 User feedback

The pre-upload diff summary and post-upload split report SHALL remain unchanged.
During upload, `upload_folder`'s built-in progress bar provides the status.
Counters SHALL report the number of staged files:
- On success: `ok = N` (files staged), `fail = 0`, return 0
- On failure: `ok = 0`, `fail = N`, return 1
- On zero staged files (`N = 0`): return 0

```
  ...
  ↑  repo/  →  (root)
  ✓  repo/
  ...
  ============================================================
  Result: 132 uploaded, 0 failed
  ============================================================
```

Files that do not exist on disk at staging time SHALL be reported as NOT FOUND
and skipped — they are never uploaded.

#### 4.1.4 Scenarios

**Normal upload with batch staging**

```
GIVEN a valid DatasetConfig with license="cc0-1.0" and
      two CSV file entries
WHEN upload(cfg) is called
THEN build_schema_report SHALL be called first
  AND build_dataset_card SHALL be called with the schema
  AND build_license_file SHALL be called with "cc0-1.0"
  AND all files SHALL be staged in staging_root mirroring HF layout
  AND HfApi.upload_folder(staging_root, …) SHALL be called exactly once
  AND NO individual HfApi.upload_file() calls SHALL be made for staged files
  AND the function SHALL return 0
```

**Batch upload failure**

```
GIVEN staged files are ready in staging_root/
WHEN HfApi.upload_folder() raises an exception
THEN the error SHALL be printed
  AND fail counter SHALL be set to staged file count
  AND the function SHALL return 1
  AND the tmpdir SHALL be cleaned up
```

**Dry-run does NOT stage or upload**

```
GIVEN a valid DatasetConfig and dry_run=True
WHEN upload(cfg, dry_run=True) is called
THEN _repo_diff_summary and _check_overwrite_protection SHALL run as before
  AND NO files SHALL be uploaded
  AND NO upload_folder() or upload_file() calls SHALL be made
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

**Parquet conversion before compliance**

```
GIVEN a DatasetConfig with one CSV file entry
WHEN upload(cfg) is called
THEN conversion SHALL run BEFORE build_schema_report
  AND build_schema_report SHALL receive staging_dir=tmpdir
  AND the schema SHALL be read from the converted Parquet file
```

---

### 4.2 Codebook Batch Staging (RC-C01)

The `upload()` orchestration SHALL copy generated codebook artifacts into
`staging_root/` preserving their remote path structure. The root index
`codebook.md` in the config directory SHALL be copied to
`staging_root/codebook.md`. Every per-file codebook under `data/codebooks/`
SHALL be copied mirroring its relative path under a `codebooks/` prefix
(e.g. `data/codebooks/DPTO.md` → `staging_root/codebooks/DPTO.md`;
`data/codebooks/Labels/etiquetas_a.md` → `staging_root/codebooks/Labels/etiquetas_a.md`).
Codebooks SHALL be uploaded as part of the single `HfApi.upload_folder()` call,
NOT via individual `HfApi.upload_file()` calls.

A missing root index or missing `data/codebooks/` directory SHALL be skipped
without failing the upload. When no codebooks exist, an advisory message to
run `sofer codebook --all-files` SHALL be printed to stderr, but the upload
SHALL proceed normally for all other files.

The legacy single-file `cfg.codebook` upload (to `codebook/{name}`) is
superseded: when per-file codebooks are present, they SHALL be staged and
uploaded using this new batch convention.

#### 4.2.1 Scenarios

**Codebooks staged and uploaded in batch**

```
GIVEN generated `codebook.md` and `data/codebooks/DPTO.md` on disk
WHEN upload(cfg) is called
THEN codebook.md SHALL be copied to staging_root/codebook.md
  AND data/codebooks/DPTO.md SHALL be copied to staging_root/codebooks/DPTO.md
  AND HfApi.upload_folder(staging_root, …) SHALL include both codebook files
  AND NO individual HfApi.upload_file() calls SHALL be made for codebooks
  AND upload(cfg) SHALL return 0
```

**No codebooks generated — upload proceeds**

```
GIVEN no `codebook.md` and no `data/codebooks/` directory on disk
WHEN upload(cfg) is called
THEN the advisory message to run `sofer codebook --all-files` SHALL print
  AND the upload SHALL proceed with only data and compliance files staged
  AND upload(cfg) SHALL return 0
```

**Declared single codebook is superseded**

```
GIVEN cfg.codebook = "codebook.md" in the TOML
WHEN upload(cfg) is called with generated codebooks present
THEN the generated root index and per-file codebooks SHALL be staged and
  uploaded per the RC-C01 batch convention
  AND the legacy `codebook/{name}` single-file upload SHALL NOT occur
```

---

### 4.3 Overwrite Protection Bypass for Auto-Generated Files (RC-C02)

The upload pipeline SHALL always overwrite auto-generated compliance files on the
Hugging Face Hub without interactive confirmation. These files are programmatically
produced by `upload()` and are never hand-authored, so protecting them from overwrite
adds friction with no user benefit.

The auto-generated set SHALL consist of:

| File / Pattern | Check |
|----------------|-------|
| `README.md` | Exact match (lowercased) |
| `LICENSE` | Exact match (lowercased) |
| `codebook.md` (root index) | Exact match (lowercased) |
| `codebooks/**/*.md` (per-file RC-C01) | Path prefix `codebooks/` |

When any of these files already exist on the Hub, the upload SHALL proceed without
prompting the user, even when `force=False`.

#### 4.3.1 Scenarios

**README.md always uploaded even when it already exists on Hub**

- GIVEN `existing_files` on Hub includes `README.md`
- AND `force=False`
- WHEN `upload(cfg)` is called
- THEN `_check_overwrite_protection` SHALL NOT include `readme.md` in its protected set
- AND `README.md` SHALL be uploaded unconditionally

**LICENSE always uploaded even when it already exists on Hub**

- GIVEN `existing_files` on Hub includes `LICENSE`
- AND `force=False`
- WHEN `upload(cfg)` is called
- THEN `_check_overwrite_protection` SHALL NOT include `license` in its protected set
- AND `LICENSE` SHALL be uploaded unconditionally

**Root codebook index always uploaded when it exists on Hub**

- GIVEN `existing_files` on Hub includes `codebook.md`
- AND the local `codebook.md` exists on disk
- WHEN `upload(cfg)` is called
- THEN `codebook.md` SHALL be uploaded without overwrite protection

**Per-file codebooks always uploaded when they exist on Hub**

- GIVEN `existing_files` on Hub includes `codebooks/DPTO.md`
- AND `data/codebooks/DPTO.md` exists locally
- WHEN `upload(cfg)` is called
- THEN `codebooks/DPTO.md` SHALL be uploaded without overwrite protection

**Advisory printed when codebooks are missing locally**

- GIVEN `codebook.md` does NOT exist on disk
- AND `data/codebooks/` directory is absent or empty
- WHEN `upload(cfg)` is called
- THEN the function SHALL print a message advising to run `sofer codebook --all-files`
- AND the upload SHALL proceed normally for all other files (no error)

---

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
