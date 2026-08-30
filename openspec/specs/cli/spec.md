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
updated in the same change. Parser description and `init` template SHALL NOT reference stale `data/` hint; `init` template SHALL state `# Source files → raw/ (scan copies to cache/)` and description SHALL mention `raw/→cache/→build/`.

#### Scenario: prepare help lists all flags

- GIVEN `sofer prepare --help`
- WHEN the help is rendered
- THEN `--output`, `--all-files`, `--no-checks`, `--force`, and `--verify` SHALL be listed

#### Scenario: publish help lists all flags

- GIVEN `sofer publish --help`
- WHEN the help is rendered
- THEN `--target`, `--output`, `--force`, `--keep-csv`, and `--dry-run` SHALL be listed

#### Scenario: No stale upload

- GIVEN the parser description and the `init` template
- WHEN the CLI is built
- THEN neither SHALL mention `upload`
- AND the README SHALL document `prepare` and `publish` instead

#### Scenario: No stale upload and raw/ layout
- GIVEN parser + template
- WHEN built
- THEN neither mentions `upload`, README documents `prepare`/`publish` and `raw/` layout, and `init` template contains `raw/` guidance with no stale `data/` hint

---

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

---

### Requirement: --version reports the installed release version (CLI-R05)

> Added by change `installable-cli-pypi` (archived 2026-08-26).

`sofer --version` SHALL print `sofer v<version>` where `<version>` is resolved
at runtime from installed distribution metadata — never from a static constant.
The output SHALL be non-empty and PEP 440-valid, and SHALL work from an
installed console script without `uv run`.

#### Scenario: Released install reports the tag version

- GIVEN a non-editable install of a wheel built at tag `v0.3.0`
- WHEN `sofer --version` runs
- THEN stdout SHALL be `sofer v0.3.0` and the exit code SHALL be 0

#### Scenario: Dev install reports a derived version

- GIVEN a dev/editable install with no release tag at HEAD
- WHEN `sofer --version` runs
- THEN the printed version SHALL be non-empty and PEP 440-valid
- AND it SHALL NOT equal any hardcoded literal

#### Scenario: Standalone console script works

- GIVEN an installed (non-editable) console script
- WHEN `sofer --version` runs as a subprocess outside the repository
- THEN the exit code SHALL be 0 and stdout SHALL be non-empty

---

### Requirement: Document stamping uses the shared version resolver (CLI-R06)

> Added by change `installable-cli-pypi` (archived 2026-08-26).

The version stamped into generated documents (`generated.version` in
`metadata.yaml`) SHALL be produced by the SAME shared runtime resolver that
backs `--version`. The static `__version__` constant SHALL be removed; in
dev/editable contexts where installed metadata is unavailable, the resolver
SHALL fall back to a non-empty derived value.

#### Scenario: Stamped version equals the CLI version

- GIVEN a `profile` run in any install context
- WHEN the generated `metadata.yaml` is inspected
- THEN `generated.version` SHALL equal the value printed by `sofer --version`
- AND it SHALL be non-empty

#### Scenario: No static version constant remains

- GIVEN the package source
- WHEN searched for version definitions
- THEN no hardcoded `__version__` string literal SHALL exist
- AND installed-metadata lookup (with dev fallback) SHALL be the version source

---

### Requirement: init creates raw/ and --move-existing (CLI-R07)

`sofer init <name>` MUST create `raw/` (`RAW_DIR`) via `mkdir -p` idempotently alongside `<name>.toml`. Template SHALL state `# Source files → raw/ (scan copies to cache/)`. `--move-existing` SHALL move depth-1 supported files (`SUPPORTED_FORMATS`, direct children of cwd, excluding `cache`/`build`/`raw`/EXCLUSIONS) into `raw/` with: `check_flatten_collisions` before any move; collision with existing `raw/` content → fail naming sources; `--dry-run` previews no mutation; `--force` or non-interactive skip prompt, else prompt `[y/N]` and abort on `N`. Without flag, loose files stay.

#### Scenario: init creates raw/
- GIVEN no `raw/`
- WHEN `sofer init my-ds`
- THEN `raw/` exists and `my-ds.toml` contains `raw/` comment

#### Scenario: Idempotent
- GIVEN `raw/` exists with files
- WHEN `sofer init other`
- THEN succeeds, `raw/` unchanged

#### Scenario: Depth-1 only supported
- GIVEN `a.csv`, `subdir/b.csv`, `notes.txt`, `cache/c.csv`
- WHEN `sofer init my-ds --move-existing --force`
- THEN only `a.csv` → `raw/a.csv`

#### Scenario: Collision guard
- GIVEN `raw/a.csv` exists and loose `a.csv` exists
- WHEN `--move-existing --force`
- THEN fail naming both, no move

#### Scenario: Dry-run preview
- GIVEN loose `a.csv`, `b.xlsx`
- WHEN `--move-existing --dry-run`
- THEN lists `a.csv → raw/a.csv`, no move, `raw/` not created if absent

#### Scenario: Non-interactive guard
- GIVEN loose `a.csv`, `not isatty`, no `--force`
- WHEN `--move-existing`
- THEN skip move, `raw/` still created, message hints `--force`

#### Scenario: Prompt N aborts
- GIVEN loose `a.csv`, tty
- WHEN `--move-existing` user `N`
- THEN no move, exit 0

#### Scenario: Template mentions raw/
- GIVEN `sofer init my-ds` done
- WHEN `my-ds.toml` inspected
- THEN contains `raw/` guidance, no stale `data/` hint

### Requirement: Help for init --move-existing (CLI-R08)

`sofer init --help` SHALL document `raw/` creation and `--move-existing`/`--dry-run`/`--force` (depth 1, `SUPPORTED_FORMATS`, collision, non-interactive). Description SHALL mention `raw/→cache/→build/`.

#### Scenario: Help lists flags
- GIVEN `sofer init --help`
- WHEN rendered
- THEN `--move-existing`, `--dry-run`, `--force` SHALL appear
