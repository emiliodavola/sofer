# Proposal: Registered MCP and CLI process-boundary regression suite (#119)

## Intent

Build a reusable verification harness that proves MCP/CLI behavior through the same boundaries real agents use: FastMCP in-process `Client(server)` for registered tools, schemas, envelopes, and `tools/list`; a subprocess invoking the actual CLI entrypoint; a stdio/process fixture with parent server root and nested dataset CWD. Helper-level tests let `tools/list`, schema serialization, process CWD, Windows console encoding, and CLI output regressions pass unnoticed — this change makes them regressible. Test-only: no production redesign.

## Scope

### In Scope
- New `tests/test_mcp_process.py`: stdio/process boundary — server spawn, parent-root vs nested-dataset CWD, cp1252 help, CLI subprocess dispatch
- Shared boundary fixtures/helpers in `tests/conftest.py` (stdio server fixture, CLI subprocess + cp1252 env helpers, Root-unwrap `_mcp_payload`) — reusable by siblings #116–#122
- Route direct-call MCP tests (`sofer_publish_confirm`/`sofer_init`/`sofer_validate` in `test_mcp_server.py`; `test_offline_happy_path` in `test_mcp_schema.py`) through `Client(server)`
- Executable-subprocess CLI tests in `tests/test_cli.py` for user-visible output (cp1252 help, dispatch)
- Recovery replay: execute returned `next` calls; assert the second call reaches the intended branch
- CI: keep complete-run `uv run pytest -v` as the gate (no focused-only command)

### Out of Scope
- Production changes (none needed — exploration found behavior already holds)
- Network publish/upload; installed `sofer-mcp` binary proof (delivery issue)
- Windows CI runner; `SOFER_TRACE.md`

## Capabilities

### New Capabilities
None — test-only change; no new product behavior is specified.

### Modified Capabilities
None — existing `mcp-server` and `cli` specs already state the contracts these tests pin (MSP-R01/R02, CLI-R01/R02).

## Approach

Hybrid of exploration approaches 1 + 3:
- Dedicated `tests/test_mcp_process.py` + shared conftest fixtures (matches issue scope; one home for process boundaries; siblings reuse).
- Port the reference attempt's boundary patterns (`_call_mcp`, `_mcp_payload`, `_run_cli`, cp1252 subprocess, recovery replay) WITHOUT its absent `execution_context`/`workflow` modules — rewrite assertions against current envelopes (`ok`/`exit_code`/`output`/`next`/`config_errors`).
- Keep lean: one shared stdio fixture per module, not per-test spawns — 1258 tests exist; subprocess adds wall-clock.

Rejected: approach 2 alone (reuses helpers but smears boundaries; no reusable stdio fixture).

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `tests/test_mcp_process.py` | New | stdio/process boundary suite |
| `tests/conftest.py` | Modified | shared boundary fixtures/helpers |
| `tests/test_mcp_server.py` | Modified | direct calls → `Client(server)` |
| `tests/test_mcp_schema.py` | Modified | `test_offline_happy_path` → `Client(server)` |
| `tests/test_cli.py` | Modified | subprocess output tests |
| `.github/workflows/ci.yml` | Modified | confirm complete-run gate |
| `src/sofer/mcp_server.py`, `src/sofer/cli.py` | Read-only | boundary references |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| `_SERVER_ROOT`/`_APPROVAL_PHRASE` are per-process globals | High | one `build_server` per test (existing convention) |
| cp1252 tests need a Windows console on ubuntu CI (no Windows runner) | Med | `PYTHONIOENCODING=cp1252` + `errors="strict"` (cross-platform); win32-safe skips |
| `_capture_output` swaps global stdout | Med | subprocess tests bypass; in-process serialized under `_EXEC_LOCK` |
| Root-model wrapping hides schemas | Med | share `_unwrap`/`_mcp_payload`, don't duplicate |
| mypy skips `tests/`; suite wall-clock growth | Low | ruff still lints; type helpers anyway; lean shared fixtures |
| `SOFER_TRACE.md` untracked at root | Med | never read/modified/staged |

## Proposal question round

Assumptions needing user review: (1) hybrid approach 1+3; (2) zero production changes (no test hooks required); (3) cp1252 coverage runs on ubuntu CI via `PYTHONIOENCODING`, not a Windows job.

## Rollback Plan

Pure test change — delete `tests/test_mcp_process.py`, revert conftest/test edits; no production surface, no migration, no data impact.

## Dependencies

- `fastmcp` (already a dependency); no new deps; no pytest-asyncio (existing `asyncio.run` convention).

## Success Criteria

- [ ] Each boundary slice has ≥1 test through the public boundary it changes
- [ ] MCP tests use `Client(server)` or real stdio transport; no new boundary-hiding direct calls
- [ ] CLI user-visible output tested via executable subprocess
- [ ] Recovery replay tests execute returned calls and reach the intended branch
- [ ] Empty/existing/greenfield config, triage, nested output, malformed config, delivery handoff covered
- [ ] Complete run `uv run pytest tests/ -q`, Ruff, mypy, `git diff --check` pass; deterministic, offline, no HF credentials; `SOFER_TRACE.md` untouched