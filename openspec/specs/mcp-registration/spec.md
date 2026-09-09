# mcp-registration Specification

## Purpose

Register `sofer-mcp` in opencode/codex/gemini agent configs via the `sofer mcp add/remove` subcommands. Registration edits the agent's on-disk config idempotently: unrelated keys are preserved, a single `.bak` backup precedes the first mutation, writes are atomic, and the agent process (or file merge fallback) is preferred over direct file surgery. Env forwarding persists **names only** — secret values are never written to disk.

## Requirements

### Requirement: MCP add idempotent and safe (MCP-REG-01)

`sofer mcp add --agent <opencode|codex|gemini|all> [--scope user|project] [--cwd PATH] [--dry-run]` MUST be idempotent, MUST preserve unrelated keys, MUST back up `.bak` before edit, MUST set `command=sofer-mcp` with absolute anchored `cwd`, MUST use atomic write, MUST exit 1 with no backup/write on an unreadable config, MUST enforce Gemini `sofer` with explicit `env` mapping known keys to `$KEY` references — never secret values — and Codex `env_vars` as an allow-list of known env NAMES present in the environment, MUST normalize Codex `command` variations, MUST prefer native registration else file merge.

| Agent | File | Entry |
|-------|------|-------|
| opencode | `opencode.json` | `mcp.sofer={type:"local",command:["sofer-mcp"],cwd}` |
| codex | `config.toml` | `[mcp_servers.sofer] command,cwd,env_vars=[HF_TOKEN,...]` (env NAMES only) |
| gemini | `settings.json` | `mcpServers.sofer={command:"sofer-mcp",cwd,env:{HF_TOKEN:"$HF_TOKEN",...}}` |

Both Gemini `env` and Codex `env_vars` persist env NAMES only (an allow-list of keys present in the environment); secret values (`HF_TOKEN`, `SOFER_MCP_APPROVAL_PHRASE`) are never written to disk. Gemini's CLI expands the `$KEY` references from the host environment at runtime.

#### Scenario: Add all

- GIVEN no `sofer` in any config
- WHEN add all runs
- THEN 3 configs SHALL contain correct `sofer` entry

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

- GIVEN native discoverable
- WHEN add codex runs
- THEN native tried first; fallback to file merge on miss/fail

---

### Requirement: MCP remove idempotent and safe (MCP-REG-02)

`sofer mcp remove --agent <opencode|codex|gemini|all> [--scope user|project] [--dry-run]` MUST remove `sofer` idempotently, MUST backup before edit, MUST preserve others, MUST do no write if absent, MUST prefer native else file edit, MUST not mutate on --dry-run, MUST exit 1 on unreadable.

#### Scenario: Remove single

- GIVEN `sofer` in opencode
- WHEN remove opencode runs
- THEN `sofer` absent, others preserved

#### Scenario: Remove all

- GIVEN `sofer` in 3 configs
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
