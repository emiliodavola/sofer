# Delta for cli

> **Change** `2026-10-16-feat-mcp-doctor` (issue **#322**) · branch `feat/322-mcp-doctor` from
> `dev@24520b6` · store **hybrid**.
>
> **One modified requirement, one added.** `doctor` joins the `mcp` children, and its contract is
> stated: measure the real `initialize` round trip, report it beside what `mcp add` writes, and never
> fail because a machine is slow.
>
> **Rule-6 resolution.** `cli` is a permanent declared-backlog spec
> (`openspec/test-mapping-registry.md`), so the scenarios below carry their evidence inline
> (`**Evidence:**`) and this change adds **no** `## Test Mapping` table and **no** registry edit.
>
> **How to read this delta.** For a requirement this change only *extends*, the delta carries the
> changed prose in full, the scenario it changed, and an explicit list of the scenarios it leaves alone.
> The merged text of record is `openspec/specs/cli/spec.md`; duplicating every unchanged scenario here
> would be a second copy that drifts (AGENTS.md rule 4).

## MODIFIED Requirements

### Requirement: mcp add/remove help (CLI-R09)

**Changed:** the child list gains `doctor`, and its two flags.

`sofer` MUST expose `mcp` with `add`/`remove`/`doctor`. `add` MUST accept `--agent <opencode|codex|gemini|pi|hermes|all> [--scope user|project] [--cwd PATH] [--user-config PATH] [--dry-run]`; `remove` MUST accept `--agent <opencode|codex|gemini|pi|hermes|all> [--scope user|project] [--user-config PATH] [--dry-run]`; `doctor` MUST accept `--agent <opencode|codex|gemini|pi|hermes|all>` and `--json`. Help for `sofer --help` and `sofer mcp*` MUST list these.

**Changed scenario:**

#### Scenario: mcp lists children

- GIVEN `sofer mcp --help` rendered
- WHEN inspected
- THEN `add`, `remove` and `doctor` SHALL appear

**Evidence:** `test: tests/test_mcp_doctor.py::TestCliSurface::test_mcp_help_lists_doctor`

**Unchanged by this change** (carried by the canonical spec, each with its existing evidence): `mcp in
top help`, `add help`, `remove help`, `add help documents env forwarding`, `add help documents the YAML
preservation and the single-scope note`, `help documents native delegation fidelity`.

## ADDED Requirements

### Requirement: The measured cold start, and the deadline to configure (CLI-R15)

`sofer mcp doctor [--agent <agent>] [--json]` SHALL measure the **real** launch: it SHALL spawn the
`sofer-mcp` console script when it is on `PATH`, else the module entry point, and SHALL time the stdio
`initialize` round trip — never import time, because the deadline the measured value is compared against
covers connect **and** handshake. It SHALL report the measured milliseconds beside the per-agent entry
key and the value `sofer mcp add` would write there, taking both from the registration module's own
adapter table and timeout mapping so the two surfaces cannot disagree. It SHALL compare the measurement
against `[tool.sofer] mcp_connect_timeout_seconds` — never a literal (AGENTS.md rule 1).

The command SHALL be informational: a measurement above the budget SHALL NOT change the exit code — the
same contract as the timeout and env-drop notes (MCP-REG-03, MCP-REG-05). Only a launch that could not
be measured at all SHALL exit 1. The command SHALL read no agent config file and write none. An agent
whose entry schema accepts no timeout key SHALL be named by the same `dropped_timeout_note` the
registration path emits, never given an invented value. The row SHALL carry the adapter's own unit, so a
host expressing the deadline in milliseconds cannot be read as seconds.

`--json` SHALL emit the CLI-R10 stable-key object (`ok`, `exit_code`, `message`) extended with this
command's own keys, and SHALL never emit a Python `repr`.

#### Scenario: The cold start is measured through the real stdio handshake — issue #322

- GIVEN `sofer mcp doctor --json` on a machine where `sofer-mcp` can start
- WHEN the command completes
- THEN its exit code SHALL be 0
- AND the JSON SHALL carry `ok: true` and a positive `measured_ms`

**Evidence:** `test: tests/test_mcp_doctor.py::TestRealLaunch::test_the_real_launch_is_measured_and_reported_as_json`

#### Scenario: The entry point falls back to the module — issue #322 §"Proposed solution" 3

- GIVEN `sofer-mcp` is not on `PATH`
- WHEN the entry point is resolved
- THEN the module entry point SHALL be used, naming the module it runs

**Evidence:** `test: tests/test_mcp_doctor.py::TestEntryPointResolution::test_falls_back_to_the_module_entry_point`, `test: tests/test_mcp_doctor.py::TestEntryPointResolution::test_the_fallback_names_the_module_it_runs`

#### Scenario: Each agent's row is what mcp add would write — issue #322

- GIVEN the configured `[tool.sofer]` deadlines
- WHEN the per-agent rows are built
- THEN each row's key and value SHALL equal what `timeout_entry_keys` writes for that agent
- AND an agent whose schema accepts no key SHALL carry the MCP-REG-05 note and no value
- AND a host expressing the deadline in milliseconds SHALL report that unit

**Evidence:** `test: tests/test_mcp_doctor.py::TestAgentRows::test_the_row_value_matches_what_mcp_add_would_write`, `test: tests/test_mcp_doctor.py::TestAgentRows::test_opencode_carries_the_note_instead_of_a_value`, `test: tests/test_mcp_doctor.py::TestAgentRows::test_gemini_reports_milliseconds_not_seconds`

#### Scenario: Exceeding the budget is reported, not failed — issue #322

- GIVEN a measurement above `mcp_connect_timeout_seconds`
- WHEN `sofer mcp doctor` reports it
- THEN the output SHALL name `--connect-timeout` and `--timeout`
- AND the exit code SHALL remain 0

**Evidence:** `test: tests/test_mcp_doctor.py::TestCommandHandler::test_a_measurement_over_budget_still_exits_zero`

#### Scenario: Nothing measurable fails, and names what it tried

- GIVEN a launch that cannot be measured
- WHEN `sofer mcp doctor` runs
- THEN the exit code SHALL be 1
- AND the output SHALL name the entry point that was attempted

**Evidence:** `test: tests/test_mcp_doctor.py::TestCommandHandler::test_nothing_measurable_exits_one_and_names_what_it_tried`

#### Scenario: The budget is configuration, not a literal — AGENTS.md rule 1

- GIVEN the command's handler runs
- WHEN it measures
- THEN the timeout it passes SHALL be the one read from `[tool.sofer]`

**Evidence:** `test: tests/test_mcp_doctor.py::TestCommandHandler::test_the_handler_uses_the_configured_connect_deadline`

#### Scenario: --json is stable JSON, not a repr — CLI-R10

- GIVEN `sofer mcp doctor --json`
- WHEN its stdout is parsed
- THEN it SHALL decode as JSON carrying `ok` and `exit_code`
- AND no `repr`-style Python literal SHALL appear

**Evidence:** `test: tests/test_mcp_doctor.py::TestJsonPayload::test_the_payload_carries_the_stable_keys`, `test: tests/test_mcp_doctor.py::TestJsonPayload::test_the_serialized_payload_is_json_not_a_repr`

#### Scenario: doctor help lists its flags and what is measured — CLI-R02

- GIVEN `sofer mcp doctor --help`
- WHEN rendered
- THEN `--agent` and `--json` SHALL be listed
- AND the description SHALL name the `initialize` round trip

**Evidence:** `test: tests/test_mcp_doctor.py::TestCliSurface::test_doctor_help_lists_its_flags`, `test: tests/test_mcp_doctor.py::TestCliSurface::test_doctor_help_documents_what_is_measured`
