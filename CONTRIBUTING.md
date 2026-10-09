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

> Get your token at: <https://huggingface.co/settings/tokens>

## Development commands

Run these from the repository root:

```bash
uv run pytest
uv run mypy src/ scripts/
uv run pyright                   # second type gate (config-driven; src/ + scripts/)
uv run ruff check src/ tests/ scripts/
uv run coverage run -m pytest   # complete suite under coverage (gate: 90%)
uv run coverage report -m       # totals + per-file missed lines; fails below 90%
```

## Architecture

sofer is a single Python package with one module per concern: CLI dispatch
lives in `cli.py`, dataset configuration in `model.py`, tool-wide defaults in
`config.py`, and each command owns its domain module.

```
src/sofer/
├── __init__.py          # Package docstring + public API
├── _version.py          # Runtime version resolution (installed metadata + dev fallback)
├── _formats.py          # Supported file extension registry
├── _sentinels.py        # Shared sentinel value sets
├── _csv_reader.py       # CSV/TSV streaming reader
├── _mirror.py           # Remote-path validation + dir-aware mirror copies
├── _patterns.py         # Shared regexes (EMAIL_PATTERN)
├── _clean.py            # Build/cache cleanup helpers (publish --clean)
├── _converters.py       # Format-specific Parquet conversion
├── _parquet_helpers.py  # Shared Parquet dtype helpers
├── _toml.py             # TOML parser selection (tomllib/tomli fallback)
├── cli.py               # argparse CLI with 10 subcommands (init, scan, validate, prepare, publish, codebook, profile, render, mcp, report-failure)
├── config.py            # Tool-wide defaults from [tool.sofer] (discovery + reload)
├── model.py             # DatasetConfig + InferenceStatus
├── checks.py            # DatasetValidator — data integrity checks
├── quality.py           # QualityValidator — 9 quality checks (single-pass)
├── codebook.py          # Multi-format codebook generator
├── scanner.py           # File discovery, TOML merge, copy-to-cache
├── prepare.py           # Offline generation: Parquet conversion, card, LICENSE, codebooks
├── publish.py           # Delivery: HF upload_folder / local copy, auto-prepare, dry-run
├── semantic.py          # Semantic type inference detectors (email)
├── pii.py               # Possible-PII detection detectors (email)
├── metadata.py          # metadata.yaml schema + deterministic (de)serialization
├── profile.py           # Read-only profile orchestrator → metadata.yaml
├── render.py            # Render status-annotated README.md from metadata.yaml
├── repo_compliance.py   # Dataset Card & schema compliance
├── splits.py            # Split detection (train/test/validation)
├── verification.py      # load_dataset() end-to-end verification
├── execution_context.py # Shared dataset-identity contract (CLI init + MCP sofer_init)
├── manifest.py          # Package artifact manifest (publishable vs intermediate)
├── workflow.py          # Typed workflow metadata + result envelopes for adapters
├── failure_report.py    # Assisted failure reporting: context, anonymization, gh send, persistence
├── mcp_server.py        # Optional MCP server (stdio) — tools, resources, prompts
└── mcp_registration.py  # MCP agent registration adapters (opencode/codex/gemini/pi/hermes)
```

## Development conventions

### Code style

This project uses **ruff** 0.16.8 for linting and formatting. Configuration lives in `pyproject.toml` under `[tool.ruff]` (`target-version = "py310"`, `line-length = 100`, `extend-exclude = ["openspec"]`). Run `ruff check` and `ruff format` before committing — the pre-commit hook does this automatically.

### Type checking

Two type checkers gate the source — **mypy** (`[tool.mypy]`, `strict = true`) and **pyright**
(`[tool.pyright]`, `typeCheckingMode = "standard"`). Both are wired into the local pre-commit hooks and
into the CI `lint` job, and `pyproject.toml` is the single source of the mode, scope and version each one
runs with:

```bash
uv run mypy src/ scripts/   # the enforced mypy invocation (CI + the `mypy` hook)
uv run pyright              # the enforced pyright invocation (CI + the `pyright` hook)
```

The scope is `src/` and `scripts/`; **`tests/` is excluded from both type gates** by policy (recorded in
`openspec/specs/ci/spec.md` CI-09) — test helpers are still annotated by convention
(`process-boundary` PB-07), but the test tree is never type-checked. Both analyzers are pinned exactly in `[dependency-groups] dev` and resolved through `uv.lock` — a
floating range would let the gate's behaviour move under CI with no diff (the rule CI-08 already enforces
for ruff). pyright must be run through `uv run`: it resolves third-party imports against the project
environment, so running it any other way (bare, `npx`, `uvx`) can report phantom missing imports.

### Dependency updates

Automated dependency updates are driven by `.github/dependabot.yml`. Minor and patch
updates are grouped and opened automatically; **major** updates are deliberately left out
of every group so each arrives as its own PR for explicit review and code adaptation.

Three bumps are intentionally not automated:

- **ruff** — its single version is declared in four homes that must move together: the
  `[dependency-groups] dev` pin and `[tool.ruff] required-version` in `pyproject.toml`, the
  `astral-sh/ruff-pre-commit` `rev` in `.pre-commit-config.yaml`, and the version named in
  this file's Code style section. CI-08 forces them to agree, and Dependabot's `uv`
  ecosystem can move only the first, so the bot ignores `ruff`. To bump it, edit all four
  declarations plus `uv.lock`, then run the CI-08 guard row and the full suite.
- **mypy and pyright** — each analyzer's exact version is declared in three text homes that
  must move together: the `[dependency-groups] dev` pin in `pyproject.toml`, and the version
  named in `openspec/project.md` and `openspec/config.yaml`. The tool-version guard forces
  them to agree, and Dependabot's `uv` ecosystem can move only the first, so the bot ignores
  both (#275). To bump either, edit all three declarations plus `uv.lock`, then run the
  tool-version guard row and the full suite.
- **fastmcp majors** — the MCP SDK API changes across majors, so adoption needs a
  code-adapting change rather than a bot PR. Minor and patch updates stay automatic; the
  declared `<5` cap is a real boundary because majors are ignored.

When a bump still breaks CI, the failure is a guard, not a missing manual edit: the fix is
to move the declaration that drifted. The guards live in `tests/test_ci_workflows.py` —
action-ref consistency across every workflow, the setup-uv release parity derived from
`ci.yml`, the `.python-version` ↔ gate-job interpreter pin, and the Dependabot policy above.

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
- Total coverage is gated at **90%** (`fail_under = 90` in `pyproject.toml`):
  CI and the release workflow fail below the floor, and `uv run coverage report
  -m` lists the missed lines. Raising the floor is a spec change
  (`openspec/specs/ci/spec.md` CI-01), never an ad-hoc workflow tweak.

## Reporting bugs

Use the issue template and include:

- Steps to reproduce
- Expected vs actual behaviour
- `sofer --version` output
- Relevant TOML config (sanitised)

When a CLI command crashes with an uncaught error, sofer offers to file the issue
for you on an interactive terminal: it collects the command, the traceback, and the
environment versions, anonymizes home paths, and shows the full body before sending.
If `gh` is missing, unauthenticated, or offline, the report is persisted under the
sofer state directory (`~/.local/state/sofer/failure-reports/`) and
`sofer report-failure <file>` retries it later. See
[README → Assisted failure reporting](README.md#assisted-failure-reporting). Never
paste dataset rows or secret values into an issue.

## Questions?

Open a [discussion](https://github.com/emiliodavola/sofer/discussions) or reach out in an issue.
