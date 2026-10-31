# Dataset configuration

A dataset is described by one TOML file. Tool-wide defaults live separately in
`pyproject.toml` under `[tool.sofer]`; see
[Tool-wide configuration](configuration.md).

## Minimal example

```toml
[dataset]
name = "my-dataset"
repo_id = "your-username/my-dataset"
private = true
build_dir = "build"

[meta]
description = "Short description"
license = "MIT"
source = "Some organisation"
tags = ["tag1", "tag2"]

[[file]]
local = "cache/file.csv"
remote = "file.csv"

[[file]]
local = "cache/documents/"
remote = "docs/"
recursive = true

[[check]]
min_files = 2

[[check]]
columns = "file.csv"
expected = ["column_a", "column_b"]

[[quality]]
check = "duplicates"
severity = "fail"

[[quality]]
check = "null_profiling"
max_null_pct = 15.0
```

## `[dataset]`

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `name` | string | required | Short human-readable name; also names the generated TOML during `init`. |
| `repo_id` | string | required | Hugging Face `user/repo` identifier. |
| `repo_type` | string | `"dataset"` | Repository type. |
| `private` | bool | `true` | Target visibility. Repositories are private by mandate; `private = false` requires an explicit `public_reason`. |
| `public_reason` | string | `""` | Required authorization when `private` is explicitly `false`. Echoed into the publish plan, `sofer_auth_status`, and the manifest. |
| `skip_cross_file_schema` | bool | `false` | Skip the schema consistency check across files that share column names. |
| `build_dir` | string | `"build"` | Output directory for `prepare` and publish input, relative to the TOML directory. `--output` overrides it per run. |

## `[meta]`

`[meta]` is the Dataset Card and LICENSE metadata. `sofer init` writes
placeholders; filling them is a required step before the build. The settable
surface is 39 keys — every `[meta]` key the pipeline reads.

### Required before build

| Key | Kind | Meaning |
| --- | --- | --- |
| `description` | text | One-line description shown on the repository page. |
| `license` | text | SPDX identifier or `restricted`. |
| `source` | text | Origin institution or organization. |
| `tags` | list | Discoverability tags. |

### Visibility and data-sharing fields

| Key | Kind | Meaning |
| --- | --- | --- |
| `confidential` | flag | Marks sensitive or legally protected data. A publish requires `acknowledge_confidential`. An explicit `confidential = false` requires `confidentiality_reason`. |
| `confidentiality_reason` | text | Authorization for an explicit confidentiality opt-out. |
| `language` | list | ISO 639-1/639-3 language codes, e.g. `["en"]`. |
| `pretty_name` | text | Human-readable display name for the card. |
| `task_categories` | list | Hugging Face task category labels. |
| `size_categories` | text | Canonical Hugging Face size category. |
| `citation` | text | BibTeX or plain-text citation. |
| `collection_method` | text | How the data was collected. |
| `csv_delimiter` | text | Dataset-level CSV delimiter (default `;`). |
| `csv_encoding` | text | Dataset-level CSV encoding (default `utf-8-sig`). |
| `annotations_creators` | list | Source of annotations. |
| `language_creators` | list | Source of language content. |
| `language_details` | list | Additional language metadata. |
| `multilinguality` | text | `monolingual`, `multilingual`, `translation`, or `other`. |
| `task_ids` | list | Hugging Face task identifiers. |
| `paperswithcode_id` | text | Papers With Code dataset identifier. |
| `config_names` | list | Configuration names for multi-config datasets. |
| `license_name` | text | Custom license name when `license` is not an SPDX identifier. |
| `license_link` | text | URL or relative path to the license text. |
| `license_details` | text | Additional license terms. |
| `funded_by` | text | Funder or grant. |
| `shared_by` | text | Person or organization that shared the dataset. |
| `paper_url` | text | URL to an associated paper. |
| `demo_url` | text | URL to an interactive demo. |
| `dataset_card_authors` | text | Card authors, comma-separated or free text. |
| `repository` | text | Repository section of the card. |
| `direct_use` | text | Intended use. |
| `out_of_scope_use` | text | Out-of-scope use. |
| `bias_risks_limitations` | text | Bias, risks, and limitations. |
| `contact` | text | Contact information. |
| `curation_rationale` | text | Rationale for the curation decisions. |

### Documentation files

These optional paths resolve against the TOML directory, never the process
working directory:

| Key | Kind | Meaning |
| --- | --- | --- |
| `readme` | text | Additional README embedded into the card. |
| `codebook` | text | Codebook file. |
| `study_design` | text | Study-design document. |
| `recipe` | text | Processing recipe or reproduction steps. |

### Writing `[meta]`

Over the CLI:

```bash
sofer meta check my-dataset.toml
sofer meta set my-dataset.toml --set license=MIT --set tags=census,tabular
```

Over MCP: `sofer_meta_check` and `sofer_meta_set`. Both preserve unrelated keys,
comments, and tables; the write is atomic and idempotent.

## `[[file]]`

