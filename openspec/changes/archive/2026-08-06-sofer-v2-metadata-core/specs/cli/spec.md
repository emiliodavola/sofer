# Delta for CLI

## ADDED Requirements

### Requirement: profile and render are top-level subcommands (CLI-R03)

The system SHALL register `profile` and `render` as top-level subcommands,
alongside `validate`, `prepare`, `publish`, `codebook`, `init`, and `scan`.

#### Scenario: profile and render appear in help

- GIVEN `sofer --help`
- WHEN the help is rendered
- THEN `profile` SHALL appear as a subcommand
- AND `render` SHALL appear as a subcommand

#### Scenario: profile dispatches correctly

- GIVEN `sofer profile dataset.csv`
- WHEN the command executes
- THEN the profile handler SHALL run with `dataset.csv` as its argument

#### Scenario: render dispatches correctly

- GIVEN `sofer render ./build/`
- WHEN the command executes
- THEN the render handler SHALL run with `./build/` as its argument

### Requirement: Help text accurate for profile and render (CLI-R04)

The parser's `help=` and `description=` strings for `profile` and `render` SHALL
accurately document each command, and the README SHALL be updated in the same
change.

#### Scenario: profile help accurate

- GIVEN `sofer profile --help`
- WHEN the help is rendered
- THEN the help SHALL describe profiling a dataset into `metadata.yaml`

#### Scenario: render help accurate

- GIVEN `sofer render --help`
- WHEN the help is rendered
- THEN the help SHALL describe rendering `README.md` from `metadata.yaml`
