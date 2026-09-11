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

> Added by change `sofer-mcp-server` (archived 2026-08-28). Modified by `mcp-dx-audit-surface` (archived 2026-08-31). Modified by `fix-sofer-init-cwd-windows-todo` (archived 2026-08-31) — adds optional `cwd` to `sofer_init`. Modified by `fix-dataset-identity-context` (archived 2026-09-04) — `sofer_init` output_schema declares `config_path`/`dataset_root` per INIT-03.

Server SHALL expose 14 callables: `sofer_validate, sofer_prepare, sofer_publish, sofer_publish_confirm, sofer_codebook, sofer_codebook_all, sofer_profile, sofer_profile_all, sofer_render, sofer_render_all, sofer_scan_dry_run, sofer_scan_apply, sofer_init, sofer_auth_status`. Every param SHALL be `Annotated[Field(description)]` non-empty (10.1); `target` SHALL be `Literal["local"]`/`Literal["hf"]` single-value (const or enum) (10.5); `output` SHALL split to `output_file` vs `output_dir` (10.7); `all_files` removed — batch via `*_all` (10.6); `no_checks` → `run_checks:bool=true` (10.9); every tool SHALL have `annotations` and typed `output_schema`. `sofer_init` additionally exposes `cwd: str | None = None` per INIT-02 and its `output_schema` SHALL declare `config_path`/`dataset_root` (absolute strings) per INIT-03.

(Previously: `sofer_init` schema carried no identity fields; 11 callables, polymorphic profile/render, free-string target, dual-typed output, bare params, generic schema; then 14 callables without `cwd`.)

#### Scenario: Constrained schemas

- GIVEN `tools/list`
- WHEN inspected
- THEN count SHALL be 14, `target` SHALL have `const` or `enum` single value, no tool SHALL expose `all_files`/`no_checks`/`output` (only `output_file`/`output_dir`/`run_checks`), and every `properties[*].description` SHALL be non-empty

#### Scenario: Annotations and output_schema typed

- GIVEN `tools/list`
- WHEN inspected
- THEN no `annotations` SHALL be null and each `output_schema` SHALL declare `ok:bool, exit_code:int, output:str` plus specific fields

#### Scenario: sofer_init cwd schema

- GIVEN `tools/list` `sofer_init`
- WHEN inspected
- THEN `cwd` SHALL be optional `str`, default `None`, and `C:/Windows` SHALL raise `PathOutsideRootError`

#### Scenario: sofer_init identity fields in schema

- GIVEN `tools/list` `sofer_init` `output_schema`
- WHEN inspected
- THEN `config_path` and `dataset_root` SHALL be declared as string properties and SHALL appear in the call envelope

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

`sofer_publish_confirm` SHALL enforce a fail-closed authorization ladder: it SHALL require `acknowledge_risk=True` (default `False`; a call without it SHALL be refused with a typed error, never a warning); SHALL require `acknowledge_confidential=True` when the config's `[meta] confidential` is true; SHALL require a host-configured `approval_phrase` (from `build_server(root, approval_phrase)` or the `SOFER_MCP_APPROVAL_PHRASE` environment variable) and SHALL refuse on absent or mismatched phrase, compared with a constant-time comparison (`hmac.compare_digest`). When the server has NO phrase configured — including an empty or whitespace-only value, which SHALL be normalized to unconfigured — `sofer_publish_confirm` SHALL refuse with `PUBLISH_APPROVAL_NOT_CONFIGURED` and never reach the upload; the acknowledgment booleans alone are never sufficient. The confirm envelope SHALL expose `confidential`, both acknowledgment flags, `skipped_protected`, and `partial`. Empty-string and absent `HF_TOKEN` SHALL fail identically; `HF_HUB_TOKEN` SHALL be accepted as an alias. The quality gate SHALL run before the token check (offline, deterministic fail).

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

> Added by change `sofer-mcp-server` (archived 2026-08-28). Modified by `2026-09-11-fix-status-resource` (archived 2026-09-11).

The server SHALL expose `sofer://dataset/{config_path}` (raw TOML text), `sofer://codebook/{data_file}` (codebook markdown generated on demand, pure read), and `sofer://metadata/{data_file}` (metadata.yaml content when present). Plain artifacts SHALL be read via `file://` URIs. The config path SHALL be the identity — no name-based scheme.

All resource URIs and tool path arguments SHALL be contained under the server root: paths SHALL be resolved, canonicalized, and verified inside the root (rejecting `..` traversal, absolute paths outside root, and symlink escapes) with per-resource extension allow-lists; violations SHALL raise a typed `PathOutsideRootError`. Resource reads SHALL honor a size guard (`agent_resource_max_bytes`, default 50 MB) before reading. The `file://` boundary SHALL be documented as governed by the MCP client's own permission model — the server SHALL NOT add new escape hatches beyond it.

