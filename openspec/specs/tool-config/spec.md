# Tool Config Specification

## Purpose

Tool-wide `[tool.sofer]` configuration discovery for sofer: where the config
is searched (dataset TOML directory walk-up → cwd walk-up → built-in
defaults), when it is resolved during a CLI or library run, how consumers
read resolved values without import-time freezing, and how the resolved
source becomes visible on request.

## Requirements

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

Keys needed before any dataset TOML is known (`default_config_name`, `output_dir`, `raw_dir`) SHALL honor `[tool.sofer]` overrides only via cwd walk-up. Dataset-dir-sourced overrides of these bootstrap keys are out of reach by construction; this limitation SHALL be documented rather than heuristically resolved.

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

> Added by change `readme-overhaul-es` (archived 2026-08-28).

The deep `[tool.sofer]` reference SHALL reside in `docs/configuration.md`,
which SHALL document the anchoring rules, the precedence order (dataset dir →
cwd → defaults), the cwd-only limitation for bootstrap keys, and the behavior
shift for editable installs of sofer itself. The README SHALL keep a short
summary of the `[tool.sofer]` section, SHALL link to `docs/configuration.md`
for the full reference, and SHALL NOT duplicate the deep reference in the
README body. The README SHALL retain a one-line `SOFER_VERBOSE` troubleshooting
pointer.
(Previously: the README itself carried the full `[tool.sofer]` reference
section, including discovery rules, precedence, bootstrap-key caveat, and
editable-install notes.)

#### Scenario: Docs cover precedence and maintainer shift

- GIVEN a reader consults `docs/configuration.md`
- THEN they find the three-step precedence, the bootstrap-key caveat, and a note that sofer's own repo TOML no longer applies at runtime

#### Scenario: README points to the authoritative reference

- GIVEN a user reading `README.md` looks for `[tool.sofer]` details
- WHEN they reach the configuration summary
- THEN the README links to `docs/configuration.md`
- AND the README body does not carry the full deep reference

#### Scenario: SOFER_VERBOSE pointer survives extraction

- GIVEN the deep config reference has moved to `docs/configuration.md`
- WHEN a user troubleshoots verbosity from the README
- THEN the README keeps a one-line `SOFER_VERBOSE` pointer
- AND the pointer indicates where the full explanation lives

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

---

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

---

### Requirement: Card collapse threshold config (TC-12)

The system MUST add `card_collapse_threshold: int` to `[tool.sofer]` with built-in default `15` in `config._DEFAULTS` (`DEFAULTS["card_collapse_threshold"] = 15`). The value SHALL be a non-negative integer (`int >= 0`); non-int or negative values SHALL cause `ValueError` during `_read_tool_section`/`reload`. Module constant `CARD_COLLAPSE_THRESHOLD` SHALL be bound from `_DEFAULTS` at import and rebound via `config.reload` (discovery per TC-02: dataset-dir → cwd → defaults; TC-06 dynamic `config.X` access). No consumer SHALL hardcode the literal `15`. `pyproject.toml` example and `docs/configuration.md` SHALL document the key as tool-wide. This key SHALL NOT be read from per-dataset TOML `[meta]` — it is tool-wide only.

#### Scenario: TC-12.01 default is 15

- GIVEN no `pyproject.toml` provides `card_collapse_threshold`
- WHEN any command resolves config
- THEN `config.CARD_COLLAPSE_THRESHOLD` SHALL equal `15`

#### Scenario: TC-12.02 pyproject overrides threshold

- GIVEN `pyproject.toml` sets `card_collapse_threshold = 30`
- WHEN `config.reload(<anchor>)` resolves
- THEN `CARD_COLLAPSE_THRESHOLD` SHALL be `30`
- AND `repo_compliance.build_dataset_card` SHALL apply `30` as the per-table gate

#### Scenario: TC-12.03 dataset-dir wins over cwd

- GIVEN dataset-dir `pyproject.toml` sets `card_collapse_threshold = 5` and cwd sets `30`
- WHEN resolving with dataset-dir anchor (e.g. `DatasetConfig.from_toml`)
- THEN effective value SHALL be `5`

#### Scenario: TC-12.04 validation rejects bad values

- GIVEN `card_collapse_threshold = -1` or `card_collapse_threshold = "many"`
- WHEN `config.reload` runs
- THEN a `ValueError` SHALL be raised naming the key

#### Scenario: TC-12.05 consumers read via config at call time

- GIVEN `src/sofer/repo_compliance.py` searched for literals
- WHEN inspected
- THEN no hardcoded `15` or `> 15` SHALL appear for the collapse gate except via `config.CARD_COLLAPSE_THRESHOLD`

#### Scenario: TC-12.06 high threshold disables collapse (rollback)

- GIVEN `card_collapse_threshold = 999` and a dataset with 20 columns
- WHEN the card is generated
- THEN no `<details>` SHALL appear (single-group below threshold → flat table)

#### Scenario: TC-12.07 discoverability

- GIVEN a reader consults `docs/configuration.md` or `pyproject.toml` example
- THEN they SHALL find `card_collapse_threshold` listed under `[tool.sofer]` with default `15` and description "columns per table above which Data Fields collapses; multi-table datasets always per-sheet"
