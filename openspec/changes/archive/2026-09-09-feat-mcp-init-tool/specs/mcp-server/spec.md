# Delta for mcp-server

## ADDED Requirements

### Requirement: MCP init tool sofer_init — dataset bootstrap (INIT-01)

The system MUST expose `sofer_init` creating `<name>.toml` from `_INIT_TEMPLATE` and scaffolding `raw/`. It SHALL accept `name: str` (required), `move_existing=false`, `dry_run=false`, `force=false`. Docstring SHALL state side effects/network verbatim with UNTRUSTED note. Execution SHALL be serialized and capture stdout/stderr into `output`. Results SHALL return `{ok, exit_code, output, config_errors}`; hard failures SHALL raise typed errors.

#### Scenario: Creates TOML and raw/

- GIVEN no `<name>.toml` under the server root
- WHEN `sofer_init(name="my-ds")` is called
- THEN `<root>/my-ds.toml` SHALL equal `_INIT_TEMPLATE.format(name="my-ds")` and `<root>/raw/` SHALL exist with `{ok:true, exit_code:0}`

#### Scenario: Idempotency when TOML exists

- GIVEN `<root>/my-ds.toml` already exists
- WHEN `sofer_init(name="my-ds", force=false)` is called
- THEN it SHALL return `{ok:false, exit_code:1}` and NOT overwrite the file

#### Scenario: Force allows overwrite

- GIVEN `<root>/my-ds.toml` already exists
- WHEN `sofer_init(name="my-ds", force=true)` is called
- THEN the TOML SHALL be overwritten and return `{ok:true, exit_code:0}`

#### Scenario: dry_run does not mutate raw/ or move files

- GIVEN depth-1 supported files exist and `raw/` is absent
- WHEN `sofer_init(name="my-ds", move_existing=true, dry_run=true)` is called
- THEN no `raw/` SHALL be created, no candidate moved, and `output` SHALL list planned `a.csv -> raw/a.csv`

#### Scenario: move_existing reuses check_flatten_collisions

- GIVEN candidates plus existing `raw/` content would flatten-collide
- WHEN `sofer_init(name="my-ds", move_existing=true)` is called
- THEN it SHALL return `{ok:false, exit_code:1}` with no file moved

#### Scenario: move_existing preserves tree on success

- GIVEN candidates `a.csv` without collision
- WHEN `sofer_init(name="my-ds", move_existing=true, dry_run=false)` is called
- THEN each candidate SHALL move to `raw/<relative_to(root)>` preserving tree and TOML SHALL be created

#### Scenario: Containment CF-2 — traversal rejected

- GIVEN `name` is `"../evil"` or `"/abs/evil"` or symlink escape
- WHEN `sofer_init(name="../evil")` is called
- THEN it SHALL raise `PathOutsideRootError` or return `{ok:false, config_errors}` and no file outside `<root>` SHALL be touched

#### Scenario: Minimal TOML validation and errors

- GIVEN a successful `sofer_init(name="my-ds")`
- WHEN the TOML is loaded via `DatasetConfig.from_toml`
- THEN it SHALL parse and `cfg.name` SHALL equal `"my-ds"`; empty `name` SHALL return `{ok:false, config_errors}`

## MODIFIED Requirements

### Requirement: Tool roster and schema contract (MSP-R03)

> Added by change `sofer-mcp-server` (archived 2026-08-28).

The server SHALL expose 11 callables / 9 logical tools (publish, codebook each 1 logical/2 callables; scan 2 logical — no `input()` on stdio; init 1/1). Every callable SHALL mirror CLI flags as JSON-Schema and appear in `tools/list`.

(Previously: 10 callables / 8 logical tools without sofer_init)

| Callable | Parameters | Side effect | Network |
|---|---|---|---|
| sofer_validate | config | ro report | none |
| sofer_prepare | config, output?, all_files?, no_checks?, force?, verify? | writes | none |
| sofer_publish | config, target?, output?, force?, keep_csv?, dry_run? | plan/copy | none |
| sofer_publish_confirm | config, target?, output?, force?, keep_csv?, ack_risk?, ack_conf?, phrase? | HF upload | HF |
| sofer_codebook | path, output?, max_sample? | md | none |
| sofer_codebook_all | config, output? | codebooks | none |
| sofer_profile | dataset, output? | metadata | none |
| sofer_render | package, output? | README | none |
| sofer_scan_dry_run | config | discovery | none |
| sofer_scan_apply | config, force? | copy+TOML | none |
| sofer_init | name!, move_existing?, dry_run?, force? | toml+raw/preview | none |

#### Scenario: tools/list shows correct schemas

- GIVEN server running
- WHEN `tools/list` is called
- THEN exactly 11 callables SHALL be listed matching the table

#### Scenario: Validate is read-only and structured

- GIVEN a config path
- WHEN `sofer_validate` is called
- THEN result SHALL carry `{passed, errors, warnings, quality_failures, quality_warnings, ran_checks}` and no file modified nor network used

#### Scenario: Prepare overwrite protection and verify skip

- GIVEN existing artifacts in output dir
- WHEN `sofer_prepare` with `force=false` runs
- THEN it SHALL return `{ok:false, exit_code:1}`; with `force=true` SHALL regenerate; with `verify` and no `datasets` SHALL skip non-blockingly
