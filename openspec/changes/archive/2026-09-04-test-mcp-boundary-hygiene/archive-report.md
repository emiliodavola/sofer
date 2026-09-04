# Archive Report — test-mcp-boundary-hygiene

**Change**: test-mcp-boundary-hygiene
**Issue**: GitHub #130 (closes; residual PB-01 conversion list + PB-03 framing from #119 / PR #123)
**Date**: 2026-09-04
**Artifact store**: hybrid (OpenSpec files + Engram)
**Status**: archived
**Verify verdict**: PASS — 9/9 scenarios (7 PB-01 + 2 PB-03), 2/2 requirements, 0 blockers, 0 CRITICAL
**Branch**: fix/130-boundary-hygiene @ cab251d (base e3fe857)

## Summary

Test-only change. Converted the 8 remaining direct registered-tool call sites in `tests/test_mcp_server.py` (6× `sofer_publish` — stream-restore trigger, dry-run default, hf-schema-rejected, garbage refused, aws refused, local copy — + 2× `sofer_scan_apply` in `test_xlsx_registered_validate_passes_and_idempotent`) plus `sofer_auth_status` at `tests/test_mcp_schema.py` (`test_auth_status_no_leak`) to the public `fastmcp.Client(server)` boundary via the shared `call_tool`/`_call` helper. The stream-restore test switched to a body-raising trigger (missing TOML → `MCPToolError` → `ToolError` at the boundary) so `_capture_output`'s finally-restore is genuinely exercised. `test_garbage_target_dry_run_ok_no_network` was deleted — its asserted behavior is direct-call-only and unreproducible at the boundary; the `calls == []` value survives via `test_garbage_target_dry_run_false_refused_no_api`, now provably "tool body never runs" (in-schema Literal rejection). `test_publish_hf_without_confirm_raises` renamed `test_publish_hf_target_schema_rejected`. The `process-boundary` spec delta MODIFIED PB-01 (extended conversion list + boundary-honest ToolError semantics) and PB-03 (hint-VALUE replay contract, `next` projection re-audit). Zero production changes (`src/` untouched).

## Files Changed (git diff e3fe857...HEAD)

```
 .../apply-progress.md                              | 100 +++++++++++++++++
 .../archive-report.md                              |  85 +++++++++++++++
 .../2026-09-04-test-mcp-boundary-hygiene/design.md | 119 +++++++++++++++++++++
 .../exploration.md                                 |  81 ++++++++++++++
 .../proposal.md                                    |  74 +++++++++++++
 .../specs/process-boundary/spec.md                 |  68 ++++++++++++
 .../2026-09-04-test-mcp-boundary-hygiene/tasks.md  |  58 ++++++++++
 .../verify-report.md                               |  96 +++++++++++++++++
 openspec/specs/process-boundary/spec.md            |  49 ++++++---
 tests/test_mcp_process.py                          |   2 +-
 tests/test_mcp_schema.py                           |  12 ++-
 tests/test_mcp_server.py                           | 112 ++++++++++---------
 12 files changed, 791 insertions(+), 74 deletions(-)
```

- `tests/test_mcp_server.py` — 8 boundary conversions (L291/1064/1073/1179/1189/1222/2577/2591); L1210 test deleted; `test_publish_hf_without_confirm_raises` renamed `test_publish_hf_target_schema_rejected`; L291 rewritten with body-raise trigger + `io.StringIO()` fakes; `import io` added (apply deviation 1); import block otherwise unchanged (design D7).
- `tests/test_mcp_schema.py` — L251 `test_auth_status_no_leak` converted + `next` asserts added; import trimmed to `from sofer.mcp_server import build_server` (D7).
- `tests/test_mcp_process.py` — module docstring L6 wording only: "``next`` hints" → "hint VALUES" (D8).
- `openspec/changes/test-mcp-boundary-hygiene/` — SDD artifacts (exploration/proposal/spec delta/design/tasks/apply-progress), moved verbatim to the archive by this change.

## Spec Sync

