# Spec delta: fix-mcp-opencode-env

> **Change:** `2026-09-12-fix-mcp-opencode-env` (GitHub #147) · branch `fix/147-opencode-env-warning`.
>
> CLI help delta for the opencode env-drop warning. `sofer mcp add --help`
> gains (additively) a documented statement that codex/gemini forward env names
> only while opencode entries carry no environment and print a warning when
> known env keys are present (AGENTS.md §7 — help text reflects behavior
> changes in the same change). MODIFIED CLI-R09 below copies the full canonical
> block verbatim and appends one scenario; the four existing scenarios are
> preserved unchanged.

## MODIFIED Requirements

### Requirement: mcp add/remove help (CLI-R09)

> Added by change `feat-mcp-registration-automation` (archived 2026-09-09).
> Extended by change `2026-09-12-fix-mcp-opencode-env` (additive env-forwarding scenario).

`sofer` MUST expose `mcp` with `add`/`remove`. `add` MUST accept `--agent <opencode|codex|gemini|all> [--scope user|project] [--cwd PATH] [--dry-run]`; `remove` MUST accept `--agent <opencode|codex|gemini|all> [--scope user|project] [--dry-run]`. Help for `sofer --help` and `sofer mcp*` MUST list these.

The `sofer mcp add` help text SHALL additionally document env-forwarding behavior: codex and gemini receive env forwarding with names only, and opencode entries carry no environment, so a warning is emitted when `HF_TOKEN`/`SOFER_MCP_APPROVAL_PHRASE` are set and `--agent opencode` (or `all`) is chosen.

(Previously: CLI-R09 documented only the flag surface; env-forwarding behavior was not part of the help contract.)

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

#### Scenario: remove help

- GIVEN `sofer mcp remove --help`
- WHEN rendered
- THEN `--agent`, `--scope`, `--dry-run` SHALL be listed

#### Scenario: add help documents env forwarding

- GIVEN `sofer mcp add --help`
- WHEN rendered
- THEN the description SHALL state that codex and gemini receive env forwarding (names only)
- AND the description SHALL state that opencode entries carry no environment and that a warning is emitted when `HF_TOKEN`/`SOFER_MCP_APPROVAL_PHRASE` are set with `--agent opencode` (or `all`)

---

<!-- Informational only: maps the ADDED scenario to its apply-phase test
(AGENTS.md §6 / openspec/config.yaml — every spec scenario MUST have a
corresponding test). Not part of the archived requirement blocks. -->

| Scenario | Test (tests/test_cli.py, `TestMcpCliHelp`) |
| --- | --- |
| add help documents env forwarding | new `test_mcp_add_help_env_forwarding` — additive assertion that the updated `sofer mcp add --help` description covers codex/gemini names-only forwarding and the opencode no-env warning; existing `test_mcp_add_help_flags` stays unchanged |
