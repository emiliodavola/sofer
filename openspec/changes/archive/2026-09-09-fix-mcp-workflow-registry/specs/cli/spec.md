# Delta for cli

## ADDED Requirements

### Requirement: Machine-readable status as stable JSON (CLI-R10)

> Added by change `fix-mcp-workflow-registry`.

CLI status output that is machine-readable SHALL be stable JSON, not a Python
dictionary `repr`. Where a command already emits a status/result line for
tools or agents to consume, that line SHALL serialize to JSON with the same
stable keys as the MCP envelope contract (`ok`, `exit_code`, `phase`,
`requires`, `next`, `config_path`, `dataset_root`, `error_code`, `message`,
`config_errors`) or a documented subset, keeping parity between CLI and MCP
status (acceptance criterion: "minimal CLI status serialization needed for
parity").

(Previously: CLI status was human prose; machine-readable status, where
present, was not contractually JSON.)

#### Scenario: CLI status line is parseable JSON

- GIVEN a CLI command that emits a machine-readable status line
- WHEN the line is parsed
- THEN it SHALL decode as JSON with the documented stable keys

#### Scenario: CLI status does not leak Python syntax

- GIVEN a command that emits status
- THEN `repr`-style Python literals (e.g. `{'ok': True}`) SHALL NOT appear; only JSON appears