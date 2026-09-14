# Proposal: chore-ruff-format-drift

**Change**: `2026-09-14-chore-ruff-format-drift` · **Issue**: #177 · **Branch**: `chore/177-ruff-format-drift` (off `dev`)
**Artifact mode**: hybrid — this file is the OpenSpec artifact; Engram mirrors it at `sdd/2026-09-14-chore-ruff-format-drift/proposal`
**Size**: 6 test files, ~41 changed lines, formatting only · **Delivery**: `ask-on-risk` · budget 400 changed lines
**Exploration**: none persisted under `sdd/…/explore`; the parent supplied the measurements inline and they are reused below.

## Intent

`uv run ruff format --check src/ tests/` is red on six test files that no one touched
(`6 files would be reformatted, 61 files already formatted`, exit 1). A contributor following
CONTRIBUTING.md ("run `ruff format` before committing") gets a failure unrelated to their change,
and genuine formatting regressions hide inside that noise. Fix it mechanically: format exactly
those six files, zero logic change. This does **not** close the defect class (see Non-goals).

## Verified state

| Fact | Evidence | Verified in |
|---|---|---|
| Drift = 6 files, 82 `--diff` lines (~41 changed) | `uv run ruff format --diff src/ tests/` | parent (reused) |
| Files: `test_ci_workflows.py`, `test_coverage_contract.py`, `test_mcp_registration.py`, `test_profile.py`, `test_publish.py`, `test_splits.py` | `--check` output; both contract guards read and confirmed present | parent + this phase |
| **No workflow runs `format --check`** — only `ruff check`. Enforcement is the local pre-commit `ruff-format` hook on *staged* files, so drift survives on files nobody edits | grep `format --check` over `.github/workflows/` → 0 matches; `ci.yml` runs only `ruff check src/ tests/ scripts/` | this phase |
| Ambient ruff **0.16.0**; `.pre-commit-config.yaml` pins ruff-pre-commit **v0.16.7** while the dev group declares `ruff>=0.9.0` | `.pre-commit-config.yaml`, `pyproject.toml` `[dependency-groups]` | this phase |
| Branch exists at dev's SHA (`bdcff254…`), zero commits ahead, **but HEAD is on `refs/heads/dev`, not on the chore branch** | loose refs `refs/heads/dev` and `refs/heads/chore/177-ruff-format-drift` identical (`.git/HEAD` → `ref: refs/heads/dev`) | this phase |
| Local gates are green with no flags (`dev` pins `.python-version` = 3.13, PR #193) | parent | parent (reused) |

## Scope

- One commit: `uv run ruff format` over **exactly those six files**. No logic change.
- SDD artifacts for this change. No `src/sofer/` capability is added or modified; the spec phase
  records a verification contract (formatting integrity), not behavior.

## Non-goals

- **No `ruff format --check` gate in CI** — a separate, undecided policy question (new `ci.yml`
  step + `ci` spec scenario). **Follow-up: the defect class is therefore not closed; the drift can
  return the same way.**
- No formatting change to any file outside the six (not `src/sofer/**`, not other tests).
- No logic, assertion, import, or test-behaviour change. A reformat that alters behaviour is a bug
  to report, never to absorb.
- No fix for the stale counts in `AGENTS.md` rule 6 (#162), `openspec/project.md` (#184), or the
  `ruff.toml` reference in CONTRIBUTING.md (#187).
- No touch of `README.md` / `README_ES.md`, `CONTRIBUTING.md`, `openspec/specs/**`,
  `openspec/config.yaml`, `openspec/changes/archive/**`, or the still-active
  `openspec/changes/2026-09-14-chore-python-version-313/` (separate, unfinished SDD change).
- No tag movement; no commit, push, or PR (parent owns delivery).

## Affected areas

| Area | Impact | Description |
|---|---|---|
| `tests/{test_ci_workflows,test_coverage_contract,test_mcp_registration,test_profile,test_publish,test_splits}.py` | Reformatted | ~41 lines, whitespace/token reflow only |
| `openspec/changes/2026-09-14-chore-ruff-format-drift/**` | New | Proposal + spec/design/tasks · `src/sofer/**` and `openspec/specs/**` untouched |

## Verification (formatting-only — no behaviour to unit-test)

V1 `uv run ruff format --check src/ tests/` → exit 0, **0** to reformat · V2 `uv run ruff check src/ tests/` → still `All checks passed!`.
V3 `uv run pytest tests/ -q` → baseline tally recorded **before** the format, then identical, 0 failures.
V4 `uv run mypy src/` → clean (32 files) · V5 `bash scripts/check_core_coverage.sh` → exit 0, four core modules at 100% (covered lines unmoved).
V6 `git diff --stat` → exactly the six test files; `ruff format --diff` after the change shows nothing left to do.

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Reformatting the two static contract guards perturbs asserted content | Low | `ruff format` never rewrites string contents; V3 exercises both files |
| The commit lands on `dev` because HEAD is there, mixing a chore into the default branch | Med | Resolve the ref (`.git/HEAD` or `git branch --show-current`) immediately before committing; commit on `chore/177-ruff-format-drift` only |
| Hook ruff (0.16.7) and ambient ruff (0.16.0) disagree, so drift returns on the next edit | Low, **unverified** | Recorded as a follow-up (align the pin); no shell execution was available in this phase to test it |

## Proposal question round

Assumptions I proceeded on — correct either and I revise; a second round is available on request.
1. Ship the six-file format as hygiene only, accepting that no CI step caught or now prevents the drift,
   rather than folding the `format --check` gate (a policy change) into this change.
2. Leave the ruff version-pin mismatch (`v0.16.7` hook vs ambient `0.16.0`) as a follow-up issue.
