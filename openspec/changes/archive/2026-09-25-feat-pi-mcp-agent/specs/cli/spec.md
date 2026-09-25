# Spec delta: feat-pi-mcp-agent (cli)

> **Change:** `2026-09-25-feat-pi-mcp-agent` (GitHub #142) · branch `feat/142-pi-mcp-agent`.
>
> CLI-R09 is MODIFIED: the `--agent` surface and the env-forwarding help
> sentence grow from three agents to four (`pi` added). The `mcp add`/`mcp
> remove` flag shape is otherwise unchanged.

## MODIFIED Requirements

### Requirement: mcp add/remove help (CLI-R09)

> Added by change `feat-mcp-registration-automation` (archived 2026-09-09).
> Extended by change `2026-09-12-fix-mcp-opencode-env` (additive env-forwarding scenario).
> Extended by change `2026-09-25-feat-pi-mcp-agent` (#142) — `pi` added to the agent set.

`sofer` MUST expose `mcp` with `add`/`remove`. `add` MUST accept `--agent <opencode|codex|gemini|pi|all> [--scope user|project] [--cwd PATH] [--dry-run]`; `remove` MUST accept `--agent <opencode|codex|gemini|pi|all> [--scope user|project] [--dry-run]`. Help for `sofer --help` and `sofer mcp*` MUST list these.

The `sofer mcp add` help text SHALL additionally document env-forwarding behavior: codex, gemini and pi receive env forwarding with names only, and opencode entries carry no environment, so a warning is emitted when `HF_TOKEN`/`SOFER_MCP_APPROVAL_PHRASE` are set and `--agent opencode` (or `all`) is chosen.

(Previously: CLI-R09 documented only the flag surface; env-forwarding behavior was not part of the help contract. #142 adds `pi` to the agent set and to the forwarding sentence.)

#### Scenario: mcp in top help

- GIVEN `sofer --help` rendered
- WHEN inspected
- THEN `mcp` SHALL appear

#### Scenario: mcp lists children

- GIVEN `sofer mcp --help` rendered
- WHEN inspected
- THEN `add` and `remove` SHALL appear

#### Scenario: add help

- GIVEN `sofer mcp add --help`
- WHEN rendered
- THEN `--agent`, `--scope`, `--cwd`, `--dry-run` SHALL be listed
- AND the `--agent` choices SHALL include `opencode`, `codex`, `gemini`, `pi` and `all`

#### Scenario: remove help

- GIVEN `sofer mcp remove --help`
- WHEN rendered
- THEN `--agent`, `--scope`, `--dry-run` SHALL be listed
- AND the `--agent` choices SHALL include `opencode`, `codex`, `gemini`, `pi` and `all`

#### Scenario: add help documents env forwarding

- GIVEN `sofer mcp add --help`
- WHEN rendered
- THEN the description SHALL state that codex, gemini and pi receive env forwarding (names only)
- AND the description SHALL state that opencode entries carry no environment and that a warning is emitted when `HF_TOKEN`/`SOFER_MCP_APPROVAL_PHRASE` are set with `--agent opencode` (or `all`)
