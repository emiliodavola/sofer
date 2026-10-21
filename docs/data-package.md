# Data package

`prepare` builds a local package. `publish` delivers that package unchanged;
whether it goes to Hugging Face Hub or a local directory, the build is the
object of record. Building locally is not publishing.

## Supported formats

| Format | `scan` | `codebook` | `profile` | `prepare` | `publish` |
| --- | --- | --- | --- | --- | --- |
| CSV (`.csv`) | Yes | Yes | Yes | Yes¹ | Yes |
| TSV (`.tsv`) | Yes | Yes | Yes | Yes¹ | Yes |
| Parquet (`.parquet`) | Yes | Yes | Yes | Yes | Yes |
| Excel (`.xlsx`) | Yes | Yes | Yes | Yes¹ | Yes |
| JSON Lines (`.jsonl`) | Yes | Yes | Yes | Yes¹ | Yes |

¹ `prepare` converts `csv`, `tsv`, `xlsx`, and `jsonl` to normalized Parquet by
default. Excel produces one Parquet file per sheet as
`stem__sheet.parquet`. Set `convert_to_parquet = false` per `[[file]]` to keep
the original; `upload_as_csv = true` is a deprecated CSV-only alias.
`publish` delivers the prepared package as-is. `--keep-csv` keeps the original
`.csv` alongside its Parquet (CSV only).

## Package contents

A typical package contains:

- the converted Parquet files, or the originals when conversion is disabled;
- `README.md`, the generated Dataset Card;
- `LICENSE`, generated from `[meta] license`;
- `manifest.json`, the record of what the package declares and delivers;
- with `--all-files`, `codebook.md` plus `codebooks/**/*.md`.

## Conversion never changes a value

A column whose values are zero-padded codes (a leading `0` followed by digits,
for example `"001"`) is not a number. `prepare` forces such a column to
`string` instead of letting pyarrow's inference store an integer: it probes the
source (at most `leading_zero_probe_rows` rows, default 1000), prints each
decision, and keeps the source text.

To state the intent in the config, add an inline `column_types` table to the
`[[file]]` entry:

```toml
[[file]]
local = "cache/geo.csv"
remote = "geo.csv"
column_types = { "DPTO" = "string" }
```

`"string"` is the only type accepted today; any other value is refused naming
the accepted set. If a value cannot be preserved, `prepare` fails naming the
column, a sample value, and the exact declaration that fixes it. Nothing is
delivered for that file and the command exits non-zero. `sofer validate`
reports the same finding as a warning before you run `prepare`.

## Parquet conversion limitations

`prepare` uses pyarrow's automatic type inference. It is best-effort, not a
guarantee. These patterns can produce unexpected column types or a failed
conversion; in the failure case `prepare` prints a warning and stages the
original CSV instead. Zero-padded codes are not one of these patterns: they are
protected as described above.

| CSV pattern | What can go wrong | Workaround |
| --- | --- | --- |
| Comma as decimal separator (`3,14`) | pyarrow reads the comma as a field delimiter, not a decimal mark. | Use a non-comma `csv_delimiter` in the TOML. |
| Mixed-type column, more than 50% numeric-looking with some text | pyarrow may promote the whole column to `string` or fail. | Clean the column or accept the `string` type. |
| Extremely long string fields (over 2 GB) | `large_string` handles them, but the CSV parser can hit memory limits. | Split the file or trim the field. |

## Split detection

`prepare` groups files into `train`, `validation`, and `test` splits following
Hugging Face repository conventions. Detection reads the remote paths declared
in the TOML.

- **Keywords.** `train` / `training`, `validation` / `valid` / `val` / `dev`,
  and `test` / `testing` / `eval` / `evaluation`.
- **Delimiting rule.** A keyword counts only when it is delimited by non-word
  characters: `test-file.csv` is a test split, `testfile.csv` is not. `-`, `_`,
  `.`, and whitespace all delimit; a bare run of word characters does not.
- **Sources, in cascade order** — the first source that yields at least one
  split wins:
  1. Top-level directory name (`train/data.csv`, `test/data.csv`).
  2. Filename stem (`train.csv`, `my-train-data.csv`).
  3. Shard pattern (`train-00001-of-00005.parquet`; needs at least two distinct
     splits to count).
