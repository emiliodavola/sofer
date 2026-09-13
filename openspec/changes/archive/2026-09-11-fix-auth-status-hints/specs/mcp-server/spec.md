# Delta for mcp-server

Change `2026-09-11-fix-auth-status-hints` — **issue #144 ONLY** (`hint/message contract`).

- **ADDED** — `### Requirement: Approval-phrase configuration diagnostics (APX-01)`.
- No **MODIFIED** requirements, no **REMOVED** requirements. Requirement `Auth status preflight read-only (10.8)` is **NOT** touched by this change: its envelope rows (`phrase_source`, `server_process_id`, `server_started_at`, `server_version`) belong to the sibling change `2026-09-11-fix-auth-status-posture` (issue #145), which extends section 10.8 at its own archive.
- No `openspec/specs/mcp-server/spec.md` edit in this phase; the canonical file is merged at archive.

> Consolidation note: the combined planning change `2026-09-11-fix-auth-status-diagnostics` carries the same domain path with a combined delta (APX-01 + the 10.8 posture rewrite). APX-01 below is the authoritative #144 slice and is written to compose cleanly with the future #145 delta: this requirement references **no** posture field, and ADDS only. When #145 archives its 10.8 never-leak bullet it MAY reference APX-01's guidance; nothing here references posture.
> Posture symbols (`phrase_source`, `server_process_id`, `server_started_at`, `server_version`) are deliberately absent from this delta — do not add them during apply.

## ADDED Requirements

### Requirement: Approval-phrase configuration diagnostics (APX-01)

*Introduced by change `2026-09-11-fix-auth-status-hints` (issue #144).*

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

*Tests:* `tests/test_mcp_server.py::TestHintContentActionable::test_auth_status_unconfigured_hint_is_actionable`
`tests/test_mcp_server.py::TestHintContentActionable::test_auth_status_unconfigured_hint_restart_required_is_true`
`tests/test_mcp_server.py::TestHintContentActionable::test_auth_status_unconfigured_hints_are_flat_scalars`
`tests/test_mcp_server.py::TestHintContentActionable::test_auth_status_configured_hints_have_no_guidance_keys`
(extended) `tests/test_mcp_schema.py::TestEnvelope::test_auth_status_approval_not_configured` — keep `hints["action"]` and `"approval_phrase" not in envelope["hints"]`, add the guidance-key assertions additively.

#### Scenario: Publish refusal message carries the same process-start semantics

- GIVEN a server with no configured approval phrase
- WHEN `sofer_publish_confirm` is called with the required acknowledgments set
- THEN the envelope SHALL return `error_code = PUBLISH_APPROVAL_NOT_CONFIGURED` and the upload SHALL never be reached
- AND the message SHALL name `SOFER_MCP_APPROVAL_PHRASE`, state that the phrase is read once at server start, state that it must be set in the launching process's environment, and state that a restart is required
- AND the message SHALL keep its `"publish is disabled:"` prefix and the refusal `hints` SHALL be exactly `{"action": "configure_approval_phrase"}`

*Tests:* `tests/test_mcp_server.py::TestApprovalNotConfiguredMessage::test_publish_approval_not_configured_message_process_start_semantics`
`tests/test_mcp_server.py::TestApprovalNotConfiguredMessage::test_publish_refusal_hints_unchanged_exact_dict`
(extended) `tests/test_mcp_server.py::TestPublishAuthorizationLadder::test_no_phrase_configured_refuses_fail_closed` — additive asserts only; existing assertions untouched.

#### Scenario: Guidance message and hints share one fact source

- GIVEN the unconfigured-approval surface on both `sofer_auth_status` and `sofer_publish_confirm`
- WHEN the hint guidance values and the refusal message are compared
- THEN each process-start fact (variable NAME, read-once-at-start, launching-process environment, restart required) SHALL be derivable from the same module constants — each fact constant SHALL appear as a substring of both the corresponding hint value and the message
- AND the opencode per-agent guidance SHALL assert only the keys `mcp_registration.py` writes (`type`, `command`, `cwd`) and SHALL NOT claim that registration forwards the environment

*Tests:* `tests/test_mcp_server.py::TestApprovalNotConfiguredMessage::test_approval_phrase_facts_not_drifted_between_hints_and_message`
`tests/test_mcp_server.py::TestHintContentActionable::test_auth_status_unconfigured_hint_uses_verified_registration_keys`

#### Scenario: Guidance leaks no phrase material and invents no config path

- GIVEN `approval_phrase="phrase123"` present on the server, and the unconfigured-approval guidance produced without one
- WHEN the whole `sofer_auth_status` envelope and the refusal message are serialized
- THEN `"phrase123"` SHALL NOT appear anywhere in either
- AND no guidance key SHALL carry a phrase-derived value, and `hints` SHALL NOT contain the bare `approval_phrase` key
- AND no guidance text SHALL name an on-disk agent config file or directory (e.g. `opencode.json`, `config.toml`, `settings.json`) as the place to put the phrase

*Tests:* `tests/test_mcp_server.py::TestHintContentActionable::test_auth_status_unconfigured_guidance_has_no_phrase_material`
`tests/test_mcp_server.py::TestHintContentActionable::test_auth_status_unconfigured_guidance_names_no_config_path`
(extended) `tests/test_mcp_schema.py::TestEnvelope::test_auth_status_no_leak` — scan the serialized guidance payload and message for phrase material.
