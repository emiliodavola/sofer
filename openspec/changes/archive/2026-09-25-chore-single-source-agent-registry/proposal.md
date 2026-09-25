# Proposal: 2026-09-25-chore-single-source-agent-registry

**Change:** `2026-09-25-chore-single-source-agent-registry` · **Issue:** #235 `type:chore`
· **Branch:** `chore/235-single-source-agent-set` (base `dev@93677b3`, PR-only)

## Intent

Issue #235: the MCP agent set (`opencode`, `codex`, `gemini`) is duplicated across at
least eight sites in `mcp_registration.py` and `cli.py`, so adding the fourth agent
`pi` (#142) is a copy-paste sweep that already has a failure mode — accepting
`--agent pi` in argparse while `resolve_config_path` raises `ValueError`. Two pieces of
surrounding code are dead: `ADAPTERS[...]["key"]` is never read and `delegate_add`
declares three native command shapes but runs only the first. This change makes the
agent set and every per-agent capability a single registry entry, so #142 becomes a
one-entry change and there is nothing left to drift.

## Scope

### In Scope

- `src/sofer/mcp_registration.py`: extend `ADAPTERS` into the single per-agent registry
  (fmt, config key, user/project path parts, command style, env capability, delegation);
  derive `AGENT_NAMES` from it; make `resolve_config_path`, `build_entry`,
  `_entries_equal`, `merge`, `remove_entry`, `probe_native`, `delegate_add`,
  `delegate_remove` and `dropped_env_keys` consume it. Use or remove `ADAPTERS["key"]`.
  Remove the dead `cmd_variants` from `delegate_add`.
- `src/sofer/cli.py`: both `--agent` argparse `choices` and both `all` expansions derive
  from `mcp_registration.AGENT_NAMES`; `fmt` is read from the registry.
- Tests: single-source/drift coverage in `tests/test_mcp_registration.py` (registry vs
  paths, CLI choices, and a sentinel registry entry that flows into choices and
  `--agent all`), plus the `_normalize_codex_command` → `_normalize_command` rename.

### Out of Scope

- **#142 (`pi`)** — no `pi` entry, no new adapter shape, no `all` → 4 in this PR; #142
  lands on top.
- **#167 (env forwarding) and #232** — untouched.
- **`src/sofer/mcp_server.py:218-236`** — its own `_APPROVAL_PHRASE_AGENT_ENTRY_KEYS`
  table is a *different* concern (approval-phrase setup hints); the issue scopes files
  to `mcp_registration.py`, `cli.py` and their tests. Noted as an adjacent follow-up.
- **Behavior change of any kind** — entries, paths, idempotency, delegation and env
  handling are preserved; this is an internal refactor.

### New Capabilities

None — no spec-level behavior changes.

### Modified Capabilities

None — pure refactor. `mcp-registration` and `cli` are registered as unmapped and carry
no `## Test Mapping` table, so the test-mapping contract is unchanged.

## Approach

1. `ADAPTERS` becomes the single source: each entry carries `fmt`, `key`, `user_parts`,
   `project_parts`, `command` (`array`/`string`), `adds_type_local`, `env`
   (`none`/`allow_list`/`refs`) and `delegates`.
2. `AGENT_NAMES = tuple(ADAPTERS)`. A private `_adapter(agent)` helper centralises the
   unknown-agent `ValueError`.
3. Every consumer derives: path resolution joins the registry parts; `build_entry`
   builds from `command`/`adds_type_local`/`env`; `merge`/`remove_entry` use `key`;
   `_entries_equal` normalises command for all agents and compares env per capability;
   delegation and env-drop read the capability flags.
4. `delegate_add` declares one native shape and returns its exit status.
5. Refresh test names and add drift tests.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/mcp_registration.py` | Modified | Registry is the single source; per-agent branches removed |
| `src/sofer/cli.py` | Modified | Choices + `all` derive from `AGENT_NAMES`; registry `fmt` |
| `tests/test_mcp_registration.py` | Modified | Drift tests + helper rename |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Refactor silently changes entry shape or path | Low | Existing MCP-REG-01/02 tests assert entries, paths, idempotency, backups; all pass |
| A consumer still hardcodes the set and drifts | Low | Sentinel-registry test proves choices and `all` track `ADAPTERS`; choices test compares to `AGENT_NAMES` |
| Coverage floor for `mcp_registration.py` (≥90) or `cli.py` (100) regresses | Low | Measured 100% both; core gate script green |
| Dropping the `Literal` weakens typing | Low | Runtime `_adapter` validation + argparse choices; mypy/pyright clean |

## Rollback Plan

Revert the three-file diff. No data, config-format, migration or public CLI surface
change; existing registrations keep working because entry shapes and paths are
byte-equivalent.

## Dependencies

- None. `#142` depends on this change, not the reverse.

## Success Criteria

- [x] The agent set has one source (`ADAPTERS`); `AGENT_NAMES`, both choices, both `all`
      expansions and `resolve_config_path` derive from it.
- [x] `ADAPTERS["key"]` is used (`merge`/`remove_entry`); no per-agent key is hardcoded.
- [x] `delegate_add` declares only the shape it uses (dead variants removed).
- [x] Drift tests: a new registry entry flows into CLI choices and `--agent all`.
- [x] `uv run pytest tests/ -q` green; ruff / mypy / pyright / test-mapping / core-coverage clean.
