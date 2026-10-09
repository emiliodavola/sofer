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

Verification: the change carries its own red-then-green, and these figures are **reproducible with the
released test file** — the class's `skipif` guards read the *test module's* own `sys`, not the module
under test, so the file collects against the base revision:

| Run | Command | Result |
| --- | --- | --- |
| RED | the released `TestUserConfigResolution` against the sources of `22877b0` | **16 failed, 2 passed, 2 skipped** (the 2 that pass are the regression guards for the existing resolution) |
| GREEN | the same class on this branch | **18 passed, 2 skipped** |
| Full suite | `uv run pytest tests/ -q` | **2028 passed, 8 skipped** vs base `2012 passed, 6 skipped` |

The class holds **20 tests**: 18 run on Windows, 2 are POSIX-only and run on the Linux coverage job.

> **Correction, per rule 15's second clause.** An earlier draft of this report cited a 13-test RED of
> `10 failed, 3 passed` and a 16-test GREEN. Those figures were true of an earlier *draft* of the test
> class, not of the released artifact: four tests were added afterwards, two of them while closing the
> `cli.py` coverage gap and two while removing the `skipif`'s dependency on the module under test. The
> old RED was also not reproducible from the artifact, because the draft's `skipif` dereferenced
> `mcp_registration.sys`, which the base module does not import — so the file could not even be
> collected against the base. Both defects were found by the independent verifier and are fixed here,
> before the merge, which is the whole point of archiving inside the delivering PR.

`cli.py`, an AGENTS.md rule-14 module, measures **100.00%** with no `# pragma: no cover`, and
`scripts/check_core_coverage.sh` exits 0. `ruff check`, `ruff format --check`, `mypy src/ scripts/` and
`pyright` are clean; `check_test_mapping.py` exits 0; TOTAL coverage is 94%.

Two things this change states rather than hides:

- **A test was vacuous and was strengthened.** The first draft of
  `test_cmd_remove_uses_the_declared_user_config` used `dry_run=True` with a nonexistent file, where
  removal writes nothing and exits 0 regardless — it passed against the old code and proved nothing. It
  now asserts the declared file was mutated. The same weakness was found by an independent verifier in
  slice 1 (`"SHALL NOT write"` asserted under `dry_run=True`), which is why it was looked for here.
- **`mcp_registration.py` measures 98% on this Windows host, and its 100% on Linux is INFERRED, not
  observed here.** Lines 267-272 are the POSIX-only `pwd` path, unreachable on Windows because the two
  tests covering them are `skipif`-guarded — unguarded they would error on `import pwd` and break the
  Windows test matrix. The inference rests on those guards being False on Linux (so the tests run) and
  on the locally missing set being exactly those lines. `cli.py` is 100% on both platforms.
- **The `all` rejection's "before any write" half is test-proven, not inspected.** Two tests run the
  rejection with `dry_run=False` and assert that none of the four project-scope agent files exists
  afterwards. Slice 1 had the same gap (`"SHALL NOT write"` asserted under `dry_run=True`) and the
  independent verifier caught it there; this change was checked for it in review and the gap was
  found again, then closed.

Issue #274 is closed by this change: it is the issue's own defect — the `$HOME` resolution that made a
successful write a silent no-op — and the fix is the explicit declaration plus the warning that names a
home divergence.

Unfinished tasks and unresolved findings: none.