The server SHALL additionally expose ONE **static** resource `sofer://status` — no path variables, registered so FastMCP lists it under `resources/list` (NOT under `resources/templates/list`, which is where the three URI templates above appear) — returning a JSON posture object with exactly six fields:

- `approval_configured: bool` — true only when the server has a non-blank approval phrase set (`_APPROVAL_PHRASE is not None`, identical semantics to the `sofer_auth_status` envelope);
- `phrase_source: "env"|"explicit"|"none"` — the configuration path that produced `approval_configured`, captured once at `build_server` and never re-derived; invariant `phrase_source == "none"` ⟺ `approval_configured is False` SHALL hold;
- `root: str` — the resolved absolute containment root (the same full path every path-bearing tool/resource anchors on; consistent with `sofer_init`'s absolute `config_path`/`dataset_root`);
- `version: str` — the installed package version, non-empty, never raises;
- `started_at: str` — ISO-8601 UTC timestamp with microsecond precision captured at `build_server` (the restart-proof signal);
- `tool_count: int` — the size of the workflow registry `workflow.WORKFLOW_METADATA` (MSP-R13), never a hardcoded roster count.

The resource carries process-lifecycle metadata only: the approval phrase, any phrase-derived value (hash, length, prefix/suffix, boolean probe, comparison result), and the configured env value SHALL NEVER appear in the payload — `phrase_source` describes the configuration path only. The shared posture fields SHALL match the `sofer_auth_status` envelope of the same process (one fact source, two surfaces). Reading `sofer://status` SHALL require zero tools, SHALL have no side effects, and SHALL not touch the network.

The containment, size-guard, and per-resource extension-allow-list clauses above govern path-bearing resources and tool path arguments; they SHALL NOT be extended to the static `sofer://status` resource, which has no path argument and performs no file read.

(Previously: the server exposed only the three URI templates; because every registered resource was a template, `resources/list` was empty by design.)

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

#### Scenario: Static status resource listed with posture content

- GIVEN a server built with `build_server(root=..., approval_phrase="phrase123")`
- WHEN `resources/list` is requested and `sofer://status` is read
- THEN the list SHALL be non-empty and SHALL include `sofer://status`
- AND `sofer://status` SHALL be registered with no path variables (static, not a template)
- AND the three URI templates (`sofer://dataset/{config_path}`, `sofer://codebook/{data_file}`, `sofer://metadata/{data_file}`) SHALL remain listed under `resources/templates/list`
- AND the payload SHALL carry exactly six fields with build-time values: `approval_configured:true`, `phrase_source:"explicit"`, `root` equal to the resolved build root, `version` equal to the installed package version, `started_at` ISO-8601 UTC with microsecond precision, and `tool_count` equal to `len(workflow.WORKFLOW_METADATA)` (never a hardcoded count)

#### Scenario: Status posture consistent across surfaces and free of secret material

- GIVEN a server built with `approval_phrase="phrase123"` and `SOFER_MCP_APPROVAL_PHRASE` configured, plus the unconfigured paths (no phrase with env absent; blank/whitespace env)
- WHEN the `sofer://status` payload and the `sofer_auth_status` envelope of the same build are inspected and the serialized payload is scanned
- THEN the shared posture fields SHALL agree across the two surfaces: `approval_configured`/`phrase_source` equal, `started_at` equal to the envelope's `server_started_at`, and `version` equal to the envelope's `server_version` (one fact source, two surfaces)
- AND the phrase, any phrase-derived value (hash, length, prefix/suffix, boolean probe, comparison result), and the configured env value SHALL NOT appear anywhere in the serialized payload
- AND `phrase_source` SHALL belong to `{"env","explicit","none"}` and describe the configuration path only
- AND across the unconfigured paths the invariant `phrase_source == "none"` ⟺ `approval_configured is False` SHALL hold


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

> Added by change `sofer-mcp-server` (archived 2026-08-28). Modified by `fix-dataset-identity-context` (archived 2026-09-04).

Every dataset tool SHALL take `config: str` (TOML path) as its first parameter; `DatasetConfig.from_toml` SHALL accept an optional `discovery_root: Path | None = None` and SHALL pass `stop_at=discovery_root` into `config.reload` — when provided, tool-config discovery SHALL be bounded (walk-up stops at `discovery_root`); the MCP adapter SHALL ALWAYS supply `discovery_root=_get_root()` so discovery never escapes the server root, and the post-hoc `_bound_discovery` re-bind SHALL be retired. The CLI SHALL pass no bound (unbounded, behavior unchanged). Codebook and scan tools SHALL NOT silently apply `default_config_name` — agents pass explicit paths. Relative paths SHALL resolve against the client cwd (stdio server inherits it). Relative `output_dir`/`output_file` overrides SHALL anchor to the config's `config_path.parent` — never the server root or process cwd. Codebook tools SHALL inject post-reload `config.CSV_DELIMITER`/`config.CSV_ENCODING` — never the hardcoded `";"`/`"utf-8-sig"` debt in `codebook.generate` (rule-3 fix).

Every dataset tool SHALL self-anchor config state per call to avoid cross-call module-state pollution: scan tools SHALL reload from the config's directory before reading output directories; `sofer_codebook(path)`, `sofer_profile(dataset)`, and `sofer_render(package)` SHALL anchor on their input's directory. `sofer_codebook_all` SHALL use `cfg.csv_delimiter`/`cfg.csv_encoding` from the dataset's `[meta]` (the authoritative source), not the process-global `config.CSV_DELIMITER`. `sofer_prepare` SHALL pass `run_checks=not no_checks` to match CLI parity.

(Previously: `from_toml` had no `discovery_root`; MCP compensated with the post-hoc `_bound_discovery` re-bind; output overrides anchored to the server root.)

#### Scenario: Tool config resolves per dataset directory

- GIVEN a TOML under a tree with `[tool.sofer]` overrides
- WHEN any dataset tool calls `DatasetConfig.from_toml(config)`
- THEN `config.reload(toml_dir)` SHALL rebind module constants before the domain function runs

#### Scenario: Discovery bounded at server root

- GIVEN `[tool.sofer]` overrides in a `pyproject.toml` ABOVE the server root and a dataset TOML inside it
- WHEN `sofer_prepare(config)` runs via MCP
- THEN the above-root overrides SHALL NOT apply (walk-up stops at the server root)

#### Scenario: Relative output override anchors to config dir

- GIVEN dataset at `<root>/proj/dataset.toml` and `sofer_prepare(config, output_dir="build")`
- WHEN the call runs
- THEN the package SHALL be written under `<root>/proj/build`, not `<root>/build`

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

System MUST return expected failures as `{"ok":false,"error_code":E,"message":str,"next":obj,"config_errors":[...]}` and MUST NOT throw `McpError` for them; only transport/containment MAY throw typed `PathOutsideRootError`/`PublishRefusedError`. `error_code` MUST be `CONFIG_ERROR|VALIDATION_FAILED|QUALITY_GATE_FAILED|PUBLISH_RISK_NOT_ACKD|PUBLISH_CONFIDENTIAL_NOT_ACKD|PUBLISH_APPROVAL_REQUIRED|PUBLISH_APPROVAL_NOT_CONFIGURED|TARGET_INVALID` — `PATH_OUTSIDE_ROOT` is NOT an envelope code: path escapes are raised as `PathOutsideRootError` (transport-mapped to `isError`), never emitted through `_error_envelope`.

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

> Added by change `mcp-dx-audit-surface` (archived 2026-08-31). Modified by `2026-09-11-fix-auth-status-posture` (archived 2026-09-11).

System MUST expose `sofer_auth_status(config)` with `annotations.readOnlyHint:true`, returning `{token:"present"|"missing", confidential:bool, requires_ack_confidential:bool, approval_configured:bool, requires_approval_phrase:bool, phrase_source:"env"|"explicit"|"none", server_process_id:int, server_started_at:str, server_version:str, next:obj}` without leaking token/phrase values or requiring network. `requires_approval_phrase` is always `true` (a phrase is always required for publish); `approval_configured` reflects whether the server has a non-blank phrase set. An empty or whitespace-only phrase MUST be treated as unconfigured (`approval_configured:false`). `ok` SHALL reflect publish readiness — `true` only when config validation passes AND a token is present AND (when `requires_approval_phrase`) the approval phrase is configured; a dataset that cannot publish never reads `ok:true`.

The four posture fields carry **process-lifecycle metadata only** (never secrets):

- `phrase_source` — `"env" | "explicit" | "none"`, the configuration path that produced `approval_configured`, derived **exactly once at `build_server`** from the same single read that resolves the phrase (explicit `approval_phrase` argument > `SOFER_MCP_APPROVAL_PHRASE` > none); blank/whitespace always maps to `"none"`; a blank explicit argument SHALL NOT fall back to the environment. The source is captured at build time and **never re-derived at tool-call time** — a running server MUST NOT re-read the environment, so environment changes take effect only after a full process restart. Invariant: `phrase_source == "none"` ⟺ `approval_configured is False`.
- `server_process_id` — `os.getpid()` of the hosting process, captured at `build_server`; **process-scoped** (stable for the life of the process) and MUST NOT be asserted to differ across `build_server()` calls within one process.
- `server_started_at` — ISO-8601 UTC timestamp with **microsecond precision** captured at `build_server`; MUST differ AND strictly increase across two `build_server()` calls even within one process — this is **the restart-proof criterion**, anchored here and never on the pid.
- `server_version` — package version from installed metadata (`_version.get_version()`), non-empty, never raises.

NEVER-LEAK (extended to the four posture fields): the phrase, any phrase-derived value (hash, length, prefix/suffix, boolean probe, comparison result), and the configured env value MUST NEVER appear in any of the four posture fields or any rendering of the envelope; `phrase_source` describes the configuration path only.

(Previously: the envelope carried no posture metadata — no `phrase_source`, `server_process_id`, `server_started_at`, or `server_version` — and the never-leak clause named only token/phrase values.)

#### Scenario: Preflight without publish

- GIVEN config `confidential=true`, no `HF_TOKEN`
- WHEN `sofer_auth_status(config)` called
- THEN return `token=missing, confidential=true` and `next` lists `acknowledge_risk` and `acknowledge_confidential` steps

#### Scenario: Posture fields present in envelope and schema

- GIVEN `build_server(root=..., approval_phrase="phrase123")` and `sofer_auth_status(config)` on a valid config
- WHEN the envelope and the `output_schema` are inspected
- THEN the envelope SHALL carry `phrase_source="explicit"`, an integer `server_process_id`, an ISO-8601 UTC `server_started_at` with microseconds, and a non-empty `server_version` equal to `_version.get_version()`
- AND `output_schema.properties` SHALL declare all four fields (additive, typed `string`/`integer`) with `required` unchanged (`["ok", "exit_code", "output"]`) and no `enum` on `phrase_source`
- AND no other tool's envelope or `output_schema` SHALL gain the four posture fields (scope containment)

#### Scenario: phrase_source follows configuration precedence

- GIVEN the five configuration paths for `build_server`:
  - `approval_phrase="x"` → `phrase_source` SHALL be `"explicit"`, `approval_configured:true`
  - no argument, `SOFER_MCP_APPROVAL_PHRASE="x"` → `"env"`, `approval_configured:true`
  - no argument, env absent → `"none"`, `approval_configured:false`
  - no argument, env `""` / whitespace → `"none"`, `approval_configured:false`
  - `approval_phrase=""` while env set → `"none"`, `approval_configured:false` (blank explicit never falls back to env)
- WHEN `sofer_auth_status(config)` is called under each path
- THEN `phrase_source` SHALL equal the mapped value and the invariant `phrase_source == "none"` ⟺ `approval_configured is False` SHALL hold on every path

#### Scenario: server_started_at is the restart-proof signal across server builds

- GIVEN two `build_server()` calls in the same process (back-to-back)
- WHEN the envelopes from the two builds are compared
- THEN the second `server_started_at` SHALL differ from the first AND SHALL be strictly greater (ISO-8601 UTC, fixed-width microseconds, monotonic bump) — the restart-proof criterion anchors here, never on the pid
- AND `phrase_source` SHALL reflect each build's own configuration path

#### Scenario: server_process_id is process-scoped

- GIVEN two `build_server()` calls in the same process
- WHEN `server_process_id` is inspected in both envelopes
- THEN it SHALL equal `os.getpid()` in both, SHALL be identical across the two builds, and SHALL NOT be asserted to differ across builds (no drift promise — pid is process-scoped)

#### Scenario: No phrase material in the posture fields

- GIVEN a server built with `approval_phrase="phrase123"` and `SOFER_MCP_APPROVAL_PHRASE` configured
- WHEN the serialized `sofer_auth_status` envelope (including the four posture fields) is scanned
- THEN `"phrase123"` SHALL NOT appear anywhere and no posture field SHALL carry the phrase or any phrase-derived value (hash, length, prefix/suffix, boolean probe, comparison result)
- AND `phrase_source` SHALL belong to `{"env","explicit","none"}` and describe the configuration path only

---

### Requirement: Approval-phrase configuration diagnostics (APX-01)

> Added by change `2026-09-11-fix-auth-status-hints` (archived 2026-09-11).

System MUST make the unconfigured-approval-phrase state actionable on the two surfaces that report it, instead of today's dead-end `{"action": "configure_approval_phrase"}`-only hint.

When `sofer_auth_status` reports `approval_configured:false`, its flat `hints` object MUST keep `action: "configure_approval_phrase"` as the stable machine-readable key AND MUST additionally carry human-readable guidance covering, in the same payload:

- the variable NAME — `SOFER_MCP_APPROVAL_PHRASE` (name only; never a value);
- **process-start semantics** — the phrase is read exactly once, when the MCP server process starts (`build_server`), from the `approval_phrase` argument or `SOFER_MCP_APPROVAL_PHRASE`; the running server MUST NOT be presented as re-reading the environment;
- the required location — the variable MUST be present in the environment of the process that **launches** `sofer-mcp`; a variable set in a separate shell or terminal MUST NOT be presented as sufficient;
- the restart requirement — the change takes effect only after a full restart of the agent/server host process, signalled both as prose and as a machine-readable flat boolean key `approval_phrase_restart_required: true`; the guidance MUST NOT suggest that re-calling the tool resolves the state without a restart (no runtime re-read);
- per-agent setup guidance whose named keys MUST be the shapes `mcp_registration.py` actually writes: `sofer mcp add --agent opencode` writes only the `mcp.sofer` entry keys `type`, `command`, `cwd` and forwards **NO** environment (so the guidance MUST NOT claim env forwarding for opencode), `codex` persists an `env_vars` allow-list of environment-variable NAMES, and `gemini` persists an `env` mapping of NAME → `$NAME` references; secret VALUES are never written to disk;
- the verification step — after the restart, `sofer_auth_status` reports `approval_configured:true`.

All guidance keys MUST be namespaced with the `approval_phrase_*` prefix (so the bare `approval_phrase` key of the configured branch stays absent when unconfigured) and MUST be **flat scalars** — no nested object or array value anywhere in `hints` (MSP-R13 flatness invariant).

The same process-start semantics MUST appear in the `PUBLISH_APPROVAL_NOT_CONFIGURED` message returned by `sofer_publish_confirm` when no phrase is configured: the message MUST name `SOFER_MCP_APPROVAL_PHRASE`, MUST state the phrase is read once at server start, MUST state the variable must be in the launching process's environment, and MUST require a restart. The refusal MUST still never reach the upload (MSP-R05 unchanged), MUST keep its `"publish is disabled:"` prefix and its `error_code`, and its `next`/`hints` recovery payload MUST remain exactly `{"action": "configure_approval_phrase"}` (guidance rides in the message/output there, not in the refusal `hints`).

NEVER-LEAK: guidance and message MUST NOT contain the phrase, any phrase-derived value (hash, length, prefix/suffix, boolean probe, comparison result), or the configured value of `SOFER_MCP_APPROVAL_PHRASE`; only the variable NAME may appear. Guidance MUST NOT name an on-disk agent config file or directory path as the place to put the phrase (the registration tooling writes the `mcp.sofer` entry, not a phrase file). The guidance lives in the flat preflight `hints` object; the registry-driven `next` continuation MUST remain unchanged (MSP-R13).

#### Scenario: Unconfigured approval hint is actionable

- GIVEN a server built with no `approval_phrase` and `SOFER_MCP_APPROVAL_PHRASE` absent from the environment, so `approval_configured:false`
- WHEN `sofer_auth_status(config)` is called
- THEN `hints["action"]` SHALL remain `"configure_approval_phrase"`
- AND `hints` SHALL additionally carry guidance text naming `SOFER_MCP_APPROVAL_PHRASE`, stating the phrase is read once at server start, stating the variable must be in the launching process's environment, and stating a full restart is required
- AND `hints["approval_phrase_restart_required"]` SHALL be `True` and every `hints` value SHALL be a scalar (flat payload, no nested dict/list)
- AND the guidance SHALL name the verification step (`approval_configured:true` after the restart)
- AND the configured branch SHALL be unaffected: with a configured phrase `hints` SHALL NOT contain any `approval_phrase_*` guidance key

#### Scenario: Publish refusal message carries the same process-start semantics

- GIVEN a server with no configured approval phrase
- WHEN `sofer_publish_confirm` is called with the required acknowledgments set
- THEN the envelope SHALL return `error_code = PUBLISH_APPROVAL_NOT_CONFIGURED` and the upload SHALL never be reached
- AND the message SHALL name `SOFER_MCP_APPROVAL_PHRASE`, state that the phrase is read once at server start, state that it must be set in the launching process's environment, and state that a restart is required
- AND the message SHALL keep its `"publish is disabled:"` prefix and the refusal `hints` SHALL be exactly `{"action": "configure_approval_phrase"}`

#### Scenario: Guidance message and hints share one fact source

- GIVEN the unconfigured-approval surface on both `sofer_auth_status` and `sofer_publish_confirm`
- WHEN the hint guidance values and the refusal message are compared
- THEN each process-start fact (variable NAME, read-once-at-start, launching-process environment, restart required) SHALL be derivable from the same module constants — each fact constant SHALL appear as a substring of both the corresponding hint value and the message
- AND the opencode per-agent guidance SHALL assert only the keys `mcp_registration.py` writes (`type`, `command`, `cwd`) and SHALL NOT claim that registration forwards the environment

#### Scenario: Guidance leaks no phrase material and invents no config path

- GIVEN `approval_phrase="phrase123"` present on the server, and the unconfigured-approval guidance produced without one
- WHEN the whole `sofer_auth_status` envelope and the refusal message are serialized
- THEN `"phrase123"` SHALL NOT appear anywhere in either
- AND no guidance key SHALL carry a phrase-derived value, and `hints` SHALL NOT contain the bare `approval_phrase` key
- AND no guidance text SHALL name an on-disk agent config file or directory (e.g. `opencode.json`, `config.toml`, `settings.json`) as the place to put the phrase

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

---

### Requirement: Windows-safe init placeholder (INIT-01)

> Added by `fix-sofer-init-cwd-windows-todo` (archived 2026-08-31).

System MUST emit `_INIT_TEMPLATE` with Windows-safe `[[file]] local`. Placeholder SHALL be `raw/example.csv` (or equivalent), MUST NOT contain `:`. TOML MUST parse on win32 with `ntpath.splitdrive` drive `""`; `:` is reserved except drive `X:`.

#### Scenario: Win32 no drive
- GIVEN `sofer_init(name="test")` output
- WHEN `ntpath.splitdrive("raw/example.csv")` on win32
- THEN drive is `""` and `":"` absent

#### Scenario: No TODO colon
- GIVEN fresh `test.toml`
- WHEN text inspected
- THEN `TODO:` not present in `[[file]] local` values

#### Scenario: Colon rejected
- GIVEN TOML `local="TODO: raw/file.csv"`
- WHEN validated on Windows
- THEN rejected (`:` illegal NTFS)

---

### Requirement: sofer_init cwd containment (INIT-02)

> Added by `fix-sofer-init-cwd-windows-todo` (archived 2026-08-31). Modified by `fix-dataset-identity-context` (archived 2026-09-04).

`sofer_init` SHALL expose `cwd: str | None = None`. Resolution SHALL be fail-closed strict-descendant: `cwd=None` SHALL select the live process CWD only when it is a STRICT descendant of the server root (`live != root.resolve() AND live.is_relative_to(root.resolve())`); otherwise SHALL refuse with an actionable `IdentityResolutionError` naming the required `cwd` argument — the server root SHALL NEVER be silently selected. `cwd=str` SHALL be resolved via `_contained_path(cwd, root=_SERVER_ROOT, must_exist=False)`, MUST satisfy `is_relative_to(_SERVER_ROOT.resolve())`, per-call `effective_root`, MUST NOT mutate `_SERVER_ROOT`. Escape → `PathOutsideRootError`.

(Previously: `cwd=None` back-compat auto-selected `_get_root()`, silently picking the parent root when live CWD equaled or escaped the root.)

#### Scenario: cwd omitted with live CWD strictly inside root

- GIVEN `build_server(root=Desktop)`, live CWD `Desktop/test` (a real directory)
- WHEN `sofer_init(name="test", cwd=None)`
- THEN effective root SHALL be `Desktop/test` and `Desktop/test/test.toml` SHALL be written

#### Scenario: cwd omitted with live CWD equal to root fails closed

- GIVEN `build_server(root=Desktop)`, live CWD `Desktop` (root == dataset root)
- WHEN `sofer_init(name="test", cwd=None)`
- THEN `IdentityResolutionError` SHALL name the required `cwd` argument and NO file SHALL be written

#### Scenario: cwd omitted with live CWD outside root fails closed

- GIVEN `build_server(root=Desktop)`, live CWD `C:/elsewhere`
- WHEN `sofer_init(name="test", cwd=None)`
- THEN `IdentityResolutionError` SHALL name the required `cwd` argument and NO file SHALL be written

#### Scenario: cwd contained succeeds

- GIVEN `cwd="Desktop/test"` under `Desktop`
- WHEN `sofer_init(cwd="Desktop/test", name="test")`
- THEN succeeds with root `Desktop/test`

#### Scenario: cwd outside rejected

- GIVEN `_SERVER_ROOT=Desktop`
- WHEN `sofer_init(cwd="C:/Windows")`
- THEN `PathOutsideRootError`, no write

#### Scenario: traversal rejected

- GIVEN `_SERVER_ROOT=Desktop`
- WHEN `cwd="Desktop/../Windows"`
- THEN `PathOutsideRootError`

#### Scenario: no global mutation

- GIVEN `_SERVER_ROOT=Desktop`
- WHEN `sofer_init(cwd="Desktop/test", name="test")` done
- THEN `_get_root()` still `Desktop`

---

### Requirement: Anchored writes and canonical identity reporting (INIT-03)

> Added by `fix-sofer-init-cwd-windows-todo` (archived 2026-08-31). Modified by `fix-dataset-identity-context` (archived 2026-09-04).

`sofer_init` MUST create `<name>.toml` and `raw/` only inside `effective_root` (INIT-02). No parent writes. The TOML SHALL be written BEFORE `raw/` is scaffolded (and the CLI `init` SHALL do the same) so a TOML write failure never leaves an orphan `raw/` — no partial state. The success envelope SHALL report the canonical identity: `config_path` (absolute `effective_root/<name>.toml`) and `dataset_root` (absolute resolved `effective_root`) — both SHALL appear in the envelope AND in the tool's `output_schema` (INIT-03, MSP-R03).

(Previously: anchored writes only; the envelope reported no identity fields.)

#### Scenario: stale-root anchored

- GIVEN `build_server(root=Desktop)` + dir `Desktop/test`
- WHEN `sofer_init(cwd="Desktop/test", name="test")`
- THEN `Desktop/test/test.toml` + `Desktop/test/raw/` exist, `Desktop/test.toml` absent

#### Scenario: idempotent

- GIVEN `Desktop/test/test.toml` + `raw/keep.csv`
- WHEN re-run `sofer_init(cwd="Desktop/test", name="test")`
- THEN succeeds, `keep.csv` preserved

#### Scenario: cleanup not parent

- GIVEN effective root `Desktop/test`
- WHEN init completes
- THEN parent `Desktop/raw` not created

#### Scenario: canonical identity reported

- GIVEN `sofer_init(cwd="Desktop/test", name="test")` succeeds
- WHEN the envelope is inspected
- THEN it SHALL contain absolute `config_path` `Desktop/test/test.toml` and absolute resolved `dataset_root` `Desktop/test`

---

### Requirement: xlsx discovery after init (INIT-04)

> Added by `fix-sofer-init-cwd-windows-todo` (archived 2026-08-31).

After `sofer_init` → `sofer_scan_apply`, scanner MUST discover `DATA_GOT_ALL.xlsx` and `dataset.xlsx` via `SUPPORTED_FORMATS`, copy flattened to `cache/*.xlsx`, register `local="cache/<name>.xlsx"`. `sofer_validate` MUST pass post-scan.

#### Scenario: xlsx registered
- GIVEN `DATA_GOT_ALL.xlsx` + `dataset.xlsx` loose in `Desktop/test`
- WHEN `sofer_init` then `sofer_scan_apply(config="Desktop/test/test.toml")`
- THEN TOML has both `cache/*.xlsx` and files exist in `cache/`

#### Scenario: validate passes
- GIVEN post-scan TOML with 2 xlsx
- WHEN `sofer_validate`
- THEN `ok:true`, no `Local path not found`

#### Scenario: scan idempotent
- GIVEN post-scan with 2 entries
- WHEN `sofer_scan_apply` rerun
- THEN count stays 2, no dupes

---

### Requirement: Dataset identity validation before any write (INIT-05)

> Added by `fix-dataset-identity-context` (archived 2026-09-04).

`sofer_init` SHALL validate identity BEFORE any write: `name` and `user` SHALL both be mandatory, non-empty, and safe single components — no `/`, no `\`, no drive/UNC path (`ntpath.splitdrive`), no `.`/`..` components, no quotes, no newlines/control characters, no leading/trailing whitespace. `name` SHALL additionally contain no Windows-invalid filename character (`<>:"/\|?*`) and SHALL NOT be a Windows reserved device name — `CON`, `PRN`, `AUX`, `NUL`, `COM1`-`COM9`, `LPT1`-`LPT9`, case-insensitive, stem-matched so `CON.txt` is rejected too (dots are legal in names; `<name>.toml` with a reserved stem is unmaterializable on Windows, and the validation is platform-independent pre-write). `user` SHALL match `^[\w\-]+\Z` — the `\Z` end-of-string anchor, NOT `$` (Python `$` also matches before a trailing `\n`, so `\Z` is the exact no-trailing-newline contract; it is a strict superset of the earlier `^[\w\-]+$` prose form) — and SHALL NOT be a placeholder (`YOUR_USER` or any normalized `model._PLACEHOLDERS` value). Any violation SHALL refuse the call with an actionable error BEFORE creating `<name>.toml` or `raw/`; the generated TOML SHALL NEVER contain `YOUR_USER`. CLI parity is specified in CLI-R07.

(Previously: only empty `name` was refused; a missing/blank `user` silently emitted the `YOUR_USER` placeholder.)

#### Scenario: Valid identity accepted

- GIVEN `sofer_init(name="test", user="emiliodavola", cwd="Desktop/test")`
- WHEN the call executes
- THEN `ok:true` and `Desktop/test/test.toml` SHALL contain `repo_id = "emiliodavola/test"`

#### Scenario: Missing or blank identity refused before write

- GIVEN `name` missing/blank or `user` missing/blank (`None`, `""`, `"   "`)
- WHEN `sofer_init` executes
- THEN a refusal SHALL name the missing value and NO TOML and NO `raw/` SHALL be created

#### Scenario: Placeholder user banned pre-write

- GIVEN `user="YOUR_USER"` (or any normalized `_PLACEHOLDERS` value)
- WHEN `sofer_init` executes
- THEN the call SHALL be refused before any write and the generated TOML SHALL NOT contain `YOUR_USER`

#### Scenario: Unsafe or injection-shaped name rejected

- GIVEN `name` containing a separator (`a/b`, `a\b`), drive (`C:/evil`), traversal (`a/../b`), quotes, newline, or control character
- WHEN `sofer_init` executes
- THEN the call SHALL be refused before any write

#### Scenario: Windows-invalid or reserved name rejected

- GIVEN `name` containing a Windows-invalid character (`a*b`, `a?b`, `a<b`, `a>b`, `a|b`, `a:b`) or a reserved device name (`CON`, `con.toml`, `COM1`, `LPT9`)
- WHEN `sofer_init` executes
- THEN the call SHALL be refused before any write, with NO TOML and NO `raw/`

#### Scenario: Non-conforming user rejected

- GIVEN `user` not matching `^[\w\-]+\Z` (e.g. `user.name`, `user name`, `alice\n`)
- WHEN `sofer_init` executes
- THEN the call SHALL be refused before any write


### Requirement: Authoritative workflow registry with executable continuations (MSP-R13)

The MCP server SHALL expose one authoritative workflow registry: every registered tool SHALL have exactly one registry entry with `phase`, `branch`, `requires`, and a valid `next` continuation or explicit human gate. The same registry SHALL drive `tools/list` metadata, tool descriptions, prompts, server instructions, and runtime envelopes (no per-tool hand-built `next` hints).

A `next` continuation SHALL be executable only when its tool exists and every required argument resolves (a `<config_path>` binding with no config SHALL degrade to `input_required`). A human approval stop SHALL be a typed `human_gate` envelope (`{kind: "human_gate", name, reason}`), never a fake tool call. When a required human value is unknowable, the envelope SHALL name the missing input instead of emitting a guaranteed-failing call.

Canonical branches: greenfield `sofer_init -> sofer_scan_dry_run -> sofer_scan_apply -> sofer_validate`; existing-config `sofer_validate -> sofer_prepare -> sofer_codebook_all -> sofer_profile_all -> sofer_render_all`; single-file triage `sofer_codebook` / `sofer_profile` / `sofer_render`; delivery `sofer_auth_status -> sofer_publish(dry_run=true) -> HUMAN APPROVAL STOP -> sofer_publish_confirm`.

(Previously: workflows were described by `_PHASED_INSTRUCTIONS`, docstrings, prompts, and per-envelope `next` hints with no single source of truth.)

#### Scenario: Every tool has exactly one registry entry

- GIVEN the registered tool set
- WHEN the registry is enumerated
- THEN every tool SHALL have exactly one entry with phase, branch, requires, and valid next/gate

#### Scenario: tools/list metadata comes from the registry

- GIVEN a running server
- WHEN `tools/list` is requested
- THEN tool descriptions SHALL surface the registry entry's phase, branch, and continuation

#### Scenario: Envelope next is executable against the registry

- GIVEN an envelope carrying a `next` continuation
- THEN a registered FastMCP client SHALL be able to invoke that tool with those arguments and receive an envelope, for every registry next
- AND when the continuation needs a human value, `input_required` SHALL name it instead

#### Scenario: Missing config recovery is structured

- GIVEN a greenfield request with no dataset TOML
- THEN the envelope SHALL carry `error_code`, `message`, and an executable `next` (or `input_required`) — never a Python repr and never a fabricated credential

#### Scenario: Delivery branch routes render_all through auth_status

- GIVEN the existing-config branch reaches `sofer_render_all`
- THEN its registry continuation SHALL name `sofer_auth_status` before any publish dry-run

#### Scenario: Single-file triage never advertises a config-bearing publish call

- GIVEN `sofer_render` triage on a single file
- THEN its metadata SHALL NOT suggest `sofer_publish` (a config-bearing call)

#### Scenario: Human approval stop is a typed gate

- GIVEN `sofer_publish(dry_run=true)` completes
- THEN the envelope SHALL return the `human_gate` approval stop before `sofer_publish_confirm` is offered

#### Scenario: Greenfield branch continues init -> scan_dry_run -> scan_apply -> validate

- GIVEN `sofer_init` on a greenfield root
- THEN its `next` SHALL name `sofer_scan_dry_run`, whose `next` names `sofer_scan_apply`, whose `next` names `sofer_validate`
