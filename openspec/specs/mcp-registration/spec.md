# mcp-registration Specification

## Purpose

Register `sofer-mcp` in opencode/codex/gemini/pi agent configs via the `sofer mcp add/remove` subcommands. Registration edits the agent's on-disk config idempotently: unrelated keys are preserved, a single `.bak` backup precedes the first mutation, writes are atomic, and the agent process (or file merge fallback) is preferred over direct file surgery. Env forwarding persists **names only** — secret values are never written to disk.

## Requirements

### Requirement: MCP add idempotent and safe (MCP-REG-01)

`sofer mcp add --agent <opencode|codex|gemini|pi|all> [--scope user|project] [--cwd PATH] [--dry-run]` MUST be idempotent, MUST preserve unrelated keys, MUST back up `.bak` before edit, MUST set `command=sofer-mcp` with absolute anchored `cwd`, MUST use atomic write, MUST exit 1 with no backup/write on an unreadable config, MUST enforce Gemini `sofer` with explicit `env` mapping known keys to `$KEY` references — never secret values — MUST enforce Pi `sofer` with explicit `env` mapping known keys to `${KEY}` references — never secret values — and Codex `env_vars` as an allow-list of known env NAMES present in the environment, MUST normalize Codex `command` variations, and MUST delegate to the agent's native `mcp add` only when the native CLI can faithfully forward the same env NAMES and scope as the file edit, else fall back to file merge (see MCP-REG-04).

| Agent | File | Entry |
|-------|------|-------|
| opencode | `opencode.json` | `mcp.sofer={type:"local",command:["sofer-mcp"],cwd}` |
| codex | `config.toml` | `[mcp_servers.sofer] command,cwd,env_vars=[HF_TOKEN,...]` (env NAMES only) |
| gemini | `settings.json` | `mcpServers.sofer={command:"sofer-mcp",cwd,env:{HF_TOKEN:"$HF_TOKEN",...}}` |
| pi | `mcp.json` | `mcpServers.sofer={command:"sofer-mcp",cwd,env:{HF_TOKEN:"${HF_TOKEN}",...}}` |

Both Gemini and Pi `env` and Codex `env_vars` persist env NAMES only (an allow-list of keys present in the environment); secret values (`HF_TOKEN`, `SOFER_MCP_APPROVAL_PHRASE`) are never written to disk. Gemini's CLI expands the `$KEY` references from the host environment at runtime; Pi's `pi-mcp-adapter` interpolates only the braced `${KEY}` form and MUST never receive a bare `$KEY`. The Pi user-scope file is `$PI_CODING_AGENT_DIR/mcp.json` when that variable is set to a non-empty value, else `~/.pi/agent/mcp.json`; the project-scope file is `<cwd>/.pi/mcp.json`. Pi entries MUST NOT carry an array `command`, `type`, or `enabled` field, and Pi MUST be file-edit only (no native CLI to delegate to).

The `--cwd` value SHALL be an **existing directory**, and that SHALL be the whole rule: `add` SHALL exit 1 with a message naming the resolved path when it is not, and SHALL NOT write. A resolved `--cwd` that is an existing directory but lies **outside** both `Path.home()` and the process cwd SHALL be **accepted**, with a warning naming the resolved cwd and the roots it is outside of printed to stderr — an explicit `--cwd` is the caller's own declaration, so an unusual tree is named rather than refused. Containment of the *server root* is a separate contract (MSP-R01/MSP-R07) and is unaffected by this clause.

