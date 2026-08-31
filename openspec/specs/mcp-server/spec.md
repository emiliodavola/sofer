# mcp-server Specification

## Purpose

Distribution contract for sofer's MCP server: exposes the CLI's deterministic pipeline (validate → prepare → codebook → profile → render → publish) as MCP tools, resources, and prompts over stdio, so an agent can operate sofer while humans authorize network writes. The server is a thin adapter over existing domain functions — it never re-implements logic, never calls an LLM, and ships no remote transport in v1.

## Requirements

### Requirement: Transport and entry point (MSP-R01)

> Added by change `sofer-mcp-server` (archived 2026-08-28).

`[project.scripts]` SHALL declare `sofer-mcp = "sofer.mcp_server:main"`; running `sofer-mcp` SHALL start an MCP stdio server speaking JSON-RPC 2.0 over stdin/stdout, supporting `initialize`, `tools/list`, `tools/call`, `resources/list`+`read`, `prompts/list`+`get`. There SHALL be no remote/streamable-http transport in v1. The server SHALL never call an LLM; its only network access SHALL be the HF upload path inside the confirm tool.

#### Scenario: Stdio handshake with clean framing

- GIVEN sofer installed with the `mcp` extra
- WHEN `sofer-mcp` runs as a subprocess and `initialize` is sent
- THEN a valid JSON-RPC response SHALL be received
- AND no stray bytes SHALL appear on stdout outside the framing

#### Scenario: No LLM, no remote transport

- GIVEN the running server
- WHEN an agent drives the full pipeline over stdio
- THEN no LLM endpoint SHALL be contacted
- AND no non-stdio transport SHALL be exposed

---

### Requirement: Import without the extra fails clearly (MSP-R02)

> Added by change `sofer-mcp-server` (archived 2026-08-28). Modified by `feat-mcp-auto-install` (2026-08-31).

`sofer.mcp_server` SHALL import on lean install. `fastmcp>=3.4,<4` SHALL be in `dependencies` so `pip install "sofer @ git+..."` and `uv tool install "sofer @ git+..."` SHALL install `fastmcp` and `sofer-mcp --help` SHALL succeed. `mcp` alias `["fastmcp>=3.4,<4"]` SHALL remain one minor. Guard in `mcp_server.py` SHALL stay degraded-only with `pip`+`uv tool` and `sofer[mcp] @ git+...`.

(Previously: base stayed lean — `fastmcp` not a core dep; import raised `ImportError` to `pip install 'sofer[mcp]'`.)

#### Scenario: Lean install includes fastmcp

- GIVEN clean env
- WHEN `uv tool install "sofer @ git+https://github.com/emiliodavola/sofer.git@vX.Y.Z" --force` runs
- THEN `fastmcp` SHALL be installed and `sofer-mcp --help` SHALL exit 0

#### Scenario: Alias sofer[mcp] @ URL still works

- GIVEN same tag
- WHEN `pip install "sofer[mcp] @ git+https://github.com/emiliodavola/sofer.git@vX.Y.Z"` runs
- THEN install SHALL succeed and `import sofer.mcp_server` SHALL succeed

#### Scenario: Guard retained with pip+uv+PEP 508 message

- GIVEN degraded install (`fastmcp` absent)
- WHEN `import sofer.mcp_server` executes
- THEN `ImportError` SHALL mention `pip`, `uv tool`, `sofer[mcp] @ git+https://` and NOT `git+...[mcp]`

#### Scenario: import fastmcp succeeds

- GIVEN lean install
- WHEN `python -c "import fastmcp"` runs
- THEN it SHALL succeed

#### Scenario: Wheel METADATA unconditional

- GIVEN built wheel
- WHEN METADATA `Requires-Dist` inspected
- THEN `fastmcp>=3.4,<4` SHALL appear without `extra == 'mcp'`

#### Scenario: uv.lock unconditional

