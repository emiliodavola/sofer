# Delta for mcp-registration

> **Change** `2026-10-09-feat-mcp-hermes-adapter` (issue **#272**) · branch
> `feat/272-mcp-hermes-adapter` · store **hybrid**.
>
> **One modification, no new requirement.** MCP-REG-01 gains the fifth agent (`hermes`), the YAML
> write contract that `fmt="yaml"` implies, and the single-scope resolution rule. Hermes Agent is not
> in `ADAPTERS`, so the server had to be registered by hand, and a hand registration that does not
> reproduce the contained `cwd` leaves the MCP refusing every dataset path.
>
> **Rule-6 resolution.** `mcp-registration` is a permanent declared-backlog spec
> (`openspec/test-mapping-registry.md`), so the new scenarios map to `TestHermesAdapter` and
> `TestYamlEdit` (`tests/test_mcp_registration.py` / `tests/test_yaml_edit.py`) without a Test Mapping
> row, and the registry is not edited.

## MODIFIED Requirements

### Requirement: MCP add idempotent and safe (MCP-REG-01)

> Added by change `sofer-mcp-agents` (archived 2026-08-30). Modified by
> `2026-10-09-fix-mcp-user-config-resolution` (issue #274) — the `--cwd` rule became existence instead
> of containment. Modified by `2026-10-09-feat-mcp-user-config-flag` (issue #274) — the user-scope
> config file resolves by explicit declaration first. Modified by
> `2026-10-09-feat-mcp-hermes-adapter` (issue #272) — `hermes` added to the agent set, the YAML write
> contract, and the single-scope resolution.

**Modification scope.** Exactly four spans move, and nothing else in the requirement does:

| Span | Operation |
| --- | --- |
| the agent table | the env-enforcement sentence gains the Hermes form; one `hermes` row appended |
| the requirement body | one paragraph appended: the YAML write contract and the single-scope resolution |
| the requirement body | one amendment blockquote appended after that paragraph |
| the scenarios | `Add all` amended (4 → 5 configs); four scenarios appended |

**Modified sentence (verbatim, as it reads in the canonical spec after this change):**

... MUST enforce Gemini `sofer` with explicit `env` mapping known keys to `$KEY` references — never
secret values — MUST enforce Pi `sofer` with explicit `env` mapping known keys to `${KEY}` references
— never secret values — MUST enforce Hermes `sofer` with explicit `env` mapping known keys to
`${KEY}` references — never secret values — and Codex `env_vars` as an allow-list of known env NAMES
present in the environment ...

**Added table row (verbatim):**

| Agent | File | Entry |
|-------|------|-------|
| hermes | `config.yaml` | `mcp_servers.sofer={command:"sofer-mcp",cwd,env:{HF_TOKEN:"${HF_TOKEN}",…}}` (env NAMES only) |

**Added clause (verbatim, as it reads in the canonical spec after this change):**

The Hermes user-scope file is `$HERMES_HOME/config.yaml` when that variable is set to a non-empty
value, else `~/.hermes/config.yaml`. Hermes entries MUST NOT carry an array `command` or a
`type` field, and Hermes MUST be file-edit only: `hermes mcp add` documents no `cwd` and no env
surface, and a native path that omitted `cwd` would reintroduce the broken registration this clause
exists to prevent. A Hermes edit SHALL splice only the `sofer` entry into `config.yaml` and SHALL leave
every unrelated key, comment and indentation byte-identical; the declared "TOML edits may strip
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

#### Scenario: Add all (amended)

- GIVEN no `sofer` in any config
- WHEN add all runs
- THEN 5 configs SHALL contain correct `sofer` entry

#### Scenario: Add hermes

- GIVEN a Hermes config without `sofer`
- WHEN `add --agent hermes --scope user` runs
- THEN `~/.hermes/config.yaml` (or `$HERMES_HOME/config.yaml`) SHALL contain
  `mcp_servers.sofer={command:"sofer-mcp",cwd,env}` with an absolute `cwd`
- AND every unrelated line of the file SHALL be byte-identical
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
