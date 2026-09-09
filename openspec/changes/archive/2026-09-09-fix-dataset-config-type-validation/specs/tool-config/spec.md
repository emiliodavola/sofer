# Delta for tool-config

## ADDED Requirements

### Requirement: Configuration type validation with stable diagnostics (TC-13)

> Added by change `fix-dataset-config-type-validation`.

Invalid configuration SHALL fail before reader execution with stable, actionable diagnostics — never reach comparisons or readers as an arbitrary Python type, and never silently fall back to a default. Dataset `[meta]` and `[[check]]`/`[[quality]]` values are validated by `DatasetConfig` at parse time; `[tool.sofer]` values are validated by the tool-config merge.

`csv_delimiter` MUST be a single-character string; `csv_encoding` MUST be a non-empty string; `confidential`, `private`, `skip_cross_file_schema` MUST be booleans; `repo_type` MUST be a non-empty string; `min_files` MUST be a non-bool integer ≥ 0; `min_total_size_mb` MUST be a non-bool number ≥ 0; quality numeric fields (`max_null_pct`, `min`, `max`, `min_unique`) MUST be numbers when present; column-check `expected` MUST be a list of strings. Diagnostics SHALL name the offending key, the expected type, and the received value. The CLI SHALL exit non-zero with the same semantic error; the MCP SHALL return `ok:false, exit_code:1`, stable `error_code`, diagnostics, and a truthful recovery description.

(Previously: `DatasetConfig.from_toml` assigned raw TOML values without type checks, and the `[tool.sofer]` merge loop's fallback branch accepted any type.)

#### Scenario: Invalid csv_delimiter type rejected at load

- GIVEN `[meta] csv_delimiter = 5` in the dataset TOML
- WHEN `DatasetConfig.from_toml` runs
- THEN the diagnostic SHALL name `csv_delimiter`, expect a string, and show the received `5`
- AND no reader SHALL execute

#### Scenario: Invalid csv_encoding type rejected at load

- GIVEN `[meta] csv_encoding = ["utf-8"]`
- WHEN `DatasetConfig.from_toml` runs
- THEN the diagnostic SHALL name `csv_encoding` and expect a non-empty string

#### Scenario: Non-bool confidential rejected

- GIVEN `[meta] confidential = "yes"`
- WHEN `DatasetConfig.from_toml` runs
- THEN the diagnostic SHALL name `confidential` and expect a boolean

#### Scenario: Invalid min_files type rejected

- GIVEN `[[check]] min_files = "two"`
- WHEN `DatasetConfig.from_toml` runs
- THEN the diagnostic SHALL name `min_files` and expect a non-negative integer
- AND `min_files = true` SHALL also be rejected (bool is not an int here)

#### Scenario: Invalid min_total_size_mb rejected

- GIVEN `[[check]] min_total_size_mb = [1.0]`
- WHEN `DatasetConfig.from_toml` runs
- THEN the diagnostic SHALL name `min_total_size_mb` and expect a non-negative number

#### Scenario: Negative min_files rejected

- GIVEN `[[check]] min_files = -1`
- WHEN `DatasetConfig.from_toml` runs
- THEN the diagnostic SHALL name `min_files` and expect a non-negative integer

#### Scenario: Tool-config typed keys reject wrong types

- GIVEN `[tool.sofer] output_max_bytes = "huge"` (or any typed default given a wrong type)
- WHEN the tool-config merge runs
- THEN it SHALL raise a stable diagnostic naming the key and expected type

#### Scenario: CLI surfaces the diagnostic non-zero

- GIVEN a dataset TOML with `[meta] csv_delimiter = 5`
- WHEN a CLI command loads the config
- THEN the process SHALL exit non-zero and print the stable diagnostic

#### Scenario: MCP surfaces config_errors with stable error_code

- GIVEN a dataset TOML with `[meta] csv_delimiter = 5` under the server root
- WHEN an MCP tool loads the config
- THEN the envelope SHALL be `ok:false, exit_code:1` with the diagnostic in `config_errors` and a stable `error_code`

#### Scenario: Valid values keep working

- GIVEN a well-formed dataset TOML
- WHEN `DatasetConfig.from_toml` runs
- THEN parsing SHALL succeed and `validate()` SHALL report no type diagnostics
