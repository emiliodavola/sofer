# Archive Report: Ignore the multi-home analyzer pins in the Dependabot group

**Change**: `2026-10-09-fix-dependabot-multi-home-pins`
**Archived to**: `openspec/changes/archive/2026-10-09-fix-dependabot-multi-home-pins/`
**Branch**: `ci/275-dependabot-multi-home-pins` (base `origin/dev` @ `b0b6012`)

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `ci` | Updated | CI-14 "Dependabot update policy" amended: 1 clause added (`mypy` and `pyright` ignored at every update type), 1 scenario added (`uv updates ignore the coordinated analyzer pins`), 1 Test Mapping row appended, and the requirement's header blockquote extended with the change attribution. No new requirement. |

The canonical `openspec/specs/ci/spec.md` was amended **in place** from the delta's
`## MODIFIED Requirements` block: one bullet inserted between the existing `ruff` and `fastmcp`
bullets (matching the order of the `ignore` list it describes), one scenario inserted after
`uv updates ignore the coordinated ruff pin`, and one row appended to the Test Mapping table
immediately after the `ruff` row. The #258 tool-version guard
(`test_openspec_context_declares_the_enforced_tool_versions`) and its helpers were deliberately left
**byte-identical** — this change removed a bump the bot could not complete, never the check that
catches the drift.

## Archive Contents

- `proposal.md` — present
- `design.md` — present
- `tasks.md` — present, all tasks complete
- `specs/ci/spec.md` (delta) — present

This change was delivered in a single PR and produced no `explore.md`, `apply-progress.md`,
`verify-report.md` or `sync-report.md` siblings; the four files above are the complete set. The
verification evidence it does not carry as a file is recorded under "SDD Cycle Complete" below.

## Source of Truth Updated

- `openspec/specs/ci/spec.md` — CI-14 is canonical with its new clause, scenario and Test Mapping
  row. The `ci` spec carries a `## Test Mapping` table, so it stays out of
  `openspec/test-mapping-registry.md` and the registry bijection is unaffected.

## SDD Cycle Complete

Implementation: complete (`.github/dependabot.yml`, `tests/test_ci_workflows.py`, `CONTRIBUTING.md`,
`AGENTS.md`, canonical `ci` spec).

Verification: independent read-only verifier, all nine gates exit 0. Base `1997 passed / 6 skipped` →
branch `1998 passed / 6 skipped` (delta exactly +1 test, the new guard; no skip changed). Coverage
TOTAL 94% with the four rule-14 files at 100%. The new guard was proven non-vacuous with a scratch
probe outside the repository: it rejects both a missing ignore entry and an `update-types`-narrowed
entry. The protected files (`pyproject.toml`, `uv.lock`, `openspec/project.md`,
`openspec/config.yaml`) and everything under `src/` were absent from the diff.

Delivery: PR #276, merged by the maintainer as `b05d977`. Work-unit commits `1c4589c` (policy, guard
and docs), `3f10c54` (SDD record), `9596da7` (routine-update cadence `weekly` → `monthly`, requested
by the maintainer during implementation) and `80d08d9` (harness tracking under `odd/`). Issue #275
closed as COMPLETED.

Unfinished tasks and unresolved findings: none.
