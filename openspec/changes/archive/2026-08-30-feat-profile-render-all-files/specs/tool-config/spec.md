# Delta for tool-config

## ADDED Requirements

### Requirement: profile_dir and render_dir config (TC-11)

The system SHALL add `profile_dir = "profiles"` and `render_dir = "renders"` to `[tool.sofer]` with defaults in `config._DEFAULTS`, module constants `PROFILE_DIR`/`RENDER_DIR` bound at import and rebound via `config.reload`, and `pyproject.toml` example. Values MUST be non-empty strings; overrides via dataset-dir → cwd → defaults (TC-02). Consumers MUST read `config.PROFILE_DIR`/`RENDER_DIR` at call time (no hardcodes). `mcp_server._validate_output_targets` MUST include both dirs for containment.

#### Scenario: Defaults are profiles/renders

- GIVEN no `pyproject.toml` provides `profile_dir`/`render_dir`
- WHEN config resolves
- THEN `config.PROFILE_DIR` SHALL be `profiles` and `RENDER_DIR` SHALL be `renders`

#### Scenario: pyproject overrides profile_dir

- GIVEN `pyproject.toml` sets `profile_dir = "docs/profiles"`
- WHEN `config.reload` resolves
- THEN batch profile outputs SHALL be under `docs/profiles/`

#### Scenario: pyproject overrides render_dir

- GIVEN `pyproject.toml` sets `render_dir = "docs/renders"`
- WHEN `config.reload` resolves
- THEN batch render outputs SHALL be under `docs/renders/`

#### Scenario: No hardcoded output dirs

- GIVEN `src/sofer/profile.py` and `render.py` searched for literals
- WHEN inspected
- THEN no hardcoded `"profiles"`/`"renders"` SHALL appear except via `config`

#### Scenario: MCP containment covers new dirs

- GIVEN MCP server with `profile_dir = "../../evil"`
- WHEN `_validate_output_targets` runs
- THEN validation SHALL reject the escaped path
