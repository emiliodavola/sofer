# Delta for tool-config

## ADDED Requirements

### Requirement: Raw directory bootstrap key (TC-10)

`raw_dir` SHALL be a tool-wide `[tool.sofer]` bootstrap key with built-in default `"raw"`. It SHALL be discovered via the same walk-up precedence as `output_dir`/`default_config_name` (TC-02): dataset-dir → cwd → `_DEFAULTS`. It MUST be a non-empty string; overrides in `pyproject.toml` SHALL take precedence. Module constant `RAW_DIR` SHALL reflect the resolved value after `reload`. `pyproject.toml` example SHALL include `raw_dir = "raw"` and `docs/configuration.md` SHALL document it with the other bootstrap keys.

#### Scenario: Default raw_dir is "raw"
- GIVEN no `pyproject.toml` provides `[tool.sofer] raw_dir`
- WHEN any command resolves config
- THEN `config.RAW_DIR` SHALL equal `"raw"`

#### Scenario: pyproject overrides raw_dir
- GIVEN cwd `pyproject.toml` sets `raw_dir = "data-raw"`
- WHEN `config.reload(None)` runs
- THEN `RAW_DIR` SHALL be `"data-raw"`

#### Scenario: Dataset-dir wins over cwd for raw_dir
- GIVEN dataset-dir `pyproject.toml` sets `raw_dir = "raw"` and cwd sets `raw_dir = "inputs"`
- WHEN resolving with dataset-dir anchor
- THEN effective `raw_dir` SHALL be `"raw"`

## MODIFIED Requirements

### Requirement: Bootstrap keys anchor on cwd until a dataset config exists (TC-07)

Keys needed before any dataset TOML is known (`default_config_name`, `output_dir`, `raw_dir`) SHALL honor `[tool.sofer]` overrides only via cwd walk-up. Dataset-dir-sourced overrides of these bootstrap keys are out of reach by construction; this limitation SHALL be documented rather than heuristically resolved.
(Previously: listed only `default_config_name`/`output_dir`; now includes `raw_dir`.)

#### Scenario: cwd pyproject supplies default_config_name
- GIVEN cwd `pyproject.toml` sets `default_config_name = "my.toml"`
- WHEN `sofer scan` runs with no positional config
- THEN `my.toml` SHALL be used as default

#### Scenario: cwd pyproject supplies raw_dir
- GIVEN cwd `pyproject.toml` sets `raw_dir = "inputs"`
- WHEN `sofer init` runs before any dataset TOML exists
- THEN `inputs/` SHALL be created (not `raw/`)

#### Scenario: Bootstrap limitation documented
- GIVEN `docs/configuration.md`
- WHEN reader checks bootstrap keys section
- THEN it SHALL list `default_config_name`, `output_dir`, `raw_dir` as cwd-only with note that dataset-dir overrides are unreachable
