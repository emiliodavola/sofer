# Spec delta: fix-mcp-native-delegation (cli)

> **Change:** `2026-09-25-fix-mcp-native-delegation` (GitHub #167, #232) · branch
> `fix/167-232-native-mcp-delegation`.
>
> CLI-R09 is MODIFIED so the `mcp add` / `mcp remove` help contract documents
> that native delegation is used only when it can faithfully forward the same
> env NAMES and scope as the file edit, and that a warning is printed when it
> cannot.

## MODIFIED Requirements

### Requirement: mcp add/remove help (CLI-R09)

> Added by change `feat-mcp-registration-automation` (archived 2026-09-09).
> Extended by change `2026-09-12-fix-mcp-opencode-env` (additive env-forwarding scenario).
> Extended by change `2026-09-25-feat-pi-mcp-agent` (#142) — `pi` added to the agent set.
> Extended by change `2026-09-25-fix-mcp-native-delegation` (#167/#232) — native
> delegation fidelity sentence.

`sofer` MUST expose `mcp` with `add`/`remove`. `add` MUST accept `--agent <opencode|codex|gemini|pi|all> [--scope user|project] [--cwd PATH] [--dry-run]`; `remove` MUST accept `--agent <opencode|codex|gemini|pi|all> [--scope user|project] [--dry-run]`. Help for `sofer --help` and `sofer mcp*` MUST list these.

The `sofer mcp add` help text SHALL additionally document env-forwarding behavior: codex, gemini and pi receive env forwarding with names only, and opencode entries carry no environment, so a warning is emitted when `HF_TOKEN`/`SOFER_MCP_APPROVAL_PHRASE` are set and `--agent opencode` (or `all`) is chosen.

The `sofer mcp add` / `sofer mcp remove` help text SHALL also document native
delegation fidelity: native `codex`/`gemini` delegation is used only when the
native CLI can faithfully forward the same env NAMES and scope as the file edit,
and when it cannot the config file is edited instead with a warning on stderr.

(Previously: CLI-R09 documented only the flag surface and the env-forwarding
behavior; native delegation fidelity was not part of the help contract. #167/#232
add the fidelity sentence.)

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

#### Scenario: help documents native delegation fidelity

- GIVEN `sofer mcp add --help` (and `sofer mcp remove --help`)
- WHEN rendered
- THEN the description SHALL state that native delegation is used only when it can forward the same env NAMES and scope as the file edit
- AND the description SHALL state that when it cannot, the config file is edited with a warning on stderr