Every file or directory to publish gets its own `[[file]]` entry.

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `local` | path | required | Local path, relative to the TOML file or absolute. For `scan` output this is under `cache/`. |
| `remote` | string | required | Destination path inside the repository. |
| `recursive` | bool | `false` | Upload a directory recursively. |
| `convert_to_parquet` | bool | `true` | Convert CSV/TSV/XLSX/JSONL to normalized Parquet; `false` keeps the original. |
| `upload_as_csv` | bool | `false` | Deprecated, CSV-only alias for `convert_to_parquet = false`. An explicit `convert_to_parquet` wins. |
| `include_in_schema` | bool | `true` | Whether the file contributes to the schema report. |
| `column_types` | table | `{}` | Force named columns to a declared type. `"string"` is the only accepted value today; a zero-padded code such as `"001"` uses it to keep its source text. |

Example: keep a zero-padded code as text.

```toml
[[file]]
local = "cache/geo.csv"
remote = "geo.csv"
column_types = { "DPTO" = "string" }
```

`prepare` probes the source (at most `leading_zero_probe_rows` rows, default
1000) and prints each forced-type decision. If a value cannot be preserved, the
run fails naming the column, a sample value, and the exact declaration that
fixes it; that file is not delivered. `sofer validate` reports the same finding
as a warning before `prepare` runs.

## `[[check]]`

Integrity thresholds and expected columns.

| Key | Type | Meaning |
| --- | --- | --- |
| `min_files` | int | Minimum number of file entries (default 1). |
| `min_total_size_mb` | float | Minimum total data size in MB. A miss is a warning, not a block. |
| `columns` | string | Remote file name to check. |
| `expected` | list | Column names that must exist in that file. |

## `[quality]` and `[[quality]]`

Quality checks run in a single streaming pass with bounded per-row memory.
The tool-wide policy lives in
[Tool-wide configuration](configuration.md#quality-scan-bounds).

Per-check overrides:

```toml
[[quality]]
check = "duplicates"
severity = "fail"
min_unique = 100

[[quality]]
check = "null_profiling"
columns = ["person_id"]
max_null_pct = 5
```

| Key | Meaning |
| --- | --- |
| `check` | Check name: `duplicates`, `empty_rows`, `empty_columns`, `null_profiling`, `format_consistency`, `corrupt_records`, `value_range`, `cross_file_types`, or `encoding_validation`. |
| `severity` | `warn` or `fail`. |
| `columns` | Column subset; omitted means all columns. Not accepted by `duplicates`, which compares whole records — declaring it there is a configuration error. |
| `max_null_pct` | Threshold for `null_profiling` (0-100). |
| `min` / `max` | Bounds for `value_range`. |
| `min_unique` | Minimum number of distinct records for `duplicates`. Records are counted per file, so identical rows in two different files count separately. |
| `ignore_values` | Values treated as non-missing during type inference. |

Dataset-level scan policy:

```toml
[quality]
full_scan = "auto"   # auto | always | never
max_sample = 100000
```

TOML forbids `[quality]` and `[[quality]]` in the same file, so the policy
table and per-check overrides are mutually exclusive.

## Source layout

```text
raw/     tracked source root — put CSV/XLSX/JSONL here (e.g. raw/DPTO.csv)
cache/   sofer artifact cache (OUTPUT_DIR, gitignored) — scan copies here
build/   prepare output + publish input (per-dataset [dataset] build_dir, default "build")
```

```text
raw/DPTO.csv                -> cache/DPTO.csv                -> build/*.parquet
raw/Labels/etiquetas_a.csv  -> cache/Labels/etiquetas_a.csv  -> build/*.parquet
```

`sofer init` scaffolds `raw/` idempotently. `sofer init --move-existing` moves
depth-1 supported files (`.csv`, `.tsv`, `.parquet`, `.xlsx`, `.jsonl`) into
`raw/`; `--dry-run` previews and `--force` skips the confirmation prompt.

`sofer scan` is MOVE-then-copy:

1. It discovers supported files outside `raw/`, `cache/`, and `EXCLUSIONS`
   (`.git`, `__pycache__`, `.venv`, `node_modules`, `dist`, `build`).
2. It MOVEs each loose file to `raw/<relative_to(base_dir)>`, preserving the
   tree and creating parents. `check_raw_collisions` runs before any move, so a
   collision aborts atomically. `--dry-run` prints `-> raw/<rel>`;
   `--force`/`[y/N]` gates the move.
3. It copies `raw/` to `cache/`, keyed relative to `raw/`
   (`raw/DPTO.csv` → `cache/DPTO.csv`, `raw/Labels/x.csv` →
   `cache/Labels/x.csv`), registers each new file as a `[[file]]` entry, and
   copies it into `cache/`.

The move is not optional in either scan surface: `sofer_scan_apply` runs it
unconditionally, so registered sources never live only in the disposable
`cache/`. Re-running `scan` is safe; already-registered files are skipped.

## Configuration semantics

- `private` defaults to `true`.
- Relative `local`, `build_dir`, and documentation paths resolve against the
  TOML directory, not the process working directory.
- An empty or placeholder `[meta]` value makes `sofer validate` warn. The
  warning never changes the exit code.
- A `build/` tree that predates a `[meta]` edit keeps the old card and LICENSE
  until `sofer prepare` runs again.
