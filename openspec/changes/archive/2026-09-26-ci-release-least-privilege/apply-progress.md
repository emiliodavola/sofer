# Apply Progress: scope release.yml write access to the release job (GitHub #261)

**Change**: `2026-09-26-ci-release-least-privilege`
**Mode**: Standard (Strict TDD disabled per `openspec/config.yaml`)

## Completed Tasks

- [x] 1.1 `release.yml` workflow-level `permissions: contents: read`
- [x] 1.2 `release.yml` `release` job declares `permissions: contents: write`
- [x] 2.1 CI-15 guard added
- [x] 2.2 Module docstring range CI-01..CI-15
- [x] 2.3 `ci` delta written and composed
- [x] 2.4 Two CI-15 Test Mapping rows appended
- [x] 3.1–3.5 Gates green (see verify-report.md)
- [x] 4.1 Change folder archived

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `.github/workflows/release.yml` | Modified | Workflow-level read-only; `release` job `contents: write` |
| `tests/test_ci_workflows.py` | Modified | `test_release_workflow_permissions_are_least_privilege`; docstring range |
| `openspec/specs/ci/spec.md` | Modified | CI-15 requirement + two Test Mapping rows |

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and result | `uv run pytest tests/test_ci_workflows.py -q` — 50 passed |
| Runtime harness command/scenario and result | `uv run pytest tests/ -q` — 1994 passed, 2 skipped; `uv run python scripts/check_test_mapping.py` — exit 0 |
| Rollback boundary | revert `release.yml`, `tests/test_ci_workflows.py`, canonical `ci` spec |

## Deviations from Design

None.

## Issues Found

- The local gitignored `.coverage` was left over from the previous branch; the
  contract guard read it against this branch's source and failed. Removed the
  stale artifact (the guard skips on a clean checkout, and CI re-measures); the
  full suite then ran green.

## Remaining Tasks

None.

## Status

All tasks complete. Ready for archive.
