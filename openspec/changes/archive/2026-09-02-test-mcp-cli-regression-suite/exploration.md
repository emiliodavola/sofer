# Exploration: MCP/CLI process-boundary regression suite (#119)

Parent tracker: #115. This exploration maps the current test/source state on branch
`test/mcp-cli-regression-suite` to support building the reusable verification harness.
It maps facts only — it does not design the solution.

## Current State

### Test suite layout (this branch — 1258 tests collected, no Windows CI)

| Module | Lines | Invocation style | Boundary exercised |
|---|---|---|---|
| `tests/test_mcp_server.py` | 2699 | Mixed: in-process `Client(server)` (`_call`, `_tool_schema`) for roster/schema/containment/resources/prompts/init; **direct imported tool calls** (`sofer_publish_confirm(...)`, `sofer_init(...)`, `sofer_validate(...)`) for publish/init paths; **one real stdio subprocess smoke test** (`TestStdioSmoke`) | Registration + schemas + envelopes + stdio |
| `tests/test_mcp_schema.py` | 323 | In-process `Client(server)` for `tools/list` + schemas + annotations + output_schema; direct calls for envelope/refusal tests; `test_offline_happy_path` **explicitly opts into direct function calls** ("MCP client would also work") | Schemas, envelope shape |
| `tests/test_cli.py` | 1063 | Parser-level (`_build_parser().parse_args`) + `_cmd_*` handlers with `Namespace` + `cli.main()` via monkeypatched `sys.argv` (capsys). **No executable-subprocess test** | argparse output, dispatch |
| `tests/test_mcp_registration.py` | 564 | `_cmd_mcp_add/_cmd_mcp_remove` with `Namespace`; real config files (opencode.json, .codex/config.toml, .gemini/settings.json); `Path.home` patching; mocked `subprocess.run` for delegation | `sofer mcp add/remove` handoff |
| `tests/conftest.py` | 67 | Only `pytree` + `restore_tool_config` | — |
| `tests/fixtures/mcp-happy-path/` | data.csv + dataset.toml | Copied into tmp_path by `test_mcp_schema.TestHappyPath` | Real config + data |

- **No `tests/test_mcp_process.py`** exists on this branch (nor on the reference branch).
- **No async/anyio pytest plugin**: tests use `asyncio.run(coro)` around `fastmcp.Client(server)` — already works in-process.
- Direct-call helpers that **hide the registration boundary**: `sofer_publish_confirm`/`sofer_init`/`sofer_validate` imported and called straight; `test_mcp_schema.py:277` comments the choice. `_unwrap` (test_mcp_server.py:95) manually unwraps FastMCP Root models — needed because tools declare `output_schema`.

### Public boundaries agents use (source of truth)

- **Registration**: `build_server(root=None, approval_phrase=None)` (mcp_server.py:2329) → `_register_tools` (mcp_server.py:1836) registers 14 callables via **manual `server.tool(fn, annotations={...}, output_schema={...})`** — not decorator style. `_FastMCP` = `fastmcp.FastMCP` (v3.4.x). Tools are plain functions returning dict envelopes (`ok`, `exit_code`, `output`, `error_code`, `message`, `next`, `config_errors` + extras) built by `_error_envelope` (636) / `_refusal` (670).
- **Framing/serialization**: `_capture_output` (217) swaps `sys.stdout/stderr` to `StringIO` per tool body (stray bytes would corrupt stdio JSON-RPC framing); `_tool_execution` (200) serializes bodies under `_EXEC_LOCK` (threadpool dispatch).
- **Process CWD**: `build_server()` with `root=None` anchors `_SERVER_ROOT = Path.cwd().resolve()` — the stdio launch process CWD IS the server root. `sofer_init` (1647) resolves a per-call `effective_root` (explicit `cwd` → `_contained_path`; `cwd=None` → live `Path.cwd()` when inside server root, else server root) and **never mutates `_SERVER_ROOT`**. `_contained_path` (282) is the single containment gate (Windows drive/UNC/dotdot vectors covered).
- **Windows console encoding (cp1252)**: `sys.stdout.reconfigure(encoding="utf-8")` on win32 exists **only inside `publish()` (publish.py:630) and `prepare()` (prepare.py:690)**. `cli.main()` (cli.py:1477) does NOT reconfigure. **Live probe on this branch**: `PYTHONIOENCODING=cp1252` + `[sys.executable, "-m", "sofer.cli", "--help"]` → RC=0, stdout strict-decodes as cp1252. The behavior holds; there is simply **no test** for it.
- **CLI entrypoint**: `sofer = sofer.cli:main` (`[project.scripts]`), and `python -m sofer.cli` works (`if __name__ == "__main__"`). `main()` = `config.reload(None)` → `_build_parser()` → `sys.exit(args.func(args))`.

### CI (ci.yml, release.yml — both ubuntu-only)

- lint: ubuntu-latest, py3.13, `uv run ruff check src/ tests/ scripts/` + `uv run mypy src/ scripts/`.
- test: ubuntu-latest, matrix py3.10–3.14, **`uv run pytest -v` (complete suite — no focused-only command)** + `uv run sofer --help` smoke.
- **No Windows runner**: "supported CI matrix" = ubuntu × 5 Pythons. Windows compatibility must be guaranteed by tests being win32-safe (skips where privileges missing), not by a Windows job. `PYTHONIOENCODING` is cross-platform, so cp1252 tests run on ubuntu too (the reference attempt did exactly this).
- mypy excludes `tests/` — new test helpers are not type-checked by CI; ruff still lints tests/.

### Reference-only prior attempt (NOT merged; evidence only)

