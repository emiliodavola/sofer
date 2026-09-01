# Apply Progress: Registered MCP and CLI process-boundary regression suite

## Status

Phase 1 (PR 1) complete — tasks 1.1–1.5 done. Standard mode (`strict_tdd=false`
per `openspec/config.yaml`); Work Unit Evidence recorded below.

## Completed Tasks

- [x] 1.1 Add `mcp_payload(result)` Root-unwrap to `tests/conftest.py` (ported from `_unwrap`), typed (PB-09/07).
- [x] 1.2 Add `run_cli(argv, *, cwd, env=None, encoding="utf-8")` — spawns `[sys.executable, "-m", "sofer.cli", ...]` (PB-02).
- [x] 1.3 Add module-scoped `mcp_stdio_server`: one `main()` stdio spawn per module (PB-09).
- [x] 1.4 `test_mcp_server._unwrap` delegates to `mcp_payload` (D2).
- [x] 1.5 Gate: full pytest, ruff, mypy, `git diff --check`; `SOFER_TRACE.md` untouched (PB-07/08).

## Work Unit Evidence

| Evidence | Required value |
|---|---|
| Focused test command and exact result | `uv run pytest tests/test_mcp_server.py -q` → **137 passed, 2 skipped** (delegation exercised by every `_call`-based test) |
| Runtime harness command/scenario and exact result | Real stdio subprocess through `sofer.mcp_server.main()`: initialize + `tools/list` (14 tools) + `sofer_validate` round-trip → clean framing, `ok:true`; `run_cli(["--help"])` → rc 0, lists every subcommand; `run_cli([<unknown>])` → rc 2 (throwaway harness in temp dir, not committed) |
| Rollback boundary | Revert `tests/conftest.py` + `tests/test_mcp_server.py` (delegation + import); delete `openspec/changes/test-mcp-cli-regression-suite/` — zero production surface (`src/sofer/` untouched) |

## Files Changed

| File | Action | What Was Done |
|---|---|---|
| `tests/conftest.py` | Modified | Added `mcp_payload` (faithful port of `_unwrap`), `run_cli`, `McpStdioServer` + module-scoped `mcp_stdio_server` fixture |
| `tests/test_mcp_server.py` | Modified | `_unwrap` delegates to `mcp_payload`; added `from conftest import mcp_payload` |
| `openspec/changes/test-mcp-cli-regression-suite/tasks.md` | Modified | Marked 1.1–1.5 `[x]` |
| `openspec/changes/test-mcp-cli-regression-suite/apply-progress.md` | Created | This artifact |

## Deviations from Design

- **`mcp_stdio_server` return type**: yields a `McpStdioServer` config object
  (server-root `cwd` + `spawn() -> StdioServerParameters`) instead of the
  design sketch `-> Path`. Required by task 1.3's apply-time note:
  `server.run("stdio")` serves exactly one client session per subprocess, so
  the module-scoped fixture creates one server root + one spawn config per
  module and each stdio session calls `spawn()` for a fresh subprocess. The
  PB-09 lean-spawn bound (one spawn per module, never one per test) holds
  because the process module has a single stdio framing test per module.
- **`mcp_payload` typing**: `(result: Any) -> Any` (design named the helper
  only); the unwrap legitimately returns dict | Root.root | passthrough.
  Logic is a faithful port of `_unwrap` (identical field list); the single
  `result.model_dump()` call became `getattr(result, "model_dump")()` to keep
  the editor type-checker quiet — same semantics.
- **`run_cli` errors**: strict decoding (`errors="strict"`) hardcoded inside
  the helper per D4 (spec PB-02 requires strict-decodable stdout); the
  task-specified signature (no `errors` param) kept exactly.

## Issues Found

- None blocking. Note for later PRs: `tests/test_mcp_server.py::_make_dataset`
  and conftest's `_write_minimal_dataset` are near-duplicates; refactoring
  `_make_dataset` to use the conftest writer is deferred out of PR 1 scope
  (task 1.4 touches only `_unwrap`).

## Remaining Tasks (later PRs in the chain)

- [ ] 2.1–2.5 Phase 2 (PR 2): direct-call → Client(server) conversions
- [ ] 3.1–3.6 Phase 3 (PR 3): `mcp-config-states/` + stdio/CWD/recovery
- [ ] 4.1–4.6 Phase 4 (PR 4): config states + handoff
- [ ] 5.1–5.5 Phase 5 (PR 5): test_cli subprocess + CI

## Workload / PR Boundary

- Mode: chained PR slice (feature-branch-chain on `test/mcp-cli-regression-suite`)
- Current work unit: PR 1 — conftest fixtures + `_unwrap` delegation
- Boundary: tracker branch → shared boundary fixtures + delegation; planning
  trail ships with the code (repo `chore(sdd):` convention)
- Estimated review budget impact: low (< 400 changed lines)

## Status

5/5 Phase 1 tasks complete. Ready for review of PR 1; next batch = PR 2 (Phase 2).