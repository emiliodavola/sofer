# Tasks: Release gate integrity (CI-03/CI-10 contradiction + #233 lint parity)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~70 authored (workflow ~12, tests ~55, canonical spec ~10); SDD artifacts excluded from the review budget |
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
| 1 | Correct the release workflow + spec parity and pin it | PR 1 | `uv run pytest tests/test_ci_workflows.py -q` | `uv run python scripts/check_test_mapping.py` | revert `release.yml`, `tests/test_ci_workflows.py`, `openspec/specs/ci/spec.md` |

## Phase 1: Workflow and spec truth

- [x] 1.1 In `.github/workflows/release.yml`, correct the header comment: state the `lint`-job
      parity with `ci.yml` and the shipped COV-06 gate (CI-03); remove the stale "tracked
      separately as issue #185" claim.
- [x] 1.2 In `.github/workflows/release.yml`'s `lint` job, add the format step
      (`uv run ruff format --check src/ tests/`) after `Lint with ruff`.
- [x] 1.3 Add the bare pyright step (`uv run pyright`) after `Type check with mypy`.
- [x] 1.4 Add the test-mapping step (`uv run python scripts/check_test_mapping.py`) after pyright.
- [x] 1.5 In `openspec/specs/ci/spec.md`, amend CI-10 (drop the #185 claim + scenario) and append
      CI-12, using `gentle-ai sdd-archive-compose`; remove the stale CI-10 Test Mapping row and
      append the three CI-12 rows.

## Phase 2: Guards

- [x] 2.1 Update `tests/test_ci_workflows.py::test_release_test_job_mirrors_ci_os_axis_and_cli_smoke`
      to drop the `"185" in header` assertion and its docstring sentence.
- [x] 2.2 Add `test_release_lint_job_runs_the_ci_lint_gates` (CI-12 S1).
- [x] 2.3 Add `test_release_lint_job_mirrors_ci_lint_invocations` (CI-12 S2).
- [x] 2.4 Add `test_release_header_states_lint_parity_without_the_stale_cov06_claim` (CI-12 S3).
- [x] 2.5 Update the module docstring requirement range to CI-01..CI-12.

## Phase 3: Verification

- [x] 3.1 Run `uv run pytest tests/ -q` and confirm green.
- [x] 3.2 Run `uv run python scripts/check_test_mapping.py` and confirm exit 0.
- [x] 3.3 Run `uv run ruff check src/ tests/ scripts/`, `uv run ruff format --check src/ tests/`,
      `uv run mypy src/ scripts/`, `uv run pyright`.
- [x] 3.4 Record verify-phase runtime evidence (gate exit codes) in `verify-report.md`.

## Phase 4: Archive

- [x] 4.1 Move the change folder to `openspec/changes/archive/2026-09-25-fix-release-gate-integrity/`
      (mechanical `git mv`) and confirm the canonical spec composition.
