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
├── _yaml.py             # YAML parsing + surgical single-entry editing (MCP configs)
├── cli.py               # argparse CLI with 11 subcommands (init, scan, validate, prepare, publish, codebook, profile, render, mcp, meta, report-failure)
├── config.py            # Tool-wide defaults from [tool.sofer] (discovery + reload)
├── model.py             # DatasetConfig + InferenceStatus
├── checks.py            # DatasetValidator — data integrity checks
├── quality.py           # QualityValidator — 9 quality checks (single-pass)
├── codebook.py          # Multi-format codebook generator
├── scanner.py           # File discovery, TOML merge, copy-to-cache
├── file_edit.py         # Surgical [[file]] editor for the dataset TOML
├── meta_edit.py         # Surgical [meta] editor for the dataset TOML
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
├── mcp_doctor.py        # Real sofer-mcp cold-start measurement vs the written deadline
└── mcp_registration.py  # MCP agent registration adapters (opencode/codex/gemini/pi/hermes)
```

The module set is whatever `ls src/sofer/` reports — the tree above is a reading aid, not an
exhaustive contract. **Windows safety:** placeholders use `raw/example.csv` (NTFS-valid; `:` is
reserved — the old `TODO: raw/...` was invalid); MCP `sofer_init(cwd=...)` resolves per call through
`_contained_path` + `is_relative_to` as `effective_root` under the server root, never mutating a
global root; TOML paths use forward slashes (`raw/`, `cache/`).

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

## Releases

Releases are **tag-driven and automated** by `.github/workflows/release.yml`: pushing a `v*` tag
runs lint + the full test matrix + a wheel-build validation job, then creates a GitHub Release with
auto-generated notes. There is no PyPI publishing. A `citation-check` guard job fails the workflow
when `CITATION.cff` does not declare the tagged version, so the CFF must be synced before tagging.

### Cutting a release

Track each release with the **Release** issue template (`.github/ISSUE_TEMPLATE/release.md`); it
mirrors this runbook as a checklist. The steps below are the authority.

1. Select `X.Y.Z` and create a short-lived release-preparation branch from updated `main`. Run
   `uv run --python 3.13 python scripts/update_citation.py --version X.Y.Z`, review the
   `CITATION.cff` diff, and open a preparation PR against `main`.
2. Merge that PR only after the applicable checks and review. Record the intended final `main`
   commit as `RELEASE_SHA` — after a squash or rebase merge that is the merged commit, not the
   preparation branch's pre-merge commit. If more changes entered `main` in the meantime, decide
   explicitly whether they belong in the release; never silently tag the newer tip.
3. Do **not** bump a version anywhere else: the version is derived from the tag at build time
   (hatch-vcs, `[tool.hatch.version] source = "vcs"`). The tag is the single source of truth —
   `pyproject.toml` has no static `version` field and there is no `__version__` constant.
4. Run the preflight on that exact commit. It is read-only and fails closed: it verifies reachability
   from `origin/main`, checks the `CITATION.cff` **at that commit** through the same
   `update_citation.py --check` gate `release.yml` runs, and confirms `vX.Y.Z` exists neither locally
   nor remotely. It prints no tag command unless every check passes.

   ```bash
   git fetch origin --prune --tags
   uv run --python 3.13 python scripts/release_preflight.py --version X.Y.Z --sha <RELEASE_SHA>
   ```

   Stop on any refusal, including an unreachable remote — it refuses rather than assuming the tag is
   free. The preflight never creates or pushes the tag.
5. With explicit release authorization, set `RELEASE_VERSION` (the approved version without the
   leading `v`) and `RELEASE_SHA` (the full approved commit OID), confirm both values match the
   approved release, then create and push the annotated tag. `--no-follow-tags` is required so only
   that tag is sent, even with `push.followTags=true`:

   ```bash
   : "${RELEASE_VERSION:?Set RELEASE_VERSION to the approved version without v}"
   : "${RELEASE_SHA:?Set RELEASE_SHA to the full approved commit OID}"
   git tag -a "v${RELEASE_VERSION}" "${RELEASE_SHA}" -m "sofer v${RELEASE_VERSION}"
   git push --no-follow-tags origin "refs/tags/v${RELEASE_VERSION}:refs/tags/v${RELEASE_VERSION}"
   ```

   The preparation PR already updated remote `main`, so no branch push is needed. Run the push only
   if tag creation succeeded, and never add `--tags`, `--follow-tags`, `--all`, or `--mirror`.
6. Verify: track the `release.yml` run for that exact tag/SHA, not an arbitrary latest run. Lint,
   the full Python/OS test matrix, the coverage and core-coverage gates, wheel validation, and the
   citation check must all pass before the GitHub Release appears with notes generated from
   commits/PRs since the previous tag.

### Release rules

- Versioning is semver; pre-1.0 minor bumps (0.x) may carry breaking changes — document them in the
  release notes (e.g. v0.2.0 removed the `upload` subcommand). The shipped version always equals the
  tag: `vX.Y.Z` installs as `sofer vX.Y.Z` via `--version`, resolved at runtime from installed
  metadata (never a static constant).
- **Never move or delete a pushed tag** unless the release job never ran (e.g. quality gates failed
  before publishing); in that case repair the preparation through another PR to `main`, delete the
  tag locally and remotely, and re-tag. A published release's tag is never retagged.
- **Type-gate nuance (Python 3.13).** The workflow's lint job intentionally runs mypy only under
  Python 3.13, mirroring CI. Do not add mypy to the version matrix: a `3.10` development environment
  installs the conditional `tomli` backport (`pyproject.toml:27`), which makes the
  `import tomli as _tomli` arm of the five `try:` / `except ImportError:` fallbacks live and the
  `import tomllib as _tomli` arm dead, so the second import of the same name triggers `no-redef`
  errors (known latent issue in `cli.py`, `config.py`, `mcp_registration.py`, `mcp_server.py`,
  `model.py`) — and it leaves the COV-06 per-file gates unsatisfiable by construction, because the
  dead arm cannot be executed by any test while `# pragma: no cover` is forbidden in those modules
  (AGENTS.md rule 14). The dev-environment pin (`.python-version`) is therefore `3.13`; a
  contributor whose interpreter is older must pass `--python 3.13` explicitly for those two gates
  (`uv run --python 3.13 mypy src/ scripts/`, `uv run --python 3.13 coverage run -m pytest`). A
  pyright gate (`uv run pyright`, `[tool.pyright]`) now covers the same `src/` and `scripts/` scope;
  the four `try:` / `except ImportError:` `tomli` sites named here are resolved for that gate by the
  committed `typings/tomli-stubs/` stub (`mcp_server.py` is version-gated instead, so a static
  checker prunes its `tomli` arm; mypy already resolves the remaining sites through the global
  `ignore_missing_imports = true`), never by adding `tomli` to the dev group — which is exactly the
  move this note forbids.
- Branch flow: `main` is the single long-lived branch and the default. All work lands through a
  short-lived branch and a reviewed pull request targeting `main`; merging publishes nothing. The
  release boundary is a version tag on an approved `main` commit, so `main` may carry unreleased
  work. (Issue #362's `dev` retirement was a one-time bootstrap exception; it grants no standing
  permission to bypass review and no license to reintroduce an integration branch.)

## Pull requests

- Start a short-lived branch from updated `main`:
  `git fetch origin --prune && git switch main && git pull --ff-only`, then
  `git switch -c <type>/<short-description>`.
- Open a PR against `main`.
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