- GIVEN regenerated `uv.lock`
- WHEN `sofer` entry inspected
- THEN `fastmcp` SHALL be under `dependencies` not `optional-dependencies`

#### Scenario: Existing tests green

- GIVEN repo
- WHEN `uv run pytest tests/test_mcp_server.py tests/test_mcp_registration.py -q` runs
- THEN all SHALL pass

---

### Requirement: Tool roster and schema contract (MSP-R03)

> Added by change `sofer-mcp-server` (archived 2026-08-28). Modified by `mcp-dx-audit-surface` (2026-08-31).

Server SHALL expose 14 callables: `sofer_validate, sofer_prepare, sofer_publish, sofer_publish_confirm, sofer_codebook, sofer_codebook_all, sofer_profile, sofer_profile_all, sofer_render, sofer_render_all, sofer_scan_dry_run, sofer_scan_apply, sofer_init, sofer_auth_status`. Every param SHALL be `Annotated[Field(description)]` non-empty (10.1); `target` SHALL be `Literal["local"]`/`Literal["hf"]` enum (10.5); `output` SHALL split to `output_file` vs `output_dir` (10.7); `all_files` removed — batch via `*_all` (10.6); `no_checks` → `run_checks:bool=true` (10.9); every tool SHALL have `annotations` and typed `output_schema`. (Previously: 11 callables, polymorphic profile/render, free-string target, dual-typed output, bare params, generic schema.)

#### Scenario: Constrained schemas

- GIVEN `tools/list`
- WHEN inspected
- THEN count SHALL be 14, `target` SHALL have `enum`, no tool SHALL expose `all_files`/`no_checks`/`output` (only `output_file`/`output_dir`/`run_checks`), and every `properties[*].description` SHALL be non-empty

#### Scenario: Annotations and output_schema typed

- GIVEN `tools/list`
- WHEN inspected
- THEN no `annotations` SHALL be null and each `output_schema` SHALL declare `ok:bool, exit_code:int, output:str` plus specific fields

---

### Requirement: Tool safety contract (MSP-R04)

> Added by change `sofer-mcp-server` (archived 2026-08-28). Modified by `mcp-dx-audit-surface` (2026-08-31).

Every tool description SHALL be ≤3 sentences plus `When to use:` (≤1 sentence) and `Example:` single call, SHALL include `Requires`/`Next`, and SHALL NOT contain `MSP-R*`, `CF-*`, or `UNTRUSTED`. `UNTRUSTED` SHALL appear exactly once in server `instructions`, not per-tool (10.10). (Previously: ~280-word walls with MSP refs and 11× UNTRUSTED duplication.)

#### Scenario: Descriptions concise and UNTRUSTED single-sourced

- GIVEN `tools/list` descriptions and `instructions`
- WHEN measured
- THEN pre-`When to use:` sentences SHALL be ≤3, no description SHALL contain `MSP-R` or `UNTRUSTED`, and `instructions` SHALL contain exactly one `UNTRUSTED` occurrence

---

### Requirement: Publish confirmation gate (MSP-R05)

> Added by change `sofer-mcp-server` (archived 2026-08-28).

`sofer_publish` SHALL default to `dry_run=True` and SHALL never write to HF under any parameter combination: `target="hf"` with `dry_run=False` SHALL raise a typed error directing to `sofer_publish_confirm`. `sofer_publish_confirm` SHALL be the ONLY callable that writes to HF, SHALL require `HF_TOKEN` (clear typed error before any network call), and SHALL gate on the quality report. There SHALL be no implicit state coupling: each call is independent; no session state carries between publish and confirm.

