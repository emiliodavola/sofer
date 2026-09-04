# Delta for mcp-server

## ADDED Requirements

### Requirement: Dataset identity validation before any write (INIT-05)

`sofer_init` SHALL validate identity BEFORE any write: `name` and `user` SHALL both be mandatory, non-empty, and safe single components — no `/`, no `\`, no drive/UNC path (`ntpath.splitdrive`), no `.`/`..` components, no quotes, no newlines/control characters, no leading/trailing whitespace. `user` SHALL match `^[\w\-]+$` and SHALL NOT be a placeholder (`YOUR_USER` or any normalized `model._PLACEHOLDERS` value). Any violation SHALL refuse the call with an actionable error BEFORE creating `<name>.toml` or `raw/`; the generated TOML SHALL NEVER contain `YOUR_USER`. CLI parity is specified in CLI-R07.

(Previously: only empty `name` was refused; a missing/blank `user` silently emitted the `YOUR_USER` placeholder.)

#### Scenario: Valid identity accepted

- GIVEN `sofer_init(name="test", user="emiliodavola", cwd="Desktop/test")`
- WHEN the call executes
- THEN `ok:true` and `Desktop/test/test.toml` SHALL contain `repo_id = "emiliodavola/test"`

#### Scenario: Missing or blank identity refused before write

- GIVEN `name` missing/blank or `user` missing/blank (`None`, `""`, `"   "`)
- WHEN `sofer_init` executes
- THEN a refusal SHALL name the missing value and NO TOML and NO `raw/` SHALL be created

#### Scenario: Placeholder user banned pre-write

- GIVEN `user="YOUR_USER"` (or any normalized `_PLACEHOLDERS` value)
- WHEN `sofer_init` executes
- THEN the call SHALL be refused before any write and the generated TOML SHALL NOT contain `YOUR_USER`

#### Scenario: Unsafe or injection-shaped name rejected

- GIVEN `name` containing a separator (`a/b`, `a\b`), drive (`C:/evil`), traversal (`a/../b`), quotes, newline, or control character
- WHEN `sofer_init` executes
- THEN the call SHALL be refused before any write

#### Scenario: Non-conforming user rejected

- GIVEN `user` not matching `^[\w\-]+$` (e.g. `user.name`, `user name`)
- WHEN `sofer_init` executes
- THEN the call SHALL be refused before any write

## MODIFIED Requirements

### Requirement: sofer_init cwd containment (INIT-02)

`sofer_init` SHALL expose `cwd: str | None = None`. Resolution SHALL be fail-closed strict-descendant: `cwd=None` SHALL select the live process CWD only when it is a STRICT descendant of the server root (`live != root.resolve() AND live.is_relative_to(root.resolve())`); otherwise SHALL refuse with an actionable `IdentityResolutionError` naming the required `cwd` argument — the server root SHALL NEVER be silently selected. `cwd=str` SHALL be resolved via `_contained_path(cwd, root=_SERVER_ROOT, must_exist=False)`, MUST satisfy `is_relative_to(_SERVER_ROOT.resolve())`, per-call `effective_root`, MUST NOT mutate `_SERVER_ROOT`. Escape → `PathOutsideRootError`.

(Previously: `cwd=None` back-compat auto-selected `_get_root()`, silently picking the parent root when live CWD equaled or escaped the root.)

#### Scenario: cwd omitted with live CWD strictly inside root

- GIVEN `build_server(root=Desktop)`, live CWD `Desktop/test` (a real directory)
- WHEN `sofer_init(name="test", cwd=None)`
- THEN effective root SHALL be `Desktop/test` and `Desktop/test/test.toml` SHALL be written

#### Scenario: cwd omitted with live CWD equal to root fails closed

- GIVEN `build_server(root=Desktop)`, live CWD `Desktop` (root == dataset root)
- WHEN `sofer_init(name="test", cwd=None)`
- THEN `IdentityResolutionError` SHALL name the required `cwd` argument and NO file SHALL be written

#### Scenario: cwd omitted with live CWD outside root fails closed

- GIVEN `build_server(root=Desktop)`, live CWD `C:/elsewhere`
- WHEN `sofer_init(name="test", cwd=None)`
- THEN `IdentityResolutionError` SHALL name the required `cwd` argument and NO file SHALL be written

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

### Requirement: Anchored writes and canonical identity reporting (INIT-03)

`sofer_init` MUST create `<name>.toml` and `raw/` only inside `effective_root` (INIT-02). No parent writes. The success envelope SHALL report the canonical identity: `config_path` (absolute `effective_root/<name>.toml`) and `dataset_root` (absolute resolved `effective_root`) — both SHALL appear in the envelope AND in the tool's `output_schema` (INIT-03, MSP-R03).

(Previously: anchored writes only; the envelope reported no identity fields.)

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

#### Scenario: canonical identity reported

- GIVEN `sofer_init(cwd="Desktop/test", name="test")` succeeds
- WHEN the envelope is inspected
- THEN it SHALL contain absolute `config_path` `Desktop/test/test.toml` and absolute resolved `dataset_root` `Desktop/test`

### Requirement: Tool roster and schema contract (MSP-R03)

Server SHALL expose 14 callables: `sofer_validate, sofer_prepare, sofer_publish, sofer_publish_confirm, sofer_codebook, sofer_codebook_all, sofer_profile, sofer_profile_all, sofer_render, sofer_render_all, sofer_scan_dry_run, sofer_scan_apply, sofer_init, sofer_auth_status`. Every param SHALL be `Annotated[Field(description)]` non-empty (10.1); `target` SHALL be `Literal["local"]`/`Literal["hf"]` single-value (const or enum) (10.5); `output` SHALL split to `output_file` vs `output_dir` (10.7); `all_files` removed — batch via `*_all` (10.6); `no_checks` → `run_checks:bool=true` (10.9); every tool SHALL have `annotations` and typed `output_schema`. `sofer_init` additionally exposes `cwd: str | None = None` per INIT-02 and its `output_schema` SHALL declare `config_path`/`dataset_root` (absolute strings) per INIT-03.

(Previously: `sofer_init` schema carried no identity fields; 11 callables, polymorphic profile/render, free-string target, dual-typed output, bare params, generic schema; then 14 callables without `cwd`.)

#### Scenario: Constrained schemas

- GIVEN `tools/list`
- WHEN inspected
- THEN count SHALL be 14, `target` SHALL have `const` or `enum` single value, no tool SHALL expose `all_files`/`no_checks`/`output` (only `output_file`/`output_dir`/`run_checks`), and every `properties[*].description` SHALL be non-empty

#### Scenario: Annotations and output_schema typed

- GIVEN `tools/list`
- WHEN inspected
- THEN no `annotations` SHALL be null and each `output_schema` SHALL declare `ok:bool, exit_code:int, output:str` plus specific fields

#### Scenario: sofer_init cwd schema

- GIVEN `tools/list` `sofer_init`
- WHEN inspected
- THEN `cwd` SHALL be optional `str`, default `None`, and `C:/Windows` SHALL raise `PathOutsideRootError`

#### Scenario: sofer_init identity fields in schema

- GIVEN `tools/list` `sofer_init` `output_schema`
- WHEN inspected
- THEN `config_path` and `dataset_root` SHALL be declared as string properties and SHALL appear in the call envelope

### Requirement: Config contract (MSP-R10)

Every dataset tool SHALL take `config: str` (TOML path) as its first parameter; `DatasetConfig.from_toml` SHALL accept an optional `discovery_root: Path | None = None` and SHALL pass `stop_at=discovery_root` into `config.reload` — when provided, tool-config discovery SHALL be bounded (walk-up stops at `discovery_root`); the MCP adapter SHALL ALWAYS supply `discovery_root=_get_root()` so discovery never escapes the server root, and the post-hoc `_bound_discovery` re-bind SHALL be retired. The CLI SHALL pass no bound (unbounded, behavior unchanged). Codebook and scan tools SHALL NOT silently apply `default_config_name` — agents pass explicit paths. Relative paths SHALL resolve against the client cwd (stdio server inherits it). Relative `output_dir`/`output_file` overrides SHALL anchor to the config's `config_path.parent` — never the server root or process cwd. Codebook tools SHALL inject post-reload `config.CSV_DELIMITER`/`config.CSV_ENCODING` — never the hardcoded `";"`/`"utf-8-sig"` debt in `codebook.generate` (rule-3 fix).

Every dataset tool SHALL self-anchor config state per call to avoid cross-call module-state pollution: scan tools SHALL reload from the config's directory before reading output directories; `sofer_codebook(path)`, `sofer_profile(dataset)`, and `sofer_render(package)` SHALL anchor on their input's directory. `sofer_codebook_all` SHALL use `cfg.csv_delimiter`/`cfg.csv_encoding` from the dataset's `[meta]` (the authoritative source), not the process-global `config.CSV_DELIMITER`. `sofer_prepare` SHALL pass `run_checks=not no_checks` to match CLI parity.

(Previously: `from_toml` had no `discovery_root`; MCP compensated with the post-hoc `_bound_discovery` re-bind; output overrides anchored to the server root.)

#### Scenario: Tool config resolves per dataset directory

- GIVEN a TOML under a tree with `[tool.sofer]` overrides
- WHEN any dataset tool calls `DatasetConfig.from_toml(config)`
- THEN `config.reload(toml_dir)` SHALL rebind module constants before the domain function runs

#### Scenario: Discovery bounded at server root

- GIVEN `[tool.sofer]` overrides in a `pyproject.toml` ABOVE the server root and a dataset TOML inside it
- WHEN `sofer_prepare(config)` runs via MCP
- THEN the above-root overrides SHALL NOT apply (walk-up stops at the server root)

#### Scenario: Relative output override anchors to config dir

- GIVEN dataset at `<root>/proj/dataset.toml` and `sofer_prepare(config, output_dir="build")`
- WHEN the call runs
- THEN the package SHALL be written under `<root>/proj/build`, not `<root>/build`

#### Scenario: Codebook honors configured delimiter/encoding

- GIVEN `csv_delimiter = ","` in `[tool.sofer]`
- WHEN `sofer_codebook` runs on a CSV
- THEN the codebook SHALL reflect the configured delimiter, not the hardcoded default

#### Scenario: No silent default config name

- GIVEN a codebook or scan tool call without a config argument
- THEN the call SHALL fail on the missing required `config` parameter
- AND `default_config_name` SHALL never be applied implicitly