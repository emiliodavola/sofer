# Archive Report: Reconcile the openspec SDD context (#258)

**Change**: `docs-openspec-context-drift`
**Archived to**: `openspec/changes/archive/2026-09-26-docs-openspec-context-drift/`
**Branch**: `docs/258-openspec-context-drift` (base `dev` @ `5f6c2de`)

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| — | None | ODD: no `openspec/specs/**` requirement was amended. The guards are supporting guards (unmapped), like `test_ci_workflow_files_present`. |

## Archive Contents

- `explore.md` — present
- `proposal.md` — present
- `design.md` — present
- `tasks.md` — present, all tasks complete
- `apply-progress.md` — present
- `verify-report.md` — present (independent verification PASS + findings resolved)
- No `specs/` delta — this change amends no capability.

## Source of Truth Updated

- `openspec/project.md` — stack table, CI row, subcommand inventory, hook order, tool
  versions, and footer reconciled with `pyproject.toml`, `src/sofer/cli.py`, and the
  pre-commit config.
- `openspec/config.yaml` — context versions, `testing.quality`, `pre_commit`, and
  `rules.verify[0].build_command` reconciled with the CI lint job.
- `tests/test_ci_workflows.py` — four supporting guards (subcommand inventory, tool
  versions, pyright gate, config quality commands).
- `openspec/test-mapping-registry.md` — unchanged (no spec gained a table).

## SDD / ODD Cycle Complete

Implementation: complete (`openspec/project.md`, `openspec/config.yaml`,
`tests/test_ci_workflows.py`).
Verification: independent read-only adversarial subagent — PASS on all eight claims;
all four findings fixed; four negative-control probes fail on drift; full suite
`1992 passed, 1 skipped`; ruff check/format, mypy, pyright clean; checker exit 0.
Unfinished tasks and unresolved findings: none.
