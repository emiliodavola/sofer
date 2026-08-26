# Agent Instructions — sofer

## Code Quality Standards

### 1. No hardcoded values
- **Never** inline magic numbers or default strings in function bodies.
- Tool-wide defaults belong in `pyproject.toml` under `[tool.sofer]`, loaded via `src/sofer/config.py`.
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
- 795 tests currently pass — never reduce coverage.

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

### 11. PR template
- All pull requests must use the template in `.github/PULL_REQUEST_TEMPLATE.md`.
- Fill every section — don't leave placeholders or `<!-- comments -->`.
- Verification section must contain **actual command output**, not placeholders.
- SDD artifacts section is mandatory when the change followed the SDD workflow; for ad-hoc fixes it can be omitted but the change description must still be thorough.

### 12. Release process
Releases are **tag-driven and automated** by `.github/workflows/release.yml`: pushing a `v*` tag runs lint + the full test matrix + a wheel-build validation job, then creates a GitHub Release with auto-generated notes. There is no PyPI publishing.

Cutting a release:
1. Sync `main` with `dev`: `git checkout main && git merge --no-ff dev`. Note: `main` is **not** a fast-forward of `dev` (release PR merge commits live on `main`), so always use `--no-ff`.
2. Do **not** bump a version anywhere: the version is derived from the tag at build time (hatch-vcs, `[tool.hatch.version] source = "vcs"`). The tag is the single source of truth — `pyproject.toml` has no static `version` field and there is no `__version__` constant.
3. Create an annotated tag on the merge commit (`git tag -a vX.Y.Z -m "sofer vX.Y.Z"`) and push with `git push origin main --follow-tags`.
4. Verify: `gh run list --workflow=release.yml` must go green (including the wheel-build job asserting the wheel METADATA version equals the tag); the release appears under GitHub Releases with notes generated from commits/PRs since the previous tag.

Rules:
- Versioning is semver; pre-1.0 minor bumps (0.x) may carry breaking changes — document them in the release notes (e.g. v0.2.0 removed the `upload` subcommand). The shipped version always equals the tag: `vX.Y.Z` installs as `sofer vX.Y.Z` via `--version`, resolved at runtime from installed metadata (never a static constant).
- **Never move or delete a pushed tag** unless the release job never ran (e.g. quality gates failed before publishing); in that case fix on `dev`, merge to `main`, delete the tag locally and remotely, and re-tag.
- The workflow's lint job intentionally runs mypy only under Python 3.13, mirroring CI. Do not add mypy to the version matrix: under 3.10 the `import tomli as tomllib` fallback triggers `no-redef` errors (known latent issue in `model.py`, `config.py`, `cli.py`).
- Branch flow: all work lands on `dev` first; `main` receives changes only via merges from `dev` (typically at release time).
