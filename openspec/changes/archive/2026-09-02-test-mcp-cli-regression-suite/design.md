# Design: Registered MCP and CLI process-boundary regression suite (#119)

## Technical Approach

Test-only harness (PB-01…PB-09) proving sofer's MCP server and CLI through the same boundaries agents use: in-process `fastmcp.Client(server)` for registered tools, real stdio subprocess transport, and executable CLI subprocesses. Hybrid of exploration approaches 1+3: new `tests/test_mcp_process.py` plus shared boundary fixtures in `tests/conftest.py`, porting the reference attempt's proven shapes (`_mcp_payload`, `_call_mcp`, cp1252 subprocess, recovery replay) **without** its absent `execution_context`/`workflow` modules, asserting against current envelopes (`ok`/`exit_code`/`output`/`next`/`config_errors`). Zero production changes.

## Architecture Decisions

| # | Decision | Choice | Alternatives | Rationale |
|---|---|---|---|---|
| D1 | Layout (PB-09) | New `tests/test_mcp_process.py`; helpers in `conftest.py` | Extend modules in place | One home for process boundaries; siblings #116–#122 reuse |
| D2 | Root-unwrap | Conftest `mcp_payload`; `test_mcp_server._unwrap` delegates to it | Duplicate per module | PB-09 "no re-implementation"; output_schema Root wrapping is the one tricky seam |
| D3 | Conversions (PB-01) | Route `sofer_publish_confirm`/`sofer_init`/`sofer_validate` direct calls + `test_offline_happy_path` through `Client(server)` | Keep direct calls | Boundary no longer hidden; refusal envelopes DIFFER at the client boundary — FastMCP projects results through each tool's `output_schema`, which drops `error_code`/`message`/`next`, and non-`hf` `target` values surface as schema `ToolError` (see Open Questions) |
| D4 | CLI subprocess (PB-02) | `[sys.executable, "-m", "sofer.cli", …]`, `PYTHONIOENCODING=cp1252`, `encoding="cp1252", errors="strict"` | Windows CI job | Cross-platform; proven by reference; ubuntu-only matrix |
| D5 | Isolation (PB-06/09) | One `build_server()` per test; one module-scoped stdio fixture; `asyncio.run`; no pytest-asyncio | Shared server; async plugin | `_SERVER_ROOT`/`_APPROVAL_PHRASE` are process globals; zero new deps |
| D6 | win32 safety | Reuse `_make_link` junction-fallback pattern; skip without privileges | Fail on win32 | PB-02 "skip without privileges" |
| D7 | CI (PB-05) | Keep `uv run pytest -v` as the complete-suite gate, triggered on every branch push | Focused-only gate; PR-only trigger | Spec SHALL keep the complete run; a `push` trigger (branches `['**']`) gives chained slice branches CI — the `pull_request` `branches:` filter applies to the PR BASE, so slice PRs targeting `test/...` branches would otherwise never run the gate |

## Data Flow

    test → build_server() → Client(server) → call_tool → _tool_execution/_capture_output → envelope → mcp_payload → dict
    test → module stdio fixture: spawn [sys.executable, -c "from sofer.mcp_server import main; main()"] cwd=root
         → initialize → tools/list (14) → tools/call → clean JSON-RPC framing
    test → run_cli([...]) → argparse subprocess → rc + stdout (cp1252 strict)
    Recovery (direct): refused = call(tool, args); hint = refused["next"]; replayed = call(tool, {**args, **hint}) → assert branch
    Recovery (client boundary): refused = call_tool(tool, args); hint = DOCUMENTED constant for that refusal (next is not boundary-visible); replayed = call_tool(tool, {**args, **hint}) → assert a DIFFERENT gate or ok:True

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `tests/test_mcp_process.py` | Create | Stdio framing (PB-01), parent-root vs nested CWD (PB-04), recovery replay (PB-03), config states, delivery handoff |
| `tests/conftest.py` | Modify | Add `mcp_stdio_server` (module-scoped), `run_cli` (cp1252 env), `mcp_payload` (Root-unwrap) |
| `tests/test_mcp_server.py` | Modify | Convert direct publish_confirm/init/validate calls to `_call(server, …)`; `_unwrap` delegates to `mcp_payload` |
| `tests/test_mcp_schema.py` | Modify | `test_offline_happy_path` through `Client(server)`; keep `publish._api` monkeypatch |
| `tests/test_cli.py` | Modify | Add `TestSubprocessBoundary`: `--help` lists all subcommands; cp1252 rc=0 strict-decode; unknown command rc=2 |
| `tests/fixtures/mcp-config-states/` | Create | Deliberately `malformed.toml` + `empty.toml` configs for PB-04 — kept out of `mcp-happy-path/`, which `test_mcp_schema.py` copies wholesale |
| `.github/workflows/ci.yml` | Modify | Annotate `uv run pytest -v` as the deliberate complete gate (D7); add a `push` trigger on all branches so chained slice branches run the gate |
| `src/sofer/mcp_server.py`, `src/sofer/cli.py` | Read-only | Boundary reference; no production change |

