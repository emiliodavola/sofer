# Contributing to sofer

Thanks for taking the time to contribute! :rocket:

## Getting started

1. **Fork** the repository and clone your fork.
2. Create a branch for your change (`feat/my-feature` or `fix/bug-description`).
3. Set up the environment — see [Development setup](#development-setup) below.
4. Make your changes, add tests, and ensure `uv run pytest` passes.

## Development setup

```bash
uv sync
pre-commit install
cp .env.template .env   # then edit .env with your HF token
```

> Get your token at: https://huggingface.co/settings/tokens

## Development commands

Run these from the repository root:

```bash
uv run pytest
uv run mypy src/
uv run ruff check src/ tests/
```

## Architecture

sofer is a single Python package with one module per concern: CLI dispatch
lives in `cli.py`, configuration in `model.py`, and each command owns its
domain module.

```
src/sofer/
├── __init__.py         # Package docstring + public API
├── _version.py         # Runtime version resolution (installed metadata + dev fallback)
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
├── verification.py     # load_dataset() end-to-end verification
└── mcp_server.py       # Optional MCP server (stdio) — tools, resources, prompts
```

## Development conventions

### Code style

This project uses **ruff** for linting and formatting. Configuration is in `ruff.toml` at the repo root. Run `ruff check` and `ruff format` before committing — the pre-commit hook does this automatically.

### Type checking

We use **mypy** in strict mode. Run `mypy src/` to check types. The CI will reject PRs that don't type-check.

### Commit messages

Use [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/):

```
feat(compliance): add split detection to upload pipeline
fix(encoding): reject non-UTF-8 files in quality check
```

Prefixes: `feat`, `fix`, `docs`, `test`, `ci`, `chore`, `refactor`.

## Pull requests

- Open a PR against the `dev` branch.
- Fill the PR template — describe what, why, and how.
- Changes touching a user-facing README section MUST update README_ES.md in the same commit.
- Link related issues (`Closes #N`).
- PRs need at least one approving review before merge.

## Testing

- Run `uv run pytest` for the full suite.
- Add tests for new behaviour in the appropriate `tests/` file.
- Target: no drop in coverage.

## Reporting bugs

Use the issue template and include:
- Steps to reproduce
- Expected vs actual behaviour
- `sofer --version` output
- Relevant TOML config (sanitised)

## Questions?

Open a [discussion](https://github.com/emiliodavola/sofer/discussions) or reach out in an issue.