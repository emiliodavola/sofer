# Archive Report: README(ES) veracity sweep — MCP surface, flags table, local placeholders (#183, #190, #180)

**Change**: `docs-readme-veracity-sweep`
**Archived to**: `openspec/changes/archive/2026-09-25-docs-readme-veracity-sweep/`
**Branch**: `docs/readme-veracity-sweep` (base `dev@60cb540`)
**Work-unit commit**: `710a3e5`

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| — | None | Documentation-only change. No delta spec and no canonical-spec edit: the READMEs were corrected to agree with the already-governed `mcp-server`, `cli`, and `process-boundary` behavior. |

## Archive Contents

- `explore.md` — present
- `proposal.md` — present
- `design.md` — present
- `tasks.md` — present, 17/17 tasks complete
- `apply-progress.md` — present
- `verify-report.md` — present
- `specs/` — absent by design (no spec delta)

The change folder was moved with a mechanical `git mv`, verified by an empty `diff -r`
against a pre-move recursive snapshot (`DIFF_EMPTY_OK`).

## Source of Truth Updated

- `README.md` — summary row and MCP paragraph report 14 tools / 4 resources / 3 prompts and
  document `sofer://status`; the `--force`/`--dry-run`/`--output` rows list every accepting
  subcommand; examples use `C:\Users\...\...`, `C:/Users/.../...`, and `<hf-user>`.
- `README_ES.md` — mirrored edits (AGENTS.md rule 13).

## SDD / ODD Cycle Complete

Implementation: complete (two files, one work-unit commit `710a3e5`). Verification: focused
README tests `3 passed`; full suite `1849 passed, 2 skipped`; ruff/format/mypy/pyright clean;
`check_test_mapping.py` OK; independent read-only verifier `OVERALL: PASS`. Unfinished tasks
and unresolved findings: none observed.

Out of scope (tracked for the specs PR, `docs/specs-veracity-sweep`): the canonical-spec
`user="emiliodavola"` literals in `openspec/specs/mcp-server/spec.md` and
`openspec/specs/process-boundary/spec.md` (#180 second scope); the optional
`tests/test_docs_placeholders.py` guard.
