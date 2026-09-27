# Delta for packaging

> **Change** `docs-fastmcp-cap-drift` (issue #257) · branch `docs/257-fastmcp-cap-drift`.
>
> `fastmcp` was bumped to 4.x (PR #253). The code, `uv.lock`, and the wheel
> assertions target `>=4,<5`, but the canonical packaging requirement still
> required `fastmcp>=3.4,<4`. This delta amends it to the shipped cap.

## MODIFIED Requirements

### Requirement: MCP runtime dependency included by default (PKG-06)

> Added by `feat-mcp-auto-install` (2026-08-31). Modified by `docs-fastmcp-cap-drift`
> (issue #257, 2026-09-26) — the cap is `>=4,<5`, matching the shipped `fastmcp 4.x`.

`pyproject.toml` SHALL declare `fastmcp>=4,<5` in `dependencies`; MAY retain `mcp` alias with identical pin. `uv.lock` SHALL be regenerated.

#### Scenario: dependencies include fastmcp

- GIVEN `pyproject.toml`
- WHEN `dependencies` inspected
- THEN `fastmcp>=4,<5` SHALL be present

#### Scenario: Alias identical pin

- GIVEN `pyproject.toml`
- WHEN `optional-dependencies` inspected
- THEN `mcp` MAY be present and if so SHALL equal required pin
