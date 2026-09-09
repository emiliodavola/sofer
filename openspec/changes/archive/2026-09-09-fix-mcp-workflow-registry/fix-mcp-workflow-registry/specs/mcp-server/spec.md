# Delta for mcp-server

## ADDED Requirements

### Requirement: Authoritative workflow registry with executable continuations (MSP-R13)

> Added by change `fix-mcp-workflow-registry`.

The MCP server SHALL expose one authoritative workflow registry: every
registered tool SHALL have exactly one registry entry with `phase`, `branch`,
`requires`, and a valid `next` continuation or explicit human gate. The same
registry SHALL drive `tools/list` metadata, tool descriptions, prompts,
server instructions, and runtime envelopes (no per-tool hand-built `next`
hints).

A `next` continuation SHALL be executable only when its tool exists and every
required argument resolves (a `<config_path>` binding with no config SHALL
degrade to `input_required`). A human approval stop SHALL be a typed
`human_gate` envelope (`{kind: "human_gate", name, reason}`), never a fake
tool call. When a required human value is unknowable, the envelope SHALL name
the missing input instead of emitting a guaranteed-failing call.

Canonical branches: greenfield
`sofer_init → sofer_scan_dry_run → sofer_scan_apply → sofer_validate`;
existing-config
`sofer_validate → sofer_prepare → sofer_codebook_all → sofer_profile_all →
sofer_render_all`; single-file triage `sofer_codebook` / `sofer_profile` /
`sofer_render`; delivery
`sofer_auth_status → sofer_publish(dry_run=true) → HUMAN APPROVAL STOP →
sofer_publish_confirm`.

(Previously: workflows were described by `_PHASED_INSTRUCTIONS`, docstrings,
prompts, and per-envelope `next` hints with no single source of truth.)

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

#### Scenario: Greenfield branch continues init → scan_dry_run → scan_apply → validate

- GIVEN `sofer_init` on a greenfield root
- THEN its `next` SHALL name `sofer_scan_dry_run`, whose `next` names `sofer_scan_apply`, whose `next` names `sofer_validate`