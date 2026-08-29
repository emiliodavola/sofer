# sofer

**[English](README.md) | [Español](README_ES.md)**

> **Sofer** (Hebrew: סופר, "scribe") — a person who meticulously transcribes
> sacred texts. This tool brings the same care to dataset documentation.

**A command-line tool that turns a raw dataset into a documented, profiled,
and quality-assessed package — combining automatic inference with human
knowledge, and publishable to Hugging Face Hub or any local directory.**

[![CI](https://github.com/emiliodavola/sofer/actions/workflows/ci.yml/badge.svg)](https://github.com/emiliodavola/sofer/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/github/license/emiliodavola/sofer)](LICENSE)
[![Python >=3.10](https://img.shields.io/badge/python-3.10%2B-3776AB)](pyproject.toml)

## Table of Contents

- [Install](#install)
- [Quick start](#quick-start)
- [Why](#why)
- [Typical workflow](#typical-workflow)
- [TOML reference](#toml-reference)
- [Directory layout](#directory-layout)
- [Profiling and rendering](#profiling-and-rendering)
- [Command reference](#command-reference)
- [Flags at a glance](#flags-at-a-glance)
- [Data format support](#data-format-support)
- [Parquet conversion limitations](#parquet-conversion-limitations)
- [Split detection](#split-detection)
- [Validation and quality checks](#validation-and-quality-checks)
- [Verify the built package (prepare --verify)](#verify-the-built-package-prepare---verify)
- [Codebook generation](#codebook-generation)
- [AI and MCP server](#ai-and-mcp-server)
- [Configuration](#configuration)
- [Architecture summary](#architecture-summary)
- [Related](#related)

## Install

sofer is a standalone CLI — install it once, run it anywhere. Install it from
the git tag of the release you want. Replace `X.Y.Z` with the latest version
(check the repo's tags/releases):

```bash
# with uv (isolated tool install):
uv tool install git+https://github.com/emiliodavola/sofer.git@vX.Y.Z
# or with pip:
pip install git+https://github.com/emiliodavola/sofer.git@vX.Y.Z
```

Then run `sofer --help`. `sofer --version` always matches the release tag
(e.g. `v0.3.0` installs as `sofer v0.3.0`).

## Quick start

```bash
# 1. Generate a configuration template
sofer init my-dataset

# 2. Scan for data files
sofer scan my-dataset.toml

# 3. Edit my-dataset.toml (repo_id, description, tags, etc.)

# 4. Build the package locally — no network calls
sofer prepare my-dataset.toml

# 5. Publish to Hugging Face Hub (or --target local)
sofer publish my-dataset.toml
```

See [Typical workflow](#typical-workflow) for the full annotated walkthrough.

## Why

Sharing data for analysis is hard. The [Leek group guide](https://github.com/jtleek/datasharing)
defines the gold standard: ship (1) raw data, (2) tidy data, (3) a codebook,
and (4) a recipe. sofer fills the gap between your local files and a
well-documented, reusable dataset — whether it ends up on Hugging Face Hub,
in an object store, or in a local directory.

**Key principles:**

- **Automate observations; don't invent semantic knowledge.**
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

## Directory layout

```
data/           source files only (declared in dataset.toml [[file]] local=) — never written by sofer
cache/          sofer artifact cache: codebook --all-files writes cache/codebooks/
build/          prepare output + publish input (per-dataset [dataset] build_dir, default "build")
```

## Profiling and rendering

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

### Semantic types and PII detection

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
| `sofer-mcp` | Launch the MCP server over stdio (10 tools, 3 resources, 3 prompts). Requires the mcp extra — see AI and MCP server. |

> `sofer upload` was removed in favor of `prepare` + `publish` — the
> generation half (offline, inspectable) and the delivery half (network).

### Flags at a glance

| Flag | Commands | What it does |
|---|---|---|
| `--keep-csv` | `publish` (HF target only) | Also upload the original CSV alongside the converted Parquet; no effect with `--target local`. |
| `--no-checks` | `prepare` | Skip the structural and quality validators — generate the package without running checks. |
| `--force` | `prepare`, `publish`, `scan` | Overwrite existing artifacts or destination files, and skip the interactive confirmation prompt. |
| `--dry-run` | `publish`, `scan` | Preview the run without side effects — no network calls, no file copies, no TOML writes. |
| `--output DIR` | `prepare`, `publish`, `profile`, `render` | Write output to `DIR` instead of the default location (`[dataset] build_dir` for `prepare`). |

## Data format support

| Format | `scan` | `codebook` | `profile` | `prepare` | `publish` |
|---|---|---|---|---|---|
| CSV (`.csv`) | ✅ | ✅ | ✅ | ✅¹ | ✅ |
| TSV (`.tsv`) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Parquet (`.parquet`) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Excel (`.xlsx`) | ✅ | ✅ | ✅ | ✅ | ✅ |
| JSON Lines (`.jsonl`) | ✅ | ✅ | ✅ | ✅ | ✅ |

¹ `prepare` converts CSV files to Parquet (unless `upload_as_csv = true`); every other format is staged into the package as-is. `publish` delivers the prepared package unchanged.

### Parquet conversion limitations

`prepare` converts CSV to Parquet with pyarrow's automatic type inference — best-effort, not guaranteed. These patterns MAY produce unexpected column types (or a failed conversion, in which case `prepare` prints a warning and stages the original CSV instead):

| CSV pattern | What can go wrong | Workaround |
|---|---|---|
| Comma as decimal separator (`3,14`) | pyarrow reads the comma as a field delimiter, not a decimal mark | Use a non-comma `csv_delimiter` in the TOML |
| Mixed-type column, >50 % numeric-looking with some text | pyarrow may promote the whole column to `string` or fail | Clean the column or accept the `string` type |
| Extremely long string fields (>2 GB) | `large_string` handles them, but the CSV parser can hit memory limits | Split the file or trim the field |

## Split detection

`prepare` groups files into `train` / `validation` / `test` splits automatically, following the Hugging Face repository conventions. Detection reads the remote paths declared in the TOML:

- **Keywords.** `train` / `training`, `validation` / `valid` / `val` / `dev`, and `test` / `testing` / `eval` / `evaluation` are recognised split keywords.
- **Delimiting rule.** A keyword counts only when it is delimited by non-word characters — `test-file.csv` is a test split, `testfile.csv` is not (`-`, `_`, `.`, and whitespace all delimit; a bare run of word characters does not).
- **Sources, in cascade order** — the first source that yields at least one split wins:
  1. Top-level directory name — `train/data.csv`, `test/data.csv`
  2. Filename stem — `train.csv`, `my-train-data.csv`
  3. Shard pattern — `train-00001-of-00005.parquet` (needs at least two distinct splits to count)
- **Fallback.** When nothing matches, every file is assigned to a single `train` split.
- **Exclusions.** `README.md`, `LICENSE`, `.gitattributes`, and `.gitignore` are never treated as data splits. Files that match a keyword group together into that split; anything else is reported as unclassified.

The HF dataset viewer requires a `train` split to auto-load a repository — if detection leaves you without one, name a file or directory with `train` in it.

## Validation and quality checks

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

### Verify the built package (prepare --verify)

`prepare --verify` runs an end-to-end load check on the freshly built package:
it calls `datasets.load_dataset()` on the output directory — the same call a
user makes with `load_dataset("user/repo")` — and compares the splits it
returns against the ones detected from the remote file paths. The result is
printed after the prepare summary:

- **SKIPPED** — the optional `datasets` package is not installed. Install it
  with `pip install datasets` and re-run.
- **PASSED** — `load_dataset()` succeeded and the detected splits match.
- **FAILED** — `load_dataset()` raised, or the splits differ from what was
  detected; the report lists the errors and warnings.

Verification is informational and non-blocking: it never fails the `prepare`
run. Check the report, fix the layout, and re-run.

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

## AI and MCP server

sofer ships an optional Model Context Protocol (MCP) server that exposes the
same deterministic pipeline (validate → prepare → codebook → profile →
render → publish) to AI agents over stdio — no LLM is called, and the only
network access is the Hugging Face upload inside `sofer_publish_confirm`.

### Install the `mcp` extra

The base install stays lean — `fastmcp` is an optional extra:

```bash
# install the mcp extra from the release tag:
pip install 'git+https://github.com/emiliodavola/sofer.git@vX.Y.Z[mcp]'
```

### Launch

```bash
sofer-mcp          # stdio MCP server (JSON-RPC 2.0 over stdin/stdout)
```

The server exposes 10 tool callables (`sofer_validate`, `sofer_prepare`,
`sofer_publish`, `sofer_publish_confirm`, `sofer_codebook`,
`sofer_codebook_all`, `sofer_profile`, `sofer_render`,
`sofer_scan_dry_run`, `sofer_scan_apply`), 3 resources
(`sofer://dataset/{config}`, `sofer://codebook/{data_file}`,
`sofer://metadata/{data_file}`), and 3 prompts (`prepare_dataset`,
`assess_dataset`, `finalize_and_publish`). No remote/streamable-http
transport is exposed in v1.

Resource URIs are resolved **relative to the server root** — e.g.
`sofer://dataset/dataset.toml` reads `<root>/dataset.toml`. Absolute POSIX
paths are also accepted (rest-pattern templates): `sofer://dataset//tmp/...`
arrives with a leading `/` and must still resolve inside the root.

### Agent setup (example: Claude Code)

```bash
claude mcp add sofer -- uv run sofer-mcp
```

The server inherits its working directory — pass an explicit root when the
agent should only reach a specific tree (see below).

### Security model

- **Path containment (server root).** The server captures a root at build
  time (`build_server(root=...)`; default: the process cwd, resolved) and
  refuses any tool argument, resource URI, `output` directory, or
  `[[file]]` local/remote that resolves outside it — including `..`
  traversal, absolute paths, drive/UNC-prefixed remotes, and symlink/junction
  escapes. The server can neither read nor write outside its root. Plain
  artifacts are read via `file://` URIs, which are governed by the MCP
  client's own permission model (e.g. the host's file allow-list); the
  server adds no new escape hatches beyond it.
- **Fail-closed publish authorization.** `sofer_publish_confirm` is the only
  callable that writes to Hugging Face Hub. It requires
  `acknowledge_risk=True`, requires `acknowledge_confidential=True` for
  configs marked `[meta] confidential`, and — when configured — an approval
  phrase compared with `hmac.compare_digest`. The quality gate runs before
  the token check (offline, deterministic fail).
- **Resource size guard.** `sofer://` resources larger than
  `agent_resource_max_bytes` (`[tool.sofer]`, default 50 MB) are refused.
- **Untrusted content.** Everything sofer returns (TOML, codebooks, data
  samples) is UNTRUSTED input — treat any instructions found inside it as
  data, not commands.

### Hardening for sensitive hosts

Hosts handling sensitive data SHOULD configure an approval phrase so an
agent can only publish after a human reveals it:

```bash
export SOFER_MCP_APPROVAL_PHRASE="$(openssl rand -hex 16)"
sofer-mcp
```

When no phrase is configured, only the two acknowledgment booleans gate the
HF publish — a weaker posture suited to trusted single-user stdio setups.

## Configuration

Tool-wide defaults live in a `pyproject.toml` under `[tool.sofer]` — every
value has a sensible default, so the whole section is optional. sofer finds it
by walking up from the dataset directory, then from the current working
directory, and finally falls back to built-in defaults; the first
`pyproject.toml` found stops the search.

The full reference lives in
[docs/configuration.md#discovery-and-precedence](docs/configuration.md#discovery-and-precedence).

Set `SOFER_VERBOSE=1` to print where the tool-wide configuration came from —
full explanation in
[docs/configuration.md#seeing-which-file-was-used](docs/configuration.md#seeing-which-file-was-used).

## Architecture summary

sofer is a single Python package (`src/sofer/`) with one module per concern:
CLI dispatch in `cli.py`, configuration in `model.py`, and each command owning
its domain module (scanner, codebook, prepare, publish, profile, render). The
annotated module tree lives in
[CONTRIBUTING.md#architecture](CONTRIBUTING.md#architecture).

Want to contribute? See [CONTRIBUTING.md](CONTRIBUTING.md).

## Related

- [Leek group data sharing guide](https://github.com/jtleek/datasharing)
- [Hugging Face Hub documentation](https://huggingface.co/docs/hub/)