`fix/mcp-end-to-end-reliability` (commit c4dab7f) added `tests/test_sdd_foundation.py` (1210 lines) with reusable boundary patterns: `_call_mcp` (in-process `Client(server)`), `_mcp_payload` (Root unwrap), `_run_cli` (`cli.main()` via sys.argv), recovery **replay** (`replayed = _call_mcp(server, recovery["tool"], recovery["arguments"])`), cp1252 subprocess help (`PYTHONIOENCODING=cp1252`, `encoding="cp1252"`, `errors="strict"`), CLI subprocess `[sys.executable, "-m", "sofer.cli", ...]`, delivery handoff metadata, triage, malformed tool-config refusals. **It depended on production modules `sofer.execution_context` and `sofer.workflow` that DO NOT EXIST on this branch** — those were the reference's production changes (sibling-issue territory). The test *patterns* are portable; the assertions on `phase`/`branch`/`config_path`/`dataset_root`/`requires` fields are not (current envelopes lack those fields).

### Gaps vs. #119 acceptance criteria (mapped, not designed)

- MCP via `Client(server)`/stdio: **partial** — publish/init/confirm paths call imported functions directly; only one stdio test exists.
- CLI subprocess for user-visible output: **missing** in-suite (parser + capsys only; CI has a bare `sofer --help` smoke).
- Recovery replay ("execute returned calls"): **missing** — `next` hints exist (`{"force": True}`, `{"acknowledge_risk": True}`) but no test replays them; init refusals return `next: {}`.
- Scenario coverage: empty config (present), existing config (present), greenfield (present), triage (present), malformed config (present), delivery handoff (present via direct calls), nested output (thin); "real config files and public outputs" — fixture exists and is used by one module only.
- Complete run: CI already uses the complete suite; deterministic/offline: held today via `publish._api` monkeypatch — must be preserved.

## Affected Areas (for the harness work)

- `tests/test_mcp_server.py` — add Client-based coverage where direct calls hide the boundary; reuse `_call`/`_unwrap`/`_make_dataset`.
- `tests/test_mcp_schema.py` — `test_offline_happy_path` is a boundary-hiding helper; candidate to route through `Client(server)`.
- `tests/test_cli.py` — add executable-subprocess tests for help output (cp1252) and dispatch.
- `tests/conftest.py` — only home for shared boundary fixtures (stdio server fixture, CLI subprocess helper, cp1252 env helper).
- `tests/test_mcp_process.py` (new, or equivalent) — issue scope names it; stdio fixture + process CWD (parent server root vs nested dataset CWD).
- `src/sofer/mcp_server.py` — read-only reference for `build_server`/`_register_tools`/envelopes; **no production change planned by #119** except minimal test hooks if a public contract needs one.
- `src/sofer/cli.py` — read-only reference for the entrypoint/subprocess shape.
- `.github/workflows/ci.yml` — confirm the complete-run invocation is the gate (already is).

## Approaches (options for the proposal to weigh — not a design)

1. **New `tests/test_mcp_process.py` + shared conftest fixtures** — dedicated home for the process boundary (stdio spawn, CLI subprocess, cp1252, parent-root/nested-CWD), fixtures reusable by sibling issues #116–#122.
   - Pros: matches issue scope naming; one place for process-boundary concerns; no hidden boundaries.
   - Cons: new module must build its own helpers or extend conftest; adds subprocess wall-clock to the suite.
2. **Extend existing modules in place** — add `Client(server)` tests to test_mcp_server.py/test_mcp_schema.py and subprocess tests to test_cli.py.
   - Pros: reuses existing helpers; no new module.
   - Cons: boundaries stay smeared across modules; no reusable stdio fixture for siblings.
3. **Adopt reference-attempt patterns without its production modules** — port `_call_mcp`/`_mcp_payload`/`_run_cli`/cp1252-subprocess/recovery-replay shapes, dropping `execution_context`/`workflow` dependencies.
   - Pros: proven shapes, fast to adapt.
   - Cons: assertions must be rewritten against current envelope fields.

## Recommendation

Map current state; the proposal should (a) add a dedicated process-boundary module per the issue scope, (b) extend conftest with shared fixtures that exercise real boundaries, (c) route the remaining direct-call MCP tests through `Client(server)`, (d) port the reference attempt's boundary *patterns* (cp1252 subprocess help, recovery replay, `_mcp_payload`) without its production modules, and (e) keep CI on the complete `uv run pytest` run. Effort: Medium.

## Risks

- **One-server-per-process globals** (`_SERVER_ROOT`, `_APPROVAL_PHRASE`): two servers in one process inherit the last posture — one `build_server` per test (docstring warns; current tests comply).
- **`_capture_output` swaps `sys.stdout` globally** under `_EXEC_LOCK`: in-process concurrency tests are serialized by design; subprocess tests bypass it entirely.
- **Windows**: stdio spawn via `sys.executable` works on win32; the installed `sofer-mcp` binary proof is out of scope (delivery issue). Symlink/junction vectors already skip without privileges.
- **Direct-call tests prove domain logic, not the public boundary**; converting them hits `output_schema` Root-model wrapping — the `_unwrap`/`_mcp_payload` handling must be shared, not duplicated.
- **mypy skips `tests/`** — test-helper type errors pass CI; ruff still covers tests/.
- **Suite growth**: 1258 tests now; stdio/subprocess tests add wall-clock — keep the harness lean and avoid per-test process spawns where one shared fixture suffices.
- **`SOFER_TRACE.md`** (untracked at repo root, `??` in git status) must never be read/modified/staged — it is not part of this change.

## Ready for Proposal

Yes — current state is fully mapped; the proposal should pick among the three approaches above and can proceed to sdd-propose.