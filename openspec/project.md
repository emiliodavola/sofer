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
├── __init__.py          # Module entry, version
├── cli.py               # argparse CLI, 6 commands: init, validate, prepare, publish, codebook, scan
├── model.py             # DatasetConfig dataclass, TOML loading, config validation
├── config.py            # Tool-wide defaults from [tool.sofer] in pyproject.toml
├── checks.py            # DatasetValidator — data integrity checks
├── scanner.py           # Dataset scanning / CSV inspection
├── codebook.py          # CSV analysis + markdown codebook generation
├── prepare.py           # Local artifact generation (parquet, card, LICENSE, codebooks) — offline
├── publish.py           # Delivery engine: hf target (upload_folder) + local target
├── _mirror.py           # Shared mirror-layout helpers (dir-aware copy, planned remotes)
├── repo_compliance.py   # HF repo compliance checks
├── splits.py            # Split keyword detection
├── verification.py      # load_dataset() verification
├── quality.py           # Data quality checks
├── _sentinels.py        # Shared sentinel module
├── _csv_reader.py       # CSV reading utilities
├── _parquet_helpers.py  # Shared parquet <-> HF dtype conversion
└── _formats.py          # Format registry

tests/
├── test_cli.py              # Parser tests + init command
├── test_checks.py           # Validator: files, size, columns
├── test_codebook.py         # CSV type inference + codebook generation
├── test_model.py            # TOML loading + config validation
├── test_prepare.py          # prepare() offline generation (PRP-01..08)
├── test_publish.py          # publish() delivery: hf/local targets, auto-prepare
├── test_mirror.py           # _mirror helpers (dir-aware copy, planned remotes)
├── test_splits.py           # Split detection + schema assertion suites
├── test_scanner.py          # Scan command behavior
├── test_repo_compliance.py  # HF repo compliance checks
├── test_quality.py          # Data quality checks
├── test_parquet_conversion.py  # Parquet conversion helpers
└── test_sentinels.py        # Sentinel semantics
```

## Architecture

- CLI dispatches to pure-Python commands via argparse subparsers with `func` dispatch pattern
- `DatasetConfig.from_toml()` loads config, returns dataclass
- `DatasetValidator(cfg).run_all()` runs integrity checks, returns ValidationReport
- `prepare()` generates all artifacts locally (parquet, README, LICENSE, codebooks) — zero network
- `publish()` delivers a prepared package: `--target hf` uses `upload_folder`, `--target local` writes to disk
- `publish` auto-runs `prepare` when artifacts are stale (TOML/source mtimes vs newest parquet)
- `codebook.generate()` analyses CSV and returns markdown string
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

- Strict TDD: active (verify-reports in archive document Strict TDD mode with 6/6 TDD compliance)
- Test runner: pytest 9.1.1 — `uv run pytest tests/ -q`
- Current suite: 553 tests passing (2026-08-06: prepare-publish-split — upload removed, prepare/publish added)
- Coverage tooling: not installed (no pytest-cov / coverage dependency)

---
*Generated by sdd-init. Last updated: 2026-08-06.*
