# Delta for cli

## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Help text accurate for new commands (CLI-R02)
Parser `help=`/`description=` for `prepare` (`--output`, `--all-files`, `--no-checks`, `--force`, `--verify`) and `publish` (`--target hf|local`, `--output`, `--force`, `--keep-csv`, `--dry-run`) SHALL be accurate. Parser description and `init` template SHALL NOT reference `upload`; README SHALL update.
(Previously: init template used generic `TODO: path/to/file.csv`; now `raw/` convention.)

#### Scenario: prepare help
- GIVEN `sofer prepare --help`
- WHEN rendered
- THEN all `prepare` flags SHALL appear

#### Scenario: publish help
- GIVEN `sofer publish --help`
- WHEN rendered
- THEN all `publish` flags SHALL appear

#### Scenario: No stale upload
- GIVEN parser + template
- WHEN built
- THEN neither mentions `upload`, README documents `prepare`/`publish` and `raw/` layout
