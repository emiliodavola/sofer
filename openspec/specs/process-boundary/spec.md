# process-boundary Specification

## Purpose

Contracts for the test-only regression suite that pins sofer's MCP server and CLI through the same boundaries real agents use: in-process FastMCP `Client(server)`, real stdio transport, and executable CLI subprocesses. The suite SHALL make `tools/list`, schema serialization, process CWD, Windows console encoding, and CLI output regressions visible. No production behavior is specified here — the contracts these tests pin are already stated by the `mcp-server` (MSP-R01/R02) and `cli` (CLI-R01/R02) specs.

## Requirements

### Requirement: Registered MCP tools via public boundary (PB-01)

The suite SHALL exercise registered MCP tools through `fastmcp.Client(server)` (in-process) or the real stdio transport, and SHALL NOT rely on imported tool functions alone. Direct-call tests for `sofer_publish_confirm`, `sofer_init`, `sofer_validate`, `sofer_publish`, and `sofer_scan_apply` in `tests/test_mcp_server.py` — plus `test_offline_happy_path` and `test_auth_status_no_leak` in `tests/test_mcp_schema.py` — SHALL be routed through `Client(server)` via the shared `call_tool`/`_call` helper. The suite SHALL verify `tools/list`, JSON-Schema generation, envelopes, and a `tools/call` round-trip. Invalid Literal inputs (e.g. non-`local` `sofer_publish` targets) SHALL surface as `ToolError` at the client boundary through in-schema rejection, NOT as envelope `error_code` branches. New tests SHALL NOT add boundary-hiding direct calls for registered tools.
(Previously: conversion list named only `sofer_publish_confirm`/`sofer_init`/`sofer_validate`; invalid inputs were asserted via envelope `error_code` branches.)

#### Scenario: tools/list and call via in-process client

- GIVEN `build_server()` and an in-process `Client(server)`
- WHEN `tools/list` and one `tools/call` execute
- THEN 14 callables SHALL be listed and the call SHALL return the documented envelope

#### Scenario: Seven publish/scan_apply conversions through the client

- GIVEN the seven conversion sites in `tests/test_mcp_server.py` (`test_publish_dry_run_default_no_network`, `test_publish_hf_target_schema_rejected`, `test_garbage_target_dry_run_false_refused_no_api`, `test_aws_target_dry_run_false_refused`, `test_local_target_dry_run_false_copies_package`, and `test_xlsx_registered_validate_passes_and_idempotent` covering the two `sofer_scan_apply` sites)
- WHEN each runs via `_call(server, "sofer_publish"|"sofer_scan_apply", {...})` through `Client(server)`
- THEN valid-input conversions (dry-run plan `test_publish_dry_run_default_no_network`, local copy `test_local_target_dry_run_false_copies_package`, scan registration `test_xlsx_registered_validate_passes_and_idempotent`) SHALL return the documented envelope shape

#### Scenario: Stdio transport with clean framing

- GIVEN the server spawned as a subprocess
- WHEN `initialize → tools/list → tools/call` run
- THEN every response SHALL be valid JSON-RPC with no stray stdout bytes

#### Scenario: No remaining direct-call proofs

- GIVEN the converted test suite
- WHEN direct-call sites are enumerated across `tests/test_mcp_server.py` and `tests/test_mcp_schema.py`
- THEN zero registered tool SHALL be imported and called directly — every registered-tool call SHALL go through `Client(server)` or stdio

#### Scenario: Invalid Literal target rejected before the tool body

