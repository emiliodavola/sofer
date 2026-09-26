# Apply Progress: Reconcile the openspec SDD context (#258)

**Change**: `docs-openspec-context-drift`
**Mode**: ODD (documentation reconciliation; no runtime boundary, no capability amended)

## Completed Tasks

- [x] 1.1–1.5 `project.md` and `config.yaml` reconciled with `pyproject.toml`, `cli.py`, the CI lint job, and the pre-commit config.
- [x] 2.1–2.5 Four supporting guards + module-docstring note.
- [x] 3.1–3.5 Focused + full verification; negative-control probes; checker.
- [x] 4.1 Archive the change folder.

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `openspec/project.md` | Modified | mypy strict + pyright in the stack table and CI row; 10-subcommand inventory; hook order; ruff/mypy/pyright versions; pre-commit line |
| `openspec/config.yaml` | Modified | Context versions; `quality` command scopes + `second_type_checker`; `pre_commit`; `verify.build_command` |
| `tests/test_ci_workflows.py` | Modified | Four supporting drift guards + module-docstring note |
| `openspec/changes/archive/2026-09-26-docs-openspec-context-drift/` | New | This change's artifacts |

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Work-unit commit | single ODD commit (this branch) |
| Focused test command and result | `uv run pytest tests/test_ci_workflows.py -q` — `49 passed` |
| Runtime harness command/scenario and result | N/A — documentation/spec context; no runtime boundary. Full `uv run pytest tests/ -q` — `1992 passed, 1 skipped` |
| Negative controls | count `10→9` fails the inventory guard; `mypy 2.3.1→2.3.0` fails the version guard; removing `uv run pyright` fails the pyright guard; formatter `--check` removed fails the quality-command guard |
| Lint/type gates | `ruff check src/ tests/ scripts/` all passed; `ruff format --check src/ tests/` 73 files formatted; `mypy src/ scripts/` no issues; `pyright` 0 errors, 1 pre-existing `_toml.py` warning |
| Test-mapping checker | `uv run python scripts/check_test_mapping.py` — `OK: test-mapping contract holds` |
| Rollback boundary | Revert the three-file diff; no source, dependency, workflow, or release state touched |

## Deviations from Design

None.

## Remaining Tasks

None.
