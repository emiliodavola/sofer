# Tasks: add a push trigger to ci.yml (GitHub #262)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~80 authored (workflow ~5, tests ~24, canonical spec ~28, rows ~2); SDD artifacts excluded |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Delivery strategy | single-pr |
| Chain strategy | size-exception |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Close the direct-push bypass and pin the trigger contract | PR 1 | `uv run pytest tests/test_ci_workflows.py -q` | `uv run python scripts/check_test_mapping.py` | revert `ci.yml`, `tests/test_ci_workflows.py`, canonical `ci` spec |

## Phase 1: Workflow

- [x] 1.1 `ci.yml`: add `push: branches: [main, dev]` alongside the existing `pull_request` trigger (comment explains the CI-16 rationale).

## Phase 2: Guard and spec

- [x] 2.1 `tests/test_ci_workflows.py`: add `test_ci_has_push_and_pr_triggers_targeting_main_and_dev` (CI-16 S1/S2).
- [x] 2.2 Update the module docstring range to CI-01..CI-16 and name the CI-16 guard.
- [x] 2.3 Write the `ci` delta (ADDED CI-16, two scenarios); compose into the canonical spec.
- [x] 2.4 Append the two CI-16 Test Mapping rows.

## Phase 3: Verification

- [x] 3.1 `uv run pytest tests/test_ci_workflows.py -q` green (50 passed).
- [x] 3.2 `uv run pytest tests/ -q` green (1994 passed, 2 skipped).
- [x] 3.3 ruff check / ruff format --check / mypy / pyright clean.
- [x] 3.4 `uv run python scripts/check_test_mapping.py` exit 0.
- [x] 3.5 Record verify-phase evidence in `verify-report.md`.

## Phase 4: Archive

- [x] 4.1 `git mv` the change folder to `openspec/changes/archive/2026-09-26-ci-push-trigger/`.
