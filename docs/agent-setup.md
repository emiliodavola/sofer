# Agent setup

This page covers launching `sofer-mcp`, choosing its root, registering it with
the supported agents, forwarding environment variables, and configuring host
timeouts. For the tool surface, see [MCP server](mcp.md). For containment and
publish authorization, see [Security](security.md).

## Launch

```bash
sofer-mcp          # stdio MCP server (JSON-RPC 2.0 over stdin/stdout)
```

The server's containment root defaults to its working directory (the process
`cwd`, resolved). Point it at a specific tree with `--root PATH` or the
`SOFER_MCP_ROOT` environment variable; the argument wins when both are set. A
path outside that root is refused with `PathOutsideRootError` (fail closed), so
the agent can only reach the chosen tree.

Example with Claude Code:

```bash
claude mcp add sofer -- uv run sofer-mcp
```

## Register with an agent

`sofer` can register itself in five agent configurations idempotently,
preserving existing servers and backing up the original to `.bak`:

```bash
sofer mcp add --agent all                 # register in all five
sofer mcp add --agent opencode --scope project --cwd ./my-proj
sofer mcp add --agent codex --scope user
sofer mcp add --agent gemini --scope user --dry-run   # preview, no write
sofer mcp add --agent pi --scope user                 # pi-mcp-adapter
sofer mcp add --agent hermes --scope user             # Hermes Agent (config.yaml)
sofer mcp remove --agent all              # remove from all five
```

Per-agent locations and shapes:

| Agent | Scope | File | Entry |
| --- | --- | --- | --- |
| opencode | `--scope project` | `./opencode.json` | `mcp.sofer={type:"local",command:["sofer-mcp"],cwd}` |
| opencode | `--scope user` | `~/.config/opencode/opencode.json` | same |
| codex | `--scope user` | `$CODEX_HOME/config.toml` (default `~/.codex/config.toml`) | `[mcp_servers.sofer] command, cwd, env_vars=[HF_TOKEN,…]` |
| codex | `--scope project` | `./.codex/config.toml` | same |
| gemini | `--scope user` | `~/.config/gemini/settings.json` | `mcpServers.sofer={command:"sofer-mcp",cwd,env:{HF_TOKEN:"$HF_TOKEN",…}}` |
| gemini | `--scope project` | `./.gemini/settings.json` | same |
| pi | `--scope user` | `$PI_CODING_AGENT_DIR/mcp.json` (default `~/.pi/agent/mcp.json`) | `mcpServers.sofer={command:"sofer-mcp",cwd,env:{HF_TOKEN:"${HF_TOKEN}",…}}` |
| pi | `--scope project` | `./.pi/mcp.json` | same |
| hermes | `--scope user` | `$HERMES_HOME/config.yaml` (default `~/.hermes/config.yaml`) | `mcp_servers.sofer={command:"sofer-mcp",cwd,env:{HF_TOKEN:"${HF_TOKEN}",…}}` |
| hermes | `--scope project` | the same user-scope file — Hermes has no project-scope config; the substitution is named on stderr | same |

## Host timeouts

`sofer mcp add` writes the host's per-request and connect/startup deadlines into
the `sofer` entry. Both are real: `sofer-mcp` imports pandas, pyarrow, datasets,
and fastmcp before it can answer `initialize`, so a first launch after an
install or upgrade is slower than a warm one. When it exceeds the host's connect
deadline, the host reports `Connection failed … timed out`, which reads exactly
like a broken registration.

Measure the first launch on your machine with `sofer mcp doctor`. It prints the
measurement beside the entry key and the value written by `mcp add`, and names
the flags that raise them. The written value comes from `[tool.sofer]`, never
from a number frozen in the documentation.

A tool call on a real corpus can run for minutes: `sofer_prepare` measured about
680 s and `sofer_codebook_all` about 100 s on a 3.2 GB / 66.2 M-row corpus,
against a documented 60 s host default. In that case the server finishes, writes
its artifacts, and loses only the response — so the caller cannot tell a failure
from an unheard success.

| Agent | Per-request key | Connect/startup key | Unit | Host default |
| --- | --- | --- | --- | --- |
| pi | `timeout` | — (connects in the background) | seconds | 60, reset by progress notifications |
| hermes | `timeout` | `connect_timeout` | seconds | 300 / 60 |
| codex | `tool_timeout_sec` | `startup_timeout_sec` | seconds | 60 / 10 |
| gemini | `timeout` | — (same key covers discovery) | milliseconds | 600,000 |
| opencode | — | `timeout` | milliseconds | 5,000 for the tool fetch; 30,000 in code |

Defaults come from `[tool.sofer] mcp_request_timeout_seconds` (900) and
`mcp_connect_timeout_seconds` (120). Override per invocation with `--timeout` /
`--connect-timeout`, or omit both keys with `--no-timeout`.

Writing a timeout is also why native codex/gemini delegation declines with the
reason `timeout`: neither `<agent> mcp add` takes a timeout flag, and
`--no-timeout` restores that path. The decline names the flag on stderr, but only
when `timeout` is the sole reason. With an env key present the reasons are
`env forwarding, timeout`, and the flag clears only the second.

