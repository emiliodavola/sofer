# sofer

> **Sofer** (Hebrew: סופר, "scribe") — a person who meticulously transcribes
> sacred texts. This tool brings the same care to dataset documentation.

**Publish any dataset to Hugging Face Hub with built-in validation and
data-sharing standards.**

```
sofer init my-dataset           # create a .toml template
sofer scan my-dataset.toml      # discover & register data files
sofer validate my-dataset.toml  # check data integrity + quality
sofer codebook data.csv         # generate a codebook for one file
sofer codebook --all-files      # generate codebooks for all tables
sofer upload   my-dataset.toml  # upload to Hugging Face
```

## Why

Sharing data for analysis is hard. The [Leek group guide](https://github.com/jtleek/datasharing)
defines the gold standard: ship (1) raw data, (2) tidy data, (3) a codebook,
and (4) a recipe.  Hugging Face Hub provides the storage — this tool fills
the gap between your local files and a well-documented HF dataset.

**Key principles:**

- **Confidential by default.** Repos are private unless you say otherwise.
- **Validate before uploading.** Never ship a broken dataset.
- **Self-documenting.** Every dataset gets a codebook and a README.
- **Domain-agnostic.** Works for census data, survey exports, shapefiles,
  document collections — anything you'd put in a HF dataset repo.

## Setup

```bash
uv sync
cp .env.template .env   # then edit .env with your HF token
```

> Get your token at: https://huggingface.co/settings/tokens

## Typical workflow

```bash
# 1. Create a configuration template
sofer init my-dataset

# 2. Scan for data files (auto-registers all CSV, Parquet, Excel, JSONL files)
sofer scan my-dataset.toml

# 3. Edit my-dataset.toml (repo_id, description, tags, etc.)

# 4. Generate codebooks for all registered tables
sofer codebook --all-files --config my-dataset.toml

# 5. Validate locally — no network calls
sofer validate my-dataset.toml

# 6. Upload to Hugging Face (auto-creates the repo if missing)
sofer upload my-dataset.toml
```

## TOML reference

```toml
[dataset]
name = "my-dataset"
repo_id = "your-username/my-dataset"
private = true

[meta]
description = "Short description"
license = "MIT"
tags = ["tag1", "tag2"]

# Every file or directory to upload gets its own [[file]] section.
[[file]]
local = "data/file.csv"
remote = "file.csv"

[[file]]
local = "data/documents/"
remote = "docs/"
recursive = true

# Validation checks: run before every upload.
[[check]]
min_files = 2

[[check]]
columns = "file.csv"
expected = ["column_a", "column_b"]

# Quality checks: run automatically with sensible defaults.
# Uncomment to customise severity or thresholds:
# [[quality]]
# check = "duplicates"
# severity = "fail"
#
# [[quality]]
# check = "null_profiling"
# max_null_pct = 15.0
```

## Command reference

| Command | Description |
|---|---|
| `init <name>` | Generate a ready-to-edit `.toml` template. |
| `scan [config.toml]` | Discover supported files, register in TOML, copy to `data/`. Use `--dry-run` to preview. |
| `validate <config.toml>` | Verify config + data integrity + quality checks. Never contacts HF. |
| `upload <config.toml>` | Validate + quality gate + upload to HF. Supports `--dry-run`, `--force`, `--verify-load`, `--keep-csv`. |
| `codebook <file>` | Generate a markdown codebook for one file. Supports CSV, TSV, Parquet, Excel, JSONL. |
| `codebook --all-files` | Generate codebooks for every `[[file]]` entry. Always creates a root index. Use `--config` to specify the TOML file. |
| `--help` | Detailed help for any command. |

## Data format support

| Format | `scan` | `codebook` |
|---|---|---|
| CSV (`.csv`) | ✅ | ✅ |
| TSV (`.tsv`) | ✅ | ✅ |
| Parquet (`.parquet`) | ✅ | ✅ |
| Excel (`.xlsx`) | ✅ | ✅ |
| JSON Lines (`.jsonl`) | ✅ | ✅ |

## Validation & quality checks (automatic)

Every dataset is checked before upload:

### Integrity checks

| Check | What it does | Blocks upload? |
|---|---|---|
| File existence | Every declared path must exist on disk | Yes |
| Min file count | Configurable via `[[check]] min_files` | Yes |
| Min total size | Configurable via `[[check]] min_total_size_mb` | No (warning) |
| CSV columns | Checks expected columns exist | Yes |
| Config integrity | Valid `repo_id`, valid paths | Yes |

### Quality checks

| Check | What it detects |
|---|---|
| Duplicates | Duplicate rows in tabular data |
| Empty rows | Rows with no values |
| Empty columns | Columns with no values |
| Null profiling | Columns exceeding null threshold |
| Format consistency | Mixed types within columns |
| Corrupt records | Unparseable rows |
| Value range | Values outside min/max bounds |
| Cross-file types | Dtype mismatches across configs |
| Encoding validation | File encoding issues |

## Codebook generation

### Single file

```bash
sofer codebook data/persons.csv -o codebook.md
```

Supports CSV, TSV, Parquet, Excel (.xlsx), and JSON Lines (.jsonl).
Produces a table with: column name, inferred type, actual dtype (for
typed formats), unique values, missing percentage, and a sample value.

### Batch generation

```bash
sofer codebook --all-files --config my-dataset.toml
```

Generates a `codebook.md` alongside each data file under `data/`,
plus a root `codebook.md` index with a table of contents and relative
links to all per-table codebooks.

## Architecture

```
src/sofer/
├── __init__.py         # Version + public API
├── _formats.py         # Supported file extension registry
├── _sentinels.py       # Shared sentinel value sets
├── _csv_reader.py      # CSV/TSV streaming reader
├── cli.py              # argparse CLI with 6 subcommands
├── model.py            # DatasetConfig — loads & validates TOML
├── checks.py           # DatasetValidator — data integrity checks
├── quality.py          # QualityValidator — 9 quality checks (single-pass)
├── codebook.py         # Multi-format codebook generator
├── scanner.py          # File discovery, TOML merge, copy-to-data
├── uploader.py         # HF upload engine (huggingface_hub API + Parquet conversion)
├── repo_compliance.py  # Dataset Card & schema compliance
├── splits.py           # Split detection (train/test/validation)
└── verification.py     # load_dataset() end-to-end verification
```

## Development

```bash
uv run pytest
uv run mypy src/
uv run ruff check src/ tests/
```

## Related

- [Leek group data sharing guide](https://github.com/jtleek/datasharing)
- [Hugging Face Hub documentation](https://huggingface.co/docs/hub/)
