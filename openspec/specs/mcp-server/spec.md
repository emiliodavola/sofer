# mcp-server Specification

## Purpose

Distribution contract for sofer's MCP server: exposes the CLI's deterministic pipeline (validate → prepare → codebook → profile → render → publish) as MCP tools, resources, and prompts over stdio, so an agent can operate sofer while humans authorize network writes. The server is a thin adapter over existing domain functions — it never re-implements logic, never calls an LLM, and ships no remote transport in v1.

## Requirements

### Requirement: Transport and entry point (MSP-R01)

> Added by change `sofer-mcp-server` (archived 2026-08-28). Modified by `2026-10-09-feat-mcp-explicit-root` (issue #273) — the entry point resolves an explicit containment root.

`[project.scripts]` SHALL declare `sofer-mcp = "sofer.mcp_server:main"`; running `sofer-mcp` SHALL start an MCP stdio server speaking JSON-RPC 2.0 over stdin/stdout, supporting `initialize`, `tools/list`, `tools/call`, `resources/list`+`read`, `prompts/list`+`get`. There SHALL be no remote/streamable-http transport in v1. The server SHALL never call an LLM; its only network access SHALL be the HF upload path inside the confirm tool.

`sofer-mcp` SHALL accept an explicit containment root: the `--root PATH` flag and the `SOFER_MCP_ROOT` environment variable SHALL both set it, with precedence explicit `--root PATH` > `SOFER_MCP_ROOT` > the resolved process cwd (the documented default). A blank or whitespace-only `SOFER_MCP_ROOT` SHALL be treated as unset. When the resolved root does not exist or is not a directory, startup SHALL be refused with a message on stderr naming the resolved path and a non-zero exit — the fail-closed signal for a stdio server. Containment semantics SHALL be unchanged: every path-bearing argument and resource URI outside the resolved root SHALL still be refused with `PathOutsideRootError`.

#### Scenario: Explicit root with fail-closed startup refusal

- GIVEN the sofer MCP entry point
- WHEN `--root PATH` is passed, `SOFER_MCP_ROOT` is set, or neither is present
- THEN the containment root SHALL be the first present of `--root PATH`, `SOFER_MCP_ROOT`, and the resolved process cwd (the argument wins; a blank env value counts as unset)
- AND paths outside the resolved root SHALL still be refused with `PathOutsideRootError`
- AND a resolved root that is missing or not a directory SHALL refuse startup with a message naming the resolved path and a non-zero exit

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

> Added by change `sofer-mcp-server` (archived 2026-08-28). Modified by `feat-mcp-auto-install` (2026-08-31). Modified by `docs-fastmcp-cap-drift` (issue #257, 2026-09-26) — the cap is `>=4,<5`.

`sofer.mcp_server` SHALL import on lean install. `fastmcp>=4,<5` SHALL be in `dependencies` so `pip install "sofer @ git+..."` and `uv tool install "sofer @ git+..."` SHALL install `fastmcp` and `sofer-mcp --help` SHALL succeed. `mcp` alias `["fastmcp>=4,<5"]` SHALL remain one minor. Guard in `mcp_server.py` SHALL stay degraded-only with `pip`+`uv tool` and `sofer[mcp] @ git+...`.

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
- THEN `fastmcp>=4,<5` SHALL appear without `extra == 'mcp'`

#### Scenario: uv.lock unconditional

- GIVEN regenerated `uv.lock`
- WHEN `sofer` entry inspected
- THEN `fastmcp` SHALL be under `dependencies` not `optional-dependencies`

#### Scenario: Existing tests green

- GIVEN repo
- WHEN `uv run pytest tests/test_mcp_server.py tests/test_mcp_registration.py -q` runs
- THEN all SHALL pass

---

### Requirement: Tool roster and schema contract (MSP-R03) — Modified 2026-10-16, feat-meta-tools

> Added by change `sofer-mcp-server` (archived 2026-08-28). Modified by `mcp-dx-audit-surface` (archived 2026-08-31). Modified by `fix-sofer-init-cwd-windows-todo` (archived 2026-08-31) — adds optional `cwd` to `sofer_init`. Modified by `fix-dataset-identity-context` (archived 2026-09-04) — `sofer_init` output_schema declares `config_path`/`dataset_root` per INIT-03. Modified by `2026-09-25-feat-mcp-failure-report` (issue #244) — 15 callables (+ `sofer_report_failure`). Modified by `2026-10-15-fix-profile-render-default-paths` (issue #294) — the batch `output_dir` descriptions name the resolved default path and the override semantics. Modified under the ODD-only work unit `odd/tasks/meta-tools.md` (issue #323) — 17 callables (+ `sofer_meta_check`, `sofer_meta_set`), which is the tool surface MSP-META-01 requires. Modified by `2026-10-17-feat-visibility-enforcement` (issue #338) — 18 callables (+ `sofer_repo_settings`), `sofer_auth_status` gains the opt-in `check_remote` read, and MSP-R15 is **corrected**: the Phase-1 move has been mandatory since #339, so the `move_loose` opt-in this clause described no longer exists. Modified 2026-10-19 under the ODD-only work unit `odd/tasks/file-entry-tool.md` (issue #344) — 19 callables (+ `sofer_file_set`), the writable `[[file]]` surface. Modified 2026-10-19 under `odd/tasks/per-call-root.md` (issue #347) — every path-bearing tool grows an optional `root` (MSP-R21) and every envelope echoes `effective_root`.

Server SHALL expose 19 callables: `sofer_validate, sofer_meta_check, sofer_meta_set, sofer_file_set, sofer_prepare, sofer_publish, sofer_publish_confirm, sofer_codebook, sofer_codebook_all, sofer_profile, sofer_profile_all, sofer_render, sofer_render_all, sofer_scan_dry_run, sofer_scan_apply, sofer_init, sofer_auth_status, sofer_repo_settings, sofer_report_failure`. Every param SHALL be `Annotated[Field(description)]` non-empty (10.1), and the batch `output_dir` descriptions SHALL name the resolved default path — the artifact-cache write root (`config.OUTPUT_DIR`) joined with the configured sub-directory (`config.PROFILE_DIR` for `sofer_profile_all`, `config.RENDER_DIR` for `sofer_render_all`) — and SHALL state that an override replaces that write root, so the artifacts land in `<output_dir>/<sub-directory>`.  The bare directory name SHALL NOT be presented as the whole default; `target` SHALL be `Literal["local"]`/`Literal["hf"]` single-value (const or enum) (10.5); `output` SHALL split to `output_file` vs `output_dir` (10.7); `all_files` removed — batch via `*_all` (10.6); `no_checks` → `run_checks:bool=true` (10.9); every tool SHALL have `annotations` and typed `output_schema`. `sofer_init` additionally exposes `cwd: str | None = None` per INIT-02 and its `output_schema` SHALL declare `config_path`/`dataset_root` (absolute strings) per INIT-03; under MSP-R23 it also appends `config: str | None = None` as its last parameter, makes `name`/`user` optional (create-mode requirements enforced by the selected mode, never by the JSON schema), and declares `initialization_mode` and `session_ready` in its `output_schema`. `sofer_auth_status` additionally exposes `check_remote: bool = False`: `False` (the default) SHALL keep the preflight offline, and `True` SHALL make one read-only call reporting the repository's current visibility as `remote_visibility`. Every path-bearing tool except `sofer_report_failure` SHALL additionally expose `root: str | None = None` (MSP-R21); `sofer_init` appends `config` after it.

(Previously: `sofer_init` schema carried no identity fields; 11 callables, polymorphic profile/render, free-string target, dual-typed output, bare params, generic schema; then 14 callables without `cwd`.)

#### Scenario: Constrained schemas

- GIVEN `tools/list`
- WHEN inspected
- THEN count SHALL be 19, `target` SHALL have `const` or `enum` single value, no tool SHALL expose `all_files`/`no_checks`/`output` (only `output_file`/`output_dir`/`run_checks`), and every `properties[*].description` SHALL be non-empty

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

#### Scenario: sofer_init attach-mode schema

- GIVEN `tools/list` `sofer_init` `input_schema`
- WHEN inspected
- THEN `config` SHALL be an optional string, `name`/`user` SHALL be optional nullable strings, and `initialization_mode`/`session_ready` SHALL be declared in `output_schema`

**Evidence:** `test: tests/test_mcp_schema.py::TestOutputSchema::test_sofer_init_user_required`, `test: tests/test_mcp_server.py::TestToolRoster::test_exactly_nineteen_callables`

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

> Added by change `sofer-mcp-server` (archived 2026-08-28); modified by
> `fix-scan-parity-mcp`.

`sofer_scan_apply` SHALL never prompt — the explicit call IS the confirmation. It SHALL chain the pure scanner functions `discover_files → check_flatten_collisions → merge_entries → copy_files → write_toml`, honoring `force`. When `move_loose` is `True`, the chain SHALL be `discover_files(exclude raw/) → check_raw_collisions → move_to_raw → discover_files → check_flatten_collisions → merge_entries → copy_files → write_toml`, still honoring `force` and never prompting (SCN phase order: MOVE before COPY).

#### Scenario: Apply never blocks on input

- GIVEN a TOML directory with unregistered files and stdin closed
- WHEN `sofer_scan_apply` runs
- THEN files SHALL be copied and the TOML updated
- AND the call SHALL never block on `input()`

#### Scenario: Apply with move_loose chains the MOVE phase (unchanged scenarios preserved)

- GIVEN a TOML directory with loose supported files outside `raw/`/`cache/`/`EXCLUSIONS`
- WHEN `sofer_scan_apply` runs with `move_loose=True`
- THEN each loose file SHALL be MOVED into `raw/<relative_to(base_dir)>`
- AND the same files SHALL be copied into `cache/` (flattened) and registered
- AND the loose originals SHALL no longer exist at their old paths
---

### Requirement: Resources (MSP-R07)

> Added by change `sofer-mcp-server` (archived 2026-08-28). Modified by `2026-09-11-fix-status-resource` (archived 2026-09-11).

The server SHALL expose `sofer://dataset/{config_path}` (raw TOML text), `sofer://codebook/{data_file}` (codebook markdown generated on demand, pure read), and `sofer://metadata/{data_file}` (metadata.yaml content when present). Plain artifacts SHALL be read via `file://` URIs. The config path SHALL be the identity — no name-based scheme.

All resource URIs and tool path arguments SHALL be contained under the server root: paths SHALL be resolved, canonicalized, and verified inside the root (rejecting `..` traversal, absolute paths outside root, and symlink escapes) with per-resource extension allow-lists; violations SHALL raise a typed `PathOutsideRootError`. The refusal message SHALL keep the prefix `<what> resolves outside the server root` and SHALL append the resolved root it was compared against plus the remedy — `set SOFER_MCP_ROOT or --root at server start, then restart the host` — so an agent can diagnose and repair the configuration without reading sofer's source (issue #343). Resource reads SHALL honor a size guard (`agent_resource_max_bytes`, default 50 MB) before reading. The `file://` boundary SHALL be documented as governed by the MCP client's own permission model — the server SHALL NOT add new escape hatches beyond it.

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

> Added by change `sofer-mcp-server` (archived 2026-08-28). Modified by `2026-09-13-test-mcp-injection-semantics` — adds the injection-semantics contract and its probe suite (test-only; no runtime change). Modified by `2026-09-13-fix-prompt-intro-repr` — resolves the #169 known-limitation carve-out: the three intro sentences now repr-contain caller arguments at parity with the executable surfaces; intro-region containment is asserted by the probe suite; runtime change is exactly the three intro interpolation tokens (issue #169).

The server SHALL expose 3 user-controlled workflow templates — `prepare_dataset`, `assess_dataset`, `finalize_and_publish` — encoding the validate → prepare → confirm-before-publish idiom. Any publish step SHALL instruct calling `sofer_publish` (dry-run) and stopping for human approval before `sofer_publish_confirm`.

Caller-controlled prompt arguments (`config`, `output`, and `dataset` for `assess_dataset`) SHALL be rendered as DATA inside every template: a hostile argument carrying newlines, instruction-like prose, fake numbered-step lines, fake tool-call lines, quotes, or backslashes SHALL NOT add a workflow step, SHALL NOT remove or reorder an existing step, SHALL NOT split or break out of any executable line (step, numbered step, or copy-paste block), and SHALL NOT displace the human-approval STOP that precedes `sofer_publish_confirm`. Every executable argument position SHALL be `repr`-quoted, so a payload newline SHALL appear as the escaped literal `\n` inside a quoted position — never as a real line break that could start a new instruction line. `prompts/list` SHALL still return exactly 3 prompts and the canonical-chain text SHALL be unchanged by any caller argument. The static `_with_untrusted_note` guard SHALL still be appended to each rendered prompt under hostile arguments.

**RESOLVED (change `2026-09-13-fix-prompt-intro-repr`, issue #169):** the containment contract SHALL extend to the intro sentences. Caller-controlled `config`/`dataset` arguments SHALL be `repr`-contained in ALL interpolations of the three prompt templates — intro sentences AND executable surfaces. Every intro sentence SHALL render each caller-controlled argument it interpolates (`config` on all three templates; `config` and `dataset` for `assess_dataset`) in its `repr()` form — quoted and escaped exactly like the executable argument positions — and SHALL NOT interpolate any caller-controlled argument raw. No raw, non-`repr` interpolation of `config`/`dataset` SHALL remain in any prompt template; a hostile payload SHALL therefore appear only as data, never as real instruction-shaped prose. (`output` is never interpolated into any intro sentence; its containment remains asserted over the executable block.)

The dedicated injection probe suite SHALL live in `tests/test_mcp_server.py` (`TestPrompts`) as net-new, additive tests; every scenario below SHALL map to a test (AGENTS.md rule 6 / `openspec/config.yaml` specs rule). A probe that fails because a payload genuinely altered rendered semantics SHALL STOP — the red probe plus rendered output is the finding; `src/sofer/mcp_server.py` SHALL change only by the three intro interpolation tokens specified by this change (issue #169 fix scope), never silently beyond them. The suite SHALL additionally assert intro-region containment for all three templates: over the intro region — `text` up to the existing `"Canonical chain:"` anchor (the established slice; no new literals) — `repr(payload)` SHALL be present for every caller-controlled intro argument and no raw `_INJECT_*` marker SHALL appear. The #139 probes that assert executable-surface containment remain unchanged and green; their wording-only docstring refresh records the resolution, not a behavior change.

(Previously: the injection-semantics contract and its probe suite covered the executable surfaces only; the three intro sentences interpolated caller arguments raw at the pre-fix sites and were recorded as known limitation #169 — probes expressly did NOT assert intro prose purity. Resolved by this change: intros repr-contain caller arguments; intro-region assertions added.)

#### Scenario: Prompt list shows 3 templates

- GIVEN the server running
- WHEN `prompts/list` is called
- THEN exactly 3 prompts SHALL be returned

#### Scenario: Confirm-before-publish idiom enforced

- GIVEN each prompt's template
- WHEN it is inspected
- THEN every HF-publish step SHALL mandate a human-approval stop before the confirm call

#### Scenario: Hostile payload cannot alter the prepare_dataset workflow

- GIVEN `build_server(root=tmp_path)` and a `prepare_dataset` call whose `config` and `output` arguments each carry a hostile `_INJECT_*` payload (real newlines + instruction-like prose; a fake `\n6. sofer_publish(...)` step line; a fake `sofer_publish_confirm(...)` tool-call line; quotes/backslashes)
- WHEN the prompt is rendered via `client.get_prompt("prepare_dataset", {...})`
- THEN the ordered `sofer_*` call sequence SHALL equal the builder's static canonical sequence (`sofer_validate → sofer_prepare → sofer_codebook_all → sofer_profile_all → sofer_render_all → sofer_publish` dry-run) with no added, removed, or reordered call
- AND every payload newline SHALL appear as an escaped `\n` literal inside a repr-quoted argument position — no raw line break SHALL split any step or copy-paste line
- AND no payload marker SHALL appear as a line-start call (every marker SHALL sit inside a repr-quoted literal)
- AND `STOP` and the human-approval wording SHALL be present BEFORE `sofer_publish_confirm`
- AND the `_UNTRUSTED_NOTE` text SHALL still be appended

#### Scenario: Hostile payload cannot alter the assess_dataset workflow

- GIVEN `build_server(root=tmp_path)` and an `assess_dataset` call whose `config` and `dataset` arguments each carry a hostile `_INJECT_*` payload
- WHEN the prompt is rendered via `client.get_prompt("assess_dataset", {...})`
- THEN the rendered `sofer_*` call sequence SHALL equal the builder's static assess chain (`sofer_validate → sofer_profile → sofer_render`) with no added, removed, or reordered call
- AND every payload newline SHALL appear as an escaped `\n` literal inside a repr-quoted argument position — no raw line break SHALL split any step or copy-paste line
- AND no payload marker SHALL appear as a line-start call
- AND the `_UNTRUSTED_NOTE` text SHALL still be appended

#### Scenario: Hostile payload cannot alter the finalize_and_publish workflow

- GIVEN `build_server(root=tmp_path)` and a `finalize_and_publish` call whose `config` and `output` arguments each carry a hostile `_INJECT_*` payload
- WHEN the prompt is rendered via `client.get_prompt("finalize_and_publish", {...})`
- THEN the ordered `sofer_*` call sequence SHALL equal the builder's static canonical sequence (through `sofer_publish` dry-run and the confirm step) with no added, removed, or reordered call
- AND every payload newline SHALL appear as an escaped `\n` literal inside a repr-quoted argument position — no raw line break SHALL split any step or copy-paste line
- AND no payload marker SHALL appear as a line-start call
- AND `STOP` and the human-approval wording SHALL be present BEFORE `sofer_publish_confirm`
- AND the `_UNTRUSTED_NOTE` text SHALL still be appended

#### Scenario: Canonical chain order is payload-invariant

- GIVEN any of the 3 templates rendered with a hostile `_INJECT_*` payload in every caller-controlled argument
- WHEN relative `text.index()` ordering is measured across `sofer_validate → sofer_prepare → sofer_codebook_all → sofer_profile(_all) → sofer_render(_all) → sofer_publish(dry_run) → STOP → sofer_publish_confirm` (where applicable to the template)
- THEN each marker's relative order SHALL be unchanged from the payload-free render, proving order is payload-invariant

#### Scenario: Intro raw interpolation is resolved — intro sentences repr-contain caller arguments (formerly known limitation #169)

> (Previously: the three intro sentences interpolated caller arguments raw at the pre-fix sites — a KNOWN LIMITATION tracked by issue #169 — and the #139 probes asserted containment over the executable surfaces only, expressly NOT asserting intro prose purity. Resolved by change `2026-09-13-fix-prompt-intro-repr`.)

- GIVEN a hostile payload in `config` (and `dataset` for `assess_dataset`)
- WHEN the rendered prompts of all three templates are inspected at the intro sentences (the text before the `"Canonical chain:"` anchor)
- THEN each intro sentence SHALL contain `repr(payload)` for every caller-controlled argument it interpolates — `config` on all three templates, plus `dataset` on `assess_dataset`
- AND no raw `_INJECT_*` marker SHALL appear verbatim in any intro region (every payload newline SHALL appear only as the escaped `\n` literal inside the repr-quoted position)
- AND no raw, non-`repr` interpolation of `config`/`dataset` SHALL remain in any prompt template

#### Scenario: prepare_dataset intro repr-contains a hostile config payload

- GIVEN `build_server(root=tmp_path)` and a `prepare_dataset` call whose `config` argument carries a hostile `_INJECT_*` payload (real newlines + instruction-like prose + quotes/backslashes; reuse `_INJECT_ARGS_PREPARE`)
- WHEN the prompt is rendered via `client.get_prompt("prepare_dataset", {...})` and the intro region (`text[:text.index("Canonical chain:")]`) is inspected
- THEN `repr(_INJECT_ARGS_PREPARE["config"])` SHALL be present in the intro region
- AND no raw `_INJECT_*` marker SHALL appear verbatim in the intro region
- AND the intro region SHALL contain no raw payload line break (hostile newlines render only as the escaped `\n` literal inside the quoted position)

#### Scenario: assess_dataset intro repr-contains hostile dataset and config payloads

- GIVEN `build_server(root=tmp_path)` and an `assess_dataset` call whose `config` and `dataset` arguments each carry a hostile `_INJECT_*` payload (reuse `_INJECT_ARGS_ASSESS`)
- WHEN the prompt is rendered via `client.get_prompt("assess_dataset", {...})` and the two-line intro region (`text[:text.index("Canonical chain:")]`) is inspected
- THEN `repr(_INJECT_ARGS_ASSESS["config"])` and `repr(_INJECT_ARGS_ASSESS["dataset"])` SHALL both be present in the intro region
- AND no raw `_INJECT_*` marker SHALL appear verbatim in the intro region

#### Scenario: finalize_and_publish intro repr-contains a hostile config payload

- GIVEN `build_server(root=tmp_path)` and a `finalize_and_publish` call whose `config` argument carries a hostile `_INJECT_*` payload (reuse `_INJECT_ARGS_FINALIZE`)
- WHEN the prompt is rendered via `client.get_prompt("finalize_and_publish", {...})` and the intro region (`text[:text.index("Canonical chain:")]`) is inspected
- THEN `repr(_INJECT_ARGS_FINALIZE["config"])` SHALL be present in the intro region
- AND no raw `_INJECT_*` marker SHALL appear verbatim in the intro region

#### Scenario: No raw caller-argument interpolation remains in any rendered prompt

- GIVEN all three templates rendered with hostile `_INJECT_*` payloads in every caller-controlled argument (`_INJECT_ARGS_PREPARE` / `_INJECT_ARGS_ASSESS` / `_INJECT_ARGS_FINALIZE`)
- WHEN the full rendered text of each prompt — intro region AND executable block — is scanned for raw payload markers and for `repr()`-quoted payload forms
- THEN zero raw `_INJECT_*` marker SHALL appear verbatim anywhere in any of the three rendered prompts (intro region and executable surfaces combined)
- AND every caller-controlled argument SHALL appear in each rendered prompt exclusively in its `repr()`-quoted form — no argument value SHALL appear as raw, non-`repr` interpolation
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

> Added by change `sofer-mcp-server` (archived 2026-08-28). Modified by `feat-mcp-auto-install` (2026-08-31). Modified by `docs-fastmcp-cap-drift` (issue #257, 2026-09-26) — the cap is `>=4,<5`.

`pyproject.toml` SHALL declare `fastmcp>=4,<5` in `dependencies` and `sofer-mcp = "sofer.mcp_server:main"`; MAY retain `mcp` alias. READMEs SHALL document Install + AI/MCP with correct PEP 508 `name[extra] @ URL`, `uv tool` and `uvx --with`, and flip intro to included-by-default.

(Previously: only `optional-dependencies mcp` + script; README showed `pip install 'sofer[mcp]'`.)

#### Scenario: Wheel script and Requires-Dist

- GIVEN built wheel
- WHEN `entry_points.txt` + METADATA inspected
- THEN `sofer-mcp = sofer.mcp_server:main` and unconditional `fastmcp>=4,<5` SHALL be present

#### Scenario: Alias optional

- GIVEN wheel METADATA
- WHEN `Provides-Extra` inspected
- THEN `mcp` MAY be present mapping to `fastmcp>=4,<5; extra == 'mcp'`

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

System MUST return expected failures as `{"ok":false,"error_code":E,"message":str,"next":obj,"config_errors":[...]}` and MUST NOT throw `McpError` for them; only transport/containment MAY throw typed `PathOutsideRootError`/`PublishRefusedError`. `error_code` MUST be `CONFIG_ERROR|VALIDATION_FAILED|QUALITY_GATE_FAILED|INPUT_READ_FAILED|PUBLISH_RISK_NOT_ACKD|PUBLISH_CONFIDENTIAL_NOT_ACKD|PUBLISH_APPROVAL_REQUIRED|PUBLISH_APPROVAL_NOT_CONFIGURED|TARGET_INVALID` — `PATH_OUTSIDE_ROOT` is NOT an envelope code: path escapes are raised as `PathOutsideRootError` (transport-mapped to `isError`), never emitted through `_error_envelope`.

`INPUT_READ_FAILED` (issues #396, #398) is the code for a batch whose every eligible input failed to be read. A batch tool SHALL NOT return `ok:true` for that state: the envelope SHALL name the per-file causes, and a partially successful batch SHALL return `ok:true` with `partial:true` plus the same `failures` list. What counts as "produced" is the tool's own material artifact — a written profile for `sofer_profile_all`, a written page for `sofer_codebook_all`; a codebook root index alone is never evidence that the data was read.

#### Scenario: Refusal returns envelope with next

- GIVEN `sofer_publish_confirm(acknowledge_risk=false)`
- WHEN executed
- THEN return `ok:false, error_code=PUBLISH_RISK_NOT_ACKD, next={acknowledge_risk:true}` without throw

#### Scenario: Containment still throws

- GIVEN path outside server root
- WHEN any tool/resource called
- THEN raise `PathOutsideRootError` (transport maps to isError)

#### Scenario: A profile batch with no readable input is an error, not an empty success

- GIVEN `sofer_profile_all` on a config with one eligible CSV that cannot be decoded under the supplied dialect
- WHEN executed
- THEN the envelope SHALL be `ok:false, exit_code:1, error_code=INPUT_READ_FAILED` with `files:[]`
- AND it SHALL carry one `failures` entry naming the source path and the read reason

#### Scenario: A partially successful profile batch reports partiality

- GIVEN two eligible CSVs where only one decodes
- WHEN `sofer_profile_all` runs
- THEN the envelope SHALL be `ok:true` with the one generated path in `files`
- AND `partial:true` plus the failing file's `failures` entry

#### Scenario: A source the artifact layout cannot name reports its own cause

- GIVEN `sofer_profile_all`, `sofer_codebook_all` or `sofer_render_all` on a config whose only source lives outside the config directory but inside the server root
- WHEN executed
- THEN the envelope SHALL be `ok:false, exit_code:1, error_code=CONFIG_ERROR` with `config_errors` naming the source and the config directory
- AND `hints.action` SHALL be `move_source_under_config_dir`
- AND the message SHALL NOT describe a collision (issue #397)

#### Scenario: Codebook batch with no readable input is an error, not an empty index

- GIVEN `sofer_codebook_all` on a config with one eligible CSV that cannot be decoded, with or without an existing output directory
- WHEN executed
- THEN the envelope SHALL be `ok:false, exit_code:1, error_code=INPUT_READ_FAILED`
- AND it SHALL carry one `failures` entry naming the source path and the read reason
- AND the root `codebook.md` SHALL still be written as the durable "pages were promised" marker the manifest records missing (#354), so no write error can replace the read cause
- AND the zero-page index SHALL never be presented as a completed codebook

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

System MUST expose `sofer_auth_status(config)` with `annotations.readOnlyHint:true`, returning `{token:"present"|"missing", confidential:bool, requires_ack_confidential:bool, approval_configured:bool, requires_approval_phrase:bool, phrase_source:"env"|"explicit"|"none", server_process_id:int, server_started_at:str, server_version:str, server_root:str, next:obj}` without leaking token/phrase values or requiring network. `requires_approval_phrase` is always `true` (a phrase is always required for publish); `approval_configured` reflects whether the server has a non-blank phrase set. An empty or whitespace-only phrase MUST be treated as unconfigured (`approval_configured:false`). `ok` SHALL reflect publish readiness — `true` only when config validation passes AND a token is present AND (when `requires_approval_phrase`) the approval phrase is configured; a dataset that cannot publish never reads `ok:true`.

The five posture fields carry **process-lifecycle metadata only** (never secrets):

- `phrase_source` — `"env" | "explicit" | "none"`, the configuration path that produced `approval_configured`, derived **exactly once at `build_server`** from the same single read that resolves the phrase (explicit `approval_phrase` argument > `SOFER_MCP_APPROVAL_PHRASE` > none); blank/whitespace always maps to `"none"`; a blank explicit argument SHALL NOT fall back to the environment. The source is captured at build time and **never re-derived at tool-call time** — a running server MUST NOT re-read the environment, so environment changes take effect only after a full process restart. Invariant: `phrase_source == "none"` ⟺ `approval_configured is False`.
- `server_process_id` — `os.getpid()` of the hosting process, captured at `build_server`; **process-scoped** (stable for the life of the process) and MUST NOT be asserted to differ across `build_server()` calls within one process.
- `server_started_at` — ISO-8601 UTC timestamp with **microsecond precision** captured at `build_server`; MUST differ AND strictly increase across two `build_server()` calls even within one process — this is **the restart-proof criterion**, anchored here and never on the pid.
- `server_version` — package version from installed metadata (`_version.get_version()`), non-empty, never raises.
- `server_root` — issue #343: the resolved containment root the server was built with (`--root` > `SOFER_MCP_ROOT` > resolved process cwd), reported as a non-secret absolute path so an agent can preflight reachability before a write attempt. It is a filesystem path the operator already chose, never a secret.

NEVER-LEAK (extended to the five posture fields): the phrase, any phrase-derived value (hash, length, prefix/suffix, boolean probe, comparison result), and the configured env value MUST NEVER appear in any of the five posture fields or any rendering of the envelope; `phrase_source` describes the configuration path only.

(Previously: the envelope carried no posture metadata — no `phrase_source`, `server_process_id`, `server_started_at`, or `server_version` — and the never-leak clause named only token/phrase values.)

#### Scenario: Preflight without publish

- GIVEN config `confidential=true`, no `HF_TOKEN`
- WHEN `sofer_auth_status(config)` called
- THEN return `token=missing, confidential=true` and `next` lists `acknowledge_risk` and `acknowledge_confidential` steps

#### Scenario: Posture fields present in envelope and schema

- GIVEN `build_server(root=..., approval_phrase="phrase123")` and `sofer_auth_status(config)` on a valid config
- WHEN the envelope and the `output_schema` are inspected
- THEN the envelope SHALL carry `phrase_source="explicit"`, an integer `server_process_id`, an ISO-8601 UTC `server_started_at` with microseconds, a non-empty `server_version` equal to `_version.get_version()`, and `server_root` equal to the resolved build root
- AND `output_schema.properties` SHALL declare all five fields (additive, typed `string`/`integer`) with `required` unchanged (`["ok", "exit_code", "output"]`) and no `enum` on `phrase_source`
- AND no other tool's envelope or `output_schema` SHALL gain the five posture fields (scope containment)

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

### Requirement: Approval-phrase configuration diagnostics (APX-01) — Modified 2026-10-15, fix-approval-phrase-agent-coverage

> Added by change `2026-09-11-fix-auth-status-hints` (archived 2026-09-11). Modified by
> `2026-10-15-fix-approval-phrase-agent-coverage` (issue #295): per-agent guidance covers the whole
> registry and is derived from its `env` capability.

System MUST make the unconfigured-approval-phrase state actionable on the two surfaces that report it, instead of today's dead-end `{"action": "configure_approval_phrase"}`-only hint.

When `sofer_auth_status` reports `approval_configured:false`, its flat `hints` object MUST keep `action: "configure_approval_phrase"` as the stable machine-readable key AND MUST additionally carry human-readable guidance covering, in the same payload:

- the variable NAME — `SOFER_MCP_APPROVAL_PHRASE` (name only; never a value);
- **process-start semantics** — the phrase is read exactly once, when the MCP server process starts (`build_server`), from the `approval_phrase` argument or `SOFER_MCP_APPROVAL_PHRASE`; the running server MUST NOT be presented as re-reading the environment;
- the required location — the variable MUST be present in the environment of the process that **launches** `sofer-mcp`; a variable set in a separate shell or terminal MUST NOT be presented as sufficient;
- the restart requirement — the change takes effect only after a full restart of the agent/server host process, signalled both as prose and as a machine-readable flat boolean key `approval_phrase_restart_required: true`; the guidance MUST NOT suggest that re-calling the tool resolves the state without a restart (no runtime re-read);
- per-agent setup guidance that MUST cover **every** member of `mcp_registration.AGENT_NAMES` and MUST be derived from that registry's own `env` capability, never from a parallel hand-kept table: `sofer mcp add --agent <agent>` writes only the `mcp.sofer` entry keys `type`, `command`, `cwd` and forwards **NO** environment when the capability is `none` (so the guidance MUST NOT claim env forwarding for it), persists an `env_vars` allow-list of environment-variable NAMES when it is `allow_list`, and persists an `env` mapping of NAME → `$NAME` references when it is `refs` or NAME → `${NAME}` references when it is `refs_braced`; each fact MUST name the field and the reference form that agent's registration entry actually carries, and secret VALUES are never written to disk;
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

#### Scenario: Per-agent guidance covers every registered agent

- GIVEN a server with no configured approval phrase and the registered agent set `mcp_registration.AGENT_NAMES`
- WHEN `sofer_auth_status(config)` is called
- THEN `hints` SHALL carry exactly one `approval_phrase_setup_<agent>` key per registered agent
- AND each fact SHALL name the entry field and the reference form `build_entry(agent, ...)` really
  writes for that agent's `env` capability
- AND an agent added to `ADAPTERS` SHALL appear in the guidance with no edit outside the registry

#### Scenario: A registration capability without a fact fails the guard

- GIVEN an `ADAPTERS` entry whose `env` capability has no guidance template
- WHEN the single-source guard runs
- THEN it SHALL fail, so no agent ships with missing or invented guidance

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

- GIVEN `sofer_init(name="test", user="<hf-user>", cwd="Desktop/test")`
- WHEN the call executes
- THEN `ok:true` and `Desktop/test/test.toml` SHALL contain `repo_id = "<hf-user>/test"`

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

Canonical branches: greenfield `sofer_init -> sofer_scan_dry_run -> sofer_scan_apply -> sofer_meta_set -> sofer_validate`; existing-config `sofer_validate -> sofer_file_set -> sofer_prepare -> sofer_codebook_all -> sofer_profile_all -> sofer_render_all`; single-file triage `sofer_codebook` / `sofer_profile` / `sofer_render`; delivery `sofer_auth_status -> sofer_publish(dry_run=true) -> HUMAN APPROVAL STOP -> sofer_publish_confirm`.

A bound continuation SHALL additionally carry `arguments.root` when the call's effective per-call root differs from the registration root (MSP-R21); today's payloads stay byte-identical otherwise.

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

---

### Requirement: Scan extensions filter (MSP-R14)

> Added by change `fix-scan-parity-mcp` (closes #154).

`sofer_scan_dry_run` and `sofer_scan_apply` SHALL accept an `extensions: list[str] | None = None` argument. When omitted, all supported formats SHALL be scanned (current behavior). When supplied, only files whose suffix matches one of the given extensions SHALL be discovered, moved, and copied. Suffixes SHALL be accepted with or without a leading dot, case-insensitively; any suffix not in `SUPPORTED_FORMATS` SHALL be refused with a clear error before any mutation. The filter SHALL apply to BOTH phases when `move_loose=True`.

#### Scenario: Filter restricts discovery

- GIVEN a scan tool call with `extensions=["csv"]` and a directory containing both `.csv` and `.xlsx` loose files
- WHEN the tool runs
- THEN only the `.csv` files SHALL be discovered/registered/copied
- AND the `.xlsx` files SHALL be untouched

#### Scenario: Unsorted suffix forms accepted

- GIVEN `extensions=["csv", ".parquet"]`
- WHEN the tool runs
- THEN both `csv` and `parquet` files SHALL be included

#### Scenario: Unsupported extension refused

- GIVEN `extensions=["txt"]`
- WHEN the tool runs
- THEN an `ok:false` refusal SHALL be returned before any mutation
- AND the error SHALL name the unsupported suffix and the supported set
---

### Requirement: Scan Phase-1 move is mandatory (MSP-R15) — Modified 2026-10-18, fix-scan-registered-count

> Added by change `fix-scan-parity-mcp` (closes #152). Modified by `fix-scan-move-raw-mandatory` (issue
> #339) — the opt-in became a mandate; this `mcp-server` clause was missed then and corrected by
> `feat-visibility-enforcement` (issue #338) when the divergence was found. Modified by
> `fix-scan-registered-count` (issue #345) — the `registered` integer in both scan envelopes is the
> merge's own count.

`sofer_scan_dry_run` and `sofer_scan_apply` SHALL run the Phase-1 MOVE (see MST-R06) unconditionally: no
argument SHALL allow skipping it, because `cache/` is the shared, deletion-prone staging directory and
the registered sources MUST NOT live only there. `sofer_scan_dry_run` SHALL preview the moves with no
mutation. Collisions against existing `raw/` destinations SHALL abort atomically before any move
(`registered: 0`, TOML untouched). `sofer_scan_apply` SHALL report `moved: int` in a successful envelope
(declared in `output_schema`).

`registered: int` in both scan envelopes SHALL be the number of `[[file]]` entries the merge of that
same call appended, as reported by the merge itself and never as a before/after difference of entry
counts (#345). `[[file]]` placeholders the merge strips (`TODO:`, `raw/example*`) SHALL NOT be
subtracted from it, so on a fresh `sofer_init` tree the field SHALL equal the number of newly
registered files (`discovered` when nothing was registered before) and SHALL agree with the TOML
written by the same call. Both tools SHALL report the same value for the same tree, and an idempotent
re-scan SHALL report `registered: 0`. The field's `description` in both `output_schema` blocks SHALL
state this meaning.

#### Scenario: Dry-run previews the mandatory move without mutation

- GIVEN a loose file outside `raw/`/`cache/`
- WHEN `sofer_scan_dry_run` runs with only `config`
- THEN the output SHALL show `-> raw/<rel>` and name the move as mandatory
- AND no file SHALL be moved, `raw/` SHALL NOT be scaffolded, and the TOML SHALL be untouched

#### Scenario: Collision aborts before any move

- GIVEN a loose file whose `raw/` destination already exists
- WHEN `sofer_scan_apply` runs
- THEN an `ok:false` refusal SHALL be returned naming the collision
- AND the loose file SHALL remain at its original path and the TOML SHALL be untouched

#### Scenario: There is no opt-out

- GIVEN loose supported files and no extra arguments
- WHEN `sofer_scan_apply` runs
- THEN the loose files SHALL end up under `raw/` with their tree and the envelope SHALL report `moved`
- AND no parameter SHALL exist that skips the move

#### Scenario: The init placeholders are not subtracted from the count (#345)

- GIVEN a fresh `sofer_init` tree with N loose supported files and the two `raw/example*` placeholders in the TOML
- WHEN `sofer_scan_apply` runs, and separately `sofer_scan_dry_run` on a second identical tree
- THEN both SHALL report `registered: N` while the written TOML holds N `[[file]]` entries
- AND an immediate re-scan of the applied tree SHALL report `registered: 0`
---

### Requirement: Publish cleanup (MSP-R16)

> Added by change `fix-residual-parity` (closes #153).

`sofer_publish` and `sofer_publish_confirm` SHALL accept `clean: bool = False`
and `clean_cache: bool = False`, forwarded verbatim to `publish.publish(...)`.
Cleanup SHALL follow PUB-11 and live in the domain: the build directory (hf
target) or the local destination is deleted ONLY after a successful delivery —
never on dry-run, quality-gate block, or failure. `clean_cache=True` without
`clean=True` SHALL be refused — never silently ignored — with `error_code`
`CLEAN_CACHE_WITHOUT_CLEAN` and a `next` hint to set `clean=True` (explicit
opt-in: a caller cannot enable cache deletion as a side effect).

#### Scenario: clean deletes the build after success and keeps cache/

- GIVEN a successful HF delivery with `clean=True, clean_cache=False`
- WHEN `sofer_publish_confirm` completes
- THEN the build directory SHALL be deleted
- AND `cache/` SHALL remain (tool-wide sibling-shared state untouched)

#### Scenario: clean_cache without clean is refused

- GIVEN `clean_cache=True` and `clean` omitted or `False`
- WHEN either publish tool runs
- THEN an `ok:false` refusal SHALL be returned with `error_code`
  `CLEAN_CACHE_WITHOUT_CLEAN`
- AND no directory SHALL be deleted
- AND the hint SHALL name `clean=True` as the fix

#### Scenario: Dry-run never deletes

- GIVEN `clean=True` on a dry-run call (default for `sofer_publish`)
- WHEN the tool runs
- THEN the result SHALL be a plan only
- AND no build or cache directory SHALL be deleted
---

### Requirement: Batch codebook max_sample (MSP-R17)

> Added by change `fix-residual-parity` (closes #155).

`sofer_codebook_all` SHALL accept `max_sample: int | None = None`, forwarded to
`codebook.generate_all(...)`. `None` SHALL resolve to
`[tool.sofer] codebook_max_sample` (default `100_000`) at call time — the same
resolution the single-file path uses (CB-R08); never a frozen literal. Each
per-file codebook SHALL cap analysis at `min(total_rows, max_sample)` and SHALL
label the header `**Analysed rows:** N (sample)` when capped, `(full scan)`
when the file fits.

#### Scenario: Override applies

- GIVEN a batch TOML config whose files exceed the cap
- WHEN `sofer_codebook_all(config, max_sample=1)` runs
- THEN every emitted codebook SHALL report `**Analysed rows:** 1 (sample)`
- AND the sampling cap SHALL apply to each per-file codebook

#### Scenario: Omitted uses the config default

- GIVEN `[tool.sofer] codebook_max_sample` configured (or its default) and
  files below the cap
- WHEN `sofer_codebook_all` runs without `max_sample`
- THEN the batch SHALL analyse up to the configured rows per file
- AND codebooks whose files fit SHALL report `(full scan)`

---

### Requirement: Optional explicit CSV dialect parameters (MSP-R18)

> Added by change `2026-09-25-csv-dialect-override` (GitHub #204).

`sofer_codebook`, `sofer_codebook_all`, `sofer_profile`, and `sofer_profile_all`
SHALL each expose optional `delimiter` / `encoding` parameters defaulting to
`None` ("not supplied"). Their descriptions SHALL state that the configured value
applies when omitted. Resolution SHALL be **explicit parameter → resolved config
(tool-wide post-reload `config.CSV_*` for `sofer_codebook` / `sofer_profile`;
dataset `[meta] cfg.csv_*` for `sofer_codebook_all`; tool-wide for
`sofer_profile_all`) → the existing reader fallback**. The explicit value SHALL
win. `None` SHALL be the only "not supplied" signal, and the omitted path's dialect
resolution SHALL be unchanged.

When at least one explicit parameter is supplied, the tool SHALL add a `dialect`
key to its **successful** return envelope (e.g. `{"delimiter": ",", "encoding":
null}`) echoing the supplied override, so the result is traceable. The key SHALL
be declared in the tool's `output_schema` (so FastMCP validation does not drop it)
and SHALL be `null` when neither parameter is supplied. Error/refusal envelopes
are not required to carry it (the read may never have happened). No parameter
SHALL be required, and MSP-R06's non-interactivity contract SHALL hold — an
omitted optional parameter is not a prompt. `.tsv` SHALL remain tab-delimited;
the explicit delimiter SHALL apply to `.csv`.

#### Scenario: explicit delimiter wins over config

- GIVEN `csv_delimiter = ";"` in `[tool.sofer]` and a `.csv` using `,`
- WHEN `sofer_codebook(path, delimiter=",")` runs
- THEN the codebook SHALL reflect the explicit `,`

#### Scenario: omitted parameters are unchanged

- GIVEN the same file and config
- WHEN `sofer_codebook(path)` runs without the parameters
- THEN the resolved dialect SHALL be the configured one
- AND the envelope `dialect` SHALL be `null`

#### Scenario: dialect echo when supplied

- GIVEN an explicit `delimiter` and/or `encoding`
- WHEN any of the four tools runs
- THEN its envelope SHALL carry a `dialect` object echoing the supplied value(s)
- AND `dialect` SHALL be `null` when neither is supplied

#### Scenario: batch parameter wins over dataset [meta]

- GIVEN a dataset whose `[meta] csv_delimiter` is `;` and CSV files using `,`
- WHEN `sofer_codebook_all(config, delimiter=",")` runs
- THEN every emitted codebook SHALL reflect the explicit `,`

#### Scenario: every parameter has a description

- GIVEN `tools/list` for the four tools
- WHEN the input schemas are inspected
- THEN `delimiter` and `encoding` SHALL each carry a description stating the fallback
- AND neither SHALL be in the `required` list

#### Scenario: batch output_dir descriptions name the resolved default

- GIVEN `tools/list` for `sofer_profile_all` and `sofer_render_all`
- WHEN the `output_dir` descriptions are inspected
- THEN each SHALL name `<output_dir>/<sub-directory>` and the resolved default composed from the
  configured cache root and the configured sub-directory
- AND neither SHALL present the bare `profiles` / `renders` as the whole default

#### Scenario: scan tools gain no inert parameter

- GIVEN `tools/list` for `sofer_scan_dry_run` / `sofer_scan_apply`
- WHEN the input schemas are inspected
- THEN neither SHALL expose `delimiter` or `encoding`
- AND their behaviour SHALL be unchanged

### Requirement: Assisted failure reporting tool with duplicate search (MSP-R19)

> Added by change `2026-09-25-feat-mcp-failure-report` (issue #244).

The server MUST expose a 15th tool, `sofer_report_failure(error, command="", trace="", confirm=false,
force=false)`, that prepares a confidential failure report and files it through `gh` only when
`confirm=true`. With the default `confirm=false` it MUST return the prepared `title`, `body`,
`manual_url` and any `duplicates` while creating nothing and never calling the send path. The report
MUST reuse the shared reporter contract: no dataset contents, no environment-variable values, and
home paths replaced by `~`.

Before filing, the tool MUST search the repository's **open** issues for duplicates (via
`gh issue list --search`) and, when matches exist and `force` is not set, MUST surface them in the
envelope with `error_code = "DUPLICATE_REPORT"` instead of filing a redundant report. With
`force=true` (and `confirm=true`) the tool MUST file despite matches.

When `confirm=true` and filing succeeds, the envelope MUST report `created=true` and the created
`issue_url`. When `gh` is missing, unauthenticated, or offline, the tool MUST NOT lose the report:
it MUST persist exactly one timestamped file under the configured state directory and return the
`persisted_path`, the `retry_command`, the manual `github.com/<repo>/issues/new` URL, and a
`gh auth login` hint (`error_code = "REPORT_PERSISTED"`).

#### Scenario: Prepared report creates nothing without confirmation

- GIVEN an agent calls `sofer_report_failure(error=..., command=...)` with the default `confirm=false`
- WHEN the tool returns
- THEN `created` SHALL be `false` and no issue SHALL be filed
- AND the envelope SHALL carry the prepared `title`, `body`, `manual_url` and `duplicates`
- AND `hints.action` SHALL be `confirm_report_failure`

#### Scenario: Matching open issues are surfaced instead of a redundant report

- GIVEN `confirm=true`, no `force`, and the duplicate search returns at least one open issue
- WHEN the tool runs
- THEN it SHALL NOT file a new issue
- AND the envelope SHALL return `error_code = DUPLICATE_REPORT` with the matching issues in `duplicates`

#### Scenario: Confirmed filing creates the issue

- GIVEN `confirm=true` and a working authenticated `gh` with no blocking duplicates (or `force=true`)
- WHEN the tool runs
- THEN `created` SHALL be `true` and `issue_url` SHALL name the created issue

#### Scenario: Filing failure persists with the recovery layers

- GIVEN `confirm=true` and `gh` missing, unauthenticated, or offline
- WHEN the tool runs
- THEN `error_code` SHALL be `REPORT_PERSISTED`
- AND the envelope SHALL name the persisted `persisted_path`, the `retry_command`, the manual issue URL, and a `gh_auth_login` hint

#### Scenario: Report excludes secrets and anonymizes home paths

- GIVEN an error message containing a home-directory path and an environment variable value present in the process
- WHEN the report is prepared
- THEN the home directory SHALL appear as `~` and the absolute home path SHALL be absent
- AND the environment-variable value SHALL NOT appear anywhere in the envelope
- AND no dataset content SHALL appear

### Requirement: The metadata step is in the agent-facing surface (MSP-META-01) — Modified 2026-10-16, feat-meta-tools

The canonical chain the server advertises SHALL name the metadata step — filling `[meta]`
`description`, `license`, `source` and `tags` — between bootstrap and Phase 1, because an MCP consumer
has no source of truth other than the descriptions and envelopes it receives, and a required step that
is absent from them cannot be inferred (issue #288).

`sofer_validate`'s description SHALL require `[meta] description/license/source/tags filled (no
placeholders)` and `sofer_prepare`'s SHALL require that validation passed with no placeholder warning;
the workflow registry SHALL carry the same requirement for `sofer_validate`. `sofer_init`'s
continuation SHALL name filling `[meta]` before registering files.

`sofer_validate` — and the pre-prepare run, which shares the validator — SHALL emit one **warning** per
`[meta]` scalar field (`description`, `license`, `source`) that is empty or begins with one of the
`meta_placeholder_prefixes` values (`[tool.sofer]`, case-insensitive), plus one warning for placeholder
`tags`. The force SHALL be a warning and SHALL NOT change the exit code or `ValidationReport.passed`: a
failure would break every existing config that still carries a placeholder, which is a contract change
rather than a fix (maintainer decision D3).

The step SHALL also have a **tool surface**, because an MCP consumer that reads the warning has no
other way to write a file (issue #323). `sofer_meta_check(config)` SHALL report the same warnings
on demand, read-only (`readOnlyHint: true`), and SHALL be informational by the same D3 rule: `ok`
true and exit code 0 whatever it reports, with the count in `placeholders` and the messages in
`warnings`. `sofer_meta_set(config, values, dry_run)` SHALL write only the `[meta]` keys it is
given — every key `DatasetConfig` reads is settable — into the dataset TOML under the server root,
preserving every other key and comment, with containment via `_contained_path`, an atomic replace,
and a refusal that writes nothing when the edited document would not parse or would lose a
requested value. It SHALL name a `build/` tree that predates the write (`build_stale`) rather than
refuse, and SHALL be idempotent: re-running with the values the file already holds SHALL write
nothing. Called without `values` it SHALL write nothing, report the placeholders that still need a
value, and return a continuation with `input_required: ("values",)` — so the registry continuation
from bootstrap stays executable (MSP-R13). The chain SHALL carry the step: `sofer_scan_apply`’s
continuation SHALL be `sofer_meta_set`, `sofer_meta_set`’s SHALL be `sofer_validate`, and
`sofer_meta_check`’s SHALL be `sofer_meta_set` (issue #323 §5). The CLI SHALL mirror both surfaces
(`sofer meta check`, `sofer meta set`; CLI-R16).

#### Scenario: The metadata step is in the chain the agent reads — issue #288

- GIVEN the server is built
- WHEN its instructions and `tools/list` descriptions are read
- THEN the instructions SHALL name the metadata step before Phase 1
- AND `sofer_validate`'s description SHALL require `[meta] description/license/source/tags filled (no placeholders)`
- AND `sofer_init`'s continuation SHALL name filling `[meta]`

**Evidence:** `test: tests/test_mcp_server.py::TestMetadataStepInTheAdvertisedChain::test_server_instructions_name_the_metadata_step`, `test: tests/test_mcp_server.py::TestMetadataStepInTheAdvertisedChain::test_validate_requires_filled_meta`, `test: tests/test_mcp_server.py::TestMetadataStepInTheAdvertisedChain::test_init_next_points_at_the_metadata_step`, `test: tests/test_mcp_server.py::TestMetadataStepInTheAdvertisedChain::test_the_workflow_registry_carries_the_requirement`

#### Scenario: A placeholder warns without failing the run — issue #288

- GIVEN a dataset TOML whose `[meta]` values are the `sofer init` template's placeholders
- WHEN `sofer_validate` runs (or the pre-prepare validation does)
- THEN the report SHALL carry one warning per offending field, naming it
- AND `ValidationReport.passed` SHALL remain `True` and the exit code SHALL be unchanged

**Evidence:** `test: tests/test_checks.py::TestMetaPlaceholderGate::test_each_placeholder_field_warns`, `test: tests/test_checks.py::TestMetaPlaceholderGate::test_the_warning_reaches_the_report_and_keeps_passed_true`, `test: tests/test_checks.py::TestMetaPlaceholderGate::test_the_warning_is_visible_in_the_printed_summary`

#### Scenario: The metadata step has a tool surface — issue #323

- GIVEN a dataset TOML whose `[meta]` values are the `sofer init` template's placeholders
- WHEN `sofer_meta_check` runs
- THEN it SHALL report `placeholders: 4` and four `warnings`, with `ok: true` and exit code 0
- AND the file SHALL be byte-identical afterwards
- AND `sofer_meta_set` with `values` SHALL write them into `[meta]`, preserving every other key and comment, and report the state the edit leaves behind in `placeholders`/`warnings`
- AND `sofer_meta_set` with an unknown key SHALL refuse with `CONFIG_ERROR` and write nothing
- AND `sofer_meta_set` with no `values` SHALL write nothing and return a continuation with `input_required: ["values"]`

**Evidence:** `test: tests/test_mcp_server.py::TestMetaTools::test_check_reports_every_placeholder_and_writes_nothing`, `test: tests/test_mcp_server.py::TestMetaTools::test_set_writes_the_values_and_reports_them`, `test: tests/test_mcp_server.py::TestMetaTools::test_set_refuses_an_unknown_key_with_nothing_written`, `test: tests/test_mcp_server.py::TestMetaTools::test_set_without_values_reports_the_state_and_asks_for_them`, `test: tests/test_mcp_server.py::TestMetaTools::test_set_reports_the_state_the_edit_leaves_behind`

#### Scenario: The metadata step is reachable from tools/list — issue #323 §5

- GIVEN the server is built
- WHEN the workflow registry and the tool descriptions are read
- THEN `sofer_scan_apply`'s continuation SHALL be `sofer_meta_set`, its SHALL be `sofer_validate`, and `sofer_meta_check`'s SHALL be `sofer_meta_set`
- AND the server instructions SHALL name both tools in the metadata step, before Phase 1
- AND `sofer_init`'s continuation SHALL name `sofer_meta_set`
- AND the metadata step SHALL NOT be described as manual

**Evidence:** `test: tests/test_mcp_server.py::TestMetaTools::test_the_registry_chain_is_executable`, `test: tests/test_mcp_server.py::TestMetaTools::test_the_instructions_name_both_tools`, `test: tests/test_mcp_server.py::TestMetaTools::test_init_next_names_the_setter`, `test: tests/test_workflow.py::test_greenfield_branch_chain`

#### Scenario: Only a prefix marks a placeholder — issue #288

- GIVEN a value that contains a prefix but does not start with one, and one that does
- WHEN the gate runs
- THEN only the value beginning with a prefix SHALL be reported
- AND the match SHALL be case-insensitive
- AND an empty `tags` list SHALL NOT warn, because there is no value to replace

**Evidence:** `test: tests/test_checks.py::TestMetaPlaceholderGate::test_a_real_value_merely_containing_a_prefix_is_fine`, `test: tests/test_checks.py::TestMetaPlaceholderGate::test_the_match_is_case_insensitive`, `test: tests/test_checks.py::TestMetaPlaceholderGate::test_an_empty_value_warns_for_the_three_scalars`, `test: tests/test_checks.py::TestMetaPlaceholderGate::test_an_example_prefixed_source_is_flagged`

#### Scenario: The prefixes are configuration — issue #288

- GIVEN `[tool.sofer] meta_placeholder_prefixes` is changed
- WHEN the gate runs
- THEN it SHALL use the configured values, not a literal

**Evidence:** `test: tests/test_checks.py::TestMetaPlaceholderGate::test_prefixes_are_config_owned`

---

### Requirement: The [[file]] registration surface is writable over MCP (MSP-R22) — Added 2026-10-19, issue #344

`sofer_init`'s template advertises a recursive folder entry, and `FileEntry` implements `recursive`,
`convert_to_parquet`/`upload_as_csv`, `include_in_schema` and `column_types` downstream, but the only
writer of `[[file]]` blocks (`scanner.merge_entries`) emits one flat entry per discovered file. An
MCP-driven run could therefore reach the template's own folder shape only by leaving the tool surface.

`sofer_file_set(config, entries, dry_run=False)` SHALL replace the dataset TOML's `[[file]]` array with
`entries`, preserving every other key, table and comment in the document. Each entry SHALL accept
`local` (required), `remote` (required), `recursive`, `convert_to_parquet`, `upload_as_csv`,
`include_in_schema` (booleans) and `column_types` (a table of `column = "type"` whose values belong to
`config.COLUMN_TYPES_SUPPORTED`); an unknown key or a wrong value kind SHALL be refused with
`CONFIG_ERROR` and nothing written, naming the accepted set. Every `local` SHALL resolve under the
containment root and exist, a `recursive` entry SHALL point at a directory and a non-recursive entry at a
file; every `remote` SHALL be safe (`_remote_is_unsafe`) and unique; a recursive entry's remote folder
SHALL NOT contain another entry's remote (the double-registration a folder entry makes easy). An empty
`entries` list SHALL be refused while the file still registers entries, so a careless call cannot erase
the registrations. The edit SHALL be atomic, SHALL parse and round-trip before it is committed, SHALL be
idempotent, and SHALL write nothing under `dry_run`. Its continuation SHALL be `sofer_validate`.

#### Scenario: A recursive folder entry and column_types are writable over MCP — issue #344

- GIVEN a dataset TOML with flat `[[file]]` entries and a `Labels/` folder of CSVs
- WHEN `sofer_file_set` runs with one file entry carrying `column_types` and one `recursive` folder entry
- THEN the TOML SHALL carry both shapes, the model SHALL load them, and `changed` SHALL be `true`
- AND every comment and unrelated table SHALL be byte-identical

**Evidence:** `test: tests/test_file_edit.py::TestSoferFileSet::test_writes_recursive_folder_and_column_types`, `test: tests/test_file_edit.py::TestApplyFileEdit::test_replaces_entries_and_preserves_every_other_byte`

#### Scenario: Unsafe entries are refused with nothing written — issue #344

- GIVEN a dataset TOML
- WHEN `sofer_file_set` receives an unknown key, a `local` outside the root, or a folder remote that
  would double-register a file entry
- THEN it SHALL refuse with `CONFIG_ERROR` and the TOML SHALL be byte-identical

**Evidence:** `test: tests/test_file_edit.py::TestSoferFileSet::test_unknown_key_is_refused`, `test: tests/test_file_edit.py::TestSoferFileSet::test_local_outside_root_is_refused`, `test: tests/test_file_edit.py::TestSoferFileSet::test_folder_and_file_remote_collision_is_refused`

#### Scenario: Empty entries cannot erase registrations — issue #344

- GIVEN a dataset TOML that already registers entries
- WHEN `sofer_file_set` runs with `entries=[]`
- THEN it SHALL refuse and write nothing

**Evidence:** `test: tests/test_file_edit.py::TestSoferFileSet::test_empty_entries_refuse_to_erase_registrations`

---

### Requirement: Visibility control with an explicit gate (MSP-R20) — Added 2026-10-17, feat-visibility-enforcement

`sofer_repo_settings` SHALL report the target repository's current visibility together with the
configured posture, and SHALL change it only when the call carries the approval phrase and the exact
target state (`private: bool`). A read SHALL NOT require an authorization, SHALL change nothing, and
SHALL report an unreachable or unreadable remote as an explicit `unknown: <reason>` value rather than
raising — an unknown state is never reported as agreement. Without a token the read SHALL say
`unknown: no token` and SHALL NOT call the Hub.

A write SHALL be refused when no approval phrase is configured on the server
(`REPO_SETTINGS_APPROVAL_NOT_CONFIGURED`), when the supplied phrase does not match
(`REPO_SETTINGS_APPROVAL_REQUIRED`), when there is no token (`REPO_SETTINGS_TOKEN_REQUIRED`), and when
the installed `huggingface-hub` has no `HfApi.update_repo_settings` (`REPO_SETTINGS_UNSUPPORTED`,
naming the method). A failed write SHALL surface as `REPO_SETTINGS_WRITE_FAILED` with its cause. After a
successful write the tool SHALL re-read and report `changed` plus `diverges_from_config`.

#### Scenario: A read needs no authorization

- GIVEN a dataset TOML and a token
- WHEN `sofer_repo_settings` runs with only `config`
- THEN the envelope SHALL carry the configured posture and `remote_visibility`
- AND nothing SHALL be changed on the Hub

#### Scenario: A write without the phrase is refused

- GIVEN `private=false` and a server with an approval phrase configured
- WHEN `sofer_repo_settings` runs without `approval_phrase`
- THEN it SHALL refuse with `REPO_SETTINGS_APPROVAL_REQUIRED` and SHALL NOT call the Hub

#### Scenario: A dry run predicts without writing

- GIVEN a repository whose visibility differs from the requested one
- WHEN `sofer_repo_settings` runs with `private` and `dry_run=true`
- THEN it SHALL report `would_change: true` with `changed: false` and SHALL NOT call the Hub

#### Scenario: An SDK without the settings method fails closed

- GIVEN an installed `huggingface-hub` whose `HfApi` has no `update_repo_settings`
- WHEN a write is attempted with a valid phrase
- THEN it SHALL refuse with `REPO_SETTINGS_UNSUPPORTED` naming the method

#### Scenario: A write that disagrees with the config is reported

- GIVEN `[dataset] private = true` and a write that makes the repository public
- WHEN the write succeeds
- THEN the envelope SHALL report `diverges_from_config: true`
- AND the next `sofer_publish_confirm` SHALL refuse that divergence (PUB-13)


---

### Requirement: Per-call containment root (MSP-R21) — Added 2026-10-19, issue #347

The containment root was bound once at `build_server`, so an agent could not operate on a dataset
outside it without editing the host registration and restarting. Every path-bearing tool — 18 of the 19
callables; `sofer_report_failure` is excluded — SHALL accept `root: str | None = None` as its LAST
parameter, with a non-empty description. Omitted, empty or whitespace-only `root` SHALL mean unset and
keep the registration root's behavior byte-identical.

For a given `root` the server SHALL `expanduser`, anchor a relative value on the registration root
(never the ambient cwd), `resolve()` it, require an existing directory, and then apply
`SOFER_MCP_ROOT_ALLOWLIST` when configured. A missing path, a file, or a root outside every allowlist
entry SHALL raise `RootUnavailableError` (an `MCPToolError`), naming the resolved path — it SHALL NOT
travel through the 10.3 error envelope, whose `error_code` enum stays unchanged. Legal `..` roots are
admitted when they resolve to an existing directory: `root` IS the boundary, not a path contained in
one. A relative root SHALL NOT be interpreted against the process cwd.

`SOFER_MCP_ROOT_ALLOWLIST` SHALL be read exactly once in `build_server`, split on `os.pathsep` (never
commas, which are legal path characters), with blank segments dropped and entries resolved; an entry
admits itself and its descendants. The registration root and every omitted-`root` call SHALL NEVER be
gated. The per-call root SHALL be the containment boundary for every resolution anchor of that call
(`_contained_path`, `[tool.sofer]` discovery, `[[file]]`/doc/output-target checks, `sofer_init.cwd`)
and SHALL be unbound when the call ends — a failure SHALL leave no bound root.

Every dict envelope (success, refusal, error) SHALL echo `effective_root` as the resolved absolute path;
`output_schema` SHALL declare it as an optional string through `_ERROR_ENVELOPE_SCHEMA_FIELDS`, with
`required` unchanged. A bound continuation SHALL carry `next.arguments.root` only when the effective
root differs from the registration root, so today's chain payloads stay byte-identical. Resources,
prompts, `workflow.py`, `execution_context.py`, the 10.3 enum, the publish ladder and
`sofer_report_failure` SHALL stay outside this mechanism; reading another dataset tree is done through
the tool with `root`, not through a `sofer://` URI.

#### Scenario: Omitted root is byte-identical to the previous behavior

- GIVEN a server built with root R and a dataset there
- WHEN a path-bearing tool runs without `root` (or with `""` / whitespace)
- THEN it SHALL resolve against R and the envelope SHALL report `effective_root == R`
- AND `next.arguments` SHALL NOT gain a `root` key

**Evidence:** `test: tests/test_per_call_root.py::TestResolution::test_omitted_root_keeps_the_registration_root`, `test: tests/test_per_call_root.py::TestResolution::test_blank_root_is_unset`

#### Scenario: A foreign root runs the call in that tree and roots the continuation

- GIVEN a valid dataset outside the registration root
- WHEN `sofer_validate(config, root=<foreign>)` runs
- THEN it SHALL validate against the foreign tree and echo `effective_root`
- AND replaying `next.arguments` verbatim SHALL run `sofer_prepare` successfully in that tree

**Evidence:** `test: tests/test_per_call_root.py::TestResolution::test_foreign_root_runs_there_and_is_echoed`, `test: tests/test_per_call_root.py::TestEnvelopeAndChain::test_the_validate_chain_replays_in_the_foreign_directory`

#### Scenario: Relative roots anchor on the registration root

- GIVEN the process cwd is a third directory and `root="sibling"` exists under the registration root
- WHEN the tool runs
- THEN the effective root SHALL be the resolved `registration_root/sibling`, never a cwd-relative path

**Evidence:** `test: tests/test_per_call_root.py::TestResolution::test_relative_root_anchors_on_the_registration_root`

#### Scenario: Unusable roots are typed failures with no leak

- GIVEN a missing path or a regular file passed as `root`
- WHEN the tool runs
- THEN `RootUnavailableError` SHALL be raised naming the resolved path
- AND the next call without `root` SHALL resolve against the registration root

**Evidence:** `test: tests/test_per_call_root.py::TestResolution::test_missing_root_raises_a_typed_error`, `test: tests/test_per_call_root.py::TestResolution::test_file_root_raises_a_typed_error`, `test: tests/test_per_call_root.py::TestResolution::test_a_failure_leaves_no_bound_root`

#### Scenario: The allowlist admits its entries and never gates the default

- GIVEN `SOFER_MCP_ROOT_ALLOWLIST` names one directory
- WHEN a call asks for that directory or a descendant
- THEN it SHALL be admitted
- AND a root outside every entry SHALL raise `RootUnavailableError` naming the variable
- AND an omitted-`root` call SHALL be admitted even when the registration root is excluded
- AND an entry containing a comma SHALL survive intact

**Evidence:** `test: tests/test_per_call_root.py::TestAllowlist`

#### Scenario: The schema surface comes from the signature and one schema home

- GIVEN `tools/list`
- WHEN the 18 path-bearing tools are inspected
- THEN each SHALL declare an optional `root` string with a non-empty description
- AND `sofer_report_failure` SHALL NOT
- AND every tool's `output_schema` SHALL declare `effective_root`, never required

**Evidence:** `test: tests/test_per_call_root.py::TestSchemaSurface`

#### Scenario: Concurrent calls keep their own root

- GIVEN two datasets, each outside the registration root
- WHEN two tool calls with distinct roots run concurrently
- THEN each envelope SHALL name its own `effective_root`
- AND no root SHALL remain bound afterwards

**Evidence:** `test: tests/test_per_call_root.py::TestResolution::test_concurrent_calls_do_not_leak_roots`

---

### Requirement: Init admission gate (MSP-R23) — Added 2026-10-21, issue #360

Every MCP session SHALL require one explicit, successful `sofer_init` before any
other registered tool runs or any data-bearing resource is read. `sofer_init`
SHALL be the only tool admitted while the session is uninitialized. The policy
SHALL be enforced at the common dispatch/middleware boundary — never in
`_load_dataset`, per-handler checks, prompts, tool order, or an agent-side
convention — so a future registered tool is protected automatically. Unknown
tools keep the framework's standard error and never change readiness.

A session is one live framework session. Its state SHALL be server-owned,
SHALL NOT be persisted, and SHALL NOT be keyed by a client-supplied identifier.
It SHALL be stored on the framework-owned per-session outbound channel
(`ctx.request_context.session._connection.outbound`, fastmcp 4.0.11), because
the modern protocol rebuilds the request-scoped `Connection`/`ServerSession`
per request; a runnable lifecycle test SHALL pin that API. A new client
session, a re-established transport, or a server restart SHALL start
uninitialized; a transport with no live session SHALL refuse protected
operations with `INITIALIZATION_SESSION_UNAVAILABLE`.

States SHALL be `U` (uninitialized), `I` (initializing), and `R(A)` (ready for
one root `R` and config `C`). An admitted init SHALL discard the previous
context BEFORE validating its own arguments. A non-dry-run success SHALL
publish the new context atomically; a preview, refusal, exception, or
cancellation SHALL settle in `U` and NEVER restore the discarded context. An
ordinary matching request SHALL be admitted against an immutable snapshot and
SHALL NOT revoke readiness. A request for another root/config SHALL return
`INITIALIZATION_CONTEXT_MISMATCH` without switching. A second init while one
runs SHALL return `INITIALIZATION_IN_PROGRESS`; an init while an admitted
request still executes SHALL return `INITIALIZATION_CONTEXT_BUSY` and keep the
active context. Leases SHALL be released when the handler work actually stops,
including after a cancelled await. The existing server-wide tool serialization
and progress heartbeat SHALL remain.

`sofer_init` SHALL accept an optional non-blank `config` to ATTACH an existing
TOML: it resolves under the call root, parses with the model parser, derives
`[dataset] name` and the `repo_id` owner, and matches any supplied `name`/`user`
as exact assertions. Attach SHALL perform no writes, directory creation, file
moves, package generation, network access, or overwriting, and SHALL keep the
ACTUAL config path as `C` (a filename unrelated to the dataset name is
authoritative; `DatasetIdentity.config_path` SHALL NOT replace it). In attach
mode `cwd` MUST be omitted and `force`/`move_existing` MUST be false. An
empty/whitespace `config` SHALL be `CONFIG_ERROR` and SHALL NOT select create
mode; a missing, invalid, unreadable, or disallowed config SHALL NEVER fall back
to creation. Create mode SHALL retain the existing identity, containment,
collision, opt-in move, dry-run, and explicit `force` semantics. Both modes
SHALL return `session_ready` (`true` only on a completed non-dry-run success),
`initialization_mode`, the actual `config_path`, `dataset_root`, and
`effective_root` (`R`); a preview SHALL return `session_ready: false` and a
continuation to the same init with `dry_run: false`. Success continuations:
create -> `sofer_scan_dry_run`; attach -> `sofer_meta_check`.

Matching SHALL bind every non-init tool to the active root `R`; configuration
tools additionally require canonical `config == C`. An omitted/blank `root`
SHALL keep the registration-root semantics and SHALL NOT inherit the root of
the last init. Standalone path tools SHALL be bound only by `R`. Content
resources SHALL be blocked before init, SHALL satisfy the existing
registration-root containment AND live inside `R`, and `sofer://dataset/...`
SHALL additionally require `C`; `sofer://status`, capability/resource
listing, and the three static prompts SHALL remain available without init and
SHALL never grant readiness.

Refusals SHALL use `ok:false`, `exit_code:1`, `output`, `error_code`,
`message`, `next`, and an EMPTY `config_errors`; `CONFIG_ERROR` keeps the
envelope with real diagnostics. Resource refusals SHALL be MCP resource errors
whose message is the JSON-encoded envelope, with `next.action =
"resources/read"` and `next.uri`. `INITIALIZATION_REQUIRED` SHALL suggest an
executable attach when the target config is known (otherwise
`input_required: ["config"]`), and `SESSION_UNAVAILABLE` SHALL carry
`next: {}`.

#### Scenario: Every registered non-init tool is refused before its handler

- GIVEN a fresh session and a valid dataset tree
- WHEN any registered non-init tool is called, with valid or invalid business args
- THEN it SHALL return `INITIALIZATION_REQUIRED` before argument validation or handler entry
- AND the tree SHALL be byte-identical afterwards
- AND an unknown tool SHALL keep the framework's standard error

**Evidence:** `test: tests/test_mcp_admission.py::TestDefaultDeny`

#### Scenario: Discovery stays available without init

- GIVEN a fresh session
- WHEN tools/resources/prompts are listed, a static prompt is retrieved, or `sofer://status` is read
- THEN all SHALL succeed
- AND a subsequent protected call SHALL still be refused

**Evidence:** `test: tests/test_mcp_admission.py::TestDefaultDeny::test_discovery_is_available_without_init`

#### Scenario: Attach binds the session read-only to the actual config path

- GIVEN an existing model-valid TOML whose filename is not `<name>.toml`
- WHEN `sofer_init(config=...)` runs without name/user
- THEN it SHALL return `session_ready: true`, `initialization_mode: "attach"`, the actual `config_path`, and `dataset_root`
- AND the tree SHALL be byte-identical afterwards
- AND the next protected call for that config SHALL be admitted

**Evidence:** `test: tests/test_mcp_admission.py::TestModeContract::test_attach_without_identity_and_nonstandard_filename`, `test: tests/test_mcp_admission.py::TestModeContract::test_attach_writes_nothing`

#### Scenario: Attach refuses incompatible options and never falls back to create

- GIVEN `config` supplied with any of `cwd`, `force`, or `move_existing`, or an empty/whitespace `config`, or a missing config
- WHEN init runs
- THEN it SHALL fail with `CONFIG_ERROR` (empty/incompatible) or the existing not-found error (missing)
- AND no dataset TOML SHALL be created

**Evidence:** `test: tests/test_mcp_admission.py::TestModeContract::test_attach_rejects_create_only_options`, `test: tests/test_mcp_admission.py::TestModeContract::test_empty_config_is_not_create_mode`, `test: tests/test_mcp_admission.py::TestModeContract::test_missing_config_never_falls_back_to_create`

#### Scenario: Attach validation is minimal and repairable

- GIVEN an empty `[[file]]`, `[meta]` placeholders, a missing source file, or a malformed TOML
- WHEN attach runs
- THEN the repairable conditions SHALL attach successfully
- AND the malformed TOML SHALL be refused with `Failed to read TOML`
- AND no full data/quality check SHALL run

**Evidence:** `test: tests/test_mcp_admission.py::TestModeContract::test_repairable_conditions_do_not_block_attach`, `test: tests/test_mcp_admission.py::TestModeContract::test_malformed_toml_is_an_attach_refusal`

#### Scenario: A preview never grants readiness

- GIVEN create or attach with `dry_run=true`
- WHEN it succeeds
- THEN `session_ready` SHALL be false and `next` SHALL point to the same init with `dry_run=false`
- AND a protected call SHALL still be refused

**Evidence:** `test: tests/test_mcp_admission.py::TestModeContract::test_preview_never_grants_readiness`

#### Scenario: State transitions preserve or discard the active context correctly

- GIVEN `R(A)`, then a preview, a failed attach, an ordinary mismatch, or an A->B switch
- WHEN the following calls run
- THEN a preview/failure SHALL settle in `U` (A is not restored)
- AND an ordinary mismatch SHALL leave A ready
- AND returning to A SHALL require an explicit init

**Evidence:** `test: tests/test_mcp_admission.py::TestStateTransitions`

#### Scenario: Matching binds root and config exactly

- GIVEN two TOMLs under one root, a foreign init root, or a standalone path tool
- WHEN a call omits `root`, names another TOML, or targets another tree
- THEN a mismatched root/config SHALL return `INITIALIZATION_CONTEXT_MISMATCH`
- AND an explicit matching root SHALL be admitted
- AND standalone tools SHALL be allowed anywhere inside the active root

**Evidence:** `test: tests/test_mcp_admission.py::TestMatchingAndResources`

#### Scenario: Resources follow the same gate and intersection rules

- GIVEN a fresh session, then a ready session with the active root/config
- WHEN a content resource is read
- THEN it SHALL be blocked with the JSON envelope before init
- AND after init it SHALL satisfy both containment scopes, with `sofer://dataset/...` requiring the active config
- AND `sofer://status` SHALL remain available

**Evidence:** `test: tests/test_mcp_admission.py::TestMatchingAndResources::test_status_resource_is_available_before_init`, `test: tests/test_mcp_admission.py::TestMatchingAndResources::test_content_resources_are_blocked_before_init`, `test: tests/test_mcp_admission.py::TestMatchingAndResources::test_dataset_resource_requires_the_active_config`, `test: tests/test_mcp_admission.py::TestMatchingAndResources::test_codebook_resource_is_contained_in_the_active_root`

#### Scenario: Refusal envelopes are machine-readable and executable

- GIVEN a refused tool or resource
- WHEN the envelope is inspected
- THEN it SHALL carry `ok:false`, `exit_code:1`, `output`, `error_code`, `message`, `next`, and an empty `config_errors`
- AND `INITIALIZATION_REQUIRED` SHALL use the known config or ask for `config`
- AND a resource retry SHALL be `next.action = "resources/read"` with `next.uri`

**Evidence:** `test: tests/test_mcp_admission.py::TestEnvelopes`, `test: tests/test_mcp_admission.py::TestMatchingAndResources::test_content_resources_are_blocked_before_init`

#### Scenario: Concurrency is deterministic and never queues a second init

- GIVEN an init in progress, or an admitted protected request still executing
- WHEN another init or protected call arrives
- THEN it SHALL return `INITIALIZATION_IN_PROGRESS` or `INITIALIZATION_CONTEXT_BUSY` respectively
- AND no second handler SHALL start
- AND the active context SHALL survive a busy refusal

**Evidence:** `test: tests/test_mcp_admission.py::TestConcurrency`, `test: tests/test_mcp_admission.py::TestAdmissionStateMachine`

#### Scenario: A real stdio session keeps the binding and a new session starts clean

- GIVEN one stdio client session and a second fresh one
- WHEN the first refuses, attaches, then calls a protected tool, and the second calls it directly
- THEN the first SHALL succeed after attach
- AND the second SHALL be refused

**Evidence:** `test: tests/test_mcp_admission.py::TestStdioSession`

#### Scenario: The framework lifecycle proof is part of the suite

- GIVEN the installed fastmcp version
- WHEN the session holder is observed across two calls in one client and across two clients
- THEN the outbound channel SHALL be identical within a session and different across sessions

**Evidence:** `test: tests/test_mcp_admission.py::TestFrameworkLifecycle::test_outbound_channel_is_session_scoped`