- **Domain**: `process-boundary` — live spec `openspec/specs/process-boundary/spec.md` updated.
- **Requirements modified (2)**: PB-01 (Registered MCP tools via public boundary) and PB-03 (Recovery replay executes returned calls) — full-block replacement per the MODIFIED delta; all 7 other requirements (PB-02, PB-04…PB-09) preserved byte-identical.
- **Delta**: `openspec/changes/test-mcp-boundary-hygiene/specs/process-boundary/spec.md` (MODIFIED-only; no ADDED/REMOVED/RENAMED sections — not a destructive merge, `rules.archive` warning not triggered).
- **Merge mechanics**: deterministic byte-level splice (CRLF→LF normalization to repo canonical per `.gitattributes eol=lf`; delta's last block lacked a trailing newline, normalized before splice). Verified in-script AND by an independent readback: merged PB-01/PB-03 blocks byte-identical to the delta blocks (semantic, trailing separators normalized); untouched blocks byte-identical including tails; 9 requirement blocks total; zero CRLF in output.
- **sha256(live spec after sync)**: `04fd98afccc4533c466e7a3c6702c4dbb5c97de0d3bf2e0c297060b18f44c24e`
- **git diff for the sync** (index vs working tree at archive time): 35 insertions, 14 deletions — the two replaced blocks only.

## Task Completion

All 15 tasks in `tasks.md` (Phases 1–4) are `[x]` — 0 unchecked implementation tasks, matching `apply-progress.md` (count corrected to 15 in the post-archive audit pass).

## Verification Evidence (final state, per verify-report obs #967)

| Gate | Result |
|------|--------|
| `uv run pytest tests/ -q` | **1269 passed, 2 skipped** (1271 collected, exit 0) — matches design prediction after L1210 deletion (baseline 1270 → 1269) |
| `uv run ruff check src/ tests/ scripts/` | clean (exit 0) |
| `uv run ruff format --check src/ tests/` | 58 files already formatted (exit 0) |
| `uv run mypy src/ scripts/` | Success: no issues in 30 source files (exit 0) |
| `git diff --check` | clean (exit 0) |
| Boundary proofs | `rg -n "sofer_publish(\|sofer_scan_apply(\|sofer_auth_status(" tests/` → 0 matches; only string refs + source-inspection refs remain |
| Zero production drift | `git diff e3fe857...HEAD -- src/` empty |
| Spec compliance | 9/9 scenarios COMPLIANT (PB-01 s1–s7, PB-03 s1–s2) |

## Lessons & Follow-ups

- **L291 stream fakes must be file-like** (apply deviation 1): after a body raise, FastMCP logs the error via the stdlib `lastResort` handler to `sys.stderr`, which crashes on a bare `object()` fake and masks the real error. `io.StringIO()` fakes keep the identity asserts meaningful. This was found and fixed during apply.
- **SOFER_TRACE.md** (repo root) remains untracked; intentionally not staged (PB-08). Follow-up: add to `.gitignore` or delete before opening the PR.
- **`next` boundary visibility**: re-audited and pinned in PB-03 — `sofer_auth_status` is the only tool whose `output_schema` declares `next`; surfacing it for other tools requires a production schema change (out of scope).
- **Follow-up**: open the PR for branch `fix/130-boundary-hygiene` (single test-only PR, ~126 changed lines, well under the 400-line budget).

## Engram Traceability

| Artifact | Topic key | Observation |
|----------|-----------|-------------|
| explore | `sdd/test-mcp-boundary-hygiene/explore` | #961 |
| proposal | `sdd/test-mcp-boundary-hygiene/proposal` | #962 |
| spec | `sdd/test-mcp-boundary-hygiene/spec` | #963 |
| design | `sdd/test-mcp-boundary-hygiene/design` | #964 |
| tasks | `sdd/test-mcp-boundary-hygiene/tasks` | #965 |
| apply-progress | `sdd/test-mcp-boundary-hygiene/apply-progress` | #966 |
| verify-report | `sdd/test-mcp-boundary-hygiene/verify-report` | #967 |
| archive-report | `sdd/test-mcp-boundary-hygiene/archive-report` | (this change) |

## Archive Mechanics

- Move: `git mv openspec/changes/test-mcp-boundary-hygiene openspec/changes/archive/2026-09-04-test-mcp-boundary-hygiene` (all 6 tracked files as renames; `verify-report.md` untracked, staged with this commit).
- Mandatory readback: pre-move recursive snapshot vs archived tree via `git diff --no-index` → **exit 0, empty diff** (byte-identical). Archive-report.md is additive and excluded from the comparison.
- Active changes dir no longer contains `test-mcp-boundary-hygiene`; archived dir follows the `2026-09-02-test-mcp-cli-regression-suite` convention.