> Amended by `2026-10-09-fix-mcp-user-config-resolution` (issue #274). The previous rule refused any cwd outside `Path.home()` or the process cwd. It was removed because, measured: it was undeclared in any spec (this clause did not exist); it was scope-blind (its `user` and `project` branches were the *same expression*); it was effectively untested (the only "rejection" test monkeypatched the function away); it protected no privilege boundary; it rejected legitimate trees (a dataset tree outside `$HOME`, which is the reported container case); and it still *accepted* a nonexistent path under either root, so it failed to catch the mistake that matters.

#### Scenario: Add all

- GIVEN no `sofer` in any config
- WHEN add all runs
- THEN 4 configs SHALL contain correct `sofer` entry

#### Scenario: Add single

- GIVEN gemini already registered
- WHEN add opencode runs
- THEN only opencode SHALL change

#### Scenario: Idempotent

- GIVEN entry equals desired
- WHEN add opencode re-runs
- THEN file byte-identical, no backup/write

#### Scenario: Dry-run

- GIVEN config exists
- WHEN add all --dry-run runs
- THEN no file or `.bak` created

#### Scenario: Backup

- GIVEN config without `sofer`
- WHEN add writes
- THEN `.bak` holds pre-edit content

#### Scenario: Unreadable

- GIVEN config unreadable/malformed
- WHEN add runs
- THEN exit 1, no backup/write

#### Scenario: Cwd custom

- GIVEN `--cwd /tmp/myproj`
- WHEN add with that cwd runs
- THEN stored `cwd` equals resolved absolute

#### Scenario: Cwd existence, not containment

- GIVEN `--cwd` resolving to a path that is not an existing directory
- WHEN add runs
- THEN exit 1 SHALL be returned with a message naming the resolved path, and no write SHALL occur
- AND GIVEN `--cwd` resolving to an existing directory outside both the home and the process cwd
- THEN the add SHALL proceed and a warning naming the resolved cwd and the roots it is outside of SHALL be printed to stderr

#### Scenario: Gemini env names only

- GIVEN `HF_TOKEN` + `SOFER_MCP_APPROVAL_PHRASE` set
- WHEN add gemini runs
- THEN `mcpServers.sofer.env` contains `HF_TOKEN` and `SOFER_MCP_APPROVAL_PHRASE` as `$KEY` references (never values)
- AND absent keys SHALL be omitted

#### Scenario: Codex merge

- GIVEN `config.toml` with `[mcp_servers.other]`
- WHEN add codex runs
- THEN `other` preserved, string/array normalized

#### Scenario: OpenCode scope

- GIVEN `--scope project` vs `user`
- WHEN add opencode with scope runs
- THEN project targets `./opencode.json`, user targets OS user path

#### Scenario: Native delegation

- GIVEN native discoverable and delegation is faithful (no env NAMES to forward, requested scope expressible)
- WHEN add codex runs
- THEN native is tried first; the file merge is the fallback on miss/fail/decline

#### Scenario: Add Pi user

- GIVEN `--scope user`, with `PI_CODING_AGENT_DIR` set to a directory and unset
- WHEN add pi runs
- THEN the file SHALL be `$PI_CODING_AGENT_DIR/mcp.json` when set, else `~/.pi/agent/mcp.json`
- AND `mcpServers.sofer` SHALL be `{command:"sofer-mcp",cwd:<abs>,env:{KEY:"${KEY}",...}}` for env keys present

#### Scenario: Add Pi project

- GIVEN `--scope project` and a cwd
- WHEN add pi runs
- THEN the file SHALL be `<cwd>/.pi/mcp.json` and the stored `cwd` SHALL be the resolved absolute cwd

#### Scenario: Pi entry shape

- GIVEN add pi runs
- WHEN the entry is inspected
- THEN `command` SHALL be the string `"sofer-mcp"` (never an array)
- AND the entry SHALL NOT contain `type`, `enabled`, or `args`

#### Scenario: Pi env braced references only

- GIVEN `HF_TOKEN` set and `SOFER_MCP_APPROVAL_PHRASE` absent
- WHEN add pi runs
- THEN `mcpServers.sofer.env` SHALL be `{HF_TOKEN:"${HF_TOKEN}"}` and SHALL NOT contain the bare form `$HF_TOKEN`
- AND the secret value SHALL NOT appear on disk

---

### Requirement: MCP remove idempotent and safe (MCP-REG-02)

`sofer mcp remove --agent <opencode|codex|gemini|pi|all> [--scope user|project] [--dry-run]` MUST remove `sofer` idempotently, MUST backup before edit, MUST preserve others, MUST do no write if absent, MUST delegate to the agent's native `mcp remove` only when it can faithfully express the requested scope, else file edit (see MCP-REG-04), MUST not mutate on --dry-run, MUST exit 1 on unreadable.

#### Scenario: Remove single

- GIVEN `sofer` in opencode
- WHEN remove opencode runs
- THEN `sofer` absent, others preserved

#### Scenario: Remove all

- GIVEN `sofer` in 4 configs
- WHEN remove all runs
- THEN each SHALL have `sofer` removed

#### Scenario: Idempotent remove

- GIVEN no `sofer` entry
- WHEN remove codex runs
- THEN exit 0, no write

#### Scenario: Remove dry-run

- GIVEN `sofer` present
- WHEN remove gemini --dry-run runs
- THEN no file or `.bak` created

#### Scenario: Remove backup

- GIVEN config with `sofer`+`other`
- WHEN remove codex edits
- THEN `.bak` exists and `other` preserved

#### Scenario: Remove Pi preserves others

- GIVEN `.pi/mcp.json` with `mcpServers.sofer` and `mcpServers.other`
- WHEN remove pi runs
- THEN only `sofer` SHALL be removed and `other` SHALL be preserved
- AND re-running SHALL exit 0 with no write

---

### Requirement: OpenCode env-drop warning (MCP-REG-03)

> Added by change `2026-09-12-fix-mcp-opencode-env` (closes #147).
> Extended by change `2026-09-25-feat-pi-mcp-agent` (#142) — `--agent all` now
> expands to four agents and Pi is a name-forwarding agent.

`sofer mcp add --agent opencode` (and the opencode member of `--agent all`)
MUST emit an informational warning on **stderr** when `collect_env()` returns at
least one known env key (the single source `_ENV_KEYS`: `HF_TOKEN`,
`SOFER_MCP_APPROVAL_PHRASE`) and the opencode entry cannot carry that
environment. The warning MUST list the dropped variable **NAMES only** — never
their values — MUST state that the opencode registration carries no environment,
and MUST point at the README's launcher-environment / `environment`-literal
alternative. The warning MUST be informational, not a gate: it MUST NOT change
the exit code, MUST NOT alter stdout registration output, and MUST NOT hard-fail
the command or `--agent all`.

The generated opencode entry MUST remain exactly
`mcp.sofer={type:"local",command:["sofer-mcp"],cwd}`. No env name or value
(`HF_TOKEN`, `SOFER_MCP_APPROVAL_PHRASE`) SHALL ever be written into
`opencode.json`, and no other format change that would start persisting secret
values is permitted. `--agent all` SHALL expand to exactly the four registered
agents `opencode`, `codex`, `gemini`, `pi`; the warning fires for the opencode
member only, while codex/gemini/pi members continue to persist names only
(`env_vars` allow-list of keys present / `env` `$KEY` references / `env` `${KEY}`
references) and MUST NOT emit the warning.

The warning MUST also appear in `--dry-run` output (emitted on the dry-run path,
before the preview branch), so a preview surfaces the drop instead of hiding it.
`--dry-run` SHALL still perform no write and create no `.bak`.

#### Scenario: Warning when opencode is chosen with env set

- GIVEN `HF_TOKEN` and `SOFER_MCP_APPROVAL_PHRASE` set in the environment
- WHEN `sofer mcp add --agent opencode` runs
- THEN stderr SHALL carry a warning naming both variables (names only, never values)
- AND the warning SHALL state the opencode entry carries no env and point at the README alternative
- AND the exit code SHALL remain `0` and stdout registration output SHALL be unchanged
- AND the written `opencode.json` `mcp.sofer` entry SHALL be exactly `{type:"local",command:["sofer-mcp"],cwd}` with no env key

#### Scenario: Warning is previewed in dry-run

- GIVEN `HF_TOKEN` set
- WHEN `sofer mcp add --agent opencode --dry-run` runs
- THEN the warning SHALL appear on stderr
- AND no config file or `.bak` SHALL be created

#### Scenario: Warning fires once for the opencode member of all

- GIVEN env keys present
- WHEN `sofer mcp add --agent all` runs
- THEN exactly ONE warning SHALL be emitted (for the opencode member)
- AND codex, gemini and pi members SHALL NOT emit the warning
- AND `all` SHALL expand to exactly `opencode`, `codex`, `gemini`, `pi`

#### Scenario: No warning without env or for forwarding agents

- GIVEN no known env key present, or `--agent codex` / `--agent gemini` / `--agent pi` with env keys present
- WHEN `sofer mcp add` runs
- THEN no opencode warning SHALL be emitted
- AND codex SHALL persist `env_vars` as an allow-list of env NAMES present, gemini SHALL persist `env` `$KEY` references, and pi SHALL persist `env` `${KEY}` references — values never on disk

#### Scenario: Values never leak into output or written file

- GIVEN `HF_TOKEN=hf123` and `SOFER_MCP_APPROVAL_PHRASE=phrase123` set
- WHEN `sofer mcp add --agent opencode` runs, in both real and `--dry-run` modes
- THEN neither `hf123` nor `phrase123` SHALL appear in stdout, stderr, or any written config file

---

### Requirement: Native delegation fidelity (MCP-REG-04)

> Added by change `2026-09-25-fix-mcp-native-delegation` (fixes #167, #232).

`sofer mcp add` / `sofer mcp remove` MUST delegate to the agent's native
`mcp add` / `mcp remove` **only when the native CLI can express the same
registration the file-edit path would write**. The decision MUST be a single
predicate driven by the single-source adapter registry, and MUST decline
(returning to the file-edit path) when either condition holds:

- **env**: at least one env NAME must be forwarded and the native CLI cannot
  forward NAME references without persisting secret values; or
- **scope**: `--scope project` is requested and the native CLI has no scope
  selector.

When delegation is declined for either reason, the CLI MUST print an
informational warning on **stderr** naming the agent and the reason(s) — the
literal reason labels `env forwarding` and `project scope`, NAMES only, never
values — and MUST then edit the config file. The warning MUST be informational:
it MUST NOT change the exit code and MUST NOT hard-fail the command or
`--agent all`.

When the native CLI does support the requested scope, the native argv MUST
carry the agent's scope selector (`gemini mcp add/remove --scope <user|project>`).
Native delegation MUST NOT receive a secret value via an `--env` / `-e`
argument, and MUST NOT emit an env flag for an agent whose native CLI cannot
forward env NAMES faithfully. Opencode and Pi MUST remain file-edit only
(`delegates=False`); an unregistered agent name SHALL be treated conservatively
(`native_env=False`, `native_scope=False`).

#### Scenario: Env NAMES make the native path decline

- GIVEN `HF_TOKEN` is set so `env_keys` is non-empty
- AND the agent CLI is available and would otherwise delegate
- WHEN `sofer mcp add --agent codex` (or `gemini`) runs
- THEN native delegation SHALL NOT be performed
- AND the file-edit path SHALL persist the env NAMES (`env_vars` allow-list / `env` `$KEY` refs), never values
- AND stderr SHALL carry a warning naming `env forwarding` (NAMES only)

#### Scenario: Scope is forwarded when the native CLI supports it

- GIVEN no known env key is set
- WHEN `sofer mcp add --agent gemini --scope project` (or `--scope user`) runs and native delegation is invoked
- THEN the native argv SHALL include `--scope project` (or `--scope user`)
- AND `sofer mcp remove --agent gemini --scope project` SHALL likewise forward `--scope project`

#### Scenario: Project scope makes the native path decline for a scope-less CLI

- GIVEN no known env key is set
- WHEN `sofer mcp add --agent codex --scope project` runs with the native CLI available
- THEN native delegation SHALL NOT be performed
- AND the project config file SHALL be edited at the requested scope (never only the user file)
- AND stderr SHALL carry a warning naming `project scope`

#### Scenario: Fidelity decline falls back and keeps the exit code

- GIVEN a fidelity decline for env or project scope
- WHEN `sofer mcp add` / `sofer mcp remove` runs
- THEN the file-edit path SHALL run and the command exit code SHALL be `0` on success
- AND the delegated success line SHALL NOT be printed

#### Scenario: Faithful cases still delegate

- GIVEN `env_keys` is empty and the requested scope is expressible (`gemini` for either scope, `codex` for user)
- WHEN native delegation is invoked
- THEN the native CLI SHALL be called and a zero exit SHALL short-circuit the file edit
