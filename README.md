# sofer

**[English](README.md) | [Español](README_ES.md)**

> **Sofer** (Hebrew: סופר, "scribe") — a person who meticulously transcribes
> sacred texts. This tool brings the same care to dataset documentation.

**A command-line tool that turns a raw dataset into a documented, profiled,
and quality-assessed package — combining automatic inference with human
knowledge, and publishable to Hugging Face Hub or any local directory.**

[![CI](https://github.com/emiliodavola/sofer/actions/workflows/ci.yml/badge.svg)](https://github.com/emiliodavola/sofer/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python >=3.10](https://img.shields.io/badge/python-3.10%2B-3776AB)](pyproject.toml)

## What sofer does

sofer fills the gap between a folder of raw files and a reusable dataset. It
converts tabular data, inspects the schema, detects splits, profiles columns,
flags possible PII, generates a codebook and a Dataset Card, and validates the
result before delivery.

It is for researchers, data stewards, and teams who publish datasets — whether
the destination is Hugging Face Hub, an object store, or a local directory.

**Principles:**

- **Automate observations; do not invent semantic knowledge.** sofer marks an
  inference as a guess, never as a fact.
- **Confidential by default.** Repositories are private unless you explicitly
  change the posture.
- **Validate before publishing.** Never ship a broken dataset.
- **Two-step workflow.** `prepare` builds offline; `publish` delivers.
- **Read-only profiling.** `profile` never modifies the source dataset.
- **Domain-agnostic.** Works for census data, surveys, spreadsheets, document
  collections, and other tabular sources.

## Install

Install the release tag you want, replacing `X.Y.Z`:

```bash
uv tool install "sofer @ git+https://github.com/emiliodavola/sofer.git@vX.Y.Z" --force
```

Then verify:

```bash
sofer --help
sofer --version
```

`sofer --version` matches the release tag. Other supported install paths:

```bash
pip install "sofer @ git+https://github.com/emiliodavola/sofer.git@vX.Y.Z"
pip install "sofer[mcp] @ git+https://github.com/emiliodavola/sofer.git@vX.Y.Z"
uvx --from git+https://github.com/emiliodavola/sofer.git@vX.Y.Z --with "sofer[mcp]" sofer-mcp --help
```

See [installation alternatives](docs/getting-started.md#install) for the full
comparison.

## Quick start

Run these commands from the dataset directory.

```bash
# 1. Create the configuration and scaffold raw/
sofer init my-dataset --user myuser

# 2. Discover data files
sofer scan my-dataset.toml

# 3. Fill the human metadata step (see below)
sofer meta check my-dataset.toml
sofer meta set my-dataset.toml \
  --set description="<what the data contains>" \
  --set license="<license from the data owner>" \
  --set source="<source organisation>" \
  --set tags="<tag1>,<tag2>"

# 4. Build the package locally — no network calls
sofer prepare my-dataset.toml

# 5. Inspect the result in build/

# 6. Publish as a separate, explicit step
sofer publish my-dataset.toml --dry-run
sofer publish my-dataset.toml --target local --output ./out/   # no network
# or: sofer publish my-dataset.toml                            # Hugging Face Hub
```

> **`scan` moves files.** Phase 1 MOVEs loose supported files into `raw/`,
> preserving the tree; Phase 2 copies `raw/` to `cache/`. The move keeps the
> registered sources in `raw/`, not only in the disposable `cache/`.

> **Local build is not publishing.** `prepare` writes the package to `build/`
> and never contacts Hugging Face. Inspect and edit the artifacts before you
> publish.

> **Repositories are private by default.** A public target is a separate
> decision and needs explicit authorization. See [Security](docs/security.md).

The metadata step is shared work: an agent can infer the description and tags,
while a human supplies the license and source. `sofer meta check` reports
placeholders and `sofer meta set` writes the real values. Do not guess a
license or a source.

## What the package contains

```text
build/                  prepare output; publish input
├── *.parquet           converted data (or originals with convert_to_parquet = false)
├── README.md           generated Dataset Card
├── LICENSE             generated from [meta] license
├── manifest.json       delivery record used by publish
├── codebook.md         root index, with --all-files
└── codebooks/          one page per file, with --all-files
```

The source layout is `raw/` → `cache/` → `build/`:

- `raw/` is the tracked source root.
- `cache/` is the gitignored artifact cache used by `scan`.
- `build/` is the package directory, configurable with `[dataset] build_dir`.

Supported input formats: CSV (`.csv`), TSV (`.tsv`), Parquet (`.parquet`),
Excel (`.xlsx`), and JSON Lines (`.jsonl`). See
[Dataset configuration](docs/dataset-config.md#source-layout) and
[Data package](docs/data-package.md#supported-formats) for conversion rules,
limitations, and splits.

## MCP for AI agents

sofer ships a stdio Model Context Protocol server with **19 tools**, **4
resources**, and **3 prompts**. It exposes the same deterministic pipeline and
calls no LLM; the only network access is the Hugging Face upload in
`sofer_publish_confirm`. `fastmcp` is included by default, and `sofer[mcp]` is
an alias for the same wheel.

Use `sofer mcp add --agent <opencode|codex|gemini|pi|hermes|all>` to register
it. The canonical chain is:

```python
# Phase 0 Bootstrap
sofer_init(name="my-dataset", user="myuser")
sofer_scan_apply(config="my-dataset.toml")
sofer_meta_set(config="my-dataset.toml", values={"license": "<license>"})
# Phase 1 Build
sofer_validate(config="my-dataset.toml")
sofer_prepare(config="my-dataset.toml", output_dir=None, run_checks=True, force=False)
sofer_codebook_all(config="my-dataset.toml")
sofer_profile_all(config="my-dataset.toml")
sofer_render_all(config="my-dataset.toml")
# Phase 2 Publish
sofer_publish(config="my-dataset.toml", dry_run=True)
```

See [MCP server](docs/mcp.md) and [Agent setup](docs/agent-setup.md).

## Documentation

| Task | Read |
| --- | --- |
| Install alternatives, full walkthrough, metadata step | [Getting started](docs/getting-started.md) |
| Commands, flags, `meta`, and `mcp` | [CLI reference](docs/cli.md) |
| Dataset TOML, `[meta]`, `[[file]]`, `[[check]]`, `[[quality]]` | [Dataset configuration](docs/dataset-config.md) |
| Formats, conversion, splits, quality, codebooks, profiling | [Data package](docs/data-package.md) |
| `[tool.sofer]` defaults and precedence | [Tool-wide configuration](docs/configuration.md) |
| MCP tools, resources, prompts, and response contracts | [MCP server](docs/mcp.md) |
| Agent registration, environment, and timeouts | [Agent setup](docs/agent-setup.md) |
| Path containment, approval phrase, credentials | [Security](docs/security.md) |
| Windows, Hub uploads, and failure reports | [Troubleshooting](docs/troubleshooting.md) |

## Contributing

Architecture, development setup, conventions, and quality gates live in
[CONTRIBUTING.md](CONTRIBUTING.md). Pull requests are welcome; see the
[PR template](.github/PULL_REQUEST_TEMPLATE.md). Security reports follow
[SECURITY.md](SECURITY.md).

## Related

- [Leek group data sharing guide](https://github.com/jtleek/datasharing)
- [Hugging Face Hub documentation](https://huggingface.co/docs/hub/)
- [MIT License](LICENSE)
