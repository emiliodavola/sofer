# Archive Report: Require an existing directory for `--cwd`

**Change**: `2026-10-09-fix-mcp-user-config-resolution`
**Archived to**: `openspec/changes/archive/2026-10-09-fix-mcp-user-config-resolution/`
**Branch**: `fix/274-cwd-existence-rule` (base `origin/dev` @ `2eb4927`)

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `mcp-registration` | Updated | MCP-REG-01 "MCP add idempotent and safe" amended: 1 clause added (the `--cwd` existence rule plus the outside-root acceptance), 1 amendment note recording why the previous rule was removed, and 1 scenario added (`Cwd existence, not containment`). No Test Mapping row and no registry edit: `mcp-registration` is a permanent declared-backlog spec. |

The canonical `openspec/specs/mcp-registration/spec.md` was amended **in place** from the delta's
`## MODIFIED Requirements` block, which describes the three spans that moved rather than re-copying
the whole requirement. The previous rule was **enforced and described nowhere** — this change is the
first time it is declared — so the amendment note carries the measured evidence for its removal, and
the next reader of `validate_cwd` can see why it stopped refusing.

## Archive Contents

- `proposal.md` — present
- `design.md` — present
- `tasks.md` — present, all tasks complete
- `specs/mcp-registration/spec.md` (delta) — present

This change was delivered in a single PR and produced no `explore.md`, `apply-progress.md`,
`verify-report.md` or `sync-report.md` siblings; the four files above are the complete set. The
verification evidence it does not carry as a file is recorded under "SDD Cycle Complete" below.

## Source of Truth Updated

- `openspec/specs/mcp-registration/spec.md` — MCP-REG-01 is canonical with its new clause, note and
  scenario.
- `openspec/test-mapping-registry.md` — **untouched**; the registry bijection still holds
  (`scripts/check_test_mapping.py` exits 0).
- `README.md` + `README_ES.md` — the flags table, the prose bullet and the command-table row now
  describe existence, not containment, in both files (rule 13).
- `AGENTS.md` — rule 7's requirement that the argparse help and the README move with a behaviour
  change is what this change initially missed and then corrected; the archive placement rule it
  prompted is rule 15.

## SDD Cycle Complete

Implementation: complete (`src/sofer/mcp_registration.py`, `src/sofer/cli.py`,
`tests/test_mcp_registration.py`, both READMEs, canonical `mcp-registration` spec).

Verification: independent read-only verifier, all nine gates exit 0, C1–C8 confirmed. `cli.py` — an
AGENTS.md rule-14 module — stayed at **100.00%** with no `# pragma: no cover`, and both new branches
were fault-injection proven (forcing `validate_cwd` to `True` fails the refusal test; forcing
`outside_root_warning` to `None` fails the warning test). The new tests were proven non-vacuous by
running them against the **old** function body taken from `2eb4927`. The spec clause was confirmed to
match the code, the removed `scope` parameter to have no remaining caller, no test to have been
silently weakened, and the diff to contain no unintended reverts — the branch was rebased after #282
merged, and a pre-rebase push would have reverted that correction.

The verifier also **falsified part of the change description**, and that is the most valuable thing it
did: the PR body understated the cost of relaxing the gate. Removing the rule also removes a
fail-closed brake on misconfiguration — an unintended tree now exits 0 with only a stderr line, so a
caller that does not surface stderr can register a server rooted somewhere unexpected. That is now
named in the PR body and recorded as risk `R1b` in `design.md`, not left implicit.

Delivery: PR #283, merged by the maintainer as `b650d1a`. Work-unit commits `6b42519` (the rule, the
tests and the spec clause), `04a9f0d` (SDD record plus harness tracking) and `a18503e` (the
post-verification correction). Issue #274 **stays open**: this change fixed a different defect found
while exploring it, and the issue's own `$HOME` resolution defect is untouched — recorded in a comment
on the issue.

Unfinished tasks and unresolved findings: none.
