# Explore: 2026-09-25-feat-pi-mcp-agent

**Change:** `2026-09-25-feat-pi-mcp-agent` · **Issue:** #142 · **Branch:** `feat/142-pi-mcp-agent`

## Question

What is the minimum, single-source change to let `sofer mcp add/remove --agent`
register/remove `sofer-mcp` in **Pi** (`pi-mcp-adapter`)'s own config, using the
exact entry shape Pi validates, on top of the #235/#241 agent registry?

## Findings from the current tree

- `src/sofer/mcp_registration.py` already has the single-source `ADAPTERS`
  registry (`Adapter` TypedDict + `AGENT_NAMES = tuple(ADAPTERS)`), consumed by
  path resolution, `build_entry`, `_entries_equal`, `merge`/`remove_entry`,
  `probe_native`/`delegate_*` and `dropped_env_keys` (#235, merged #241).
- `src/sofer/cli.py` derives both `--agent` `choices` and both `--agent all`
  expansions from `mcp_registration.AGENT_NAMES`; adding a registry entry is
  enough for the CLI to accept and expand it. Only the human-facing
  `help=`/`description=` strings name the three agents literally.
- Existing entry shapes: opencode `type/command(array)/cwd`, codex
  `command(string)/cwd/env_vars`, gemini `command(string)/cwd/env` with `$KEY`
  references.

## Pi facts (from issue #142's sourced research; `pi-mcp-adapter@2.32.1`)

- Pi-owned config: user `$PI_CODING_AGENT_DIR/mcp.json`, default
  `~/.pi/agent/mcp.json`; project `<cwd>/.pi/mcp.json`. It *reads* the shared
  `~/.config/mcp/mcp.json` at lower precedence — so a valid higher-precedence Pi
  entry also remediates the reported failure caused by an opencode-shaped shared
  entry.
- `ServerEntry.command` is a **string**; exactly one of `command`/`url`/`socket`
  must be a non-empty string. An array `command` (opencode shape) is filtered
  out → `Server must configure exactly one of command, url, or socket`.
- No native `pi mcp add` CLI exists → **file-edit only**, like opencode.
- Env interpolation only matches `${NAME}`, `$env:NAME`, `{env:NAME}` — **not**
  a bare `$NAME`. So Pi must emit `${KEY}`, unlike Gemini's `$KEY`.

## Two capabilities Pi needs that no current agent has

1. **A user config directory overridable by an environment variable**
   (`PI_CODING_AGENT_DIR`). The registry's `user_parts` are static under
   `Path.home()`. New optional adapter field: `user_env_dir`.
2. **A different env-reference syntax** (`${KEY}` vs `$KEY`). New `env`
   capability value: `refs_braced`.

Everything else Pi needs already exists as registry data (`fmt`, `key`,
`project_parts`, `command="string"`, `adds_type_local=False`, `delegates=False`).

## Options considered

| Option | Verdict |
|--------|---------|
| Add a `pi` entry with two new capability fields (`user_env_dir`, `refs_braced`) | **Chosen** — one-site change, no per-agent `if` branches beyond capability reads |
| Hardcode Pi inside `resolve_config_path`/`build_entry`/`_entries_equal` | Rejected — reintroduces the drift #235 removed |
| Write the shared `~/.config/mcp/mcp.json` instead of Pi-owned files | Rejected — lower precedence, and mixes secrets into a file other tools read |
| Add `directTools`/`lifecycle` Pi fields | Out of scope — Pi's proxy defaults are the point; a follow-up can expose them |

## Constraints

- No secret values on disk; env NAMES only, same guarantee as codex/gemini.
- `--agent all` now expands to four agents; MCP-REG-01/02/03 and CLI-R09 pin
  "three" and MUST be updated.
- CLI-core files (`cli.py`) keep 100% line coverage; `mcp_registration.py`
  keeps its per-file floor.
- `mcp_server.py`'s `_APPROVAL_PHRASE_AGENT_ENTRY_KEYS` roster is a different
  concern (approval-phrase setup hints) and stays out of scope, as recorded in
  #235's archive report.
