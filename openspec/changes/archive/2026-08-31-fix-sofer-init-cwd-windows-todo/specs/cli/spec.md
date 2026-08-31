# Delta for cli

## MODIFIED Requirements

### Requirement: init creates raw/ and --move-existing (CLI-R07)

`sofer init <name>` MUST create `raw/` via `mkdir -p` idempotently. Template `[[file]] local` MUST be Windows-safe `raw/example.csv` (no `:`, `ntpath.splitdrive` → `""`), valid NTFS. `--move-existing` moves depth-1 `SUPPORTED_FORMATS` files into `raw/` with `check_flatten_collisions` first, collision→fail, `--dry-run` preview only, non-interactive skip, prompt `[y/N]`.

(Previously: `TODO: raw/file.csv` with `:` illegal on NTFS.)

#### Scenario: Windows-safe placeholder
- GIVEN `sofer init my-ds`
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
