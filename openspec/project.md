# Project: sofer

Publish any dataset to Hugging Face Hub with built-in validation and data-sharing standards.

## Stack

| Domain           | Tool                                                 |
| ---------------- | ---------------------------------------------------- |
| Language         | Python 3.10+                                         |
| Package manager  | uv                                                   |
| Build            | hatchling                                            |
| Linter           | ruff (E, F, I, N, W, UP, RUF)                        |
| Formatter        | ruff (line-length=100, double quotes)                |
| Type checker     | mypy (strict=true) + pyright (standard)              |
| Test runner      | pytest 9.1.1                                         |
| Pre-commit       | ruff (lint+fix+format), mypy, pyright                |
| CI               | GitHub Actions (uv sync -> ruff -> mypy -> pyright -> pytest matrix 3.10-3.14) |

## Project Structure

```
src/sofer/
├── cli.py               # argparse CLI, 10 subcommands: init, scan, validate, prepare, publish, codebook, profile, render, mcp, report-failure
├── model.py             # DatasetConfig dataclass, TOML loading, config validation
├── config.py            # Tool-wide defaults from [tool.sofer] in pyproject.toml
├── checks.py            # DatasetValidator — data integrity checks
├── scanner.py           # Dataset scanning / raw↔cache helpers + TOML merge
├── codebook.py          # CSV analysis + markdown codebook generation
├── prepare.py           # Local artifact generation (parquet, card, LICENSE, codebooks) — offline
├── publish.py           # Delivery engine: hf target (upload_folder) + local target
├── profile.py           # Dataset profiling → metadata.yaml (read-only)
├── render.py            # metadata.yaml → README.md rendering
├── metadata.py          # Metadata core (profile/render domain model)
├── semantic.py / pii.py # Semantic type + PII inference
├── mcp_server.py        # MCP server (sofer-mcp) — fastmcp (included by default; sofer[mcp] is alias)
├── _mirror.py / _formats.py / _csv_reader.py / _parquet_helpers.py / _converters.py / _patterns.py / _sentinels.py / _version.py / _toml.py
├── repo_compliance.py / splits.py / verification.py / quality.py / execution_context.py / manifest.py / workflow.py
└── __init__.py          # package docstring + public API — the module set follows `ls src/sofer/`

tests/  (pytest suite — `uv run pytest tests/ -q`; CI runs the matrix `uv run pytest -v` on Python 3.10–3.14)
├── test_cli.py / test_checks.py / test_codebook.py / test_model.py / test_prepare.py / test_publish.py
├── test_micro*.py, test_scanner.py / test_repo_compliance.py / test_quality.py / test_profile.py / test_render.py / ...
└── test_update_citation.py, test_mcp*.py, test_parquet_conversion.py, test_sentinels.py, ...
```

## Architecture

- CLI dispatches to pure-Python commands via argparse subparsers with `func` dispatch pattern
- `DatasetConfig.from_toml()` loads config, returns dataclass
- `DatasetValidator(cfg).run_all()` runs integrity checks, returns ValidationReport
- `prepare()` generates all artifacts locally (parquet, README, LICENSE, codebooks) — zero network
- `publish()` delivers a prepared package: `--target hf` uses `upload_folder`, `--target local` writes to disk
- `publish` auto-runs `prepare` when artifacts are stale (TOML/source mtimes vs newest parquet)
- `codebook.generate()` analyses tabular files and returns markdown string; `generate_all()` emits N codebooks per XLSX sheet (`codebooks/<rel>/<stem>__<sanitized>.md` via `sanitize_sheet_name` + `seen` dedup, sheet-aware collision/index, single-sheet stays `stem.md`)
- `repo_compliance.build_dataset_card()` groups `ColumnSchema` by `origin` and renders per-sheet collapsible Data Fields (`<details><summary>Data Fields -- <sheet> (N cols)</summary>` + blank line) gated by `config.CARD_COLLAPSE_THRESHOLD` (`[tool.sofer] card_collapse_threshold=15`, `int>=0`, `len(group)>thr OR len(groups)>1`)
- Tool defaults centralized in `config.py` from `[tool.sofer]` — never hardcoded in functions
- Directory contract: `raw/` source files, `cache/` sofer artifacts, `build/` prepare output (via `[dataset] build_dir`)
- No async, no web framework, no database
- Domain-agnostic: works for any file-based dataset

## Conventions

- Source in `src/sofer/` (flat module, not namespace package)
- One module per concern (CLI dispatch, config model, format registry, per-command domain modules)
- Tests in `tests/` with `test_*.py` naming
- Classes named `Test*` and methods `test_*`
- `tmp_path` fixture used for filesystem tests, `monkeypatch` for env/args
- Typed code with `from __future__ import annotations`
- `__init__.py` is the package docstring + public API; the version resolves at runtime from installed metadata via `_version.py` (no static constant)
- Pre-commit hook order: ruff fix -> ruff format -> mypy -> pyright
- CI matrix tests across Python 3.10–3.14
- Config via TOML files, secrets via .env with HF_TOKEN
- CLI uses argparse with subparsers, func dispatch pattern
- Mandatory docstrings: module-level for every module, params/returns for public functions
- No hardcoded values: defaults in `[tool.sofer]` / per-dataset TOML, read via config
- CLI help text and README updated in the same change as CLI behavior

## Testing

- Strict TDD: disabled — tests MUST match spec scenarios (AGENTS.md rule 6) but red-green-refactor is not enforced (authoritative: mem #441, openspec/config.yaml strict_tdd false)
- Test runner: pytest 9.1.1 — `uv run pytest tests/ -q` is the authoritative local tally; CI runs `uv run pytest -v` across Python 3.10–3.14. Scenario counts are re-derived by `scripts/check_test_mapping.py`, never stored here.
- CI: `uv run pytest -v` matrix Python 3.10–3.14; lint `uv run ruff check src/ tests/ scripts/` (ruff 0.16.8), type `uv run mypy src/ scripts/` (mypy 2.3.1) and `uv run pyright` (pyright 1.1.414), format `uv run ruff format --check src/ tests/`
- Pre-commit: ruff (lint --fix + format) + mypy (uv run mypy src/ scripts/) + pyright (uv run pyright), runs on every commit
- Coverage: `coverage` is a dev dependency — `uv run coverage run -m pytest` then `uv run coverage report -m`; `[tool.coverage.run]` sets `branch = true` / `source = ["src/sofer"]`, and `[tool.coverage.report]` enforces `fail_under = 90` (spec `coverage`)

---
*Generated by sdd-init. Last updated: 2026-09-26 — SDD-context reconciliation (issue #258): the stack table, CI row, subcommand inventory, hook order and tool versions again match `pyproject.toml`, `src/sofer/cli.py` and the pre-commit config, with static guards so the drift cannot return silently.*