- **Fallback.** When nothing matches, every file is assigned to a single
  `train` split.
- **Exclusions.** `README.md`, `LICENSE`, `.gitattributes`, and `.gitignore`
  are never treated as data splits. Files matching a keyword group into that
  split; anything else is reported as unclassified.

The Hugging Face dataset viewer requires a `train` split to auto-load a
repository. If detection leaves you without one, name a file or directory with
`train` in it.

## Validation and quality checks

Every dataset is checked before publish.

### Integrity checks

| Check | What it does | Blocks publish? |
| --- | --- | --- |
| File existence | Every declared path must exist on disk. | Yes |
| Min file count | Configurable via `[[check]] min_files`. | Yes |
| Min total size | Configurable via `[[check]] min_total_size_mb`. | No (warning) |
| CSV columns | Checks that expected columns exist. | Yes |
| Config integrity | Valid `repo_id` and valid paths. | Yes |

### Quality checks

| Check | What it detects |
| --- | --- |
| `duplicates` | Duplicate rows in tabular data. |
| `empty_rows` | Rows with no values. |
| `empty_columns` | Columns with no values. |
| `null_profiling` | Columns exceeding the null threshold. |
| `format_consistency` | Mixed types within columns. |
| `corrupt_records` | Unparseable rows. |
| `value_range` | Values outside min/max bounds. |
| `cross_file_types` | Dtype mismatches across files. |
| `encoding_validation` | File encoding issues. |

