# Tasks: Reconcile the openspec SDD context (#258)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~30 authored across 2 docs + ~90 guard lines; SDD artifacts excluded |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Delivery strategy | single-pr / ODD work-unit commit |

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command |
|------|------|-----------|----------------------|
| 1 | SDD context matches the enforced configuration, guarded | PR 1 | `uv run pytest tests/test_ci_workflows.py -q` |

## Phase 1: Reconcile prose

- [x] 1.1 `project.md`: mypy strict + pyright in the stack table; CI row gains pyright.
- [x] 1.2 `project.md`: `cli.py` inventory → 10 subcommands incl. `report-failure`.
- [x] 1.3 `project.md`: Pre-commit hook order gains pyright.
- [x] 1.4 `project.md`: CI versions → ruff 0.16.8 / mypy 2.3.1 / pyright 1.1.414.
- [x] 1.5 `config.yaml`: context versions; quality command scopes; pre_commit; verify build_command.

## Phase 2: Guards

- [x] 2.1 Subcommand inventory guard.
- [x] 2.2 Tool-version guard.
- [x] 2.3 Pyright-gate guard.
- [x] 2.4 Config quality-command contract guard.
- [x] 2.5 Module-docstring note.

## Phase 3: Verify

- [x] 3.1 Focused guards green; negative-control probes fail on drift.
- [x] 3.2 Full suite green; ruff/mypy/pyright clean.
- [x] 3.3 `scripts/check_test_mapping.py` exit 0.
- [x] 3.4 Independent read-only verification.
- [x] 3.5 Record evidence in `verify-report.md`.

## Phase 4: Archive

- [x] 4.1 Move the change folder to `openspec/changes/archive/2026-09-26-docs-openspec-context-drift/`.
