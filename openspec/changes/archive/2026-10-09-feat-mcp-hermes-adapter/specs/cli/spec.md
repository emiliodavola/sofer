# Delta for cli

> **Change** `2026-10-09-feat-mcp-hermes-adapter` (issue **#272**) · branch
> `feat/272-mcp-hermes-adapter` · store **hybrid**.
>
> **One modification, no new requirement.** CLI-R09 (`mcp add/remove help`) names the agent set and
> the env-forwarding behavior, so a fifth agent and a new write format must be documented there.
>
> **Rule-6 resolution.** `cli` is a permanent declared-backlog spec
> (`openspec/test-mapping-registry.md`), so the amended scenarios map to the help-text tests in
> `tests/test_cli.py` without a Test Mapping row, and the registry is not edited.

## MODIFIED Requirements

### Requirement: mcp add/remove help (CLI-R09)

> Added by change `feat-mcp-registration-automation` (archived 2026-09-09).
> Extended by change `2026-09-12-fix-mcp-opencode-env` (additive env-forwarding scenario).
> Extended by change `2026-09-25-feat-pi-mcp-agent` (#142) — `pi` added to the agent set.
> Extended by change `2026-09-25-fix-mcp-native-delegation` (#167/#232) — native
> delegation fidelity sentence.
> Extended by change `2026-10-09-feat-mcp-hermes-adapter` (#272) — `hermes` added to the agent set,
> with the YAML preservation and single-scope sentences.

**Modification scope.** Exactly four spans move, and nothing else in the requirement does:

| Span | Operation |
| --- | --- |
| the flag-enumeration paragraph | `hermes` added to both `--agent` enumerations |
| the env-forwarding paragraph | `hermes` added, plus the YAML preservation and single-scope sentences |
| the test-mapping note | none |
| the scenarios | `add help` and `remove help` choices gain `hermes`; `add help documents env forwarding` names `hermes` |

**Modified paragraph (verbatim, as it reads in the canonical spec after this change):**

`sofer` MUST expose `mcp` with `add`/`remove`. `add` MUST accept
`--agent <opencode|codex|gemini|pi|hermes|all> [--scope user|project] [--cwd PATH]
[--user-config PATH] [--dry-run]`; `remove` MUST accept
`--agent <opencode|codex|gemini|pi|hermes|all> [--scope user|project] [--user-config PATH]
[--dry-run]`. Help for `sofer --help` and `sofer mcp*` MUST list these.

The `sofer mcp add` help text SHALL additionally document env-forwarding behavior: codex, gemini, pi
and hermes receive env forwarding with names only (gemini as `$KEY` references, pi and hermes as
`${KEY}` references), and opencode entries carry no environment, so a warning is emitted when
`HF_TOKEN`/`SOFER_MCP_APPROVAL_PHRASE` are set and `--agent opencode` (or `all`) is chosen. The help
text SHALL also document that a YAML config edit preserves the rest of the document while a TOML edit
may strip comments, and that `hermes` reads a single user-scope config, so `--scope project` resolves
to that same file and the substitution is named on stderr.

#### Scenario: add help (amended)

- GIVEN `sofer mcp add --help`
- WHEN rendered
- THEN `--agent`, `--scope`, `--cwd`, `--user-config`, `--dry-run` SHALL be listed
- AND the `--agent` choices SHALL include `opencode`, `codex`, `gemini`, `pi`, `hermes` and `all`

#### Scenario: remove help (amended)

- GIVEN `sofer mcp remove --help`
- WHEN rendered
- THEN `--agent`, `--scope`, `--user-config`, `--dry-run` SHALL be listed
- AND the `--agent` choices SHALL include `opencode`, `codex`, `gemini`, `pi`, `hermes` and `all`

#### Scenario: add help documents env forwarding (amended)

- GIVEN `sofer mcp add --help`
- WHEN rendered
- THEN the description SHALL state that codex, gemini, pi and hermes receive env forwarding (names
  only)
- AND the description SHALL state that opencode entries carry no environment and that a warning is
  emitted when `HF_TOKEN`/`SOFER_MCP_APPROVAL_PHRASE` are set with `--agent opencode` (or `all`)

#### Scenario: add help documents the YAML preservation and the single-scope note

- GIVEN `sofer mcp add --help`
- WHEN rendered
- THEN the description SHALL distinguish the YAML edit (preserves the rest of the document) from the
  TOML edit (may strip comments)
- AND the description SHALL state that `hermes` reads a single user-scope config and that
  `--scope project` resolves to it with a warning on stderr