`sofer_publish_confirm` SHALL enforce a fail-closed authorization ladder: it SHALL require `acknowledge_risk=True` (default `False`; a call without it SHALL be refused with a typed error, never a warning); SHALL require `acknowledge_confidential=True` when the config's `[meta] confidential` is true; SHALL accept an optional host-configured `approval_phrase` (from `build_server(root, approval_phrase)` or the `SOFER_MCP_APPROVAL_PHRASE` environment variable) and SHALL refuse on absent or mismatched phrase, compared with a constant-time comparison (`hmac.compare_digest`). The confirm envelope SHALL expose `confidential`, both acknowledgment flags, `skipped_protected`, and `partial`. Empty-string and absent `HF_TOKEN` SHALL fail identically; `HF_HUB_TOKEN` SHALL be accepted as an alias. The quality gate SHALL run before the token check (offline, deterministic fail).

#### Scenario: Publish dry-run returns a plan without network

- GIVEN a valid config
- WHEN `sofer_publish` runs with defaults
- THEN the result SHALL be a dry-run diff plan
- AND no HF network call SHALL occur

#### Scenario: Publish refuses hf without confirm

- GIVEN `sofer_publish` called with `target="hf", dry_run=False`
- WHEN the call executes
- THEN a typed error SHALL be raised naming `sofer_publish_confirm`

#### Scenario: Confirm uploads with HF_TOKEN

- GIVEN `HF_TOKEN` set and a passing quality report
- WHEN `sofer_publish_confirm` runs
- THEN the package SHALL upload via `publish._api`

#### Scenario: Confirm errors without HF_TOKEN

- GIVEN `HF_TOKEN` absent
- WHEN `sofer_publish_confirm` runs
- THEN a clear typed error SHALL be raised before any network call

---

### Requirement: Scan non-interactivity (MSP-R06)

> Added by change `sofer-mcp-server` (archived 2026-08-28).

`sofer_scan_apply` SHALL never prompt — the explicit call IS the confirmation. It SHALL chain the pure scanner functions `discover_files → check_flatten_collisions → merge_entries → copy_files → write_toml`, honoring `force`.

#### Scenario: Apply never blocks on input

- GIVEN a TOML directory with unregistered files and stdin closed
- WHEN `sofer_scan_apply` runs
- THEN files SHALL be copied and the TOML updated
- AND the call SHALL never block on `input()`

---

### Requirement: Resources (MSP-R07)

> Added by change `sofer-mcp-server` (archived 2026-08-28).

The server SHALL expose `sofer://dataset/{config_path}` (raw TOML text), `sofer://codebook/{data_file}` (codebook markdown generated on demand, pure read), and `sofer://metadata/{data_file}` (metadata.yaml content when present). Plain artifacts SHALL be read via `file://` URIs. The config path SHALL be the identity — no name-based scheme.

All resource URIs and tool path arguments SHALL be contained under the server root: paths SHALL be resolved, canonicalized, and verified inside the root (rejecting `..` traversal, absolute paths outside root, and symlink escapes) with per-resource extension allow-lists; violations SHALL raise a typed `PathOutsideRootError`. Resource reads SHALL honor a size guard (`agent_resource_max_bytes`, default 50 MB) before reading. The `file://` boundary SHALL be documented as governed by the MCP client's own permission model — the server SHALL NOT add new escape hatches beyond it.

#### Scenario: Dataset resource returns raw TOML

- GIVEN a config path
- WHEN `sofer://dataset/{config_path}` is read
- THEN the raw TOML text SHALL be returned

#### Scenario: Codebook resource generates on demand

- GIVEN a data file
- WHEN `sofer://codebook/{data_file}` is read
- THEN a markdown codebook SHALL be returned without writing anything

#### Scenario: Metadata resource when present

- GIVEN a profiled dataset
- WHEN `sofer://metadata/{data_file}` is read
- THEN the metadata.yaml content SHALL be returned
- AND a missing file SHALL produce a clear resource error

---

### Requirement: Prompts (MSP-R08)

> Added by change `sofer-mcp-server` (archived 2026-08-28).

The server SHALL expose 3 user-controlled workflow templates — `prepare_dataset`, `assess_dataset`, `finalize_and_publish` — encoding the validate → prepare → confirm-before-publish idiom. Any publish step SHALL instruct calling `sofer_publish` (dry-run) and stopping for human approval before `sofer_publish_confirm`.