Note — PB-08: no operation of the suite, fixtures, or CI reads, modifies, or stages
`SOFER_TRACE.md` (untracked at the repo root); it is not part of this change.

## Interfaces / Contracts

```python
@pytest.fixture(scope="module")
def mcp_stdio_server(tmp_path_factory: pytest.TempPathFactory) -> Path: ...  # one spawn per module; yields server-root cwd
def run_cli(argv: list[str], *, cwd: Path, env: dict[str, str] | None = None,
            encoding: str = "utf-8") -> subprocess.CompletedProcess[str]: ...
def mcp_payload(result: Any) -> dict[str, Any]: ...  # Root-model unwrap, shared
```

Recovery `next` contracts verified in current code: `sofer_init` file-exists → `{"force": True}` (mcp_server.py:1749), name-empty → `{}` (1698); `sofer_publish_confirm` risk gate → `{"acknowledge_risk": True}` (963). Replay merges the hint dict into the second call.

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| In-process | Converted direct calls; roster/schema | `Client(server)` via `_call` |
| Stdio | Clean framing; 14 tools; validate round-trip | One module-scoped spawn |
| Process CWD | `build_server(parent)` + `monkeypatch.chdir(nested)`; init writes land under nested, not parent | Assert filesystem paths, not absent envelope fields |
| CLI E2E | help / cp1252 / dispatch rc=2 | `run_cli` subprocess |
| Config states | empty/existing/greenfield/triage/malformed/handoff | Real fixture TOMLs (`mcp-happy-path/` + `mcp-config-states/`); `publish._api` monkeypatched (PB-06); no `HF_TOKEN` required |

Greenfield: `sofer_init` then `sofer_scan_apply` via client → files registered, `sofer_validate` passes. Triage: `sofer_scan_dry_run` lists candidates, copies nothing, TOML unchanged. Malformed: unparseable TOML → refusal with `config_errors`. Handoff: validate→prepare→codebook→profile→render→`publish(dry_run=True)`→`publish_confirm` (mocked `_api`, `HF_TOKEN` set) → plan returned, confirm reaches upload branch.

**Acceptance contract (PB-07)**: after the change, `uv run pytest tests/ -q`,
`uv run ruff check src/ tests/`, `uv run mypy src/`, and `git diff --check` SHALL
all pass and the pre-existing test count SHALL not regress; new test helpers SHALL
be type-annotated even though mypy excludes `tests/`.

## Migration / Rollout

No migration. Rollback: delete `tests/test_mcp_process.py`, revert conftest/test edits — no production surface.

## Effort / Risk Forecast

- **Changed lines: ~1,100–1,400** (module 450–550; conftest 120–150; conversions 250–350; test_cli 120–160; fixtures ~30; ci.yml comment-only) — within the session review budget of 3000 lines (user-configured). The standard 400-line review guard still applies: slice 1 (conftest + conversions) may brush against it at the top of its range (~270–500 lines) — flag this for the tasks-phase review-workload forecast. Chaining: slice 1 = conftest + conversions, slice 2 = `test_mcp_process.py`, slice 3 = test_cli + fixtures (each slice independently verifiable).
- **Risks**: +30–60 s suite wall-clock (mitigated: one shared stdio spawn); win32 junction privilege (skip pattern); keep help text free of non-cp1252 glyphs so strict-decode holds on ubuntu; `_capture_output` global stdout swap is serialized under `_EXEC_LOCK` in-process and bypassed by subprocess tests.

## Open Questions

Boundary envelope behavior (documented deviation, confirmed by the PR 2 gate
review): FastMCP projects each tool result through the tool's declared
`output_schema`, so the refusal envelopes for `sofer_publish_confirm` /
`sofer_init` / `sofer_validate` DIFFER at the client boundary from the
direct-call envelopes — `error_code`, `message`, and `next` are dropped (the
schema IS the documented contract), and non-`hf` `target` values surface as a
schema `ToolError` ("Input should be 'hf'") instead of the `TARGET_INVALID`
envelope branch. PB-03 recovery replay therefore keys off boundary-visible
signals: the human-readable refusal message in `output` plus the
deterministic, documented `next` hint VALUES (risk gate →
`{"acknowledge_risk": True}`, confidential → `{"acknowledge_confidential":
True}`, approval → `{"approval_phrase": ...}`, init file-exists →
`{"force": True}`, init name-empty → `{}`), merged into the replayed call.
Branch progression is asserted by the second call failing at a DIFFERENT gate
or reaching `ok:True`.