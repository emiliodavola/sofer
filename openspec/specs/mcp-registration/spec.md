# mcp-registration Specification

## Purpose

Register `sofer-mcp` in opencode/codex/gemini/pi/hermes agent configs via the `sofer mcp add/remove` subcommands. Registration edits the agent's on-disk config idempotently: unrelated keys are preserved, a single `.bak` backup precedes the first mutation, writes are atomic, and the agent process (or file merge fallback) is preferred over direct file surgery. A JSON or TOML edit rewrites the document (a TOML edit may strip comments), while a YAML edit splices only the `sofer` entry and leaves the rest of the file byte-identical. Env forwarding persists **names only** — secret values are never written to disk.

## Requirements

### Requirement: MCP add idempotent and safe (MCP-REG-01)

`sofer mcp add --agent <opencode|codex|gemini|pi|hermes|all> [--scope user|project] [--cwd PATH] [--dry-run]` MUST be idempotent, MUST preserve unrelated keys, MUST back up `.bak` before edit, MUST set `command=sofer-mcp` with absolute anchored `cwd`, MUST use atomic write, MUST exit 1 with no backup/write on an unreadable config, MUST enforce Gemini `sofer` with explicit `env` mapping known keys to `$KEY` references — never secret values — MUST enforce Pi `sofer` with explicit `env` mapping known keys to `${KEY}` references — never secret values — MUST enforce Hermes `sofer` with explicit `env` mapping known keys to `${KEY}` references — never secret values — and Codex `env_vars` as an allow-list of known env NAMES present in the environment, MUST normalize Codex `command` variations, and MUST delegate to the agent's native `mcp add` only when the native CLI can faithfully forward the same env NAMES and scope as the file edit, else fall back to file merge (see MCP-REG-04).

| Agent | File | Entry |
|-------|------|-------|
| opencode | `opencode.json` | `mcp.sofer={type:"local",command:["sofer-mcp"],cwd}` |
| codex | `config.toml` | `[mcp_servers.sofer] command,cwd,env_vars=[HF_TOKEN,...]` (env NAMES only) |
| gemini | `settings.json` | `mcpServers.sofer={command:"sofer-mcp",cwd,env:{HF_TOKEN:"$HF_TOKEN",...}}` |
| pi | `mcp.json` | `mcpServers.sofer={command:"sofer-mcp",cwd,env:{HF_TOKEN:"${HF_TOKEN}",...}}` |
| hermes | `config.yaml` | `mcp_servers.sofer={command:"sofer-mcp",cwd,env:{HF_TOKEN:"${HF_TOKEN}",...}}` (env NAMES only) |

Both Gemini, Pi and Hermes `env` and Codex `env_vars` persist env NAMES only (an allow-list of keys present in the environment); secret values (`HF_TOKEN`, `SOFER_MCP_APPROVAL_PHRASE`) are never written to disk. Gemini's CLI expands the `$KEY` references from the host environment at runtime; Pi's `pi-mcp-adapter` interpolates only the braced `${KEY}` form and MUST never receive a bare `$KEY`. The Pi user-scope file is `$PI_CODING_AGENT_DIR/mcp.json` when that variable is set to a non-empty value, else `~/.pi/agent/mcp.json`; the project-scope file is `<cwd>/.pi/mcp.json`. Pi entries MUST NOT carry an array `command`, `type`, or `enabled` field, and Pi MUST be file-edit only (no native CLI to delegate to).

The `--cwd` value SHALL be an **existing directory**, and that SHALL be the whole rule: `add` SHALL exit 1 with a message naming the resolved path when it is not, and SHALL NOT write. A resolved `--cwd` that is an existing directory but lies **outside** both `Path.home()` and the process cwd SHALL be **accepted**, with a warning naming the resolved cwd and the roots it is outside of printed to stderr — an explicit `--cwd` is the caller's own declaration, so an unusual tree is named rather than refused. Containment of the *server root* is a separate contract (MSP-R01/MSP-R07) and is unaffected by this clause.

