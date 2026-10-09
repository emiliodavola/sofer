# Archive Report: Explicit user-scope config file for `sofer mcp add`/`remove`

**Change**: `2026-10-09-feat-mcp-user-config-flag`
**Archived to**: `openspec/changes/archive/2026-10-09-feat-mcp-user-config-flag/`
**Branch**: `feat/274-mcp-user-config-flag` (base `origin/dev` @ `22877b0`)

> Archived **inside the pull request that delivers it**, per AGENTS.md rule 15. The report therefore
> cites the branch and the base, not a merge commit — the merge does not exist yet, which is the
> consequence of archiving in the same PR rather than in a follow-up.

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `mcp-registration` | Updated | MCP-REG-01 "MCP add idempotent and safe" amended: 1 clause added (the three-step user-scope resolution, blank-as-unset, the `--agent all` rejection, the mismatch warning, project-scope indifference), 1 amendment blockquote, 1 scenario added (`User-scope config resolution`). No Test Mapping row and no registry edit: declared-backlog spec. |
| `cli` | Updated | CLI-R09 "mcp add/remove help" amended: `--user-config PATH` added to the flag enumeration, 1 paragraph added stating the flag's meaning and the `--agent all` rejection, and `--user-config` added to the `add help` scenario's expected flag list. No Test Mapping row and no registry edit: declared-backlog spec. |

Both canonical specs were amended **in place** from their deltas' `## MODIFIED Requirements` blocks,
which describe the spans that moved rather than re-copying the whole requirements.

## Archive Contents

- `proposal.md` — present
- `design.md` — present
- `tasks.md` — present, **all tasks complete** (T1–T12 all `done`; verified before writing this report,
  which is rule 15's second clause)
- `specs/mcp-registration/spec.md` (delta) — present
- `specs/cli/spec.md` (delta) — present

No `explore.md`, `apply-progress.md`, `verify-report.md` or `sync-report.md` siblings were produced; the
five files above are the complete set. The verification evidence is recorded under "SDD Cycle Complete".

## Source of Truth Updated

- `openspec/specs/mcp-registration/spec.md` — MCP-REG-01 is canonical with its new clause, note and
  scenario.
- `openspec/specs/cli/spec.md` — CLI-R09 is canonical with the flag in its enumeration, its new
  paragraph and its updated help scenario.
- `openspec/test-mapping-registry.md` — **untouched**; the bijection still holds
  (`scripts/check_test_mapping.py` exits 0).
- `README.md` + `README_ES.md` — the flags table, the `--agent`/`--scope` row and the per-agent
  locations table now state the default resolution and the override, in both files (rule 13).

## SDD Cycle Complete

Implementation: complete (`src/sofer/mcp_registration.py`, `src/sofer/cli.py`,
`tests/test_mcp_registration.py`, both READMEs, both canonical specs).

Verification: the change carries its own red-then-green — the new tests failed 10 of 13 before the
implementation (the three that passed were the regression guards for the existing resolution) and pass
afterwards; the full suite is `2028 passed, 8 skipped` against a base of `2012/6`. `cli.py`, an
AGENTS.md rule-14 module, measures **100.00%** with no `# pragma: no cover`, and
`scripts/check_core_coverage.sh` exits 0. `ruff check`, `ruff format --check`, `mypy src/ scripts/` and
`pyright` are clean; `check_test_mapping.py` exits 0; TOTAL coverage is 94%.

Two things this change states rather than hides:

- **A test was vacuous and was strengthened.** The first draft of
  `test_cmd_remove_uses_the_declared_user_config` used `dry_run=True` with a nonexistent file, where
  removal writes nothing and exits 0 regardless — it passed against the old code and proved nothing. It
  now asserts the declared file was mutated. The same weakness was found by an independent verifier in
  slice 1 (`"SHALL NOT write"` asserted under `dry_run=True`), which is why it was looked for here.
- **`mcp_registration.py` measures 98% locally and 100% on Linux.** Lines 267-272 are the POSIX-only
  `pwd` path, unreachable on the Windows development host because the two tests covering them are
  `skipif`-guarded — unguarded they would error on `import pwd` and break the Windows test matrix.
  `cli.py` is 100% on both platforms.

Issue #274 is closed by this change: it is the issue's own defect — the `$HOME` resolution that made a
successful write a silent no-op — and the fix is the explicit declaration plus the warning that names a
home divergence.

Unfinished tasks and unresolved findings: none.
