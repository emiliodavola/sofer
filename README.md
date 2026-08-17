# sofer

> **Sofer** (Hebrew: סופר, "scribe") — a person who meticulously transcribes
> sacred texts. This tool brings the same care to dataset documentation.

**A command-line tool that turns a raw dataset into a documented, profiled,
and quality-assessed package — combining automatic inference with human
knowledge, and publishable to Hugging Face Hub or any local directory.**

```plaintext
sofer init my-dataset           # create a .toml template
sofer scan my-dataset.toml      # discover & register data files
sofer profile data.csv          # introspect a dataset → metadata.yaml (read-only)
sofer render metadata.yaml      # render a status-annotated README.md
sofer codebook data.csv         # generate a codebook for one file
sofer codebook --all-files      # generate codebooks for all tables
sofer prepare my-dataset.toml   # generate the package locally (build/)
sofer publish my-dataset.toml   # deliver to HF Hub or a local directory
sofer validate my-dataset.toml  # check data integrity + quality
```

## Why

Sharing data for analysis is hard. The [Leek group guide](https://github.com/jtleek/datasharing)
defines the gold standard: ship (1) raw data, (2) tidy data, (3) a codebook,
and (4) a recipe. sofer fills the gap between your local files and a
well-documented, reusable dataset — whether it ends up on Hugging Face Hub,
in an object store, or in a local directory.

**Key principles:**

- **Automatizar observaciones; no inventar conocimiento semántico.**
  sofer infers what is reliably inferable and marks everything else as a
  guess — it never presents an inference as a fact.
- **Confidential by default.** Repos are private unless you say otherwise.
- **Validate before publishing.** Never ship a broken dataset.
- **Self-documenting.** Every dataset gets structured metadata, a codebook,
  and a README.
- **Two-step workflow.** `prepare` generates everything offline; `publish`
  delivers the prepared package. Inspect and edit artifacts before they go
  anywhere.
- **Read-only profiling.** `profile` never modifies the source dataset.
- **Domain-agnostic.** Works for census data, survey exports, shapefiles,
  document collections — anything you'd put in a dataset repository.

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

# 4. Generate the dataset package locally — zero network calls:
#    Parquet conversion, Dataset Card (README.md), LICENSE, schema report
sofer prepare my-dataset.toml

#    (optionally with per-file codebooks)
sofer prepare my-dataset.toml --all-files

# 5. Validate locally — no network calls
sofer validate my-dataset.toml

# 6. Publish to Hugging Face (auto-creates the repo if missing)
sofer publish my-dataset.toml

#    ...or copy the package to a local directory (no network)
sofer publish my-dataset.toml --target local --output ./out/
```

`publish` re-runs `prepare` automatically whenever the package is missing or
stale (the TOML or any declared source file is newer than the newest Parquet).

## Profiling & rendering (metadata workflow)

`profile` and `render` form a lightweight, read-only documentation pipeline
that works on a dataset file alone — no TOML needed:

```bash
# 1. Introspect a dataset and write metadata.yaml next to it (source untouched)
sofer profile data/contacts.csv

# 2. Render a status-annotated README.md from that metadata
sofer render data/            # directory containing metadata.yaml
sofer render data/metadata.yaml   # ...or the file directly
```

`metadata.yaml` is the machine-readable source of truth; `render` is a pure
projection of it — it never recomputes inference. Inference states are always
rendered distinctly so a reader can tell a fact from a guess:

| Status | Meaning | Rendered |
|---|---|---|
| `confirmed` | high-confidence, corroborated inference | `email` |
| `inferred` | plausible but unverified guess | `email (inferred, 78%)` |
| `unknown` | not reliably inferable | `unknown` |

Unknown human-input fields (description, license, source) render as `unknown`
too — never blank, never fabricated.

### Semantic types & PII detection

`profile` distinguishes **what a column is** (semantic type) from **whether it
is sensitive** (possible PII) — two independent, extensible detector sets:

- **Semantic type** — the *meaning* of a column beyond its storage type
  (`integer` → `identifier`, a value matching an email pattern → `email`).
  Each detection carries a confidence score: `match_rate × prior`, where the
  prior reflects how reliable the pattern itself is.
- **Possible PII** — heuristic detection of potentially sensitive data
  (email, phone, …). Always reported as **`possible_pii`**, never as a
  categorical verdict: a pattern match is an observation, not a legal or
  ethical conclusion.

```yaml
# excerpt from metadata.yaml
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

Detectors are pluggable — adding a new semantic type or PII pattern is a new
detector class, no changes to the pipeline.

## Directory layout

```
data/           source files only (declared in dataset.toml [[file]] local=) — never written by sofer
cache/          sofer artifact cache: codebook --all-files writes cache/codebooks/
build/          prepare output + publish input (per-dataset [dataset] build_dir, default "build")
```

## TOML reference

```toml
[dataset]
name = "my-dataset"
repo_id = "your-username/my-dataset"
private = true
build_dir = "build"   # prepare output directory (default: "build")

[meta]
description = "Short description"
license = "MIT"
tags = ["tag1", "tag2"]

# Every file or directory to publish gets its own [[file]] section.
[[file]]
local = "data/file.csv"
remote = "file.csv"

[[file]]
local = "data/documents/"
remote = "docs/"
recursive = true

# Validation checks: run before every publish.
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

### Metadata inference tuning (`[tool.sofer]`)

The inference pipeline (used by `profile`) is fully configurable in
`pyproject.toml` — no magic numbers in code:

```toml
[tool.sofer]
# Confidence prior per semantic detector (pattern reliability).
# Higher = the pattern alone is more trustworthy.
semantic_priors = { email = 0.98 }

# Status thresholds (confidence bands).
confirm_threshold = 0.8   # >= this → confirmed
min_threshold = 0.5       # >= this → inferred; below → unknown
detect_threshold = 0.5    # match_rate below this → no detection at all

# Profiling sample size (statistics are computed over a bounded sample, never
# a full in-memory load — and reported as such).
profile_max_sample = 100000

# Confidence is rounded to this many decimal places before it is stored.
confidence_round_digits = 4
```

Every value has a sensible default — the whole section is optional.

## Command reference

| Command | Description |
|---|---|
| `init <name>` | Generate a ready-to-edit `.toml` template. |
| `scan [config.toml]` | Discover supported files, flatten first path segment (`raw/DPTO.csv` → `cache/DPTO.csv`), register in TOML, copy to `cache/`. Use `--dry-run` to preview. |
| `profile <dataset>` | Introspect a dataset file read-only (CSV, TSV, Parquet, Excel, JSONL) and write a `metadata.yaml` documenting the detected schema, per-column semantic types, and possible PII. Flags: `--output DIR`. |
| `render <package>` | Render a status-annotated `README.md` from `metadata.yaml` (the file itself or the directory containing it). Flags: `--output DIR`. |
| `codebook <file>` | Generate a markdown codebook for one file. Supports CSV, TSV, Parquet, Excel, JSONL. |
| `codebook --all-files` | Generate one codebook per `[[file]]` entry under `cache/codebooks/`, plus a root `codebook.md` index. Use `--config` to specify the TOML file. |
| `prepare <config.toml>` | Generate the full dataset package locally: CSV→Parquet conversion, cross-file schema checks, schema report, Dataset Card (`README.md`), `LICENSE`, and — with `--all-files` — per-file codebooks. Never contacts HF. Flags: `--output DIR` (default `[dataset] build_dir`), `--all-files`, `--no-checks`, `--force`, `--verify`. |
| `publish <config.toml>` | Deliver the prepared package: `--target hf` (default) ensures the HF repo, gates on the quality report, and pushes the package in a single `upload_folder` call; `--target local` copies the package to `--output` with no network. Auto-prepares when artifacts are stale or missing. Flags: `--target hf\|local`, `--output DIR`, `--force`, `--keep-csv`, `--dry-run`. |
| `validate <config.toml>` | Verify config + data integrity + quality checks. Never contacts HF. |
| `--help` | Detailed help for any command. |

> `sofer upload` was removed in favor of `prepare` + `publish` — the
> generation half (offline, inspectable) and the delivery half (network).

## Data format support

| Format | `scan` | `codebook` | `profile` |
|---|---|---|---|
| CSV (`.csv`) | ✅ | ✅ | ✅ |
| TSV (`.tsv`) | ✅ | ✅ | ✅ |
| Parquet (`.parquet`) | ✅ | ✅ | ✅ |
| Excel (`.xlsx`) | ✅ | ✅ | ✅ |
| JSON Lines (`.jsonl`) | ✅ | ✅ | ✅ |

## Validation & quality checks (automatic)

Every dataset is checked before publish:

### Integrity checks

| Check | What it does | Blocks publish? |
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

Generates one codebook per registered file under `cache/codebooks/<rel-stem>.md`,
plus a root `codebook.md` index with a table of contents and relative links to
all per-table codebooks.  Files from the same source directory that would
resolve to the same output stem (collision) are detected before writing — the
non-colliding files still get their codebook written; the run fails with an
error listing the colliding sources.

### Codebooks in the package

`prepare --all-files` writes codebooks directly into the output directory
(Option B) instead of the shared `cache/`:

- Per-file codebooks land under `build/codebooks/` mirroring their relative
  paths (e.g., `data/DPTO.csv` → `build/codebooks/DPTO.md`).
- The root index `codebook.md` is written to the output root.
- `publish` stages these codebooks after the data files, so the repo ends up
  with `codebooks/**/*.md` plus the root `codebook.md`.

## Architecture

```
src/sofer/
├── __init__.py         # Version + public API
├── _formats.py         # Supported file extension registry
├── _sentinels.py       # Shared sentinel value sets
├── _csv_reader.py      # CSV/TSV streaming reader
├── _mirror.py          # Remote-path validation + dir-aware mirror copies
├── _patterns.py        # Shared regexes (EMAIL_PATTERN)
├── cli.py              # argparse CLI with 8 subcommands (init, scan, validate, prepare, publish, codebook, profile, render)
├── model.py            # DatasetConfig + InferenceStatus
├── checks.py           # DatasetValidator — data integrity checks
├── quality.py          # QualityValidator — 9 quality checks (single-pass)
├── codebook.py         # Multi-format codebook generator
├── scanner.py          # File discovery, TOML merge, copy-to-cache
├── prepare.py          # Offline generation: Parquet conversion, card, LICENSE, codebooks
├── publish.py          # Delivery: HF upload_folder / local copy, auto-prepare, dry-run
├── semantic.py         # Semantic type inference detectors (email)
├── pii.py              # Possible-PII detection detectors (email)
├── metadata.py         # metadata.yaml schema + deterministic (de)serialization
├── profile.py          # Read-only profile orchestrator → metadata.yaml
├── render.py           # Render status-annotated README.md from metadata.yaml
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
