# Delta for mcp-server

Change `2026-09-11-fix-auth-status-posture` — **issue #145 ONLY** (`restart-proof posture fields`).

- **MODIFIED** — `### Requirement: Auth status preflight read-only (10.8)` (wholesale replacement of the envelope contract + posture semantics; the canonical scenario is kept; 5 new GWT scenarios added).
- No **ADDED** requirements, no **REMOVED** requirements. Requirement `Approval-phrase configuration diagnostics (APX-01)` — from the MERGED sibling change `2026-09-11-fix-auth-status-hints` (issue #144, PR #158 / `cf27584`) — is **NOT** re-added and **NOT** touched; it stays canonical and composes by diff at archive (10.8 replaced, everything else preserved).
- No `openspec/specs/mcp-server/spec.md` edit in this phase; the canonical file is merged at archive.

## MODIFIED Requirements

### Requirement: Auth status preflight read-only (10.8)

> Added by change `mcp-dx-audit-surface` (archived 2026-08-31). Modified by
> change `2026-09-11-fix-auth-status-posture` (issue #145).

System MUST expose `sofer_auth_status(config)` with `annotations.readOnlyHint:true`, returning `{token:"present"|"missing", confidential:bool, requires_ack_confidential:bool, approval_configured:bool, requires_approval_phrase:bool, phrase_source:"env"|"explicit"|"none", server_process_id:int, server_started_at:str, server_version:str, next:obj}` without leaking token/phrase values or requiring network. `requires_approval_phrase` is always `true` (a phrase is always required for publish); `approval_configured` reflects whether the server has a non-blank phrase set. An empty or whitespace-only phrase MUST be treated as unconfigured (`approval_configured:false`). `ok` SHALL reflect publish readiness — `true` only when config validation passes AND a token is present AND (when `requires_approval_phrase`) the approval phrase is configured; a dataset that cannot publish never reads `ok:true`.

The four posture fields carry **process-lifecycle metadata only** (never secrets):

- `phrase_source` — `"env" | "explicit" | "none"`, the configuration path that produced `approval_configured`, derived **exactly once at `build_server`** from the same single read that resolves the phrase (explicit `approval_phrase` argument > `SOFER_MCP_APPROVAL_PHRASE` > none); blank/whitespace always maps to `"none"`; a blank explicit argument SHALL NOT fall back to the environment. The source is captured at build time and **never re-derived at tool-call time** — a running server MUST NOT re-read the environment, so environment changes take effect only after a full process restart. Invariant: `phrase_source == "none"` ⟺ `approval_configured is False`.
- `server_process_id` — `os.getpid()` of the hosting process, captured at `build_server`; **process-scoped** (stable for the life of the process) and MUST NOT be asserted to differ across `build_server()` calls within one process.
- `server_started_at` — ISO-8601 UTC timestamp with **microsecond precision** captured at `build_server`; MUST differ AND strictly increase across two `build_server()` calls even within one process — this is **the restart-proof criterion**, anchored here and never on the pid.
- `server_version` — package version from installed metadata (`_version.get_version()`), non-empty, never raises.

NEVER-LEAK (extended to the four posture fields): the phrase, any phrase-derived value (hash, length, prefix/suffix, boolean probe, comparison result), and the configured env value MUST NEVER appear in any of the four posture fields or any rendering of the envelope; `phrase_source` describes the configuration path only.

(Previously: the envelope carried no posture metadata — no `phrase_source`, `server_process_id`, `server_started_at`, or `server_version` — and the never-leak clause named only token/phrase values.)

#### Scenario: Preflight without publish

(kept verbatim from canonical 10.8)

- GIVEN config `confidential=true`, no `HF_TOKEN`
- WHEN `sofer_auth_status(config)` called
- THEN return `token=missing, confidential=true` and `next` lists `acknowledge_risk` and `acknowledge_confidential` steps

*Tests:* `tests/test_mcp_server.py::TestAuthStatusValidity::test_missing_token_ok_false` (existing pin, unmodified)
`tests/test_mcp_server.py::TestAuthStatusValidity::test_approval_not_configured_ok_false` (existing pin, unmodified)
`tests/test_mcp_schema.py::TestEnvelope::test_auth_status_no_leak` (existing pin, unmodified)

#### Scenario: Posture fields present in envelope and schema

- GIVEN `build_server(root=..., approval_phrase="phrase123")` and `sofer_auth_status(config)` on a valid config
- WHEN the envelope and the `output_schema` are inspected
- THEN the envelope SHALL carry `phrase_source="explicit"`, an integer `server_process_id`, an ISO-8601 UTC `server_started_at` with microseconds, and a non-empty `server_version` equal to `_version.get_version()`
- AND `output_schema.properties` SHALL declare all four fields (additive, typed `string`/`integer`) with `required` unchanged (`["ok", "exit_code", "output"]`) and no `enum` on `phrase_source`
- AND no other tool's envelope or `output_schema` SHALL gain the four posture fields (scope containment)

*Tests:* `tests/test_mcp_server.py::TestAuthStatusPosture::test_posture_fields_present_and_typed`
`tests/test_mcp_server.py::TestAuthStatusPosture::test_server_version_equals_get_version`
`tests/test_mcp_server.py::TestAuthStatusPosture::test_posture_fields_confined_to_auth_status`
(extended) `tests/test_mcp_schema.py::TestOutputSchema::test_output_schema_typed` — additive asserts for the four properties; the `required` assertion stays unchanged.

#### Scenario: phrase_source follows configuration precedence

- GIVEN the five configuration paths for `build_server`:
  - `approval_phrase="x"` → `phrase_source` SHALL be `"explicit"`, `approval_configured:true`
  - no argument, `SOFER_MCP_APPROVAL_PHRASE="x"` → `"env"`, `approval_configured:true`
  - no argument, env absent → `"none"`, `approval_configured:false`
  - no argument, env `""` / whitespace → `"none"`, `approval_configured:false`
  - `approval_phrase=""` while env set → `"none"`, `approval_configured:false` (blank explicit never falls back to env)
- WHEN `sofer_auth_status(config)` is called under each path
- THEN `phrase_source` SHALL equal the mapped value and the invariant `phrase_source == "none"` ⟺ `approval_configured is False` SHALL hold on every path

*Tests:* `tests/test_mcp_server.py::TestAuthStatusPosture::test_phrase_source_explicit`
`tests/test_mcp_server.py::TestAuthStatusPosture::test_phrase_source_env`
`tests/test_mcp_server.py::TestAuthStatusPosture::test_phrase_source_none`
`tests/test_mcp_server.py::TestAuthStatusPosture::test_phrase_source_blank_env_is_none`
`tests/test_mcp_server.py::TestAuthStatusPosture::test_phrase_source_blank_explicit_beats_env`
`tests/test_mcp_server.py::TestAuthStatusPosture::test_phrase_source_consistent_with_approval_configured`

#### Scenario: server_started_at is the restart-proof signal across server builds

- GIVEN two `build_server()` calls in the same process (back-to-back)
- WHEN the envelopes from the two builds are compared
- THEN the second `server_started_at` SHALL differ from the first AND SHALL be strictly greater (ISO-8601 UTC, fixed-width microseconds, monotonic bump) — the restart-proof criterion anchors here, never on the pid
- AND `phrase_source` SHALL reflect each build's own configuration path

*Tests:* `tests/test_mcp_server.py::TestAuthStatusPosture::test_server_started_at_differs_across_builds`

#### Scenario: server_process_id is process-scoped

- GIVEN two `build_server()` calls in the same process
- WHEN `server_process_id` is inspected in both envelopes
- THEN it SHALL equal `os.getpid()` in both, SHALL be identical across the two builds, and SHALL NOT be asserted to differ across builds (no drift promise — pid is process-scoped)

*Tests:* `tests/test_mcp_server.py::TestAuthStatusPosture::test_server_process_id_is_host_pid`

#### Scenario: No phrase material in the posture fields

- GIVEN a server built with `approval_phrase="phrase123"` and `SOFER_MCP_APPROVAL_PHRASE` configured
- WHEN the serialized `sofer_auth_status` envelope (including the four posture fields) is scanned
- THEN `"phrase123"` SHALL NOT appear anywhere and no posture field SHALL carry the phrase or any phrase-derived value (hash, length, prefix/suffix, boolean probe, comparison result)
- AND `phrase_source` SHALL belong to `{"env","explicit","none"}` and describe the configuration path only

*Tests:* (extended) `tests/test_mcp_schema.py::TestEnvelope::test_auth_status_no_leak` — scan the serialized envelope including the four posture fields for phrase material; existing assertions untouched.