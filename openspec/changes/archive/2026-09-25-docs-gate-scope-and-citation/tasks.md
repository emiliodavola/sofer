# Tasks: Align documented gate-command scope and sync CITATION.cff on `dev` (#212, #191)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~25 authored (AGENTS.md ~8, CONTRIBUTING.md ~2, PR template ~4, CITATION.cff 2); SDD artifacts excluded |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | single PR |
| Delivery strategy | single-pr |
| Chain strategy | size-exception |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Docs name the CI-enforced scope | PR 1 | `uv run pytest tests/test_ci_workflows.py -q` | `uv run python scripts/update_citation.py --check --version 0.3.12` | revert `AGENTS.md`, `CONTRIBUTING.md`, `.github/PULL_REQUEST_TEMPLATE.md`, `CITATION.cff` |

## Phase 1: Documentation scope (#212)

- [x] 1.1 `AGENTS.md` rule 5: change `uv run mypy src/` to `uv run mypy src/ scripts/`.
- [x] 1.2 `CONTRIBUTING.md` Development commands: `uv run mypy src/` →
      `uv run mypy src/ scripts/`.
- [x] 1.3 `CONTRIBUTING.md` Development commands: `uv run ruff check src/ tests/` →
      `uv run ruff check src/ tests/ scripts/`.
- [x] 1.4 `.github/PULL_REQUEST_TEMPLATE.md` Verification block: widen the `ruff check` and `mypy`
      commands to `src/ tests/ scripts/` and `src/ scripts/`.
- [x] 1.5 `.github/PULL_REQUEST_TEMPLATE.md` Checklist: the same two commands.

## Phase 2: Release-process and CFF (#191)

- [x] 2.1 `AGENTS.md` rule 12: move the `CITATION.cff` sync to step 1 (on `dev`), make the merge
      step carry it, and keep steps 3-5 unchanged.
- [x] 2.2 `AGENTS.md` branch-flow bullet: add the sentence that the release-time CFF bump is a
      `dev` commit, so `main` receives CFF content only through a merge.
- [x] 2.3 Run `python scripts/update_citation.py --version 0.3.12 --date 2026-09-13` and review the
      `CITATION.cff` diff (only `version:` and `date-released:` move).

## Phase 3: Verification

- [x] 3.1 `uv run python scripts/update_citation.py --check --version 0.3.12` exits 0.
- [x] 3.2 `uv run pytest tests/ -q` green; `ruff check`, `ruff format --check`, `mypy`, `pyright`.
- [x] 3.3 Confirm no residual narrower gate command remains in the three docs.
- [x] 3.4 Record verify-phase evidence in `verify-report.md`.

## Phase 4: Archive

- [x] 4.1 Move the change folder to `openspec/changes/archive/2026-09-25-docs-gate-scope-and-citation/`
      (mechanical move, `diff -r` readback).
