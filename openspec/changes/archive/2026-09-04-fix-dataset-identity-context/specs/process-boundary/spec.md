# Delta for process-boundary

## MODIFIED Requirements

### Requirement: Config-state scenario coverage (PB-04)

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

### Requirement: Shared fixtures and per-test server isolation (PB-09)

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