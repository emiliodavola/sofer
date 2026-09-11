# Delta for mcp-server

Change `2026-09-11-fix-status-resource` — **issue #146 ONLY** (static `sofer://status` posture resource so `resources/list` is never empty).

- **MODIFIED** — `### Requirement: Resources (MSP-R07)` (additive amendment: one static resource `sofer://status` + never-leak and boundary clauses; the three URI templates and their containment/size-guard semantics stay unchanged).
- No **ADDED** requirements, no **REMOVED** requirements. Requirement `Auth status preflight read-only (10.8)` (from the MERGED sibling change `2026-09-11-fix-auth-status-posture`, issue #145) and requirement `Approval-phrase configuration diagnostics (APX-01)` (from the MERGED sibling change `2026-09-11-fix-auth-status-hints`, issue #144) are **NOT** re-added and **NOT** touched; they stay canonical and compose by diff at archive (MSP-R07 amended, everything else preserved).
- No `openspec/specs/mcp-server/spec.md` edit in this phase; the canonical file is merged at archive.

## MODIFIED Requirements

### Requirement: Resources (MSP-R07)

> Added by change `sofer-mcp-server` (archived 2026-08-28). Modified by
> change `2026-09-11-fix-status-resource` (issue #146).

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

(kept verbatim from canonical MSP-R07)

- GIVEN a config path
- WHEN `sofer://dataset/{config_path}` is read
- THEN the raw TOML text SHALL be returned

*Tests:* `tests/test_mcp_server.py::TestResources::test_dataset_resource_raw_toml` (existing pin, unmodified)

#### Scenario: Codebook resource generates on demand

(kept verbatim from canonical MSP-R07)

- GIVEN a data file
- WHEN `sofer://codebook/{data_file}` is read
- THEN a markdown codebook SHALL be returned without writing anything

*Tests:* `tests/test_mcp_server.py::TestResources::test_codebook_resource_generates_on_demand` (existing pin, unmodified)

#### Scenario: Metadata resource when present

(kept verbatim from canonical MSP-R07)

- GIVEN a profiled dataset
- WHEN `sofer://metadata/{data_file}` is read
- THEN the metadata.yaml content SHALL be returned
- AND a missing file SHALL produce a clear resource error

*Tests:* `tests/test_mcp_server.py::TestResources::test_metadata_resource_when_present` (existing pin, unmodified)
`tests/test_mcp_server.py::TestResources::test_metadata_missing_clear_error` (existing pin, unmodified)

#### Scenario: Static status resource listed with posture content

- GIVEN a server built with `build_server(root=..., approval_phrase="phrase123")`
- WHEN `resources/list` is requested and `sofer://status` is read
- THEN the list SHALL be non-empty and SHALL include `sofer://status`
- AND `sofer://status` SHALL be registered with no path variables (static, not a template)
- AND the three URI templates (`sofer://dataset/{config_path}`, `sofer://codebook/{data_file}`, `sofer://metadata/{data_file}`) SHALL remain listed under `resources/templates/list`
- AND the payload SHALL carry exactly six fields with build-time values: `approval_configured:true`, `phrase_source:"explicit"`, `root` equal to the resolved build root, `version` equal to the installed package version, `started_at` ISO-8601 UTC with microsecond precision, and `tool_count` equal to `len(workflow.WORKFLOW_METADATA)` (never a hardcoded count)

*Tests:* `tests/test_mcp_server.py::TestStatusResource::test_status_resource_listed`
`tests/test_mcp_server.py::TestStatusResource::test_status_resource_content_explicit`

#### Scenario: Status posture consistent across surfaces and free of secret material

- GIVEN a server built with `approval_phrase="phrase123"` and `SOFER_MCP_APPROVAL_PHRASE` configured, plus the unconfigured paths (no phrase with env absent; blank/whitespace env)
- WHEN the `sofer://status` payload and the `sofer_auth_status` envelope of the same build are inspected and the serialized payload is scanned
- THEN the shared posture fields SHALL agree across the two surfaces: `approval_configured`/`phrase_source` equal, `started_at` equal to the envelope's `server_started_at`, and `version` equal to the envelope's `server_version` (one fact source, two surfaces)
- AND the phrase, any phrase-derived value (hash, length, prefix/suffix, boolean probe, comparison result), and the configured env value SHALL NOT appear anywhere in the serialized payload
- AND `phrase_source` SHALL belong to `{"env","explicit","none"}` and describe the configuration path only
- AND across the unconfigured paths the invariant `phrase_source == "none"` ⟺ `approval_configured is False` SHALL hold

*Tests:* `tests/test_mcp_server.py::TestStatusResource::test_status_resource_consistent_with_auth_status`
`tests/test_mcp_server.py::TestStatusResource::test_status_resource_no_phrase_leak`
`tests/test_mcp_server.py::TestStatusResource::test_status_resource_unconfigured_invariant`