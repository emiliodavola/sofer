# Delta for tool-config

New capability — all requirements are ADDED. At archive time this creates
`openspec/specs/tool-config/spec.md`. Existing capabilities' behavior is
unchanged under correct discovery; no MODIFIED/REMOVED entries.

## ADDED Requirements

### Requirement: Discovery anchors on the dataset TOML directory (TC-01)

Tool-wide `[tool.sofer]` discovery SHALL walk up the directory tree starting
from the dataset TOML's directory (its `base_dir`) when a dataset config path
is known. The discovery entry point SHALL accept an explicit start path
parameter so callers (and tests) can inject the anchor. It SHALL NOT anchor on
the installed package location (`__file__`).

#### Scenario: pyproject above the dataset dir is honored

- GIVEN a `pyproject.toml` with `[tool.sofer] schema_sample_size = 500` two levels above `mydata/dataset.toml`
- WHEN any command runs with `--config mydata/dataset.toml`
- THEN the effective `schema_sample_size` is `500`

#### Scenario: Start-path injection enables testable discovery

- GIVEN a test creates a temp tree with a `pyproject.toml`
- WHEN discovery is invoked with the temp tree as start path
- THEN the temp `pyproject.toml` is selected without touching real user dirs

### Requirement: Discovery precedence is fixed (TC-02)

Resolution order SHALL be: (1) nearest `pyproject.toml` walking up from the
dataset TOML directory, (2) nearest `pyproject.toml` walking up from the
current working directory, (3) built-in `_DEFAULTS`.

#### Scenario: Dataset-dir result wins over cwd

- GIVEN dataset-dir tree sets `schema_sample_size = 500` and cwd tree sets `1000`
- WHEN a command runs with that dataset config from the cwd tree
- THEN the effective value is `500`

#### Scenario: Nothing found falls back to defaults

- GIVEN no `pyproject.toml` above the dataset dir or cwd contains `[tool.sofer]`
- WHEN any command runs
- THEN all tool-wide values equal `_DEFAULTS`

### Requirement: Runtime isolation from sofer's own repository config (TC-03)

At runtime the system MUST NOT consult the `pyproject.toml` shipped in or
next to the installed `sofer` package (editable installs included), unless
that file genuinely lies on the discovered walk-up path from the dataset or
cwd anchor.

#### Scenario: Editable install with external user project

- GIVEN sofer is installed editable (sofer's repo has a populated `[tool.sofer]`)
- AND the user's dataset lives outside the sofer repo with its own overriding `pyproject.toml`
- WHEN a command runs on that dataset
- THEN the user's overrides apply and sofer's repo values do not

### Requirement: One reload per CLI invocation after the config path resolves (TC-04)

The CLI entry point SHALL trigger exactly one tool-config resolution per
invocation, once the effective `--config` path is known. After resolution,
module-level config constants SHALL reflect the newly resolved values for all
subsequent reads within that invocation.

#### Scenario: Override honored within the same invocation

- GIVEN a working tree whose `pyproject.toml` sets `csv_delimiter = ","`
- WHEN `sofer profile data.csv` runs with the current working directory inside that tree
- THEN the CSV is read with `,` during that same invocation

(Note: the tool-wide `csv_delimiter` consumer is `sofer profile`, whose reader
defaults flow through `stream_csv`. The `prepare` command uses the
DATASET-level `[meta] csv_delimiter`, not this tool-wide key.)

#### Scenario: Single-file commands without a dataset TOML

- GIVEN `sofer codebook FILE` is invoked with no `--config`
- WHEN tool-config resolution occurs
- THEN discovery anchors on the current working directory per TC-02

### Requirement: Library callers resolve via from_toml (TC-05)

`DatasetConfig.from_toml` SHALL trigger tool-config resolution using the TOML
directory as anchor, so library consumers importing `sofer` directly get the
same discovery behavior without going through the CLI.

#### Scenario: Library load honors sibling pyproject

- GIVEN a script calls `DatasetConfig.from_toml("proj/data/dataset.toml")`
- AND `proj/pyproject.toml` sets `schema_sample_size = 250`
- THEN config constants reflect `250` after the call returns

### Requirement: Consumers read config dynamically (TC-06)

Modules MUST NOT bind config values at import time via
`from .config import X`; they SHALL access `config.X` at call time. Function
default parameters and argparse defaults MUST NOT capture pre-reload values;
they SHALL resolve through the config module at call time (a `None` sentinel
resolved inside the function body is acceptable).

#### Scenario: Codebook sample limit follows reload

- GIVEN resolution set `codebook_max_sample = 2000`
- WHEN a codebook function is called without an explicit `max_sample`
- THEN it operates with limit `2000`, not the import-time default

#### Scenario: Repeated imports stay consistent

- GIVEN config is reloaded between two operations in one process
- WHEN both operations read a config value
- THEN both see the reloaded value (no stale import-time copy)

### Requirement: Bootstrap keys anchor on cwd until a dataset config exists (TC-07)

Keys needed before any dataset TOML is known (e.g. `default_config_name`,
`output_dir`) SHALL honor `[tool.sofer]` overrides only via cwd walk-up.
Dataset-dir-sourced overrides of these bootstrap keys are out of reach by
construction; this limitation SHALL be documented rather than heuristically
resolved.

#### Scenario: cwd pyproject supplies default_config_name

- GIVEN the cwd tree's `pyproject.toml` sets `default_config_name = "my.toml"`
- WHEN `sofer scan` runs with no positional config
- THEN `my.toml` is used as the default config name

### Requirement: Resolved source is visible on request (TC-08)

When verbosity is enabled (`--verbose` flag or a documented environment
variable), the system SHALL report the absolute path of the `pyproject.toml`
sourced for tool-wide config, or state that built-in defaults were used.
Without verbosity, output SHALL NOT change.

#### Scenario: Verbose reports the sourced file

- GIVEN a discovered `pyproject.toml` and verbosity enabled
- WHEN any command runs
- THEN one line reports the absolute path of that file

#### Scenario: Defaults case reported

- GIVEN no `[tool.sofer]` anywhere on the discovery path and verbosity enabled
- WHEN any command runs
- THEN output states built-in defaults were used

#### Scenario: Silent by default

- GIVEN verbosity disabled
- WHEN any command runs
- THEN no source-path line appears and stdout content is unchanged

### Requirement: README documents discovery rules (TC-09)

The README section on `[tool.sofer]` SHALL document the anchoring rules, the
precedence order (dataset dir → cwd → defaults), the cwd-only limitation for
bootstrap keys, and the behavior shift for editable installs of sofer itself.

#### Scenario: Docs cover precedence and maintainer shift

- GIVEN a reader consults the README `[tool.sofer]` section
- THEN they find the three-step precedence, the bootstrap-key caveat, and a note that sofer's own repo TOML no longer applies at runtime
