# Delta for cli

## MODIFIED Requirements

### Requirement: profile and render are top-level subcommands (CLI-R03)

The system SHALL register `profile` and `render` as top-level subcommands, alongside `validate`, `prepare`, `publish`, `codebook`, `init`, and `scan`. Each SHALL accept `--output`, `--force`, `--all-files`, and `--config`. Positional is `dataset`/`package` for single-file; when `--all-files` is set the positional MUST be a TOML path containing `[[file]]` and the handler MUST iterate entries (PRF-05/RND-04); without `[[file]]` it MUST fail fast. Single-file without `--force` MUST guard existing dest (PRF-06/RND-05).

(Previously: only `dataset`/`package` + `--output`; no batch, no --force, no TOML contract.)

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

#### Scenario: profile --all-files dispatches batch

- GIVEN `sofer profile dataset.toml --all-files`
- WHEN the command executes
- THEN handler SHALL iterate `[[file]]` and write per-entry outputs

#### Scenario: render --all-files dispatches batch

- GIVEN `sofer render dataset.toml --all-files`
- WHEN the command executes
- THEN handler SHALL iterate `[[file]]` and write per-entry READMEs

#### Scenario: TOML without [[file]] errors

- GIVEN TOML with no `[[file]]`
- WHEN `--all-files` executes
- THEN exit code SHALL be non-zero mentioning `[[file]]`

### Requirement: Help text accurate for profile and render (CLI-R04)

The parser's `help=` and `description=` strings for `profile` and `render` SHALL accurately document each command, its flags `--output`, `--all-files`, `--force`, `--config`, the TOML `[[file]]` contract for `--all-files`, and the `use --force to overwrite` guard. The README SHALL be updated in the same change.

(Previously: only described profiling into metadata.yaml / rendering README.md.)

#### Scenario: profile help accurate

- GIVEN `sofer profile --help`
- WHEN the help is rendered
- THEN the help SHALL describe profiling a dataset into `metadata.yaml`
- AND SHALL list `--output`, `--all-files`, `--force`, `--config`

#### Scenario: render help accurate

- GIVEN `sofer render --help`
- WHEN the help is rendered
- THEN the help SHALL describe rendering `README.md` from `metadata.yaml`
- AND SHALL list `--output`, `--all-files`, `--force`, `--config`
