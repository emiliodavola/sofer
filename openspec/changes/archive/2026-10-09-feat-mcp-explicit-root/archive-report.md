# Archive Report: Explicit containment root for `sofer-mcp`

**Change**: `2026-10-09-feat-mcp-explicit-root`
**Archived to**: `openspec/changes/archive/2026-10-09-feat-mcp-explicit-root/`
**Branch**: `feat/273-mcp-explicit-root` (base `origin/dev` @ `b05d977`)

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `mcp-server` | Updated | MSP-R01 "Transport and entry point" amended: 1 clause added (the `--root PATH` / `SOFER_MCP_ROOT` contract, its precedence, and the fail-closed startup refusal), 1 scenario added (`Explicit root with fail-closed startup refusal`), and an attribution note appended to the requirement's header blockquote. No Test Mapping row and no registry edit: `mcp-server` is a permanent declared-backlog spec. |

The canonical `openspec/specs/mcp-server/spec.md` was amended **in place** from the delta's
`## MODIFIED Requirements` block. The change deliberately left `build_server`'s signature and body,
`_contained_path`, `_get_root` and `PathOutsideRootError` untouched — the diff contains none of them
— so containment semantics are unchanged and only `main()` gained behavior.

## Archive Contents

- `proposal.md` — present
- `design.md` — present
- `tasks.md` — present, all tasks complete
- `specs/mcp-server/spec.md` (delta) — present

This change was delivered in a single PR and produced no `explore.md`, `apply-progress.md`,
`verify-report.md` or `sync-report.md` siblings; the four files above are the complete set. The
verification evidence it does not carry as a file is recorded under "SDD Cycle Complete" below.

## Source of Truth Updated

- `openspec/specs/mcp-server/spec.md` — MSP-R01 is canonical with its new clause and scenario.
- `openspec/test-mapping-registry.md` — **untouched**. `mcp-server` remains listed as a permanent
  declared backlog, and the registry bijection still holds (`scripts/check_test_mapping.py` exits 0).

## SDD Cycle Complete

Implementation: complete (`src/sofer/mcp_server.py`, `tests/test_mcp_process.py`, `README.md`,
`README_ES.md`, canonical `mcp-server` spec).

Verification: independent read-only verifier, all nine gates exit 0. Base `1998 passed / 6 skipped` →
branch `2005 passed / 6 skipped` (delta exactly +7 tests; no skip changed). Coverage TOTAL 94% with
the four rule-14 files at 100%. The startup refusal was proven **end-to-end through real subprocesses
of the console script**, and the message names the **resolved absolute path** even when the argument
was passed relative — the property the issue asked for. The verifier also confirmed that
`build_server`'s body and the containment functions are absent from the diff, and that the two
READMEs still mirror each other (36 headings each, 1:1 in order, technical tokens left in English in
the Spanish file).

Delivery: PR #279, merged by the maintainer as `7c30aaa`. Work-unit commits `45a83d6` (the feature,
its seven tests and both READMEs) and `2df3aa7` (SDD record plus harness tracking). Issue #273 was
auto-closed by that merge.

Unfinished tasks and unresolved findings: none.