Quality checks run in one streaming pass with per-row memory bounded
independently of dataset size. Three `[tool.sofer]` keys control the scan; see
[Tool-wide configuration](configuration.md#quality-scan-bounds):

- `quality_full_scan` (`auto`, `always`, `never`) decides when the whole file is
  read. `auto` scans every row only for the `fail` checks that need it
  (`quality_row_requiring_checks`, default `corrupt_records`). An 8 KB probe
  such as `encoding_validation` never triggers a full pass.
- `quality_max_dup_tracking` caps the distinct row hashes tracked by
  `duplicates` (default 1,000,000). When the cap is hit, the finding is marked
  **partial** and names the cap.
- A dataset may override the policy with an optional `[quality]` table
  (`full_scan`, `max_sample`). TOML forbids `[quality]` and `[[quality]]` in the
  same file.

Findings carry a **partial** flag when their evidence comes from a sampled scan
or a capped accumulator. `validate` prints it as `(partial)` and the on-disk
quality report as `*(partial — sample-based)*`.

## Verify the built package

```bash
sofer prepare my-dataset.toml --verify
```

`prepare --verify` calls `datasets.load_dataset()` on the output directory — the
same call a user makes with `load_dataset("user/repo")` — and compares the
returned splits against the ones detected from the remote paths. The result is
printed after the prepare summary:

- **SKIPPED** — the optional `datasets` package is not installed or cannot be
  imported. Install it with `pip install datasets` and rerun; the report names
  the exception that stopped the import.
- **PASSED** — `load_dataset()` succeeded and the detected splits match.
- **FAILED** — `load_dataset()` raised, or the splits differ. The report lists
  errors and warnings.

Verification is informational and non-blocking. It never fails the `prepare`
run.

## Codebook generation

### Single file

```bash
sofer codebook raw/persons.csv -o codebook.md
```

Supports CSV, TSV, Parquet, Excel, and JSON Lines. The codebook table has column
name, inferred type, actual dtype (for typed formats), unique values, missing
percentage, and a sample value.

### Batch generation

```bash
sofer codebook --all-files --config my-dataset.toml
```

Generates one codebook per registered file under
`build/codebooks/<rel-stem>.md`, plus a root `build/codebook.md` index with a
table of contents and relative links. Files from the same source directory that
would resolve to the same output stem are detected before writing: non-colliding
files still get their codebook, and the run fails with an error listing the
colliding sources.

For `.xlsx` with multiple sheets, one codebook per sheet is emitted as
`codebooks/<rel>/<stem>__<sanitized>.md`, using the same sanitization and
deduplication as the rest of the pipeline (`Ventas` / `VENTAS` → `__ventas`,
`__ventas_2`). A single-sheet `.xlsx` stays `stem.md`. The root index counts
sheets in `**Tables:**` and sums columns in `**Total columns:**`.

### Codebooks in the package

`prepare --all-files` writes codebooks directly into the output directory:

- Per-file codebooks land under `build/codebooks/`, mirroring relative paths.
  For example, `raw/DPTO.csv` becomes `build/codebooks/DPTO.md`, and an `.xlsx`
  with two sheets becomes `build/codebooks/Report__ventas.md` plus
  `Report__costos.md`.
- The root index `codebook.md` is written to the output root.
- `publish` stages these codebooks after the data files, so the repository ends
  up with `codebooks/**/*.md` plus the root `codebook.md`.

## Profiling and rendering

`profile` and `render` form a lightweight, read-only documentation pipeline
that works on a dataset file alone — no TOML is required for single-file use.

```bash
# 1. Introspect a dataset and write metadata.yaml next to it (source untouched).
sofer profile raw/contacts.csv

# Batch: one metadata.yaml per [[file]] under cache/profiles/<rel_stem>.metadata.yaml.
sofer profile dataset.toml --all-files
sofer profile dataset.toml --all-files --output ./out

# Overwrite guard: without --force an existing destination raises FileExistsError.
sofer profile raw/contacts.csv --output ./out --force

# 2. Render a status-annotated README.md from that metadata.
sofer render raw/                 # directory containing metadata.yaml
sofer render raw/metadata.yaml    # or the file directly
sofer render dataset.toml --all-files
sofer render raw/ --output ./out --force
```

For `.xlsx` with more than one sheet, profile writes
`profiles/<rel>/<stem>__<sanitized>.metadata.yaml` and render writes
`renders/<rel>/<stem>__<sanitized>.README.md`. A single-sheet `.xlsx` stays
`stem.metadata.yaml` / `stem.README.md`. Sanitization is
lowercase → NFKD → ASCII → spaces to `_` → collapse runs of `_` → strip, with
`seen _{n}` deduplication and normalized `__+` → `_` collision handling.
Default batch directories are `profile_dir` and `render_dir` in
`[tool.sofer]`.

`metadata.yaml` is the machine-readable source of truth; `render` is a pure
projection of it and never recomputes inference. Inference states are always
rendered distinctly so a reader can tell a fact from a guess:

| Status | Meaning | Rendered |
| --- | --- | --- |
| `confirmed` | High-confidence, corroborated inference. | `email` |
| `inferred` | Plausible but unverified guess. | `email (inferred, 78%)` |
| `unknown` | Not reliably inferable. | `unknown` |

Unknown human-input fields (`description`, `license`, `source`) render as
`unknown`, never blank and never fabricated.

### Semantic types and PII detection

`profile` distinguishes **what a column is** (semantic type) from **whether it
is sensitive** (possible PII). These are two independent, extensible detector
sets:

- **Semantic type** — the meaning of a column beyond its storage type
  (`integer` → `identifier`, a value matching an email pattern → `email`).
  Each detection carries a confidence score: `match_rate × prior`, where the
  prior reflects the reliability of the pattern.
- **Possible PII** — heuristic detection of potentially sensitive data
  (email, phone, and so on). Always reported as `possible_pii`, never as a
  categorical verdict: a pattern match is an observation, not a legal or
  ethical conclusion.

```yaml
schema:
  - name: email
    storage_type: categorical/text
    semantic_type:
      type: email
      status: confirmed          # confirmed | inferred | unknown
      confidence: 0.98
    pii:
      - label: email
        note: possible_pii
```

Detectors are pluggable. Adding a semantic type or PII pattern is a new detector
class, with no change to the pipeline.

## Next steps

- [Dataset configuration](dataset-config.md) for the TOML keys used above.
- [CLI reference](cli.md) for the flags of each command.
- [Troubleshooting](troubleshooting.md) for upload and platform issues.