#### Scenario: Prompt list shows 3 templates

- GIVEN the server running
- WHEN `prompts/list` is called
- THEN exactly 3 prompts SHALL be returned

#### Scenario: Confirm-before-publish idiom enforced

- GIVEN each prompt's template
- WHEN it is inspected
- THEN every HF-publish step SHALL mandate a human-approval stop before the confirm call

---

### Requirement: Confidential/PII surfacing (MSP-R09)

> Added by change `sofer-mcp-server` (archived 2026-08-28).

Tool outputs SHALL include the config's `meta.confidential` flag and detected PII column names. Resource descriptions SHALL note that sample content may contain PII. No redaction pipeline exists in v1.

#### Scenario: Confidential flag surfaced

- GIVEN a config with `confidential = true`
- WHEN `sofer_validate` returns
- THEN the result SHALL surface the confidential flag

#### Scenario: Detected PII surfaced

- GIVEN a dataset with a detected email column
- WHEN `sofer_profile` returns
- THEN the result SHALL list that column's PII finding

---

### Requirement: Config contract (MSP-R10)

> Added by change `sofer-mcp-server` (archived 2026-08-28).

Every dataset tool SHALL take `config: str` (TOML path) as its first parameter; `DatasetConfig.from_toml` SHALL re-anchor `config.reload(toml_dir)` (verified at model.py:355). Codebook and scan tools SHALL NOT silently apply `default_config_name` — agents pass explicit paths. Relative paths SHALL resolve against the client cwd (stdio server inherits it). Codebook tools SHALL inject post-reload `config.CSV_DELIMITER`/`config.CSV_ENCODING` — never the hardcoded `";"`/`"utf-8-sig"` debt in `codebook.generate` (rule-3 fix).

Every dataset tool SHALL self-anchor config state per call to avoid cross-call module-state pollution: scan tools SHALL reload from the config's directory before reading output directories; `sofer_codebook(path)`, `sofer_profile(dataset)`, and `sofer_render(package)` SHALL anchor on their input's directory. `sofer_codebook_all` SHALL use `cfg.csv_delimiter`/`cfg.csv_encoding` from the dataset's `[meta]` (the authoritative source), not the process-global `config.CSV_DELIMITER`. `sofer_prepare` SHALL pass `run_checks=not no_checks` to match CLI parity.

#### Scenario: Tool config resolves per dataset directory

- GIVEN a TOML under a tree with `[tool.sofer]` overrides
- WHEN any dataset tool calls `DatasetConfig.from_toml(config)`
- THEN `config.reload(toml_dir)` SHALL rebind module constants before the domain function runs

#### Scenario: Codebook honors configured delimiter/encoding

- GIVEN `csv_delimiter = ","` in `[tool.sofer]`
- WHEN `sofer_codebook` runs on a CSV
- THEN the codebook SHALL reflect the configured delimiter, not the hardcoded default

#### Scenario: No silent default config name

- GIVEN a codebook or scan tool call without a config argument
- THEN the call SHALL fail on the missing required `config` parameter
- AND `default_config_name` SHALL never be applied implicitly

---

### Requirement: Offline testability (MSP-R11)

> Added by change `sofer-mcp-server` (archived 2026-08-28).

The MCP server SHALL be fully testable offline with no LLM: unit tests on tool functions; in-memory client round-trips of `tools/list` + `tools/call` verifying JSON-Schema generation; a stdio smoke test spawning `sofer-mcp` and asserting clean JSON-RPC framing; network tools SHALL monkeypatch `publish._api`; config isolation SHALL use the `restore_tool_config` fixture. The existing suite SHALL stay green.

#### Scenario: In-memory client round-trips tools

- GIVEN an in-memory MCP client connected to the server
- WHEN `tools/list` and one `tools/call` execute
- THEN the call SHALL return the structured result
- AND the listed schema SHALL validate the call's parameters

