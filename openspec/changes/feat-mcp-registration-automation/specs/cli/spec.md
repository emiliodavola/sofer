# Delta for cli

## ADDED Requirements

### Requirement: mcp help (CLI-R09)

> R09 next free; covers CLI-R05 intent.

`sofer` MUST expose `mcp` with `add`/`remove`. `add` MUST accept `--agent <opencode|codex|gemini|all> [--scope user|project] [--cwd PATH] [--dry-run]`; `remove` MUST accept `--agent <...|all> [--scope user|project] [--dry-run]`. Help for `sofer --help`, `sofer mcp*` MUST list these.

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
