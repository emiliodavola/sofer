# Delta for mcp-registration

> **Change** `2026-10-16-fix-mcp-registration-timeouts` (issues **#287**, **#296**) · branch
> `fix/287-296-mcp-registration-timeouts` from `dev@6786ba1` · store **hybrid**.
>
> **One added requirement.** The registered `sofer` entry carries the host's per-request and
> connect/startup deadlines, so neither a cold start nor a long tool call looks like a broken
> registration; the delegation gate refuses to delegate a registration it cannot reproduce.
>
> **Rule-6 resolution.** `mcp-registration` carries **no** `## Test Mapping` section — it is a
> permanent declared backlog entry in `openspec/test-mapping-registry.md` — so the scenarios below
> carry their evidence inline (`**Evidence:**`) and this change adds **no** `## Test Mapping` table
> and **no** registry edit. Every scenario here is backed by a repository test, so no `verify:`
> escape hatch is used.

## ADDED Requirements

### Requirement: Host timeouts in the registered entry (MCP-REG-05)

`sofer mcp add` MUST write the host's per-request (tool call) and connect/startup deadlines into the
`sofer` entry, using the key name and unit the adapter declares for that agent, so that neither the
measured 16–32 s cold start of `sofer-mcp` (its heavy imports precede the `initialize` answer) nor a
tool call measured in minutes fails against a host default and reports as a broken registration
(issues #287, #296). The values MUST default to the `[tool.sofer]` keys
`mcp_request_timeout_seconds` and `mcp_connect_timeout_seconds` — never to a literal in the call path
(AGENTS.md rule 1) — MUST be overridable per invocation with `--timeout` / `--connect-timeout`, MUST
be omitted entirely by `--no-timeout`, and MUST be rejected with exit 2 when non-positive.

The timeout keys SHALL be namespaced under the `sofer` server name only. Writing them MUST NOT change
any other server in the file, MUST keep the existing contracts (preserve unrelated keys, one `.bak`
before the first mutation, atomic write, no write on `--dry-run`), and MUST still be idempotent:
re-running with the same values MUST NOT write and MUST NOT create a `.bak`, while a changed
`--timeout` alone MUST be detected as a change and MUST rewrite the entry.

An agent whose entry schema accepts no timeout key SHALL keep an entry without one, and `add` SHALL
name that on stderr rather than reporting a clean success — the same informational contract as the
OpenCode env-drop warning (MCP-REG-03).

Because neither `codex mcp add` nor `gemini mcp add` accepts a timeout flag, a registration carrying
timeouts MUST decline native delegation with the reason `timeout` and fall back to the file edit
(MCP-REG-04), and `--no-timeout` MUST restore the delegation path by restoring the pre-change entry
shape.

#### Scenario: The entry carries each host's keys and unit

- GIVEN an existing directory passed as `--cwd`
- WHEN `sofer mcp add --agent <agent>` runs for `pi`, `hermes`, `codex` and `gemini`
- THEN the written entry SHALL carry `timeout` / `connect_timeout` for `hermes`, `timeout` for `pi`,
  `tool_timeout_sec` / `startup_timeout_sec` for `codex`
- AND `gemini`'s single `timeout` key SHALL be expressed in milliseconds
- AND every value SHALL come from the `[tool.sofer]` defaults unless a flag overrode it

**Evidence:** `test: tests/test_mcp_registration.py::TestRegistrationTimeouts::test_entry_carries_each_host_timeout_key_and_unit`, `test: tests/test_cli.py::TestMcpRegistrationTimeoutsCli::test_add_writes_the_default_timeout_keys`, `test: tests/test_cli.py::TestMcpRegistrationTimeoutsCli::test_timeout_flags_override_the_defaults`, `test: tests/test_cli.py::TestMcpRegistrationTimeoutsCli::test_gemini_timeout_is_written_in_milliseconds`

#### Scenario: A host without a timeout key is named, not silently skipped

- GIVEN `--agent opencode`
- WHEN `sofer mcp add` writes the entry
- THEN the entry SHALL NOT carry a timeout key
- AND stderr SHALL name that the entry carries none, with the reason
- AND the exit code SHALL be unchanged

**Evidence:** `test: tests/test_cli.py::TestMcpRegistrationTimeoutsCli::test_opencode_names_the_missing_timeout_key_on_stderr`, `test: tests/test_mcp_registration.py::TestRegistrationTimeouts::test_opencode_declares_no_timeout_key`

#### Scenario: Idempotent when unchanged, rewriting when the timeout changes

- GIVEN a registration already carrying the configured timeouts
- WHEN `sofer mcp add` runs again with the same values
- THEN no write and no `.bak` SHALL occur
- AND when it runs with a different `--timeout`
- THEN the entry SHALL be rewritten with the new value and a `.bak` SHALL exist

**Evidence:** `test: tests/test_mcp_registration.py::TestRegistrationTimeouts::test_same_timeout_is_idempotent`, `test: tests/test_mcp_registration.py::TestRegistrationTimeouts::test_changed_timeout_is_not_swallowed_by_the_idempotency_guard`, `test: tests/test_cli.py::TestMcpRegistrationTimeoutsCli::test_changed_timeout_rewrites_the_entry_and_backs_up`

#### Scenario: --no-timeout restores the pre-change shape

- GIVEN `--no-timeout`
- WHEN `sofer mcp add` writes the entry
- THEN no timeout key SHALL appear
- AND `--dry-run` SHALL still write nothing

**Evidence:** `test: tests/test_cli.py::TestMcpRegistrationTimeoutsCli::test_no_timeout_omits_the_keys`, `test: tests/test_mcp_registration.py::TestRegistrationTimeouts::test_entry_without_timeouts_keeps_the_pre_change_shape`, `test: tests/test_cli.py::TestMcpRegistrationTimeoutsCli::test_dry_run_with_timeouts_writes_nothing`

#### Scenario: A non-positive timeout is refused before any write

- GIVEN `--timeout 0`, `-1`, `abc` or `1.5`
- WHEN `sofer mcp add` parses the arguments
- THEN it SHALL exit 2 with a usage message naming the flag
- AND no config file SHALL be written

**Evidence:** `test: tests/test_cli.py::TestMcpRegistrationTimeoutsCli::test_parser_rejects_a_non_positive_timeout`

#### Scenario: Native delegation declines when it cannot reproduce the timeouts

- GIVEN a native `codex` or `gemini` binary is available and a timeout will be written
- WHEN `sofer mcp add` runs
- THEN the delegation SHALL decline with the reason `timeout`, named on stderr
- AND the file edit SHALL run and carry the keys
- AND with `--no-timeout` the delegation SHALL proceed as before

**Evidence:** `test: tests/test_mcp_registration.py::TestRegistrationTimeouts::test_native_delegation_declines_with_the_timeout_reason`, `test: tests/test_mcp_registration.py::TestRegistrationTimeouts::test_decline_reason_order_is_env_scope_timeout`, `test: tests/test_cli.py::TestMcpRegistrationTimeoutsCli::test_timeouts_decline_native_delegation_naming_the_reason`, `test: tests/test_cli.py::TestMcpRegistrationTimeoutsCli::test_no_timeout_restores_native_delegation`, `test: tests/test_mcp_registration.py::TestRegistrationTimeouts::test_no_timeouts_leaves_delegation_available`
