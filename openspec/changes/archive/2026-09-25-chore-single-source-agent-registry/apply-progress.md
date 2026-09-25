# Apply Progress: 2026-09-25-chore-single-source-agent-registry

## Summary

All tasks (Phase 1–4) implemented. Pure refactor: no entry shape, path, delegation or
env behavior changed. `git diff --stat`:

```
src/sofer/cli.py               |  63 ++++----
src/sofer/mcp_registration.py  | 320 +++++++++++++++++++++--------------------
tests/test_mcp_registration.py | 114 ++++++++++++++-
3 files changed, 303 insertions(+), 194 deletions(-)
```

## What changed

### `src/sofer/mcp_registration.py`

- `Adapter` now carries `fmt`, `key`, `user_parts`, `project_parts`, `command`,
  `adds_type_local`, `env`, `delegates`. `ADAPTERS` holds the three agents and is the
  single source; `AGENT_NAMES = tuple(ADAPTERS)`.
- `AgentName: TypeAlias = str` (design D2). `_adapter(agent)` returns the entry or
  raises `ValueError("unknown agent: ...")`; `_delegates(agent)` preserves the legacy
  unknown-name fall-through for the delegation probes.
- `resolve_config_path` joins registry path parts; `build_entry` (legacy key order
  preserved), `_entries_equal` (codex-only command normalization), `merge`,
  `remove_entry`, `probe_native`, `delegate_add`, `delegate_remove` and
  `dropped_env_keys` read the registry.
- `ADAPTERS["key"]` is now consumed by `merge`/`remove_entry`; no `"mcp"` /
  `"mcp_servers"` / `"mcpServers"` literals remain in those functions.
- `delegate_add` declares the single native shape and returns its exit status.

### `src/sofer/cli.py`

- Imports the `mcp_registration` module and drops the `_AgentName`/`_Scope` aliases.
- Both `--agent` `choices` = `[*mcp_registration.AGENT_NAMES, "all"]`; both `all`
  expansions = `list(mcp_registration.AGENT_NAMES)`; `fmt` read from the registry.
- `_cmd_mcp_add` file-edit anchor collapsed to
  `cwd_resolved if scope == "project" else None` (same resolved behavior).

### `tests/test_mcp_registration.py`

- Renamed the `_normalize_command` test.
- New `TestSingleSourceRegistry`: registry↔`AGENT_NAMES`, per-adapter completeness,
  per-agent path resolution, CLI `choices` for `add`/`remove`, and a sentinel registry
  entry that must appear in choices and be written by `--agent all`.

## Deviations from design

The first implementation generalized command normalization to all agents, which an
independent adversarial review (differential harness against `HEAD`) falsified: a gemini
config whose `sofer.command` is `["sofer-mcp"]` became "already registered" instead of
being rewritten, and the delegation probes raised on unknown names where they previously
fell through. Both were restored to exact pre-refactor behavior (`_entries_equal` keeps
codex-only normalization; `_delegates` preserves the unknown fall-through), build_entry
key order was restored, and `TestRefactorParity` pins all three. No behavior change
remains in the diff.

The `_cmd_mcp_add` project/user resolve ladder was collapsed to one expression with an
`anchor` ternary — same resolved paths, simpler branch coverage.

## Notes for #142

Adding `pi` is one `ADAPTERS` entry with the capability fields (`fmt`, `key`,
`user_parts`, `project_parts`, `command`, `adds_type_local`, `env`, `delegates`); the
CLI choices and `--agent all` pick it up with no `cli.py` change.

## Out-of-scope observation

`src/sofer/mcp_server.py:218-236` has its own `_APPROVAL_PHRASE_AGENT_ENTRY_KEYS` table
(approval-phrase setup hints). It is a different concern and stays untouched; flagged as
an adjacent follow-up, not part of #235.
