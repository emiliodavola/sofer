# Delta for mcp-server

> **Change** `2026-10-15-fix-approval-phrase-agent-coverage` (issue **#295**) · branch
> `fix/295-approval-phrase-agent-coverage` from `dev@b7dea51` · store **hybrid**
> (`odd/tasks/approval-phrase-agent-coverage.md` + this folder).
>
> **One modification, no new requirement.** APX-01's per-agent guidance clause was an enumeration of
> the three agents that existed when it was written; it now requires coverage of the whole registry and
> derivation from the registry's own `env` capability, and two scenarios pin that.
>
> **Rule-6 resolution.** `mcp-server` is a permanent declared-backlog spec
> (`openspec/test-mapping-registry.md`: `mcp-server: 125 scenario(s), unmapped`), so the new scenarios
> stay unmapped, the registry is not edited, and `scripts/check_test_mapping.py` still exits 0 — it now
> reports 127 scenarios for the domain.

## MODIFIED Requirements

### Requirement: Approval-phrase configuration diagnostics (APX-01) — Modified 2026-10-15, fix-approval-phrase-agent-coverage

Everything else in the requirement (the `action` key, the process-start facts, the restart boolean,
the flatness and namespacing invariants, the NEVER-LEAK rules, the shared fact source with the refusal
message) is unchanged. The per-agent clause now reads (verbatim, as it reads in the canonical spec
after this change):

- per-agent setup guidance that MUST cover **every** member of `mcp_registration.AGENT_NAMES` and MUST
  be derived from that registry's own `env` capability, never from a parallel hand-kept table:
  `sofer mcp add --agent <agent>` writes only the `mcp.sofer` entry keys `type`, `command`, `cwd` and
  forwards **NO** environment when the capability is `none` (so the guidance MUST NOT claim env
  forwarding for it), persists an `env_vars` allow-list of environment-variable NAMES when it is
  `allow_list`, and persists an `env` mapping of NAME → `$NAME` references when it is `refs` or
  NAME → `${NAME}` references when it is `refs_braced`; each fact MUST name the field and the reference
  form that agent's registration entry actually carries, and secret VALUES are never written to disk;

Two scenarios are added (verbatim):

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
