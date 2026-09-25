# Apply Progress: Release gate integrity (CI-03/CI-10 contradiction + #233 lint parity)

**Change**: `fix-release-gate-integrity`
**Mode**: Standard (Strict TDD disabled per `openspec/config.yaml`)

## Completed Tasks

- [x] 1.1 Correct the `release.yml` header comment (lint parity stated; stale #185 claim removed)
- [x] 1.2 Add the format step to the release `lint` job
- [x] 1.3 Add the bare pyright step
- [x] 1.4 Add the test-mapping checker step
- [x] 1.5 Amend CI-10 and add CI-12 via `gentle-ai sdd-archive-compose`; fix the Test Mapping table
- [x] 2.1 Drop the `"185"` header assertion from the CI-10 guard
- [x] 2.2 Add `test_release_lint_job_runs_the_ci_lint_gates`
- [x] 2.3 Add `test_release_lint_job_mirrors_ci_lint_invocations`
- [x] 2.4 Add `test_release_header_states_lint_parity_without_the_stale_cov06_claim`
- [x] 2.5 Update the module docstring requirement range to CI-01..CI-12
- [x] 3.1 `uv run pytest tests/ -q` green
- [x] 3.2 `uv run python scripts/check_test_mapping.py` exit 0
- [x] 3.3 ruff check / ruff format --check / mypy / pyright clean
- [x] 3.4 Verify-phase evidence recorded in `verify-report.md`
- [x] 4.1 Archive the change folder and confirm the canonical composition

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `.github/workflows/release.yml` | Modified | Header corrected; `lint` job gains format, pyright, and test-mapping steps (mirroring `ci.yml`) |
| `tests/test_ci_workflows.py` | Modified | CI-10 guard drops the `#185` assertion; three CI-12 guards added; `_CI_LINT_GATE_RUNS` contract + `_lint_gate_runs` helper; docstring range |
| `openspec/specs/ci/spec.md` | Modified | CI-10 amended (stale statements + S3 removed); CI-12 added with 3 scenarios; Test Mapping row removed/rows appended |

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and result | `uv run pytest tests/test_ci_workflows.py -q` — 39 passed |
| Runtime harness command/scenario and result | `uv run python scripts/check_test_mapping.py` — exit 0, `OK: test-mapping contract holds`; full `uv run pytest tests/ -q` — 1849 passed, 2 skipped |
| Rollback boundary | revert `release.yml`, `tests/test_ci_workflows.py`, `openspec/specs/ci/spec.md`; no other file depends on the change |

## Deviations from Design

None — implementation matches design. Note: the archive was composed with
`gentle-ai sdd-archive-compose` for the requirement blocks and a direct edit of the
`## Test Mapping` table, exactly as the design's third decision records, because the compose
tool merges requirements only.

## Issues Found

None.

## Remaining Tasks

None.

## Workload / PR Boundary

- Mode: single PR
- Current work unit: release gate integrity
- Boundary: `release.yml` + `ci` spec + `tests/test_ci_workflows.py`
- Estimated review budget impact: ~70 authored lines (Low)

## Status

14/14 tasks complete. Ready for archive.
