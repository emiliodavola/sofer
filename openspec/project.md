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
| Type checker     | mypy (strict=false, check_untyped_defs=true)         |
| Test runner      | pytest 9.1.1                                         |
| Pre-commit       | ruff (lint+fix+format), mypy                         |
| CI               | GitHub Actions (uv sync -> ruff -> mypy -> pytest matrix 3.10-3.14) |

## Project Structure

```
src/sofer/
├── cli.py               # argparse CLI, 8 commands: init, validate, prepare, publish, codebook, scan, profile, render (+ MCP)
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
├── _mirror.py / _formats.py / _csv_reader.py / _parquet_helpers.py / _converters.py / _patterns.py / _sentinels.py / _version.py
├── repo_compliance.py / splits.py / verification.py / quality.py
└── __init__.py

tests/  (24 files, 1163 passed, 2 skipped)
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
- Directory contract: `data/` source files, `cache/` sofer artifacts, `build/` prepare output (via `[dataset] build_dir`)
- No async, no web framework, no database
- Domain-agnostic: works for any file-based dataset

## Conventions

- Source in `src/sofer/` (flat module, not namespace package)
- One module per concern (CLI dispatch, config model, format registry, per-command domain modules)
- Tests in `tests/` with `test_*.py` naming
- Classes named `Test*` and methods `test_*`
- `tmp_path` fixture used for filesystem tests, `monkeypatch` for env/args
- Typed code with `from __future__ import annotations`
- `__init__.py` exports version constant
- Pre-commit hook order: ruff fix -> ruff format -> mypy
- CI matrix tests across Python 3.10–3.14
- Config via TOML files, secrets via .env with HF_TOKEN
- CLI uses argparse with subparsers, func dispatch pattern
- Mandatory docstrings: module-level for every module, params/returns for public functions
- No hardcoded values: defaults in `[tool.sofer]` / per-dataset TOML, read via config
- CLI help text and README updated in the same change as CLI behavior

## Testing

- Strict TDD: disabled — tests MUST match spec scenarios (AGENTS.md rule 6) but red-green-refactor is not enforced (authoritative: mem #441, openspec/config.yaml strict_tdd false)
- Test runner: pytest 9.1.1 — `uv run pytest tests/ -q` (1163 passed, 2 skipped on 2026-08-31; 334+ spec scenarios across 16 specs, CB-R09/RC-R21/TC-12/PRP-10 + MSP-R02/R12/PKG-03/PKG-06 added; mcp auto-install: fastmcp in dependencies with alias)
- CI: `uv run pytest -v` matrix Python 3.10–3.14; lint `uv run ruff check src/ tests/` (ruff 0.16.0), type `uv run mypy src/` (mypy 2.3.0), format `uv run ruff format`
- Pre-commit: ruff (lint --fix + format) + mypy (uv run mypy src/ scripts/), runs on every commit
- Coverage tooling: not installed (no pytest-cov / coverage dependency)

---
*Generated by sdd-init. Last updated: 2026-08-31 — feat-mcp-auto-install archived (MSP-R02/R12 mcp auto-install, PKG-03 both entry points, PKG-06 fastmcp in dependencies; 1163 passed).*
