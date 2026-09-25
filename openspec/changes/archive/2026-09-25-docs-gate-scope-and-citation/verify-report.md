# Verify Report: Align documented gate-command scope and sync CITATION.cff on `dev` (#212, #191)

**Change**: `docs-gate-scope-and-citation`
**Branch**: `docs/gate-scope-and-citation`
**Mode**: Standard (Strict TDD disabled)

## Scope Verified

| Issue | Acceptance criterion | Result |
|-------|----------------------|--------|
| #212 | Every tracked gate command in the three docs names the CI scope | PASS |
| #212 | AGENTS rule 12 keeps the mypy-under-3.13 exception | PASS (untouched) |
| #212 | No docs-vs-CI disagreement remains | PASS |
| #191 | Decision (a) recorded in AGENTS rule 12 + branch-flow rule | PASS |
| #191 | `update_citation.py` remains the only writer | PASS |
| #191 | `citation-check` guard job unchanged | PASS (workflows untouched) |

There are no spec-governed scenarios for this change: CI-06's asserted facts (floor, coverage
commands, PR-template coverage item) and CI-07's rule-12 latent-issue note are untouched.

## Runtime Evidence

| Command | Exit | Observed |
|---------|------|----------|
| `uv run python scripts/update_citation.py --check --version 0.3.12` | 0 | `OK: CITATION.cff declares version 0.3.12 with a valid date-released.` |
| `uv run pytest tests/test_ci_workflows.py -q` | 0 | `36 passed` |
| `uv run pytest tests/ -q` | 0 | `1847 passed, 1 skipped` |
| `uv run ruff check src/ tests/ scripts/` | 0 | `All checks passed!` |
| `uv run ruff format --check src/ tests/` | 0 | `70 files already formatted` |
| `uv run mypy src/ scripts/` | 0 | `Success: no issues found in 35 source files` |
| `uv run pyright` | 0 | `0 errors, 1 warning, 0 informations` |

The single pyright warning (`src/sofer/_toml.py:27` — `tomli` could not be resolved from source)
is pre-existing; the source tree is identical to `dev` (docs-only change).

## Static Evidence

- Residual scan of `AGENTS.md`, `CONTRIBUTING.md`, and `.github/PULL_REQUEST_TEMPLATE.md` finds no
  `uv run mypy src/` without `scripts/`, and no `uv run ruff check src/ tests/` without `scripts/`.
  The format gate's `uv run ruff format --check src/ tests/` is correctly unchanged (CI-11 scope).
- `git diff dev -- CITATION.cff` changes only `version:` (`0.2.2` → `0.3.12`) and `date-released:`
  (`2026-08-27` → `2026-09-13`), matching `origin/main`'s CFF for both fields.
- `AGENTS.md` rule 12's latent-issue note is byte-identical to `dev`.

## Independent Verification

A separate read-only verifier confirmed all six claims: the four documented sites name the CI
scope with no residual narrow command; rule 12 is dev-first with steps 3-5 unchanged; the
latent-issue note is byte-identical; the CFF diff is exactly two lines and matches `main`; all
commands pass; and the CI-09/CI-06 doc assertions still hold.

## Limitations

- No spec-governed behavior changes, so there is no scenario-mapped guard for the documented scope;
  the evidence is static inspection plus the existing suite.
- `#212`'s files-to-touch scope is the three docs; residual narrow-scope strings in
  `openspec/specs/process-boundary/spec.md` belong to the broader docs sweep (Ola 2).

## Result

All acceptance criteria verified; full suite and gates green. Ready for archive.
