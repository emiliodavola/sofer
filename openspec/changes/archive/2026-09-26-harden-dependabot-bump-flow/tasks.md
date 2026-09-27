# Tasks: Harden the release/dependabot bump flow

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~150 authored (tests ~90, dependabot ~15, CONTRIBUTING ~30, AGENTS ~3, canonical spec ~15); SDD artifacts excluded from the review budget |
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
| 1 | Guard + Dependabot + docs hardening | PR 1 | `uv run pytest tests/test_ci_workflows.py -q` | `uv run python scripts/check_test_mapping.py` | revert the five-file diff |

## Phase 1: Guards

- [x] 1.1 Rewrite the setup-uv half of
      `test_release_lint_job_runs_the_ci_lint_gates` to derive the ref from
      `ci.yml`; remove the `astral-sh/setup-uv@v10.2.0` literal.
- [x] 1.2 Add `test_workflow_action_refs_are_consistent_across_workflows` with a
      `_action_refs_by_action()` helper.
- [x] 1.3 Add `test_dev_interpreter_pin_matches_gate_jobs`.
- [x] 1.4 Add `_dependabot_update()` / `_dependabot_updates()` helpers and the
      three Dependabot policy guards (CI-14 S1–S3).
- [x] 1.5 Extend the module docstring requirement range to CI-01..CI-14.

## Phase 2: Dependabot config and docs

- [x] 2.1 Add `ignore: ruff` and `ignore: fastmcp` (major) to the `uv` update in
      `.github/dependabot.yml`, with explanatory comments.
- [x] 2.2 Add the `CONTRIBUTING.md` "Dependency updates" subsection.
- [x] 2.3 Add the `AGENTS.md` rule-8 pointer.

## Phase 3: Spec and verification

- [x] 3.1 Compose CI-13 + CI-14 into `openspec/specs/ci/spec.md`; append the six
      Test Mapping rows; update the Purpose sentence.
- [x] 3.2 Run `uv run pytest tests/test_ci_workflows.py -q`.
- [x] 3.3 Run `uv run pytest tests/ -q` and confirm green.
- [x] 3.4 Run `uv run python scripts/check_test_mapping.py` and confirm exit 0.
- [x] 3.5 Run `uv run ruff check src/ tests/ scripts/`, `uv run ruff format --check src/ tests/`,
      `uv run mypy src/ scripts/`, `uv run pyright`, and the coverage gate.
- [x] 3.6 Record verify-phase evidence in `verify-report.md`.

## Phase 4: Independent verification and archive

- [x] 4.1 Independent subagent read-only verification against the delta spec.
- [x] 4.2 Move the change folder to
      `openspec/changes/archive/2026-09-26-harden-dependabot-bump-flow/` and
      write `archive-report.md`.
