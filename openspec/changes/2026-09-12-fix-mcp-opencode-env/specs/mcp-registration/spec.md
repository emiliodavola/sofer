# Spec delta: fix-mcp-opencode-env

> **Change:** `2026-09-12-fix-mcp-opencode-env` (GitHub #147) · branch `fix/147-opencode-env-warning`.
>
> Closes the silent env-drop bug: `sofer mcp add --agent opencode` (and the
> opencode member of `--agent all`) now emits an informational warning when
> known env keys (`HF_TOKEN`, `SOFER_MCP_APPROVAL_PHRASE`) are present but the
> generated opencode entry cannot carry them. The delta is **ADD-only**: the
> opencode entry shape stays `mcp.sofer={type:"local",command:["sofer-mcp"],cwd}`,
> no secret value is ever written, and the names-never-values invariant is
> preserved (parity with codex/gemini). `pi` agent (#142) and any opencode
> registration-format redesign are deliberately OUT of scope.
>
> Block format follows the repo's archived change specs. The warning behavior is
> modeled as an ADDED requirement (MCP-REG-03) attached to the `sofer mcp add`
> flow instead of edits inside the MCP-REG-01 block, so archive appends to the
> canonical spec rather than destructively replacing MCP-REG-01's existing
> scenarios.

## ADDED Requirements

### Requirement: OpenCode env-drop warning (MCP-REG-03)

> Added by change `2026-09-12-fix-mcp-opencode-env` (closes #147).
> Extends the `sofer mcp add` flow of MCP-REG-01 without altering its contract:
> registration for opencode remains env-less, idempotent, safe, and
> entry-shape-identical.

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
values is permitted. `--agent all` SHALL keep expanding to exactly the three
agents `opencode`, `codex`, `gemini`; the warning fires for the opencode member
only, while codex/gemini members continue to persist names only (`env_vars`
allow-list of keys present / `env` `$KEY` references) and MUST NOT emit the
warning.

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
- AND codex and gemini members SHALL NOT emit the warning
- AND `all` SHALL still expand to exactly `opencode`, `codex`, `gemini`

#### Scenario: No warning without env or for forwarding agents

- GIVEN no known env key present, or `--agent codex` / `--agent gemini` with env keys present
- WHEN `sofer mcp add` runs
- THEN no opencode warning SHALL be emitted
- AND codex SHALL persist `env_vars` as an allow-list of env NAMES present and gemini SHALL persist `env` `$KEY` references — values never on disk

#### Scenario: Values never leak into output or written file

- GIVEN `HF_TOKEN=hf123` and `SOFER_MCP_APPROVAL_PHRASE=phrase123` set
- WHEN `sofer mcp add --agent opencode` runs, in both real and `--dry-run` modes
- THEN neither `hf123` nor `phrase123` SHALL appear in stdout, stderr, or any written config file

---

<!-- Informational only: maps each new scenario to its apply-phase test
(AGENTS.md §6 / openspec/config.yaml — every spec scenario MUST have a
corresponding test). Not part of the archived requirement blocks. -->

| Scenario | Test (tests/test_mcp_registration.py, `TestEnvForwarding`) |
| --- | --- |
| Warning when opencode is chosen with env set | new `test_opencode_warning_env_present` — warning names present keys; entry still `{type,command,cwd}`; exit code unchanged |
| Warning is previewed in dry-run | new `test_opencode_warning_dry_run` — warning on stderr; no file and no `.bak` written |
| Warning fires once for the opencode member of all | new `test_opencode_warning_all_once` — exactly one warning; codex/gemini silent; `all` stays 3 agents |
| No warning without env or for forwarding agents | new `test_no_warning_without_env` and `test_no_warning_codex_gemini_env` |
| Values never leak into output or written file | new `test_warning_values_never_leak` — configured values absent from captured stdout/stderr and from the written file (real + dry-run) |
