# Agent Instructions — sofer

## Code Quality Standards

### 1. No hardcoded values
- **Never** inline magic numbers or default strings in function bodies.
- Tool-wide defaults belong in `pyproject.toml` under `[tool.data-uploader]`, loaded via `src/data_uploader/config.py`.
- Dataset-level config belongs in the per-dataset TOML file, loaded via `DatasetConfig`.
- Before writing a numeric literal or default string, ask: "Should this be configurable?"

Examples of what to extract:
- Default delimiters, encodings, sample sizes
- Report truncation limits (`[:10]`, `[:5]`)
- Thresholds for type inference, quality checks
- Output directory names, default filenames
- Parquet settings (compression, row group size)

### 2. Documentation mandatory
- Every **module** must have a module-level docstring explaining its purpose.
- Every **public function/class** must have a docstring with parameters and return values.
- Every **CLI handler** (`_cmd_*`) must document the orchestration flow it performs.
- Complex private methods (especially in `quality.py`) need docstrings explaining the algorithm.
- Docstrings are for humans AND LLMs — be precise about contracts and edge cases.

### 3. Read from config, don't bypass it
The most critical bug pattern we've seen: code that uses a hardcoded default instead of reading from the user's TOML config.
- `checks.py` and `repo_compliance.py` must use `cfg.csv_delimiter` and `cfg.csv_encoding`, not hardcoded `";"` and `"utf-8-sig"`.
- Any function that accepts a file path should get its encoding/delimiter from config, not from a default parameter.
- Pattern: pass `cfg` or config values explicitly — don't rely on `config.py` defaults when a user-provided TOML value exists.

### 4. No duplicated logic
- If you find yourself copy-pasting a function (even with a different name), extract it to a shared module.
- Example: `_parquet_to_hf_dtype` was duplicated in `repo_compliance.py` and `uploader.py` — now in `_parquet_helpers.py`.
- Example: quality check names were hardcoded in 4 places — now in `quality.QUALITY_CHECK_NAMES`.

### 5. Pre-commit hooks run automatically
- `ruff` (lint + fix + format) and `mypy` run on every commit.
- Never commit with `--no-verify` unless you have a documented reason.
- Before pushing, run `uv run mypy src/` — the CI will reject type errors.

### 6. Tests must match specs
- Every SDD spec scenario must have a corresponding test.
- When implementing, run `uv run pytest tests/ -q` after every change batch.
- 422 tests currently pass — never reduce coverage.

### 7. CLI help text accuracy
- When adding a new flag or changing behavior, update the argparse `help=` and `description=` strings.
- The README must reflect the current CLI interface — update it in the same commit.

### 8. Naming conventions
- Private helpers: `_lowercase_with_underscores`
- Public API: `lowercase_with_underscores`
- Constants: `UPPERCASE_WITH_UNDERSCORES`
- Type annotations: always use `from __future__ import annotations`
- Use `TYPE_CHECKING` for imports that are only needed for type hints.

### 9. Dependency discipline
- Check if a dependency is already transitive before adding it (pyarrow comes via huggingface-hub).
- New dependencies go in `pyproject.toml` `dependencies`, not `dev-dependencies`, unless they're test-only.
- Prefer format-native readers over heavy dependencies (openpyxl over pandas for Excel).

### 10. Architecture: one module per concern
- CLI dispatch: `cli.py`
- Config model: `model.py`
- Tool config defaults: `config.py`
- Format registry: `_formats.py`
- Each command gets its own domain module: `scanner.py`, `codebook.py`, `uploader.py`
- Shared utilities: `_sentinels.py`, `_csv_reader.py`, `_parquet_helpers.py`
