# Delta for mcp-server

## MODIFIED Requirements

### Requirement: Import without the extra fails clearly (MSP-R02)

> Added by `sofer-mcp-server` (2026-08-28).

`sofer.mcp_server` SHALL import on lean install. `fastmcp>=3.4,<4` SHALL be in `dependencies` so `pip install "sofer @ git+..."` and `uv tool install "sofer @ git+..."` SHALL install `fastmcp` and `sofer-mcp --help` SHALL succeed. `mcp` alias `["fastmcp>=3.4,<4"]` SHALL remain one minor. Guard in `mcp_server.py` SHALL stay degraded-only with `pip`+`uv tool` and `sofer[mcp] @ git+...`.

(Previously: base stayed lean — `fastmcp` not a core dep; import raised `ImportError` to `pip install 'sofer[mcp]'`.)

#### Scenario: Lean install includes fastmcp

- GIVEN clean env
- WHEN `uv tool install "sofer @ git+https://github.com/emiliodavola/sofer.git@vX.Y.Z" --force` runs
- THEN `fastmcp` SHALL be installed and `sofer-mcp --help` SHALL exit 0

#### Scenario: Alias sofer[mcp] @ URL still works

- GIVEN same tag
- WHEN `pip install "sofer[mcp] @ git+https://github.com/emiliodavola/sofer.git@vX.Y.Z"` runs
- THEN install SHALL succeed and `import sofer.mcp_server` SHALL succeed

#### Scenario: Guard retained with pip+uv+PEP 508 message

- GIVEN degraded install (`fastmcp` absent)
- WHEN `import sofer.mcp_server` executes
- THEN `ImportError` SHALL mention `pip`, `uv tool`, `sofer[mcp] @ git+https://` and NOT `git+...[mcp]`

#### Scenario: import fastmcp succeeds

- GIVEN lean install
- WHEN `python -c "import fastmcp"` runs
- THEN it SHALL succeed

#### Scenario: Wheel METADATA unconditional

- GIVEN built wheel
- WHEN METADATA `Requires-Dist` inspected
- THEN `fastmcp>=3.4,<4` SHALL appear without `extra == 'mcp'`

#### Scenario: uv.lock unconditional

- GIVEN regenerated `uv.lock`
- WHEN `sofer` entry inspected
- THEN `fastmcp` SHALL be under `dependencies` not `optional-dependencies`

#### Scenario: Existing tests green

- GIVEN repo
- WHEN `uv run pytest tests/test_mcp_server.py tests/test_mcp_registration.py -q` runs
- THEN all SHALL pass

### Requirement: Packaging and documentation (MSP-R12)

> Added by `sofer-mcp-server` (2026-08-28).

`pyproject.toml` SHALL declare `fastmcp>=3.4,<4` in `dependencies` and `sofer-mcp = "sofer.mcp_server:main"`; MAY retain `mcp` alias. READMEs SHALL document Install + AI/MCP with correct PEP 508 `name[extra] @ URL`, `uv tool` and `uvx --with`, and flip intro to included-by-default.

(Previously: only `optional-dependencies mcp` + script; README showed `pip install 'sofer[mcp]'`.)

#### Scenario: Wheel script and Requires-Dist

- GIVEN built wheel
- WHEN `entry_points.txt` + METADATA inspected
- THEN `sofer-mcp = sofer.mcp_server:main` and unconditional `fastmcp>=3.4,<4` SHALL be present

#### Scenario: Alias optional

- GIVEN wheel METADATA
- WHEN `Provides-Extra` inspected
- THEN `mcp` MAY be present mapping to `fastmcp>=3.4,<4; extra == 'mcp'`

#### Scenario: README Install correct

- GIVEN `README.md` Install
- WHEN inspected
- THEN it SHALL show `sofer @ git+...` and `sofer[mcp] @ git+...`, `uv tool install "sofer @ git+..."` and `uvx --from git+... --with "sofer[mcp]" sofer-mcp --help`

#### Scenario: README AI/MCP fixed

- GIVEN `README.md` AI/MCP section
- WHEN inspected
- THEN `git+...[mcp]` SHALL NOT appear, `sofer[mcp] @ git+...` SHALL, intro SHALL say "included by default"

#### Scenario: README_ES mirrors README (§13)

- GIVEN `README.md` + `README_ES.md`
- WHEN inspected
- THEN headings/order SHALL match, commands identical English, fixes in both same commit
