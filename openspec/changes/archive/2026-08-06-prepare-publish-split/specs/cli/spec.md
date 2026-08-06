# CLI Specification

## Purpose

The `sofer` command-line surface: which commands are top-level, how `prepare`
and `publish` replace `upload`, and the accuracy of `--help` text. This domain
documents the CLI contract only — command behavior lives in the prepare,
publish, and other domain specs.

## Requirements

### Requirement: upload removed; prepare and publish are top-level (CLI-R01)

The `upload` subcommand SHALL be removed from the CLI. `prepare` and `publish`
SHALL be registered as top-level subcommands, each accepting the TOML config
path as their positional argument.

#### Scenario: upload is unrecognized

- GIVEN `sofer upload dataset.toml`
- WHEN the command executes
- THEN argparse SHALL reject it as an unrecognized command
- AND the exit code SHALL be 2

#### Scenario: prepare and publish appear in help

- GIVEN `sofer --help`
- WHEN the help is rendered
- THEN `upload` SHALL NOT appear
- AND `prepare` SHALL appear as a subcommand
- AND `publish` SHALL appear as a subcommand

#### Scenario: prepare dispatches correctly

- GIVEN `sofer prepare dataset.toml --force`
- WHEN the command executes
- THEN the prepare handler SHALL run with `force = True`

#### Scenario: publish dispatches correctly

- GIVEN `sofer publish dataset.toml --target local`
- WHEN the command executes
- THEN the publish handler SHALL run with `target = "local"`

---

### Requirement: Help text accurate for new commands (CLI-R02)

The parser's `help=` and `description=` strings for `prepare` and `publish`
SHALL document their exact flags: `prepare` — `--output`, `--all-files`,
`--no-checks`, `--force`, `--verify`; `publish` — `--target hf|local`,
`--output`, `--force`, `--keep-csv`, `--dry-run`. The parser description and
the `init` template SHALL NOT reference `upload`, and the README SHALL be
updated in the same change.

#### Scenario: prepare help lists all flags

- GIVEN `sofer prepare --help`
- WHEN the help is rendered
- THEN `--output`, `--all-files`, `--no-checks`, `--force`, and `--verify` SHALL be listed

#### Scenario: publish help lists all flags

- GIVEN `sofer publish --help`
- WHEN the help is rendered
- THEN `--target`, `--output`, `--force`, `--keep-csv`, and `--dry-run` SHALL be listed

#### Scenario: No stale upload references

- GIVEN the parser description and the `init` template
- WHEN the CLI is built
- THEN neither SHALL mention `upload`
- AND the README SHALL document `prepare` and `publish` instead
