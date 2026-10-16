# Proposal — `2026-10-15-fix-approval-phrase-agent-coverage`

> **Change** `2026-10-15-fix-approval-phrase-agent-coverage` · issue **#295** · branch
> `fix/295-approval-phrase-agent-coverage` from `dev@b7dea51` · store **hybrid**
> (`odd/tasks/approval-phrase-agent-coverage.md` + this folder).
>
> **Status:** implementation complete; archived inside the delivering branch (AGENTS.md rule 15).

---

## 1. Intent

`sofer_auth_status` on an unconfigured server reports the approval-phrase recovery path as flat
`approval_phrase_*` hints. Its per-agent setup facts cover **three of the five** registered agents
(`opencode`, `codex`, `gemini`): `pi` and `hermes` are missing, and they are precisely the two agents
whose registration persists `env: {NAME: "${NAME}"}` — the braced form a user cannot infer, and the
form the reporting host itself used when the gap was found (issue #295 was filed from a Pi session).

The table that looks like it keeps the guidance in sync (`_APPROVAL_PHRASE_AGENT_ENTRY_KEYS`) has **no
production reader**: its only consumer is the test that should have caught the gap, which iterates the
same incomplete dict. The real payload is three hand-written constants inlined into the hints literal.

## 2. Scope

### In scope

- `mcp_server.py`: derive each fact from `mcp_registration.ADAPTERS[agent]["env"]` — the capability
  `build_entry` itself branches on — through one capability → (reference form, template) table.
- **Delete** `_APPROVAL_PHRASE_AGENT_ENTRY_KEYS` and the three per-agent constants.
- Additive payload: `approval_phrase_setup_pi` and `approval_phrase_setup_hermes`.
- Tests: the per-agent guard cross-checks every registered agent against the real `build_entry`
  output; a capability-coverage guard; a sentinel-agent guard; the two hand-kept test key sets derive
  from `AGENT_NAMES`.
- `mcp-server` spec (APX-01) and this change folder.

### Out of scope (non-goals)

- **Issue item 3** ("emit only the asking agent's fact") — deferred, see D5.
- No `[tool.sofer]` key, no `pyproject.toml` entry, no new state or gate in production.
- The refusal message (`PUBLISH_APPROVAL_NOT_CONFIGURED`) is unchanged: it carries the process-start
  facts, not the per-agent setup, and stays minimal (MSP-R13).
- No README change: the README lists the MCP tool surface, not the guidance keys (verified).

## 3. Settled decisions

| # | Decision |
| --- | --- |
| D1 | The issue's **mechanism** is wrong, its **symptom** is right: the blamed dict is dead. The fix targets the three constants and the two hand-kept test key sets. |
| D2 | Derive from the `env` capability (`none` / `allow_list` / `refs` / `refs_braced`) — the enum `build_entry` branches on — so prose and registration cannot disagree, and `pi`/`hermes` sharing `refs_braced` is the point rather than a coincidence. |
| D3 | Delete the dead table and the three constants: net deletion, one capability table instead of N constants. |
| D4 | Payload change is additive; flatness, namespacing, the `action` key and the NEVER-LEAK rules are untouched. |
| D5 | "Only the asking agent's fact" is deferred: it needs a host-identity mechanism that does not exist and it would break consumers reading their own agent's key. |
| D6 | The guard reuses the existing sentinel-patch pattern; the two literal key sets in tests derive from `AGENT_NAMES`. |
| D7 | The registry is read at **call time**, never at import, so the sentinel guard is meaningful. |

## 4. Affected specs

`mcp-server`: APX-01 (Modified — the per-agent guidance clause is rewritten to require coverage of the
whole registry and derivation from its capability) plus two scenarios. No requirement added or
removed; `mcp-server` is a declared-backlog spec, so no `## Test Mapping` row and no registry edit.

## 5. Risks

| # | Risk | Severity | Disposition |
| --- | --- | --- | --- |
| R1 | Two new keys in a tool payload consumers read. | Low | Additive; no existing key, value or ordering guarantee changes, and the exact-set pin in tests now derives from the registry instead of a literal. |
| R2 | A capability with no template would raise at call time. | Low | Guarded by `test_capability_table_covers_every_registry_capability`, so it fails CI before it can ship; `AGENT_NAMES` is `tuple(ADAPTERS)` by definition, so the agent lookup cannot miss. |
| R3 | Template interpolation and the literal `${NAME}` braces. | Caught | The first implementation raised `KeyError: 'NAME'`; the reference form is now a separate table field interpolated as `{form}`. Recorded in `design.md`. |

## 6. Rollback

Revert-only: restoring the three constants, the dead dict and the two literal test key sets restores
the previous payload exactly. No state, no migration, no artifact to clean.

## 7. Success criteria

SC-1 Every registered agent has a setup fact; a sentinel agent added to `ADAPTERS` appears with no
     other edit.
SC-2 Each fact names the field and reference form `build_entry` really writes for that agent.
SC-3 A capability with no template fails the guard.
SC-4 Flatness, namespacing, NEVER-LEAK and the refusal message are unchanged.
SC-5 Full suite, ruff/format/mypy/pyright and the mapping checker green.
