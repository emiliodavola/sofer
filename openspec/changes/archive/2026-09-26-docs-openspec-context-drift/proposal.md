# Proposal: Reconcile the openspec SDD context with the enforced configuration (#258)

## Intent

`openspec/project.md` and `openspec/config.yaml` are read by every future SDD change, and
several of their facts contradicted the enforced configuration: the mypy strict posture, the
CLI subcommand inventory, the pinned tool versions, the pyright gate, and the quality
commands. The issue calls this "the same drift family as the closed docs-veracity sweeps
(#184, #187, #212, #214, #236)" — those sweeps did not cover these two bootstrap files.
Because nothing references them, the drift could return silently. This change reconciles the
prose and adds the missing static guards.

## Scope

### In Scope

- `openspec/project.md`: correct the stack table (mypy strict + pyright), the CI row, the
  `cli.py` subcommand inventory (10, `report-failure`), the Pre-commit hook order, and the
  CI tool versions (ruff 0.16.8 / mypy 2.3.1 / pyright 1.1.414).
- `openspec/config.yaml`: correct the context versions, the `quality` command scopes
  (`scripts/` for ruff and mypy, `--check` formatter, pyright entry), the `pre_commit`
  description, and the `verify.build_command`.
- `tests/test_ci_workflows.py`: four supporting guards that derive their expected values
  from `pyproject.toml`, `src/sofer/cli.py`, and the module's CI lint contract.

### Out of Scope

- Any `openspec/specs/**` requirement (no capability is amended — ODD).
- Any `src/sofer/**`, workflow, or pre-commit change.
- The fastmcp cap drift (#257) and the PKG-05 install contract (#259).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The guards enforce agreement among existing declarations; they introduce no new
capability requirement and no scenario (supporting guards, like `test_ci_workflow_files_present`).

## Approach

1. Reconcile `openspec/project.md` against `pyproject.toml`, `src/sofer/cli.py`, and
   `.pre-commit-config.yaml`.
2. Reconcile `openspec/config.yaml` quality commands against the CI `lint` job.
3. Add four supporting guards to `tests/test_ci_workflows.py`:
   - `test_openspec_project_md_declares_the_shipped_subcommands` — parses `cli.py`'s
     top-level `sub.add_parser(...)` names and compares the set/count to the project.md line.
   - `test_openspec_context_declares_the_enforced_tool_versions` — derives ruff/mypy/pyright
     from their dev pins and asserts each `tool version` string in both files.
   - `test_openspec_context_names_the_pyright_gate` — asserts `uv run pyright` in both files.
   - `test_openspec_config_quality_commands_match_the_ci_lint_gates` — asserts each config
     quality command is a member of the module's `_CI_LINT_GATE_RUNS` contract.
4. Run the focused guards, the full suite, ruff/mypy/pyright, and the test-mapping checker.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `openspec/project.md` | Modified | Stack table, CI row, subcommand inventory, hook order, tool versions |
| `openspec/config.yaml` | Modified | Context versions, quality commands, pre_commit, verify build_command |
| `tests/test_ci_workflows.py` | Modified | Four supporting drift guards + module-docstring note |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| The subcommand guard over-constrains inventory order | Low | It compares as a **set** plus the declared count — order is descriptive |
| A guard duplicates a fact instead of deriving it | Low | Every expected value is derived from a declaration home; only the four config commands are named, each cross-checked against `_CI_LINT_GATE_RUNS` |
| A future tool bump breaks the version guard | Low | The guard derives from the dev pins, so a consistent bump needs no test edit |

## Rollback Plan

Revert the three-file diff (`openspec/project.md`, `openspec/config.yaml`,
`tests/test_ci_workflows.py`). No source, dependency, workflow, or release state is touched.

## Dependencies

None.

## Success Criteria

- [ ] `project.md` and `config.yaml` agree with `pyproject.toml`, `cli.py`, and the CI lint job.
- [ ] The four guards pass and each fails if its declared fact drifts (negative-control probes).
- [ ] `uv run pytest tests/ -q` green; ruff check/format, mypy, pyright clean.
- [ ] `uv run python scripts/check_test_mapping.py` exits 0.
