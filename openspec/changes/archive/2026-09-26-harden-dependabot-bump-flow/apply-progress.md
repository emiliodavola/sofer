# Apply Progress: Harden the release/dependabot bump flow

## Status: complete (pending independent verification)

## What changed

| File | Change |
|------|--------|
| `tests/test_ci_workflows.py` | Docstring range CI-01..CI-14; `_SETUP_UV_REPO`/`_GATE_JOBS`/`_DEPENDABOT_CONFIG`/`_SEMVER_MAJOR`/`_GROUP_UPDATE_TYPES` constants; `_action_and_ref`, `_step_action_ref`, `_action_refs_by_action`, `_gate_job_interpreter_pins`, `_dependabot_updates`, `_dependabot_update` helpers; rewritten `test_release_lint_job_runs_the_ci_lint_gates` (derived setup-uv ref); new `test_workflow_action_refs_are_consistent_across_workflows`, `test_dev_interpreter_pin_matches_gate_jobs`, `test_dependabot_ignores_the_coordinated_ruff_pin`, `test_dependabot_ignores_fastmcp_majors`, `test_dependabot_groups_exclude_majors` |
| `.github/dependabot.yml` | Bump-policy comment; `uv.ignore` for `ruff` (all) and `fastmcp` (major) |
| `CONTRIBUTING.md` | New "Dependency updates" subsection under Development conventions |
| `AGENTS.md` | Rule 9 (Dependency discipline) bullet pointing at the procedure |
| `openspec/specs/ci/spec.md` | Purpose sentence extended; CI-13 + CI-14 requirements, six scenarios, six Test Mapping rows |

## Deviations from tasks

- The literal free-scope guard (`test_ci_workflows.py`) was authored directly; all
  other SDD artifacts were authored as planned.
- No `src/sofer/` change, no workflow file change, and no `uv.lock` change: the
  hardening is entirely in test guards, the Dependabot config, docs, and the spec.

## Verification (recorded in detail in `verify-report.md`)

- `uv run pytest tests/test_ci_workflows.py -q` → 45 passed.
- `uv run pytest tests/ -q` → 1987 passed, 2 skipped (one transient
  `TestStdioFraming` failure under concurrent sandbox load passed in isolation
  and on rerun; unrelated to this change — no `src/` edit).
- `uv run ruff check tests/test_ci_workflows.py` → clean; `ruff format --check` → formatted.
- `uv run mypy src/ scripts/` → no issues; `uv run pyright` → 0 errors, 1 pre-existing warning.
- `uv run coverage run -m pytest` + `bash scripts/check_core_coverage.sh` → four core
  modules 100%; `coverage report -m` TOTAL 94%.
- `uv run python scripts/check_test_mapping.py` → OK.
