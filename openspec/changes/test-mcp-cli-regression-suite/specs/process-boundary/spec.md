# process-boundary Specification

## Purpose

Contracts for the test-only regression suite that pins sofer's MCP server and CLI through the same boundaries real agents use: in-process FastMCP `Client(server)`, real stdio transport, and executable CLI subprocesses. The suite SHALL make `tools/list`, schema serialization, process CWD, Windows console encoding, and CLI output regressions visible. No production behavior is specified here — the contracts these tests pin are already stated by the `mcp-server` (MSP-R01/R02) and `cli` (CLI-R01/R02) specs.

## Requirements

### Requirement: Registered MCP tools via public boundary (PB-01)

The suite SHALL exercise registered MCP tools through `fastmcp.Client(server)` (in-process) or the real stdio transport, and SHALL NOT rely on imported tool functions alone. Direct-call tests for `sofer_publish_confirm`, `sofer_init`, and `sofer_validate` in `tests/test_mcp_server.py`, plus `test_offline_happy_path` in `tests/test_mcp_schema.py`, SHALL be routed through `Client(server)`. The suite SHALL verify `tools/list`, JSON-Schema generation, envelopes, and a `tools/call` round-trip. New tests SHALL NOT add boundary-hiding direct calls for registered tools.

#### Scenario: tools/list and call via in-process client

- GIVEN `build_server()` and an in-process `Client(server)`
- WHEN `tools/list` and one `tools/call` execute
- THEN 14 callables SHALL be listed and the call SHALL return the documented envelope

#### Scenario: publish/init/validate through the client

- GIVEN the happy-path fixture
- WHEN `sofer_publish_confirm`, `sofer_init`, and `sofer_validate` run via `Client(server)`
- THEN each SHALL return the same envelope shape as the documented public contract

#### Scenario: Stdio transport with clean framing

- GIVEN the server spawned as a subprocess
- WHEN `initialize → tools/list → tools/call` run
- THEN every response SHALL be valid JSON-RPC with no stray stdout bytes

#### Scenario: No new direct-call proofs

- GIVEN the added and converted tests
- WHEN the diff is inspected
- THEN no registered tool SHALL be imported and called directly to prove boundary behavior

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

Recovery tests SHALL execute the `next` hint returned by a refusal and SHALL assert the replayed (second) call reaches the intended branch — not merely that the hint is present.

#### Scenario: publish_confirm replay

- GIVEN `sofer_publish_confirm` refused with `next={acknowledge_risk:true}`
- WHEN the `next` arguments are executed as a second call
- THEN the call SHALL proceed past the risk gate to the next check

#### Scenario: init refusal replay

- GIVEN `sofer_init` returning a refusal
- WHEN the corrected arguments are replayed
- THEN the intended branch SHALL be reached

### Requirement: Config-state scenario coverage (PB-04)

The suite SHALL cover empty config, existing config, greenfield, triage, nested output, malformed config, and delivery handoff, using real config files and public outputs (e.g., `tests/fixtures/mcp-happy-path/`), not dataclass or private-helper construction alone.

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

#### Scenario: Malformed config

- GIVEN an unparseable TOML
- WHEN `sofer_validate` runs
- THEN it SHALL return a refusal envelope with `config_errors`

#### Scenario: Delivery handoff

- GIVEN a validated package and `publish._api` monkeypatched
- WHEN `sofer_publish(dry_run=True)` then `sofer_publish_confirm` run
- THEN the plan SHALL be returned and the confirm SHALL reach the upload branch

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

Boundary fixtures/helpers SHALL live in `tests/conftest.py` — a stdio server fixture, a CLI subprocess helper with cp1252 env, and a Root-unwrap `_mcp_payload` helper — and SHALL be reused across modules, not duplicated. Each test SHALL build its own server via `build_server()` because `_SERVER_ROOT`/`_APPROVAL_PHRASE` are per-process globals. Stdio spawns SHALL use one shared fixture per module to bound wall-clock. Async SHALL use `asyncio.run`; no new dependencies and no pytest-asyncio SHALL be added.

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