# Proposal: 2026-09-25-feat-pi-mcp-agent

**Change:** `2026-09-25-feat-pi-mcp-agent` · **Issue:** #142 `type:feature`
· **Branch:** `feat/142-pi-mcp-agent` (base `dev@b546db3`, PR-only)

## Intent

Issue #142: `sofer mcp add/remove --agent` supports `opencode`, `codex`, and
`gemini`, but not `pi` (the Pi coding agent, which consumes MCP through
`pi-mcp-adapter`). A user with an opencode-shaped `sofer` entry in the shared
`~/.config/mcp/mcp.json` hits `Server sofer must configure exactly one of
command, url, or socket`, because Pi reads that file at low precedence and
requires a **string** `command`, never the opencode array. Add `pi` to the
agent set so `--agent pi` and `--agent all` register/remove `sofer-mcp` in
Pi's own config with the exact shape Pi validates — which, at user scope, also
shadows and remediates the malformed shared entry.

This lands on the single-source registry of #235 (merged #241): adding Pi is
one `ADAPTERS` entry plus two new capability values, not a new per-agent
branch ladder.

## Scope

### In Scope

- `src/sofer/mcp_registration.py`: add `ADAPTERS["pi"]`; two new adapter
  capabilities — `user_env_dir` (env var overriding the user config directory,
  `PI_CODING_AGENT_DIR`) and `env="refs_braced"` (`${KEY}` interpolation);
  derive path resolution and entry building from them; make `_entries_equal`
  follow the `env` capability instead of an agent-name ladder.
- `src/sofer/cli.py`: update the human-facing `mcp`/`add` `help=`/`description=`
  strings to name Pi; both `choices` and both `all` expansions already derive
  from `AGENT_NAMES`, now four agents.
- Docs: `README.md` + `README_ES.md` agent table, examples and prose.
- Specs: `mcp-registration` MCP-REG-01/02/03 and `cli` CLI-R09 updated for the
  fourth agent and Pi's `${KEY}` env shape.
- Tests: `tests/test_mcp_registration.py` (new `TestPiAdapter`/`TestPiCli`,
  four-agent `all`) and `tests/test_cli.py` (help assertion).

### Out of Scope

- **`src/sofer/mcp_server.py`** `_APPROVAL_PHRASE_AGENT_ENTRY_KEYS` — an
  adjacent approval-phrase-hint roster; a different concern, noted as a
  follow-up (same boundary #235 drew).
- **#167 (env forwarding redesign), #232, #204** — untouched.
- **Pi `directTools`/`lifecycle`/`toolPrefix` options** — a follow-up; the
  entry stays minimal so Pi's token-efficient proxy defaults apply.

### New Capabilities

None — no new capability domain.

### Modified Capabilities

- `mcp-registration` (MCP-REG-01, MCP-REG-02, MCP-REG-03): the supported agent
  set grows to four; the add/remove tables and scenarios gain Pi; `--agent all`
  expands to four. MCP-REG-03's "exactly three agents" wording changes.
- `cli` (CLI-R09): `--agent` surface and the env-forwarding help sentence name
  the four agents.

## Approach

1. Extend `Adapter` with `user_env_dir: str | None` and add `refs_braced` to
   the `env` Literal; every entry declares `user_env_dir` (`None` except Pi).
2. `ADAPTERS["pi"] = {fmt:"json", key:"mcpServers", user_parts:(".pi","agent",
   "mcp.json"), project_parts:(".pi","mcp.json"), command:"string",
   adds_type_local:False, env:"refs_braced", delegates:False,
   user_env_dir:"PI_CODING_AGENT_DIR"}`.
3. `resolve_config_path` user scope: when `user_env_dir` is set and its variable
   is non-empty, use `<var>/<user_parts[-1]>`; else `Path.home()/user_parts`.
4. `build_entry`: `refs_braced` emits `{key: "${key}"}`; Pi stays a string
   command with no `type`/`args`/`enabled`.
5. `_entries_equal`: branch on the adapter `env` capability
   (`allow_list` / `refs`+`refs_braced` / else) rather than on agent names.
6. CLI help/descriptions + READMEs name Pi; specs updated.
7. Tests mirror the existing per-agent matrices for Pi.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/mcp_registration.py` | Modified | Pi entry + two capability values; capability-driven equality/path/entry |
| `src/sofer/cli.py` | Modified | Help/description strings name Pi |
| `src/sofer/README.md`, `README_ES.md` | Modified | Agent table, examples, env/delegation prose |
| `openspec/specs/mcp-registration/spec.md` | Modified | MCP-REG-01/02/03 four-agent + Pi scenarios |
| `openspec/specs/cli/spec.md` | Modified | CLI-R09 `--agent` + env-forwarding sentence |
| `tests/test_mcp_registration.py`, `tests/test_cli.py` | Modified | Pi coverage; four-agent `all` |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Pi entry wrong shape (array command / `type`) re-breaks Pi | Low | `TestPiAdapter` asserts exact entry dict and string command |
| `${KEY}` vs `$KEY` regression persists a literal reference | Low | Test asserts braced form and absence of bare `$HF_TOKEN` |
| `all` still expands to three somewhere | Low | Registry-derived expansion + four-agent assertions in both CLI and warnings tests |
| `user_env_dir` override leaks into other agents' paths | Low | Field is `None` for all non-Pi agents; generic path test covers every agent |
| Coverage floor for `cli.py` (100%) or `mcp_registration.py` regresses | Low | New lines exercised by the new Pi tests; measured in verify |
| MCP-REG-03 "three agents" requirement left stale | Low | Delta MODIFIES MCP-REG-03; canonical spec synced in-change |

## Rollback Plan

Revert the change. No data or migration is involved. Because `--agent all`
grows from three to four, a rollback stops touching Pi-owned files but leaves
any already-written Pi entry in place; removal is a manual edit or a re-run on
the previous revision. Existing opencode/codex/gemini registrations are
byte-identical and unaffected.

## Dependencies

- Requires the single-source registry from #235 (merged #241, `ADAPTERS` /
  `AGENT_NAMES`). No new third-party dependency.

## Success Criteria

- [ ] `sofer mcp add --agent pi` writes the Pi-owned file (user:
  `$PI_CODING_AGENT_DIR/mcp.json` else `~/.pi/agent/mcp.json`; project:
  `./.pi/mcp.json`) with `mcpServers.sofer={command:"sofer-mcp",cwd,env:{KEY:"${KEY}",…}}`
  — string command, no `type`/`args`/`enabled`, no secret values.
- [ ] Re-run is byte-identical (no `.bak`, no write); backup/atomic/dry-run/
  unreadable behave exactly like the other agents.
- [ ] `sofer mcp remove --agent pi` removes only `sofer` and preserves others;
  idempotent when absent.
- [ ] `--agent all` covers pi (four agents) for both `add` and `remove`.
- [ ] Pi never delegates (`probe_native`/`delegate_*` file-edit only).
- [ ] README + README_ES + CLI help updated; specs synced; suite and lone
  checkers green.
