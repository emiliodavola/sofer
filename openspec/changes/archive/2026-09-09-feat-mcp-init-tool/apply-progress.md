# Apply Progress: feat/mcp-init-tool — Expose `sofer init` as MCP tool `sofer_init`

**Change**: feat/mcp-init-tool
**Branch**: feat/mcp-init-tool
**Mode**: Standard (strict_tdd false)
**Date**: 2026-08-31

## Work Units

| Unit | Tasks | Commit | Notes |
|------|-------|--------|-------|
| 1 | 1.1, 1.2, 1.3, 2.1, 2.2, 3.1, 3.2, 3.3 | 6fbd4e9 feat(mcp): expose sofer init as sofer_init tool | Thin adapter with CF-2 containment, _INIT_TEMPLATE reuse, check_flatten_collisions/move_to_raw, roster 10->11 and INIT-01 scenarios |
| 2 | 4.1, 4.2 | 4374b7f docs(mcp): sync README counters to 11 tools | README/ES AI/MCP paragraph 10->11 and command-reference row |

## Completed Tasks

- [x] 1.1 Imports in mcp_server.py — _INIT_TEMPLATE, move_to_raw, SUPPORTED_FORMATS, RAW_DIR
- [x] 1.2 sofer_init(name, move_existing, dry_run, force) with _tool_execution+_capture_output, empty name guard, _contained_path, force gate, check_flatten_collisions, dry_run preview, raw_dir.mkdir, _INIT_TEMPLATE.format, move_to_raw
- [x] 1.3 Module docstring 10/8 -> 11/9
- [x] 2.1 _register_tools 10->11 with server.tool(sofer_init)
- [x] 2.2 Error mapping PathOutsideRootError propagates, idempotency/collision/empty -> ok:False
- [x] 3.1 Roster test_exactly_eleven_callables + sofer_init schema (name required string, 3 bools default false)
- [x] 3.2 INIT-01 scenarios: Creates TOML+raw, dry_run no mutation, collision, traversal
- [x] 3.3 Idempotency/force/tree preserve tests
- [x] 4.1 README.md 10->11 and sofer_init in callable list + command-reference row
- [x] 4.2 README_ES.md same sync
- [x] 4.3 Full verification green

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| src/sofer/mcp_server.py | Modified | Imports _INIT_TEMPLATE/SUPPORTED_FORMATS/move_to_raw, updated docstring 10->11, added sofer_init adapter (138 LOC), updated _register_tools to 11 with docstring |
| tests/test_mcp_server.py | Modified | Roster 10->11, added PathOutsideRootError import, stdio 10->11, execution lock list + sofer_init, added 5 test classes (13 tests) for INIT-01 |
| README.md | Modified | AI/MCP paragraph 10->11 and added sofer_init to list, sofer-mcp row 10->11 |
| README_ES.md | Modified | Same sync as README |

## Verification

| Command | Result |
|---------|--------|
| uv run ruff check --fix src/ tests/ | All checks passed |
| uv run ruff format src/ tests/ | 1 file reformatted (mcp_server), 1 file reformatted (test) |
| uv run mypy src/ | Success: no issues found in 29 source files |
| uv run pytest tests/test_mcp_server.py -q | 97 passed, 2 skipped |
| uv run pytest tests/ -q | 1179 passed, 2 skipped |

Stdio handshake: sofer-mcp clean framing verified via existing TestStdioSmoke (11 tools) and in-memory Client.list_tools.

## Deviations from Design

None — implementation matches design.md thin adapter with _contained_path(f"{name}.toml"), _INIT_TEMPLATE reuse, check_flatten_collisions(candidates+existing), dry_run guard before mkdir/move, and _tool_execution/_capture_output envelope.

## Issues Found

None. Empty name handled as ok:false; traversal raises PathOutsideRootError (MCP -> ToolError); collision returns ok:false without move; raw_dir containment checked via resolve().is_relative_to.

## Remaining Tasks

None — 11/11 tasks complete. Ready for sdd-verify.

## Workload / PR Boundary

- Mode: single PR
- Current work unit: 1 (sofer_init + registration + tests + docs)
- Boundary: feat/mcp-init-tool -> dev (PR #102)
- Estimated review budget impact: 338 insertions / low risk (forecast 220-280, actual 338 within single-PR budget)

## Status

11/11 tasks complete. Ready for verify.
