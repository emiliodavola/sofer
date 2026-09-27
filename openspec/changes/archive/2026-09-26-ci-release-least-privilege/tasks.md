# Tasks: scope release.yml write access to the release job (GitHub #261)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~110 authored (workflow ~10, tests ~45, canonical spec ~12, rows ~2); SDD artifacts excluded |
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
| 1 | Scope write access + pin it | PR 1 | `uv run pytest tests/test_ci_workflows.py -q` | `uv run python scripts/check_test_mapping.py` | revert `release.yml`, `tests/test_ci_workflows.py`, canonical `ci` spec |

## Phase 1: Workflow

- [x] 1.1 `release.yml`: workflow-level `permissions: contents: read` (comment explains the least-privilege scoping).
- [x] 1.2 `release.yml`: `release` job declares `permissions: contents: write`.

## Phase 2: Guard and spec

- [x] 2.1 `tests/test_ci_workflows.py`: add `test_release_workflow_permissions_are_least_privilege` (CI-15 S1/S2).
- [x] 2.2 Update the module docstring range to CI-01..CI-15 and name the CI-15 guard.
- [x] 2.3 Write the `ci` delta (ADDED CI-15, two scenarios); compose into the canonical spec.
- [x] 2.4 Append the two CI-15 Test Mapping rows.

## Phase 3: Verification

- [x] 3.1 `uv run pytest tests/test_ci_workflows.py -q` green (50 passed).
- [x] 3.2 `uv run pytest tests/ -q` green (1994 passed, 2 skipped).
- [x] 3.3 ruff check / ruff format --check / mypy / pyright clean.
- [x] 3.4 `uv run python scripts/check_test_mapping.py` exit 0.
- [x] 3.5 Record verify-phase evidence in `verify-report.md`.

## Phase 4: Archive

- [x] 4.1 `git mv` the change folder to `openspec/changes/archive/2026-09-26-ci-release-least-privilege/`.
