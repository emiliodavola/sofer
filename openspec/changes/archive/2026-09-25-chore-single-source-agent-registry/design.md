# Design: 2026-09-25-chore-single-source-agent-registry

## Context

`mcp_registration.py` owns the per-agent behavior; `cli.py` owns the MCP subcommands.
Before this change the agent name set appeared in the `AgentName` Literal, the
`ADAPTERS` table, two argparse `choices` lists, two `all` expansions, and inside every
per-agent branch — eight-plus copies that must be kept in lockstep. Two adjacent pieces
were dead (`ADAPTERS["key"]`, `delegate_add`'s `cmd_variants[1:]`). No public behavior
is meant to change.

## Decisions

### D1 — `ADAPTERS` is the single source; every consumer derives from it

The registry entry is the one place an agent's identity *and* capabilities are defined.
The `Adapter` `TypedDict` gains `user_parts`, `project_parts`, `command`,
`adds_type_local`, `env` and `delegates`, alongside the existing `fmt` and `key`
(previously dead). `AGENT_NAMES = tuple(ADAPTERS)` is the one derived name list.

Rationale: the issue's deliverable is "adding `pi` is a one-site change". Any design that
keeps the name list separate from the per-agent data still requires two edits. A private
`_adapter(agent)` helper centralises the `ValueError("unknown agent: ...")` contract that
`resolve_config_path`/`build_entry`/`merge`/`remove_entry` previously each re-declared.

### D2 — `AgentName` is a `str` alias, not a `Literal`

`AgentName: TypeAlias = str` documents the registry key domain. `typing.Literal` values
must be literal at type-check time, so deriving the type from `ADAPTERS` is impossible;
keeping a hand-maintained Literal would reintroduce exactly the second name list this
change removes. Static safety is preserved by `_adapter` (runtime validation for every
function) and argparse `choices` (CLI boundary). Reviewed: mypy and pyright stay clean.

### D3 — Entry/merge/remove/path logic is data-driven

- `resolve_config_path` joins `user_parts` / `project_parts` onto `Path.home()` / the
  resolved project root — the per-agent `if` ladder is gone.
- `build_entry` composes `command` (`["sofer-mcp"]` vs `"sofer-mcp"`),
  optionally `type="local"`, then `env_vars` (allow-list) or `env` (`$KEY` refs) per the
  `env` capability, in the same key order as the previous per-agent literals (`type`,
  `command`, `cwd`, then env for opencode) so serialized bytes are unchanged.
- `merge` / `remove_entry` are one generic body keyed by `ADAPTERS[agent]["key"]`.
- `_entries_equal` keeps the original per-agent semantics: codex normalizes command
  string/array and compares sorted `env_vars`; gemini compares raw command/cwd/`env`
  (it does **not** accept the array form); opencode compares full structural equality.
  The `Literal`-era behavior is pinned by tests so the refactor cannot silently change
  gemini idempotency.
- `probe_native` / `delegate_add` / `delegate_remove` gate on a `_delegates(agent)`
  helper; `dropped_env_keys` gates on the `env == "none"` capability. Unregistered
  names keep the pre-#235 fall-through (no `ValueError`) so these callables' contracts
  are unchanged.

### D4 — `delegate_add` declares only the shape it uses

The three-shape list with `[:1]` and a "fallback" comment was dead. It becomes a single
`<agent> mcp add sofer --command sofer-mcp --cwd <cwd>` invocation returning
`result.returncode == 0`; the caller keeps the documented file-edit fallback.

### D5 — `mcp_server.py` stays out

`mcp_server.py:218-236` holds a separate `_APPROVAL_PHRASE_AGENT_ENTRY_KEYS` table for
approval-phrase setup hints. It is a distinct concern, not part of the MCP registration
agent set, and the issue scopes the files explicitly. Recorded as an adjacent follow-up.

## Contract / invariants

- `tuple(ADAPTERS) == AGENT_NAMES`; each entry has all eight keys.
- For every `agent in AGENT_NAMES`: `resolve_config_path(agent, "user")` equals
  `Path.home() / user_parts` and `resolve_config_path(agent, "project", cwd)` equals
  `cwd.resolve() / project_parts`.
- Argparse `--agent` choices for `mcp add`/`mcp remove` equal `[*AGENT_NAMES, "all"]`.
- Adding an entry to `ADAPTERS` makes it accepted by both subcommands and expanded by
  `--agent all` without touching `cli.py`.

## Test strategy

- Existing MCP-REG-01/02 and CLI-R09 tests are the regression net (entries, backups,
  idempotency, dry-run, delegation, warning matrix).
- New `TestSingleSourceRegistry`: registry↔`AGENT_NAMES`, per-adapter completeness,
  path resolution for every agent, CLI choices for both subcommands, and a sentinel
  registry entry proving choices + `--agent all` track the registry.
- `_normalize_codex_command` test renamed to `_normalize_command`.

## Consequences

- Adding `pi` (#142) = one `ADAPTERS` entry (plus `Adapter` fields if it needs a new
  shape) and no `cli.py` edit.
- `AgentName` no longer narrows statically; runtime validation and CLI choices carry the
  domain instead.
