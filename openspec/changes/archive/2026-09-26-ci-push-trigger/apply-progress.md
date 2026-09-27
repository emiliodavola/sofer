# Apply Progress: add a push trigger to ci.yml (GitHub #262)

**Change**: `2026-09-26-ci-push-trigger`
**Mode**: Standard (Strict TDD disabled per `openspec/config.yaml`)

## Completed Tasks

- [x] 1.1 `ci.yml` `push: branches: [main, dev]`
- [x] 2.1 CI-16 guard added
- [x] 2.2 Module docstring range CI-01..CI-16
- [x] 2.3 `ci` delta written and composed
- [x] 2.4 Two CI-16 Test Mapping rows appended
- [x] 3.1–3.5 Gates green (see verify-report.md)
- [x] 4.1 Change folder archived

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `.github/workflows/ci.yml` | Modified | `push` trigger added; jobs unchanged |
| `tests/test_ci_workflows.py` | Modified | `test_ci_has_push_and_pr_triggers_targeting_main_and_dev`; docstring range |
| `openspec/specs/ci/spec.md` | Modified | CI-16 requirement + two Test Mapping rows |

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and result | `uv run pytest tests/test_ci_workflows.py -q` — 50 passed |
| Runtime harness command/scenario and result | `uv run pytest tests/ -q` — 1994 passed, 2 skipped; `uv run python scripts/check_test_mapping.py` — exit 0 |
| Rollback boundary | revert `ci.yml`, `tests/test_ci_workflows.py`, canonical `ci` spec |

## Deviations from Design

Numbering note applied as designed: CI-16 (CI-15 belongs to PR #268).

## Issues Found

None.

## Remaining Tasks

None.

## Status

All tasks complete. Ready for archive.
