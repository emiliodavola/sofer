# Design: 2026-09-25-feat-pi-mcp-agent

## Context

`mcp_registration.py` owns per-agent behavior through the single-source
`ADAPTERS` registry (#235, merged #241); `cli.py` derives `--agent` choices and
`--agent all` from `AGENT_NAMES = tuple(ADAPTERS)`. Pi (`pi-mcp-adapter`) needs
two capabilities no existing agent has: a user config directory selected by an
environment variable, and a braced `${KEY}` env-reference syntax. Everything
else Pi needs is ordinary registry data.

## Decisions

### D1 — Pi is one registry entry plus two capability fields

`Adapter` gains `user_env_dir: str | None` and the `env` Literal gains
`"refs_braced"`. Every entry declares `user_env_dir` (`None` for
opencode/codex/gemini) so the "every adapter is complete" test stays an exact
`set(spec) == required` invariant rather than a per-agent special case.

```python
"pi": {
    "fmt": "json",
    "key": "mcpServers",
    "user_parts": (".pi", "agent", "mcp.json"),
    "project_parts": (".pi", "mcp.json"),
    "command": "string",
    "adds_type_local": False,
    "env": "refs_braced",
    "delegates": False,
    "user_env_dir": "PI_CODING_AGENT_DIR",
}
```

Rationale: `pi` becomes exactly the "one site" #235 designed for; the new
fields are the "new field only if the agent needs a shape no other agent has"
escape hatch the #235 design documented.

### D2 — `resolve_config_path` resolves the env-dir override generically

User scope:
`override = os.environ.get(spec["user_env_dir"]) if spec["user_env_dir"] else None`;
when truthy, return `Path(override) / spec["user_parts"][-1]`; else
`Path.home() / user_parts`. This matches Pi's `getAgentDir()` (config dir env
var replaces the home prefix; the file name is `mcp.json`) and refuses empty
strings. Project scope is unchanged (`<cwd>/.pi/mcp.json`).

### D3 — `build_entry` grows one env branch: `refs_braced` → `${KEY}`

`allow_list` (codex) and `refs` (gemini) branches stay byte-identical; a new
`refs_braced` branch emits `{k: f"${{{k}}}"}`. Pi otherwise composes from the
same registry fields: `command="string"`, `adds_type_local=False`, so the entry
is `{command, cwd, env}` with no `type`/`args`/`enabled`. This is the shape
`server-manager.ts` validates (exactly one non-empty string transport), and it
deliberately shadows a malformed lower-precedence shared entry.

### D4 — `_entries_equal` follows the `env` capability, not agent names

Replace the `if agent == "codex"` / `if agent == "gemini"` ladder with:

- `env == "allow_list"` → normalize command, compare `cwd`, sorted `env_vars`
- `env in ("refs", "refs_braced")` → compare raw `command`, `cwd`, `env`
- else (`"none"`, unregistered) → full structural equality

Pi and gemini share the reference branch without copy-paste, and the behavior
pinned by the existing `_entries_equal` tests is preserved (gemini still rejects
the array command form). This is the capability-driven form #235 intended but
had left name-keyed.

### D5 — `delegates=False` makes Pi file-edit only

`probe_native`/`delegate_add`/`delegate_remove` already gate on
`_delegates(agent)`; Pi's `False` means `--agent all` never attempts a native
`pi mcp add` (which does not exist). No new code.

### D6 — `--agent all` becomes four; specs and docs move with it

MCP-REG-03 and the tests pin "all expands to exactly three". Those assertions
change to four, and MCP-REG-01/02/03 + CLI-R09 are synced in this change. The
CLI code itself needs no edit beyond `help=`/`description=` strings because both
`choices` and both expansions derive from `AGENT_NAMES`.

### D7 — `mcp_server.py` stays out

`_APPROVAL_PHRASE_AGENT_ENTRY_KEYS` is an approval-phrase-hint roster, a
different concern from registration. Adding Pi to the agent set does not
require editing it; recorded as a follow-up (same boundary #235 set).

## Contract / invariants

- `AGENT_NAMES == ("opencode", "codex", "gemini", "pi")`.
- Every adapter has exactly the nine keys, including `user_env_dir`.
- `build_entry("pi", …)` is a string-command entry with `${KEY}` env and no
  `type`/`args`/`enabled`; secret values never appear.
- `resolve_config_path("pi", "user")` is `$PI_CODING_AGENT_DIR/mcp.json` when
  set/non-empty, else `~/.pi/agent/mcp.json`; project is `<cwd>/.pi/mcp.json`.
- `--agent all` accepts and expands to four agents for `add` and `remove`.
- opencode/codex/gemini entry shapes, paths and idempotency are unchanged.

## Test strategy

- `TestPiAdapter`: registry entry, entry shape, braced env + omitted keys,
  user path (default, env override, empty env), project path, never delegates,
  capability-driven `_entries_equal`.
- `TestPiCli`: user env-dir write, project write with env, idempotent (no
  `.bak`/write), dry-run, unreadable exit 1, remove preserves others, remove
  idempotent absent.
- Existing `TestSingleSourceRegistry` updated for the fourth agent and the new
  adapter key; `TestEnvForwarding`/`TestDryRun`/`TestRemove` `all` assertions
  now expect `.pi/mcp.json`.
- `tests/test_cli.py` help assertion updated to the new env sentence.

## Consequences

- Adding `pi` changed no `cli.py` logic — only help text — proving the
  single-source contract holds for a real fourth agent.
- The shared `~/.config/mcp/mcp.json` remains untouched; Pi writes only its own
  agent-dir file, which also remediates the #142 failure at user scope.
