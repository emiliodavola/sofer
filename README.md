# data-uploader

**Publish any dataset to Hugging Face Hub with built-in validation and
data-sharing standards.**

```
data-uploader init my-dataset           # create a .toml template
data-uploader validate my-dataset.toml  # check data integrity
data-uploader upload   my-dataset.toml  # upload to Hugging Face
data-uploader codebook data.csv         # generate a markdown codebook
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
data-uploader init my-dataset

# 2. Edit my-dataset.toml (file paths, repo_id, description, etc.)

# 3. Validate locally — no network calls
data-uploader validate my-dataset.toml

# 4. Upload to Hugging Face (auto-creates the repo if missing)
data-uploader upload my-dataset.toml
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
```

## Command reference

| Command | Description |
|---|---|
| `init <name>` | Generate a ready-to-edit `.toml` template. |
| `validate <config.toml>` | Verify config + local data. Never contacts HF. |
| `upload <config.toml>` | Validate + upload everything to HF. |
| `codebook <file.csv>` | Analyse a CSV and produce a markdown codebook. |
| `--help` | Detailed help for any command. |

## Validation checks (automatic)

Every dataset is checked before upload:

| Check | What it does | Blocks upload? |
|---|---|---|
| File existence | Every declared path must exist on disk | Yes |
| Min file count | Configurable via ``[[check]] min_files`` | Yes |
| Min total size | Configurable via ``[[check]] min_total_size_mb`` | No (warning) |
| CSV columns | Checks expected columns exist | Yes |
| Config integrity | Valid ``repo_id``, valid paths | Yes |

## Codebook generation

```bash
data-uploader codebook data/persons.csv -o codebook.md
```

Produces a table with: column name, inferred type (numeric / categorical / mixed),
unique values, missing percentage, and a sample value.
Analyses up to 100 000 rows by default (configurable with ``--max-sample``).

## Architecture

```
src/data_uploader/
├── __init__.py     # Module docstring
├── cli.py          # CLI parser & command dispatch
├── model.py        # DatasetConfig — loads & validates TOML
├── checks.py       # DatasetValidator — runs data integrity checks
├── codebook.py     # CSV analyser & markdown codebook generator
└── uploader.py     # Upload engine (wraps huggingface-cli)
```

## Development

```bash
uv run pytest
uv run data-uploader validate examples/sample.toml   # smoke test
```

## Related

- [Leek group data sharing guide](https://github.com/jtleek/datasharing)
- [Hugging Face Hub documentation](https://huggingface.co/docs/hub/)