**opencode** receives `timeout` as a single scalar in milliseconds carrying the
connect budget — the shape the schema for the layout this command writes
accepts, and the budget that scalar documents (fetching the server's tools,
including the cold start). It is never written as the nested object some
releases document, which would risk failing validation of the whole `mcp` block
for a sub-key name that differs between releases. A host whose entry accepts no
timeout key at all is named on stderr rather than given an invented one.

The **position** of the opencode entry matters: a v2 opencode reads its servers
from `mcp.servers.<name>`, while this command writes the entry at `mcp.<name>` —
the position v1's schema declares and v2 still reads, because v2 normalizes the
flat V1 form in memory. One entry serves both generations; writing
`mcp.servers.<name>` here would be the defect, since that is where a stable
opencode does not look.

Long calls reset their own deadline. Every long tool (`sofer_prepare`,
`sofer_codebook_all`, `sofer_profile_all`, `sofer_render_all`,
`sofer_publish_confirm`) re-announces progress while it runs, which resets a
host's per-request timeout. Their `tools/list` descriptions say so and name the
expected duration.

## Environment forwarding

`HF_TOKEN` and `SOFER_MCP_APPROVAL_PHRASE` from the shell are forwarded:

- codex: an `env_vars` allow-list;
- gemini, pi, hermes: an explicit `env` dict (no shell inheritance);
- gemini emits `$KEY` references;
- pi and hermes emit `${KEY}` references — `pi-mcp-adapter` interpolates only
  the braced form, and Hermes resolves `${VAR}` / `${env:VAR}` inside a server
  entry;
- opencode receives no environment. When `HF_TOKEN` or
  `SOFER_MCP_APPROVAL_PHRASE` is set and `--agent opencode` (or `all`) is chosen,
  `sofer mcp add` prints a warning on stderr naming the dropped variables and
  leaves the exit code unchanged.

For a sensitive host, persist the env **name** only, never the secret. See
[Security](security.md#hardening-for-sensitive-hosts).

## Registration behavior

- **User-scope resolution.** The paths above are sofer's default resolution
  under `Path.home()`. Agents such as opencode may read their config from the
  system account home instead. Pass `--user-config PATH` to state the file
  explicitly; it wins over the adapter's env override and the home default. When
  the two homes differ, sofer prints a warning naming both instead of reporting
  a clean success.
- **Idempotency.** Re-running with the same `cwd` and env does no write and
  creates no `.bak`; the file is byte-identical.
- **Backup.** Before the first mutation the original is copied to `<path>.bak`
  (single file; overwrites any existing `.bak`).
- **Atomic write.** The new content is written to a temporary file in the same
  directory and committed via `os.replace`.
- **Cwd.** `--cwd` is stored as the resolved absolute path and must be an
  existing directory; otherwise the command exits 1 naming the resolved path. A
  tree outside the home and the process cwd is accepted with a warning naming
  it.
- **Delegation.** When a native binary is available (`codex` / `gemini`), its
  `mcp add` / `remove` is tried first (probe via `shutil.which` plus `mcp --help`
  with a 3 s timeout), but only when it can reproduce what the file edit would
  write. The native CLI must forward the same env names and the requested scope.
  Gemini receives `--scope user|project`; Codex has no scope selector and its
  native env flag takes literal values. A non-empty env (both agents), or
  `--scope project` for Codex, makes sofer decline, print a warning naming the
  reason (`env forwarding`, `project scope` — names only, never values), and
  edit the config file instead. On any native failure or timeout the command
  also falls back to a direct file edit. Opencode and Pi always use file-edit.
- **TOML warning.** Edits via `tomli` / `tomli-w` do not preserve comments or
  formatting in `config.toml`; the file is reformatted and comments are
  stripped.
- **YAML edits.** The `hermes` adapter splices only the `sofer` entry into
  `config.yaml`, so unrelated keys, comments, and indentation are preserved.
- **Hermes scope.** Hermes reads a single user-scope config, so `--scope
  project` for `--agent hermes` resolves to that same file. No
  `<cwd>/.hermes/config.yaml` is written, and the substitution is named on
  stderr.
- **Unreadable.** A malformed or unreadable config exits 1 and creates no backup
  or new file.

## Metadata ownership

`sofer init` writes a `[meta]` block whose values are placeholders. Filling them
is a required step between bootstrap and Phase 1, and it is the one step a human
and an agent share:

- the **agent** completes what the data can determine (description, tags);
- the **human** supplies what it cannot (license, source).

`sofer_meta_check` reports the state on demand and `sofer_meta_set` is the write
a tool can perform. `sofer_validate` also warns while any `[meta]` value is
empty or still starts with `TODO`, `YOUR_`, or `example`. The warning never
changes the exit code, and neither does `sofer_meta_check`.

## Verify a registration

```bash
sofer mcp doctor
sofer mcp doctor --agent opencode --json
```

`doctor` measures the real stdio `initialize` round trip, prints it beside the
per-agent entry key and the value `mcp add` writes, and uses
`[tool.sofer] mcp_connect_timeout_seconds` as the budget. Exceeding the budget
never changes the exit code: a slow machine is not a broken registration.
