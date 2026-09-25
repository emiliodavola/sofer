# Archive Report: Specs/docs veracity sweep — uploader.py, inventories, project.md (#188, #236, #187, #184)

**Change**: `docs-specs-veracity-sweep`
**Archived to**: `openspec/changes/archive/2026-09-25-docs-specs-veracity-sweep/`
**Branch**: `docs/specs-veracity-sweep` (base `dev@60cb540`)
**Work-unit commits**: `bd91eee`, `8e51139`, `4e67352`, `ffa55b5`

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `parquet-conversion` | Updated in place | §4/§5 marked superseded with owners `_converters.py`/`prepare.py`/`publish.py`; §10.3 defers to `coverage`; §11 checklist corrected |
| `repo-compliance` | Updated in place | §6.3 defers to `coverage`; checklist rows retargeted; `uploader.upload()` claim removed |
| `codebook` | Updated in place | CB-R04 names the `publish` staging layout |
| `mcp-server`, `process-boundary` | Updated in place | Canonical-spec examples de-identified to `<hf-user>` |

No delta specs were produced: the corrections are direct canonical edits (precedent
`fix/186-sarif-spec`), and all four affected specs are registered as unmapped, so the
test-mapping contract is unchanged.

## Archive Contents

- `explore.md` — present
- `proposal.md` — present
- `design.md` — present
- `tasks.md` — present, 18/18 tasks complete
- `apply-progress.md` — present
- `verify-report.md` — present
- `specs/` — absent by design (no delta spec)

The change folder was moved with a mechanical `git mv`, verified by an empty `diff -r`
against a pre-move recursive snapshot (`DIFF_EMPTY_OK`).

## Source of Truth Updated

- `openspec/specs/{parquet-conversion,repo-compliance,codebook}` — canonical specs name
  `_converters.py` / `prepare.py` / `publish.py` and defer coverage floors to the `coverage`
  capability.
- `openspec/specs/{mcp-server,process-boundary}` — examples use `<hf-user>`.
- `AGENTS.md`, `CONTRIBUTING.md`, `docs/configuration.md`, `openspec/project.md` — inventories
  defer to `ls src/sofer/`, the ruff config location is `[tool.ruff]` in `pyproject.toml`,
  the layout is `raw/ → cache/ → build/`, and `project.md` records coverage as installed with
  no stale absolute counts.

## SDD / ODD Cycle Complete

Implementation: complete (nine docs/spec files, four work-unit commits). Verification:
`check_test_mapping.py` OK; `tests/test_ci_workflows.py` `39 passed`; full suite on HEAD
`1849 passed, 2 skipped`; ruff/format/mypy/pyright clean; independent read-only verifier
`OVERALL: PASS`, with two residual references it flagged closed in `ffa55b5`. Unfinished tasks
and unresolved findings: none observed.

Out of scope (intentional): `openspec/specs/cli/spec.md:20` (`upload` is rejected — CLI-R01);
`openspec/changes/archive/**`; the optional `tests/test_docs_placeholders.py` guard.