#### Scenario: Stdio smoke test asserts clean framing

- GIVEN a spawned `sofer-mcp` subprocess
- WHEN `initialize → tools/list → tools/call` run
- THEN every response SHALL be valid JSON-RPC with no stray stdout

#### Scenario: Network tools run offline via seam

- GIVEN `publish._api` monkeypatched
- WHEN `sofer_publish_confirm` runs
- THEN the fake API SHALL receive the upload call and no real network SHALL occur

#### Scenario: Existing suite unchanged

- GIVEN the full test suite
- WHEN it runs after the change
- THEN all pre-existing tests SHALL still pass

#### Scenario: Multi-call config determinism

- GIVEN dataset A with `output_dir="cache-a"` and dataset B with `output_dir="cache-b"`
- WHEN `sofer_scan_apply` runs on B after `sofer_validate` ran on A
- THEN B's TOML registers `local="cache-b/..."` and files land in `cache-b`
- AND no residue from A's config state affects B

#### Scenario: Confirm refuses without authorization

- GIVEN a valid config and `HF_TOKEN` set
- WHEN `sofer_publish_confirm` runs with `acknowledge_risk=False`
- THEN the call SHALL be refused with a typed error
- AND no network call SHALL occur

#### Scenario: Confirm enforces path containment

- GIVEN a config argument, resource URI, or `[[file]]` local resolving outside the server root
- WHEN the corresponding tool or resource is invoked
- THEN a typed `PathOutsideRootError` SHALL be raised or the call SHALL return `ok:False` with `config_errors`
- AND no file outside the root SHALL be read or written

---

### Requirement: Packaging and documentation (MSP-R12)

> Added by change `sofer-mcp-server` (archived 2026-08-28). Modified by `feat-mcp-auto-install` (2026-08-31).

`pyproject.toml` SHALL declare `fastmcp>=3.4,<4` in `dependencies` and `sofer-mcp = "sofer.mcp_server:main"`; MAY retain `mcp` alias. READMEs SHALL document Install + AI/MCP with correct PEP 508 `name[extra] @ URL`, `uv tool` and `uvx --with`, and flip intro to included-by-default.

(Previously: only `optional-dependencies mcp` + script; README showed `pip install 'sofer[mcp]'`.)

#### Scenario: Wheel script and Requires-Dist

- GIVEN built wheel
- WHEN `entry_points.txt` + METADATA inspected
- THEN `sofer-mcp = sofer.mcp_server:main` and unconditional `fastmcp>=3.4,<4` SHALL be present

#### Scenario: Alias optional

- GIVEN wheel METADATA
- WHEN `Provides-Extra` inspected
- THEN `mcp` MAY be present mapping to `fastmcp>=3.4,<4; extra == 'mcp'`

#### Scenario: README Install correct

- GIVEN `README.md` Install
- WHEN inspected
- THEN it SHALL show `sofer @ git+...` and `sofer[mcp] @ git+...`, `uv tool install "sofer @ git+..."` and `uvx --from git+... --with "sofer[mcp]" sofer-mcp --help`

#### Scenario: README AI/MCP fixed

- GIVEN `README.md` AI/MCP section
- WHEN inspected
- THEN `git+...[mcp]` SHALL NOT appear, `sofer[mcp] @ git+...` SHALL, intro SHALL say "included by default"

#### Scenario: README_ES mirrors README (§13)

- GIVEN `README.md` + `README_ES.md`
- WHEN inspected
- THEN headings/order SHALL match, commands identical English, fixes in both same commit

---

### Requirement: Single error envelope with error_code enum (10.3)

> Added by change `mcp-dx-audit-surface` (archived 2026-08-31).