- GIVEN `sofer_publish` called via `Client(server)` with `target` outside the `"local"` Literal (`"hf"`, `"garbage"`, `"aws"`)
- WHEN the call executes
- THEN the request SHALL be rejected in-schema at input validation and SHALL surface as `ToolError` at the boundary — not an envelope `error_code` branch — and the tool body SHALL NOT run (`test_garbage_target_dry_run_false_refused_no_api`'s `calls == []` is preserved; the guard moved from the in-tool TARGET_INVALID gate to in-schema rejection)
- AND the deleted `test_garbage_target_dry_run_ok_no_network` direct-call-only test (`garbage` + `dry_run` → `ok:True`) SHALL NOT be re-added — its boundary-visible replacement is this in-schema rejection, which holds regardless of `dry_run`

#### Scenario: Stream-restore conversion exercises the tool body

- GIVEN `TestStreamRestore.test_stdout_stderr_restored_after_raise` routed through `Client(server)`
- WHEN `sofer_publish` raises INSIDE the tool body (missing TOML → `MCPToolError`), not via `target="hf"` which input validation rejects before the body
- THEN `pytest.raises(ToolError)` SHALL pass AND stdout/stderr SHALL be restored, exercising `_capture_output`'s stream swap

#### Scenario: auth_status routes via the boundary and exposes next

- GIVEN `test_auth_status_no_leak` (`tests/test_mcp_schema.py`) converted to `Client(server)`
- WHEN `sofer_auth_status` runs via the boundary
- THEN the call SHALL return the documented envelope INCLUDING `next` — the only tool whose `output_schema` declares it — making this the sole boundary-level `next` assertion

### Requirement: CLI user-visible output via executable subprocess (PB-02)

Tests in `tests/test_cli.py` SHALL invoke `[sys.executable, "-m", "sofer.cli", ...]` (or the installed script) whenever the requirement concerns user-visible output; parser-level tests SHALL remain for dispatch semantics. The cp1252 help SHALL run on the ubuntu CI matrix via `PYTHONIOENCODING=cp1252` with `encoding="cp1252", errors="strict"`, SHALL exit 0, and SHALL produce strict-decodable stdout. Windows-only behavior SHALL skip without privileges rather than fail.

#### Scenario: Help via subprocess

- GIVEN the CLI subprocess helper
- WHEN `python -m sofer.cli --help` runs
- THEN exit code SHALL be 0 and stdout SHALL list every subcommand

#### Scenario: cp1252 help on the ubuntu matrix

- GIVEN `PYTHONIOENCODING=cp1252` in the subprocess env
- WHEN `--help` runs
- THEN exit code SHALL be 0 and stdout SHALL strict-decode as cp1252

#### Scenario: Dispatch exit codes

- GIVEN `python -m sofer.cli <unknown-command>`
- WHEN it runs
- THEN argparse SHALL exit 2

### Requirement: Recovery replay executes returned calls (PB-03)

Recovery tests SHALL key off the deterministic hint VALUES that the production gates pin for each refusal, plus the boundary-visible `output` message, and SHALL execute the hinted arguments as a second call. `next` itself is NOT client-visible for `sofer_publish_confirm`/`sofer_init` because the declared `output_schema`s project envelopes and do not list `next` (re-audited: `sofer_auth_status` is the only tool whose schema declares `next`, proving the projection is the cause); surfacing `next` would require a production schema change, outside this suite's scope — the hint-VALUE substitution IS the deliberate recovery contract. Replayed calls SHALL be asserted to reach a DIFFERENT gate than the refusal, or `ok:True` — not merely that the hint is present.
(Previously: framed as "executes the documented hint arguments" with the boundary projection as a parenthetical correction.)

#### Scenario: publish_confirm replay

- GIVEN `sofer_publish_confirm` refused at the risk gate (`ok:False`; the boundary-visible `output` message states `acknowledge_risk=True` is required)
- WHEN the documented hint VALUE `{"acknowledge_risk": True}` is replayed as a second call with the token still present
- THEN the call SHALL be refused at the approval gate — the NEXT check after the risk gate — proving the risk gate accepted the acknowledgment

#### Scenario: init refusal replay

- GIVEN `sofer_init` returning a boundary-visible refusal (`config_errors`/`output` state the required correction: file-exists → replay `{"force": True}`; name-empty → replay a non-empty name)
- WHEN the documented hint VALUES are replayed
- THEN the intended branch SHALL be reached (a different gate or `ok:True`)

### Requirement: Config-state scenario coverage (PB-04)

> Modified by `fix-dataset-identity-context` (archived 2026-09-04).

The suite SHALL cover empty config, existing config, greenfield, triage, nested output, malformed config, and delivery handoff, using real config files and public outputs (e.g., `tests/fixtures/mcp-happy-path/`), not dataclass or private-helper construction alone. The nested-output proof SHALL launch the REAL MCP process over stdio with a parent server root and an intended child cwd — `build_server(root=child)` or imported-function tests are insufficient for the parent/child identity contract.

(Previously: the nested-output scenario was proven only via `monkeypatch.chdir` + `build_server`.)

#### Scenario: Empty config

- GIVEN a TOML with no `[[file]]`
- WHEN `sofer_validate` runs via the client
- THEN it SHALL return the documented empty-config result

#### Scenario: Existing config

- GIVEN a TOML with registered files
- WHEN the pipeline runs
- THEN validate SHALL pass without re-registration

#### Scenario: Greenfield bootstrap

- GIVEN an empty directory under the server root
- WHEN `sofer_init` then `sofer_scan_apply` run
- THEN files SHALL be registered and `sofer_validate` SHALL pass

#### Scenario: Triage

- GIVEN unregistered files
- WHEN `sofer_scan_dry_run` runs
- THEN the preview SHALL list candidates without copying files or writing the TOML

#### Scenario: Nested output CWD

- GIVEN a parent server root and a dataset in a nested directory
- WHEN dataset tools run with the nested CWD
- THEN writes SHALL land under the nested dataset, not the parent root

#### Scenario: Real-process parent-root launch, cwd omitted fails closed

- GIVEN the second module-scoped stdio fixture (PB-09-compliant) spawning the real `sofer-mcp` process with server root = parent dir and an existing child dataset dir, and a live CWD at the parent root
- WHEN `sofer_init(name="test", user="emiliodavola")` runs over stdio with `cwd` omitted
- THEN the call SHALL be refused with an input-required error naming the `cwd` argument
- AND NO `parent/test.toml` SHALL be written and no `raw/` SHALL be created at the parent

#### Scenario: Real-process parent-root launch, cwd=child anchors identity

- GIVEN the same parent-root stdio fixture and the intended child dataset dir `child/`
- WHEN `sofer_init(name="test", user="emiliodavola", cwd="child")` runs over stdio
- THEN `child/test.toml` and `child/raw/` SHALL exist, `parent/test.toml` SHALL NOT
- AND the envelope SHALL report absolute `config_path` `child/test.toml` and `dataset_root` `child`

### Requirement: Complete-run gate (PB-05)

CI SHALL keep the complete suite (`uv run pytest -v`) as the test gate; no focused-only command SHALL replace it.

#### Scenario: CI runs the complete suite

- GIVEN `.github/workflows/ci.yml`
- WHEN the test job is inspected
- THEN it SHALL invoke the full suite, not a focused subset

#### Scenario: No focused-only gate

- GIVEN the CI test invocation
- WHEN compared with the developer command `uv run pytest tests/ -q`
- THEN both SHALL cover the complete suite

### Requirement: Deterministic and offline (PB-06)

The suite SHALL be deterministic, run offline, and SHALL NOT require HF credentials; network-bound tools SHALL monkeypatch `publish._api`.

#### Scenario: Offline happy path

- GIVEN `publish._api` monkeypatched
- WHEN validate → prepare → codebook → profile → render → publish run
- THEN every step SHALL pass with no real network access

#### Scenario: No credentials required

- GIVEN `HF_TOKEN` absent from the environment
- WHEN the suite runs
- THEN it SHALL pass without credential-dependent skips or failures

### Requirement: Quality gates (PB-07)

After the change, `uv run pytest tests/ -q`, `uv run ruff check src/ tests/`, `uv run mypy src/`, and `git diff --check` SHALL all pass. New test helpers SHALL be type-annotated even though mypy excludes `tests/`.

#### Scenario: Full suite passes

- GIVEN the complete repository
- WHEN `uv run pytest tests/ -q` runs
- THEN all tests SHALL pass and the pre-existing count SHALL not regress

#### Scenario: Lint, types, whitespace

- GIVEN the change applied
- WHEN ruff, mypy, and `git diff --check` run
- THEN all three SHALL pass

### Requirement: SOFER_TRACE.md untouched (PB-08)

No operation of the suite, fixtures, or CI SHALL read, modify, or stage `SOFER_TRACE.md`.

#### Scenario: Untracked trace file untouched

- GIVEN `SOFER_TRACE.md` untracked at the repo root
- WHEN the suite and gates run
- THEN the file SHALL remain unchanged and unstaged

### Requirement: Shared fixtures and per-test server isolation (PB-09)

> Modified by `fix-dataset-identity-context` (archived 2026-09-04).

Boundary fixtures/helpers SHALL live in `tests/conftest.py` — a stdio server fixture, a CLI subprocess helper with cp1252 env, and a Root-unwrap `_mcp_payload` helper — and SHALL be reused across modules, not duplicated. Each test SHALL build its own server via `build_server()` because `_SERVER_ROOT`/`_APPROVAL_PHRASE` are per-process globals. Stdio spawns SHALL use one shared fixture per module to bound wall-clock; a SECOND module-scoped stdio fixture SHALL be permitted for the parent-root/child-cwd layout, keeping one spawn per module per fixture. Async SHALL use `asyncio.run`; no new dependencies and no pytest-asyncio SHALL be added.

(Previously: exactly one module-scoped stdio fixture was specified.)

#### Scenario: One server per test

- GIVEN two tests in one process
- WHEN each calls `build_server()`
- THEN no server-root or approval-phrase state SHALL leak between them

#### Scenario: Shared conftest helpers

- GIVEN `tests/conftest.py` helpers
- WHEN used by `tests/test_mcp_process.py` and sibling modules
- THEN no module SHALL re-implement the same boundary helper

#### Scenario: Lean process spawns

- GIVEN the process-boundary module
- WHEN stdio tests run
- THEN a single module-scoped server fixture SHALL be spawned, not one per test