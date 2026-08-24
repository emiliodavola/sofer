# Delta for repo-compliance — Dataset Card attribution, delivered paths, sampling, and unique counts

> Note: this capability's base spec (`openspec/specs/repo-compliance/spec.md`) uses
> numbered sections rather than named requirement blocks, so these changes are
> recorded as ID-tagged requirements (repo convention). Each states what it replaces.

## ADDED Requirements

### Requirement: RC-R05 — Column origin attribution

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

### Requirement: RC-R06 — Data Fields renders per-file attribution

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

### Requirement: RC-R07 — Real num_examples in YAML splits

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

### Requirement: RC-R08 — Data Structure lists delivered repo-relative paths only

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

### Requirement: RC-R09 — Config-driven schema sample size

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

### Requirement: RC-R10 — Unique counts exclude missing sentinels everywhere

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