System MUST return expected failures as `{"ok":false,"error_code":E,"message":str,"next":obj,"config_errors":[...]}` and MUST NOT throw `McpError` for them; only transport/containment MAY throw typed `PathOutsideRootError`/`PublishRefusedError`. `error_code` MUST be `CONFIG_ERROR|VALIDATION_FAILED|QUALITY_GATE_FAILED|PUBLISH_RISK_NOT_ACKD|PUBLISH_CONFIDENTIAL_NOT_ACKD|PUBLISH_APPROVAL_REQUIRED|PATH_OUTSIDE_ROOT|TARGET_INVALID`.

#### Scenario: Refusal returns envelope with next

- GIVEN `sofer_publish_confirm(acknowledge_risk=false)`
- WHEN executed
- THEN return `ok:false, error_code=PUBLISH_RISK_NOT_ACKD, next={acknowledge_risk:true}` without throw

#### Scenario: Containment still throws

- GIVEN path outside server root
- WHEN any tool/resource called
- THEN raise `PathOutsideRootError` (transport maps to isError)

---

### Requirement: Chain learnable from tools/list (10.4)

> Added by change `mcp-dx-audit-surface` (archived 2026-08-31).

Server `instructions` MUST contain phased diagram `Phase 0 Bootstrap (conditional) → Phase 1 Build → Phase 2 Publish` and each tool description MUST include `Requires:` and `Next:`. `tools/list` alone SHALL teach `init→scan(if greenfield)→validate→prepare→codebook_all→profile_all→render_all→publish(dry_run)→STOP→publish_confirm`.

#### Scenario: Chain visible without prompts/list

- GIVEN `initialize` + `tools/list`
- WHEN inspected without `prompts/list` or README
- THEN `instructions` SHALL contain Bootstrap/Build/Publish headings and each tool SHALL list Requires/Next

---

### Requirement: Auth status preflight read-only (10.8)

> Added by change `mcp-dx-audit-surface` (archived 2026-08-31).

System MUST expose `sofer_auth_status(config)` with `annotations.readOnlyHint:true`, returning `{token:"present"|"missing", confidential:bool, requires_approval_phrase:bool, next:obj}` without leaking token/phrase values or requiring network.

#### Scenario: Preflight without publish

- GIVEN config `confidential=true`, no `HF_TOKEN`
- WHEN `sofer_auth_status(config)` called
- THEN return `token=missing, confidential=true` and `next` lists `acknowledge_risk` and `acknowledge_confidential` steps

---

### Requirement: Bootstrap Phase 0 conditional canonical

> Added by change `mcp-dx-audit-surface` (archived 2026-08-31).

`init→scan` MUST be REQUIRED when no TOML or `[[file]]` empty, OPTIONAL otherwise. Prior `Not part of canonical` phrasing at `mcp_server.py:1283,1347,1430` and in instructions/docs MUST be removed and replaced with Phase 0 wording.

#### Scenario: Greenfield phrasing

- GIVEN `instructions` and scan/init descriptions
- WHEN inspected
- THEN they SHALL state `Phase 0: init→scan REQUIRED for greenfield` and contain zero occurrences of `Not part of canonical`

---

### Requirement: Live happy path fixtures and docs sync (10.11,10.12)

> Added by change `mcp-dx-audit-surface` (archived 2026-08-31).

System MUST ship fixtures `tests/fixtures/mcp-happy-path/` plus offline `tests/test_mcp_schema.py` asserting 10.1/10.2/10.5/10.7/10.10 via `tools/list` and running `validate→prepare→codebook_all→profile_all→render_all→publish(dry_run)→auth_status` with `publish._api` monkeypatched. `README.md`+`README_ES.md` MUST mirror phased diagram in same commit.

#### Scenario: Fixture chain offline

- GIVEN fixtures present
- WHEN happy-path sequence runs offline
- THEN each step SHALL return `ok:true` and `publish` SHALL be `dry_run:true`

#### Scenario: READMEs in sync

- GIVEN `README.md` and `README_ES.md`
- WHEN inspected
- THEN both SHALL contain Phase 0→1→2 diagram and headings/order SHALL match
