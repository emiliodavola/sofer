# Explore — `2026-09-25-chore-single-source-agent-registry`

> Change: issue **#235** (chore, `need-review`) — *agent set duplicated in 6+ sites,
> `ADAPTERS[key]` unused, `delegate_add` has dead command variants (#142 prerequisite)*.
> Branch `chore/235-single-source-agent-set` from `dev@93677b3`. Store: hybrid (files + Engram).

## Problem

Adding a fourth MCP agent (`pi`, #142) required editing the agent set in at least eight
places. The issue's line numbers were from an older `dev`; the inventory below was
re-derived on the branch HEAD by an independent `explore` sub-agent and verified by grep.

## Verified inventory (branch HEAD)

| # | Site | Evidence |
|---|------|----------|
| 1 | `AgentName` Literal | `src/sofer/mcp_registration.py:38` |
| 2 | `ADAPTERS` table | `src/sofer/mcp_registration.py:51-55` |
| 3 | argparse `choices` (add) | `src/sofer/cli.py:1524` |
| 4 | argparse `choices` (remove) | `src/sofer/cli.py:1556` |
| 5 | `all` expansion (`_cmd_mcp_add`) | `src/sofer/cli.py:665` |
| 6 | `all` expansion (`_cmd_mcp_remove`) | `src/sofer/cli.py:775` |
| 7 | `resolve_config_path` per-agent branches (user + project) | `src/sofer/mcp_registration.py:80-95` |
| 8 | per-agent branches in `build_entry`, `merge`, `remove_entry`, `delegate_*`, `dropped_env_keys` | `src/sofer/mcp_registration.py` |

Dead / unused:

- `ADAPTERS[...]["key"]` is **never read** in `src/` or `tests/` (only `["fmt"]` is read at
  `cli.py:748` and `:821`); `merge`/`remove_entry` hardcode `"mcp"`, `"mcp_servers"`, `"mcpServers"`.
- `delegate_add` declares three `cmd_variants` but `for cmd in cmd_variants[:1]` runs only the
  first and every loop path returns, so variants 2–3 are unreachable and the "fallback" comment
  is misleading.

## Options considered

| Option | Verdict |
|--------|---------|
| **Extend `ADAPTERS` into the single per-agent registry** (name, fmt, config key, paths, entry shape, delegation, env capability) and derive `AGENT_NAMES`, CLI choices, `all`, path resolution and entry/merge/remove from it | **Chosen.** One place to add an agent; every other site derives. |
| Keep a `Literal` mirror of the registry | Rejected as the *single* source: `Literal` cannot be derived from runtime data, so it would reintroduce a second name list. Documented in design D2. |
| Genuinely retry the three `delegate_add` shapes | Rejected: the native CLIs are probed best-effort and the caller already falls back to file-edit; a shape retry is untested speculation. Declare only the shape used. |

## Affected specs

`mcp-registration` and `cli` are **registered as unmapped** in
`openspec/test-mapping-registry.md` and carry no `## Test Mapping` table, so a pure
refactor — no requirement/scenario change — needs **no delta spec** and leaves the
test-mapping contract unchanged.