> Amended by `2026-10-09-fix-mcp-user-config-resolution` (issue #274). The previous rule refused any cwd outside `Path.home()` or the process cwd. It was removed because, measured: it was undeclared in any spec (this clause did not exist); it was scope-blind (its `user` and `project` branches were the *same expression*); it was effectively untested (the only "rejection" test monkeypatched the function away); it protected no privilege boundary; it rejected legitimate trees (a dataset tree outside `$HOME`, which is the reported container case); and it still *accepted* a nonexistent path under either root, so it failed to catch the mistake that matters.

The user-scope config file SHALL resolve by explicit declaration first, then the adapter's environment
override, then the home directory: (1) `--user-config PATH` — expanded and resolved, naming the **file**, with a blank or
whitespace-only value counting as unset; (2) the adapter's `user_env_dir` when that variable
is set to a non-empty value (Pi's `PI_CODING_AGENT_DIR`), whose directory replaces the home prefix and
whose file name is `user_parts[-1]`; (3) `Path.home()` joined with `user_parts` — the documented
default. `--user-config` SHALL be rejected when combined with `--agent all`, because each agent has
its own config file and one path is ambiguous for all of them. When `Path.home()` differs from the
account home (`pwd.getpwuid(os.getuid()).pw_dir` on POSIX), `add` and `remove` SHALL print a warning
naming both homes, so that a write into a file the agent never reads is never a silent success.
Project scope SHALL ignore `--user-config`: the declared file is a user-scope concept.

> Added by `2026-10-09-feat-mcp-user-config-flag` (issue #274). The previous behaviour resolved user
> scope under `Path.home()` alone, which follows `$HOME`; agents such as opencode resolve their config
> from the system account home and ignore both `$HOME` and `XDG_CONFIG_HOME`, so sofer could write the
> entry into a file the agent never reads **and report success**. Removing that silent no-op is the
> whole point of this clause.

The Hermes user-scope file is `$HERMES_HOME/config.yaml` when that variable is set to a non-empty
value, else `~/.hermes/config.yaml`. Hermes entries MUST NOT carry an array `command` or a
`type` field, and Hermes MUST be file-edit only: `hermes mcp add` documents no `cwd` and no env
surface, and a native path that omitted `cwd` would reintroduce the broken registration this clause
exists to prevent. A Hermes edit SHALL splice only the `sofer` entry into `config.yaml` and SHALL leave
every unrelated key, comment, indentation and line ending byte-identical (LF stays LF and CRLF
stays CRLF, inside and outside the spliced entry); the declared "TOML edits may strip
comments" behavior of the other formats is unchanged.

Hermes reads a single config file and has no distinct project-scope file (`hermes project` is a named
multi-folder workspace, not a config file), so it SHALL be resolved with the adapter capability
`project_scope = False`: `--scope project` resolves to the same file `--scope user` resolves to, and
`add` and `remove` SHALL print a note to stderr naming the substitution and the resolved file before
writing. Writing a project-local file Hermes never reads SHALL NOT happen — that silent no-op is the
failure #274 removed — and refusal is not the rule either, matching the accepted `--cwd` amendment. As
declared for project scope, `--user-config` SHALL still be ignored.

> Added by `2026-10-09-feat-mcp-hermes-adapter` (issue #272). Hermes Agent launches stdio children with
> its own cwd unless the server entry carries `cwd`, so a hand registration rooted every
> path-bearing tool outside the server root and every dataset path was refused while the CLI reported
> success. The adapter closes the gap in the file Hermes actually reads.

#### Scenario: User-scope config resolution

- GIVEN a user-scope `add` or `remove`
- WHEN `--user-config PATH` is passed, or the adapter's env override is set, or neither is present
- THEN the config file SHALL be the first present of `--user-config PATH`, the adapter's
  `user_env_dir` file, and `Path.home()` joined with `user_parts` (a blank `--user-config` counts as
  unset, and project scope ignores it)
- AND `--user-config` combined with `--agent all` SHALL exit 1 without writing
- AND when the home and the account home differ, a warning naming both SHALL be printed to stderr

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

#### Scenario: Add hermes

- GIVEN a Hermes config without `sofer`
- WHEN `add --agent hermes --scope user` runs
- THEN `~/.hermes/config.yaml` (or `$HERMES_HOME/config.yaml`) SHALL contain
  `mcp_servers.sofer={command:"sofer-mcp",cwd,env}` with an absolute `cwd`
- AND every unrelated line of the file SHALL be byte-identical, line endings included
- AND a single `.bak` SHALL precede the first mutation

#### Scenario: Hermes env references only

- GIVEN `HF_TOKEN` is set and `SOFER_MCP_APPROVAL_PHRASE` is not
- WHEN `add --agent hermes` runs
- THEN the entry `env` mapping SHALL be `{HF_TOKEN: "${HF_TOKEN}"}`
- AND no secret value SHALL appear anywhere in the written file

#### Scenario: Hermes single-scope project substitution

- GIVEN `--scope project` for `--agent hermes`
- WHEN `add` or `remove` runs
- THEN the resolved file SHALL be the user-scope `config.yaml`, no `<cwd>/.hermes/config.yaml` SHALL
  be created, and a note naming the substitution and the resolved file SHALL be printed to stderr
- AND `--user-config PATH` SHALL still be ignored for that scope

#### Scenario: Hermes merge preserves the document

- GIVEN a commented `config.yaml` with unrelated keys and a sibling `mcp_servers` entry
- WHEN `add --agent hermes` then `remove --agent hermes` run
- THEN the sibling entry, the unrelated keys and every comment SHALL be byte-identical afterwards
- AND re-running `add` on an equal entry SHALL NOT write and SHALL NOT create a `.bak`

---

### Requirement: MCP remove idempotent and safe (MCP-REG-02)

`sofer mcp remove --agent <opencode|codex|gemini|pi|hermes|all> [--scope user|project] [--dry-run]` MUST remove `sofer` idempotently, MUST backup before edit, MUST preserve others, MUST do no write if absent, MUST delegate to the agent's native `mcp remove` only when it can faithfully express the requested scope, else file edit (see MCP-REG-04), MUST not mutate on --dry-run, MUST exit 1 on unreadable.

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

### Requirement: Host timeouts in the registered entry (MCP-REG-05)

`sofer mcp add` MUST write the host's per-request (tool call) and connect/startup deadlines into the
`sofer` entry, using the key name and unit the adapter declares for that agent, so that neither the
measured 16–32 s cold start of `sofer-mcp` (its heavy imports precede the `initialize` answer) nor a
tool call measured in minutes fails against a host default and reports as a broken registration
(issues #287, #296). The values MUST default to the `[tool.sofer]` keys
`mcp_request_timeout_seconds` and `mcp_connect_timeout_seconds` — never to a literal in the call path
(AGENTS.md rule 1) — MUST be overridable per invocation with `--timeout` / `--connect-timeout`, MUST
be omitted entirely by `--no-timeout`, and MUST be rejected with exit 2 when non-positive.

The timeout keys SHALL be namespaced under the `sofer` server name only. Writing them MUST NOT change
any other server in the file, MUST keep the existing contracts (preserve unrelated keys, one `.bak`
before the first mutation, atomic write, no write on `--dry-run`), and MUST still be idempotent:
re-running with the same values MUST NOT write and MUST NOT create a `.bak`, while a changed
`--timeout` alone MUST be detected as a change and MUST rewrite the entry.

An agent whose entry schema accepts no timeout key SHALL keep an entry without one, and `add` SHALL
name that on stderr rather than reporting a clean success — the same informational contract as the
OpenCode env-drop warning (MCP-REG-03).

Because neither `codex mcp add` nor `gemini mcp add` accepts a timeout flag, a registration carrying
timeouts MUST decline native delegation with the reason `timeout` and fall back to the file edit
(MCP-REG-04), and `--no-timeout` MUST restore the delegation path by restoring the pre-change entry
shape.

The value written SHALL be checkable against the machine that carries it: `sofer mcp doctor` (CLI-R15)
MUST report this machine's own `initialize` round trip beside the key and the value `add` writes, and
MUST name the flags that raise them. Like the two notes above it is informational and MUST NOT change
the exit code (issue #322).

#### Scenario: The entry carries each host's keys and unit

- GIVEN an existing directory passed as `--cwd`
- WHEN `sofer mcp add --agent <agent>` runs for `pi`, `hermes`, `codex` and `gemini`
- THEN the written entry SHALL carry `timeout` / `connect_timeout` for `hermes`, `timeout` for `pi`,
  `tool_timeout_sec` / `startup_timeout_sec` for `codex`
- AND `gemini`'s single `timeout` key SHALL be expressed in milliseconds
- AND every value SHALL come from the `[tool.sofer]` defaults unless a flag overrode it

**Evidence:** `test: tests/test_mcp_registration.py::TestRegistrationTimeouts::test_entry_carries_each_host_timeout_key_and_unit`, `test: tests/test_cli.py::TestMcpRegistrationTimeoutsCli::test_add_writes_the_default_timeout_keys`, `test: tests/test_cli.py::TestMcpRegistrationTimeoutsCli::test_timeout_flags_override_the_defaults`, `test: tests/test_cli.py::TestMcpRegistrationTimeoutsCli::test_gemini_timeout_is_written_in_milliseconds`

#### Scenario: A host without a timeout key is named, not silently skipped

- GIVEN `--agent opencode`
- WHEN `sofer mcp add` writes the entry
- THEN the entry SHALL NOT carry a timeout key
- AND stderr SHALL name that the entry carries none, with the reason
- AND the exit code SHALL be unchanged

**Evidence:** `test: tests/test_cli.py::TestMcpRegistrationTimeoutsCli::test_opencode_names_the_missing_timeout_key_on_stderr`, `test: tests/test_mcp_registration.py::TestRegistrationTimeouts::test_opencode_declares_no_timeout_key`

#### Scenario: Idempotent when unchanged, rewriting when the timeout changes

- GIVEN a registration already carrying the configured timeouts
- WHEN `sofer mcp add` runs again with the same values
- THEN no write and no `.bak` SHALL occur
- AND when it runs with a different `--timeout`
- THEN the entry SHALL be rewritten with the new value and a `.bak` SHALL exist

**Evidence:** `test: tests/test_mcp_registration.py::TestRegistrationTimeouts::test_same_timeout_is_idempotent`, `test: tests/test_mcp_registration.py::TestRegistrationTimeouts::test_changed_timeout_is_not_swallowed_by_the_idempotency_guard`, `test: tests/test_cli.py::TestMcpRegistrationTimeoutsCli::test_changed_timeout_rewrites_the_entry_and_backs_up`

#### Scenario: --no-timeout restores the pre-change shape

- GIVEN `--no-timeout`
- WHEN `sofer mcp add` writes the entry
- THEN no timeout key SHALL appear
- AND `--dry-run` SHALL still write nothing

**Evidence:** `test: tests/test_cli.py::TestMcpRegistrationTimeoutsCli::test_no_timeout_omits_the_keys`, `test: tests/test_mcp_registration.py::TestRegistrationTimeouts::test_entry_without_timeouts_keeps_the_pre_change_shape`, `test: tests/test_cli.py::TestMcpRegistrationTimeoutsCli::test_dry_run_with_timeouts_writes_nothing`

#### Scenario: A non-positive timeout is refused before any write

- GIVEN `--timeout 0`, `-1`, `abc` or `1.5`
- WHEN `sofer mcp add` parses the arguments
- THEN it SHALL exit 2 with a usage message naming the flag
- AND no config file SHALL be written

**Evidence:** `test: tests/test_cli.py::TestMcpRegistrationTimeoutsCli::test_parser_rejects_a_non_positive_timeout`

#### Scenario: Native delegation declines when it cannot reproduce the timeouts

- GIVEN a native `codex` or `gemini` binary is available and a timeout will be written
- WHEN `sofer mcp add` runs
- THEN the delegation SHALL decline with the reason `timeout`, named on stderr
- AND the file edit SHALL run and carry the keys
- AND with `--no-timeout` the delegation SHALL proceed as before

**Evidence:** `test: tests/test_mcp_registration.py::TestRegistrationTimeouts::test_native_delegation_declines_with_the_timeout_reason`, `test: tests/test_mcp_registration.py::TestRegistrationTimeouts::test_decline_reason_order_is_env_scope_timeout`, `test: tests/test_cli.py::TestMcpRegistrationTimeoutsCli::test_timeouts_decline_native_delegation_naming_the_reason`, `test: tests/test_cli.py::TestMcpRegistrationTimeoutsCli::test_no_timeout_restores_native_delegation`, `test: tests/test_mcp_registration.py::TestRegistrationTimeouts::test_no_timeouts_leaves_delegation_available`

#### Scenario: The written deadline can be checked against this machine — issue #322

- GIVEN `sofer mcp doctor --agent <agent>` on a host whose entry carries a timeout key
- WHEN it reports
- THEN it SHALL name the same key and value `sofer mcp add` writes for that agent
- AND an agent whose entry accepts no timeout key SHALL be named by the same note
- AND the exit code SHALL be unchanged whatever the measurement

**Evidence:** `test: tests/test_mcp_doctor.py::TestAgentRows::test_the_row_value_matches_what_mcp_add_would_write`, `test: tests/test_mcp_doctor.py::TestAgentRows::test_opencode_carries_the_note_instead_of_a_value`, `test: tests/test_mcp_doctor.py::TestCommandHandler::test_a_measurement_over_budget_still_exits_zero`
