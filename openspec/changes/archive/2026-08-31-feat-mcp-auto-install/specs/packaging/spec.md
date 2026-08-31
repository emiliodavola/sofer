# Delta for packaging

## MODIFIED Requirements

### Requirement: Installability and entry point (PKG-03)

Build SHALL expose `sofer = sofer.cli:main` and `sofer-mcp = sofer.mcp_server:main`. Both SHALL run without `uv run`.

(Previously: only `sofer` asserted.)

#### Scenario: Both entry points in wheel

- GIVEN built wheel
- WHEN `entry_points.txt` inspected
- THEN it SHALL contain both `sofer` and `sofer-mcp` scripts

#### Scenario: Both CLIs run

- GIVEN non-editable install
- WHEN `sofer --help` and `sofer-mcp --help` run
- THEN both SHALL exit 0

## ADDED Requirements

### Requirement: MCP runtime dependency included by default (PKG-06)

`pyproject.toml` SHALL declare `fastmcp>=3.4,<4` in `dependencies`; MAY retain `mcp` alias with identical pin. `uv.lock` SHALL be regenerated.

#### Scenario: dependencies include fastmcp

- GIVEN `pyproject.toml`
- WHEN `dependencies` inspected
- THEN `fastmcp>=3.4,<4` SHALL be present

#### Scenario: Alias identical pin

- GIVEN `pyproject.toml`
- WHEN `optional-dependencies` inspected
- THEN `mcp` MAY be present and if so SHALL equal required pin
