# Delta for mcp-server

## ADDED Requirements

### Requirement: Windows-safe init placeholder (INIT-01)

System MUST emit `_INIT_TEMPLATE` with Windows-safe `[[file]] local`. Placeholder SHALL be `raw/example.csv` (or equivalent), MUST NOT contain `:`. TOML MUST parse on win32 with `ntpath.splitdrive` drive `""`; `:` is reserved except drive `X:`.

#### Scenario: Win32 no drive
- GIVEN `sofer_init(name="test")` output
- WHEN `ntpath.splitdrive("raw/example.csv")` on win32
- THEN drive is `""` and `":"` absent

#### Scenario: No TODO colon
- GIVEN fresh `test.toml`
- WHEN text inspected
- THEN `TODO:` not present

#### Scenario: Colon rejected
- GIVEN TOML `local="TODO: raw/file.csv"`
- WHEN validated on Windows
- THEN rejected (`:` illegal NTFS)

### Requirement: sofer_init cwd containment (INIT-02)

`sofer_init` SHALL expose `cwd: str | None = None`. `None` → effective root is `_get_root()` (back-compat). `str` → resolved via `_contained_path(cwd, root=_SERVER_ROOT, must_exist=False)` and MUST satisfy `is_relative_to(_SERVER_ROOT.resolve())`, per-call `effective_root`, MUST NOT mutate `_SERVER_ROOT`. Escape → `PathOutsideRootError`.

#### Scenario: cwd None back-compat
- GIVEN `build_server(root=Desktop)` live CWD `Desktop/test`
- WHEN `sofer_init(name="test", cwd=None)`
- THEN root is `Desktop`

#### Scenario: cwd contained succeeds
- GIVEN `cwd="Desktop/test"` under `Desktop`
- WHEN `sofer_init(cwd="Desktop/test", name="test")`
- THEN succeeds with root `Desktop/test`

#### Scenario: cwd outside rejected
- GIVEN `_SERVER_ROOT=Desktop`
- WHEN `sofer_init(cwd="C:/Windows")`
- THEN `PathOutsideRootError`, no write

#### Scenario: traversal rejected
- GIVEN `_SERVER_ROOT=Desktop`
- WHEN `cwd="Desktop/../Windows"`
- THEN `PathOutsideRootError`

#### Scenario: no global mutation
- GIVEN `_SERVER_ROOT=Desktop`
- WHEN `sofer_init(cwd="Desktop/test", name="test")` done
- THEN `_get_root()` still `Desktop`

### Requirement: Anchored writes under effective_root (INIT-03)

`sofer_init` MUST create `<name>.toml` and `raw/` only inside `effective_root` (INIT-02). No parent writes.

#### Scenario: stale-root anchored
- GIVEN `build_server(root=Desktop)` + dir `Desktop/test`
- WHEN `sofer_init(cwd="Desktop/test", name="test")`
- THEN `Desktop/test/test.toml` + `Desktop/test/raw/` exist, `Desktop/test.toml` absent

#### Scenario: idempotent
- GIVEN `Desktop/test/test.toml` + `raw/keep.csv`
- WHEN re-run `sofer_init(cwd="Desktop/test", name="test")`
- THEN succeeds, `keep.csv` preserved

#### Scenario: cleanup not parent
- GIVEN effective root `Desktop/test`
- WHEN init completes
- THEN parent `Desktop/raw` not created

### Requirement: xlsx discovery after init (INIT-04)

After `sofer_init` → `sofer_scan_apply`, scanner MUST discover `DATA_GOT_ALL.xlsx` and `dataset.xlsx` via `SUPPORTED_FORMATS`, copy flattened to `cache/*.xlsx`, register `local="cache/<name>.xlsx"`. `sofer_validate` MUST pass post-scan.

#### Scenario: xlsx registered
- GIVEN `DATA_GOT_ALL.xlsx` + `dataset.xlsx` loose in `Desktop/test`
- WHEN `sofer_init` then `sofer_scan_apply(config="Desktop/test/test.toml")`
- THEN TOML has both `cache/*.xlsx` and files exist in `cache/`

#### Scenario: validate passes
- GIVEN post-scan TOML with 2 xlsx
- WHEN `sofer_validate`
- THEN `ok:true`, no `Local path not found`

#### Scenario: scan idempotent
- GIVEN post-scan with 2 entries
- WHEN `sofer_scan_apply` rerun
- THEN count stays 2, no dupes

## MODIFIED Requirements

### Requirement: Tool roster and schema contract (MSP-R03)

> Modified by `fix-sofer-init-cwd-windows-todo` — adds optional `cwd` to `sofer_init`.

Server SHALL expose 14 callables: `sofer_validate, sofer_prepare, sofer_publish, sofer_publish_confirm, sofer_codebook, sofer_codebook_all, sofer_profile, sofer_profile_all, sofer_render, sofer_render_all, sofer_scan_dry_run, sofer_scan_apply, sofer_init, sofer_auth_status`. Every param `Annotated[Field(description)]` non-empty; `target` `Literal` single-value; `output` split `output_file`/`output_dir`; `all_files` removed; `no_checks→run_checks`; all have `annotations`+typed `output_schema`. `sofer_init` additionally `cwd: str | None=None` per INIT-02.

(Previously: 14 callables without `cwd`; containment for path args only.)

#### Scenario: schemas constrained
- GIVEN `tools/list`
- WHEN inspected
- THEN 14 tools, `target` const/enum, no `all_files`/`no_checks`/`output`

#### Scenario: sofer_init cwd schema
- GIVEN `tools/list` `sofer_init`
- WHEN inspected
- THEN `cwd` optional `str`, default `None`, `C:/Windows` → `PathOutsideRootError`
