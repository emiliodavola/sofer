# Delta for mcp-registration

> **Change** `2026-10-16-feat-mcp-doctor` (issue **#322**) · branch `feat/322-mcp-doctor` from
> `dev@24520b6` · store **hybrid**.
>
> **One modified requirement, extended by one paragraph and one scenario.** MCP-REG-05 states the
> deadlines `mcp add` writes; this change adds the diagnostic that lets a user check the written value
> against the machine that carries it.
>
> **Rule-6 resolution.** `mcp-registration` is a permanent declared-backlog spec
> (`openspec/test-mapping-registry.md`), so the added scenario carries its evidence inline
> (`**Evidence:**`) and this change adds **no** `## Test Mapping` table and **no** registry edit.
>
> **How to read this delta.** MCP-REG-05 is long and this change rewrites none of it: the delta carries
> the *appended* paragraph and the *appended* scenario, and states plainly that the rest of the
> requirement is unchanged. The merged text of record is
> `openspec/specs/mcp-registration/spec.md`. Transcribing the untouched paragraphs here would create a
> second copy that can drift from the canonical one (AGENTS.md rule 4).

## MODIFIED Requirements

### Requirement: Host timeouts in the registered entry (MCP-REG-05)

**Unchanged by this change:** every existing paragraph of MCP-REG-05, and every existing scenario
(`The entry carries each host's keys and unit`, `A host without a timeout key is named, not silently
skipped`, `Idempotent when unchanged, rewriting when the timeout changes`, `--no-timeout restores the
pre-change shape`, `A non-positive timeout is refused before any write`, `Native delegation declines
when it cannot reproduce the timeouts`).

**Appended paragraph** (after the native-delegation paragraph):

The value written SHALL be checkable against the machine that carries it: `sofer mcp doctor` (CLI-R15)
MUST report this machine's own `initialize` round trip beside the key and the value `add` writes, and
MUST name the flags that raise them. Like the two notes above it is informational and MUST NOT change
the exit code (issue #322).

**Appended scenario:**

#### Scenario: The written deadline can be checked against this machine — issue #322

- GIVEN `sofer mcp doctor --agent <agent>` on a host whose entry carries a timeout key
- WHEN it reports
- THEN it SHALL name the same key and value `sofer mcp add` writes for that agent
- AND an agent whose entry accepts no timeout key SHALL be named by the same note
- AND the exit code SHALL be unchanged whatever the measurement

**Evidence:** `test: tests/test_mcp_doctor.py::TestAgentRows::test_the_row_value_matches_what_mcp_add_would_write`, `test: tests/test_mcp_doctor.py::TestAgentRows::test_opencode_carries_the_note_instead_of_a_value`, `test: tests/test_mcp_doctor.py::TestCommandHandler::test_a_measurement_over_budget_still_exits_zero`
