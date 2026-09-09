# Delta for cli

## MODIFIED Requirements

### Requirement: init creates raw/ and --move-existing (CLI-R07)

`sofer init <name> --user <user>` SHALL require an explicit `--user` (missing → argparse usage error, exit 2, no write). Identity SHALL be validated pre-write via the shared contract (INIT-05): missing/blank/placeholder (`YOUR_USER` or any `_PLACEHOLDERS` value)/unsafe/injection-shaped name or user SHALL be rejected with exit 1 BEFORE any write — no `<name>.toml`, no `raw/`; the generated TOML SHALL NEVER contain `YOUR_USER`. The success line SHALL print the canonical ABSOLUTE `config_path`. `init` MUST create `raw/` (`RAW_DIR`) via `mkdir -p` idempotently alongside `<name>.toml`. Template SHALL state `# Source files → raw/ (scan copies to cache/)` and `[[file]] local` MUST be Windows-safe `raw/example.csv` (no `:`, `ntpath.splitdrive` → `""`, valid NTFS). `--move-existing` SHALL move depth-1 supported files (`SUPPORTED_FORMATS`, direct children of cwd, excluding `cache`/`build`/`raw`/EXCLUSIONS) into `raw/` with: `check_flatten_collisions` before any move; collision with existing `raw/` content → fail naming sources; `--dry-run` previews no mutation; `--force` or non-interactive skip prompt, else prompt `[y/N]` and abort on `N`. Without flag, loose files stay.

(Previously: `--user` optional defaulting to the `YOUR_USER` placeholder; no identity validation; a relative filename was printed.)

#### Scenario: init creates raw/

- GIVEN no `raw/`
- WHEN `sofer init my-ds --user myuser`
- THEN `raw/` exists and `my-ds.toml` contains `raw/` comment

#### Scenario: Idempotent

- GIVEN `raw/` exists with files
- WHEN `sofer init other --user myuser`
- THEN succeeds, `raw/` unchanged

#### Scenario: Depth-1 only supported

- GIVEN `a.csv`, `subdir/b.csv`, `notes.txt`, `cache/c.csv`
- WHEN `sofer init my-ds --user myuser --move-existing --force`
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

- GIVEN `sofer init my-ds --user myuser` done
- WHEN `my-ds.toml` inspected
- THEN contains `raw/` guidance, no stale `data/` hint

#### Scenario: Windows-safe placeholder

- GIVEN `sofer init my-ds --user myuser`
- WHEN `my-ds.toml` inspected
- THEN `local="raw/example.csv"`, no `":"`

#### Scenario: ntpath drive

- GIVEN `raw/example.csv`
- WHEN `ntpath.splitdrive` win32
- THEN `("", "raw/example.csv")`

#### Scenario: scan xlsx after init

- GIVEN `my-ds.toml` + `DATA_GOT_ALL.xlsx`
- WHEN `sofer scan` then `validate`
- THEN `cache/DATA_GOT_ALL.xlsx` registered, validate pass

#### Scenario: --user required

- GIVEN `sofer init my-ds` with no `--user`
- WHEN the command executes
- THEN argparse SHALL exit 2 naming the missing `--user` and NO file SHALL be written

#### Scenario: Placeholder user rejected pre-write

- GIVEN `sofer init my-ds --user YOUR_USER`
- WHEN the command executes
- THEN exit 1 SHALL name the placeholder and neither `my-ds.toml` nor `raw/` SHALL be created

#### Scenario: Unsafe identity rejected pre-write

- GIVEN `sofer init "a/../b" --user myuser` (or a name/user with quotes, newline, drive, or separator)
- WHEN the command executes
- THEN exit 1 SHALL name the invalid component and NO file SHALL be written

#### Scenario: canonical config_path printed

- GIVEN `sofer init my-ds --user myuser` run from `<abs>/proj`
- WHEN the command succeeds
- THEN stdout SHALL print the absolute `config_path` `<abs>/proj/my-ds.toml`