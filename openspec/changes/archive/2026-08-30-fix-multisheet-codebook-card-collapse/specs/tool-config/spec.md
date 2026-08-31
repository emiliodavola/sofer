# Delta for tool-config

## ADDED Requirements

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
