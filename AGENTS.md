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
- Never reduce coverage. The authoritative tally is what `uv run pytest tests/ -q` reports on your branch —
  re-derive it, never trust a figure here. Observed on this branch: 1766 passed, 6 skipped (1772 collected).

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
- CLI dispatch: `cli.py` (9 subcommands: init, scan, validate, prepare, publish, codebook, profile, render, mcp)
- Dataset config model: `model.py`
- Tool config defaults: `config.py` (discovery + reload, profile_dir/render_dir)
- Format registry: `_formats.py`
- Each command gets its own domain module: `scanner.py`, `codebook.py`, `prepare.py`, `publish.py`, `profile.py`, `render.py`, `mcp_registration.py`, `mcp_server.py`
- Shared utilities: `_sentinels.py`, `_csv_reader.py`, `_parquet_helpers.py`, `_clean.py`, `_converters.py`, `_mirror.py`
- Windows safety: placeholders use `raw/example.csv` (NTFS-valid, `:` reserved — old `TODO: raw/...` was invalid); MCP `sofer_init(cwd=...)` resolves per-call via `_contained_path` + `is_relative_to` as `effective_root` under server root, never mutating global `_SERVER_ROOT`; TOML paths use forward slashes (`raw/`, `cache/`).

### 11. PR template
- All pull requests must use the template in `.github/PULL_REQUEST_TEMPLATE.md`.
- Fill every section — don't leave placeholders or `<!-- comments -->`.
- Verification section must contain **actual command output**, not placeholders.
- SDD artifacts section is mandatory when the change followed the SDD workflow; for ad-hoc fixes it can be omitted but the change description must still be thorough.

### 12. Release process
Releases are **tag-driven and automated** by `.github/workflows/release.yml`: pushing a `v*` tag runs lint + the full test matrix + a wheel-build validation job, then creates a GitHub Release with auto-generated notes. There is no PyPI publishing. A `citation-check` guard job fails the workflow when `CITATION.cff` does not declare the tagged version, so the CFF must be synced before tagging.

Cutting a release:
1. Sync `main` with `dev`: `git checkout main && git merge --no-ff dev`. Note: `main` is **not** a fast-forward of `dev` (release PR merge commits live on `main`), so always use `--no-ff`.
2. Sync `CITATION.cff` with the release version: run `python scripts/update_citation.py --version X.Y.Z`, review the `CITATION.cff` diff, and commit it BEFORE creating the tag.
3. Do **not** bump a version anywhere else: the version is derived from the tag at build time (hatch-vcs, `[tool.hatch.version] source = "vcs"`). The tag is the single source of truth — `pyproject.toml` has no static `version` field and there is no `__version__` constant.
4. Create an annotated tag on the merge commit (`git tag -a vX.Y.Z -m "sofer vX.Y.Z"`) and push with `git push origin main --follow-tags`.
5. Verify: `gh run list --workflow=release.yml` must go green (including the wheel-build job asserting the wheel METADATA version equals the tag); the release appears under GitHub Releases with notes generated from commits/PRs since the previous tag.

Rules:
- Versioning is semver; pre-1.0 minor bumps (0.x) may carry breaking changes — document them in the release notes (e.g. v0.2.0 removed the `upload` subcommand). The shipped version always equals the tag: `vX.Y.Z` installs as `sofer vX.Y.Z` via `--version`, resolved at runtime from installed metadata (never a static constant).
- **Never move or delete a pushed tag** unless the release job never ran (e.g. quality gates failed before publishing); in that case fix on `dev`, merge to `main`, delete the tag locally and remotely, and re-tag.
- The workflow's lint job intentionally runs mypy only under Python 3.13, mirroring CI. Do not add mypy to the version matrix: a `3.10` development environment installs the conditional `tomli` backport (`pyproject.toml:27`), which makes the `import tomli as _tomli` arm of the five `try:` / `except ImportError:` fallbacks live and the `import tomllib as _tomli` arm dead, so the second import of the same name triggers `no-redef` errors (known latent issue in `cli.py`, `config.py`, `mcp_registration.py`, `mcp_server.py`, `model.py`) — and it leaves the COV-06 per-file gates unsatisfiable by construction, because the dead arm cannot be executed by any test while `# pragma: no cover` is forbidden in those modules (rule 14). The dev-environment pin (`.python-version`) is therefore `3.13`; a contributor whose interpreter is older must pass `--python 3.13` explicitly for those two gates (`uv run --python 3.13 mypy src/ scripts/`, `uv run --python 3.13 coverage run -m pytest`).
- Branch flow: all work lands on `dev` first; `main` receives changes only via merges from `dev` (typically at release time).

### 13. README / README_ES sync
- `README_ES.md` mirrors the user-facing headings and section order of `README.md`.
  Any change to a translated README section MUST update the matching `README_ES.md`
  section in the same commit; section additions/removals MUST land in both files.
- Technical content (commands, flags, TOML/YAML excerpts, CLI output, filenames,
  URLs) stays in English in both files; only prose is translated.

### 14. CLI-core coverage: 100% mandate, zero pragmas
- `src/sofer/cli.py`, `src/sofer/scanner.py`, `src/sofer/prepare.py`, and
  `src/sofer/publish.py` MUST each measure **100.00% line coverage** under
  `uv run coverage report -m` (the `[tool.coverage.run]` configuration:
  `branch = true`, `source = ["src/sofer"]`), over the complete suite
  (`coverage run -m pytest`). The per-file scoped gates
  (`coverage report --include=src/sofer/<file>.py --fail-under=100 -m`, listed in
  `scripts/check_core_coverage.sh` and run by the CI coverage job) are the
  enforcement; a drop below 100.00% in any of the four files fails CI.
- `# pragma: no cover` is **FORBIDDEN** in those four modules — no exception,
  including "genuinely untestable" lines. Every line must actually execute in
  tests; a line that cannot be reached from a test is a defect in the test
  strategy or a design-doc escalation, never a pragma.
- The TOTAL gate stays config-owned (`[tool.coverage.report] fail_under = 90`,
  spec `ci` CI-01) and is never weakened, bypassed, or re-declared by the
  per-file mandate. The per-file 100% gates are additive and scoped per file;
  they hardcode 100 only because 100 is a fixed policy constant, not a tunable
  floor.
- This rule justifies NO `src/sofer/` edit: the dead `if __name__ == "__main__":
  main()` guard in `cli.py` is kept and exercised in-process
  (`runpy.run_module("sofer.cli", run_name="__main__")` with argv at a harmless
  subcommand) as part of the 100.00% row — `python -m sofer.cli` remains a
  working entry point (`tests/conftest.py::run_cli` drives it as the PB-02
  subprocess boundary).
- This rule's 100% mandate covers exactly those four modules. Other modules are
  governed by their own per-file floors (spec `coverage` COV-01) or have no
  floor.
- Adjacent policy pointer (not part of this rule's mandate): the three second-tier per-file floors (`profile.py`, `mcp_registration.py`, `verification.py`) are deliberately **not** CI-gated — they stay verify-phase evidence only, and arming a gate for them is a spec change (see spec `coverage` COV-07).
