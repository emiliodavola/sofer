# Spec delta: fix-scan-parity-mcp

> Delta for requirement `mcp-server`. Block format follows the repo's archived
> change specs (full requirement blocks, scenarios preserved/added).

## MODIFIED Requirements

### Requirement: Scan non-interactivity (MSP-R06)

> Added by change `sofer-mcp-server` (archived 2026-08-28); modified by
> `fix-scan-parity-mcp`.

`sofer_scan_apply` SHALL never prompt — the explicit call IS the confirmation. It SHALL chain the pure scanner functions `discover_files → check_flatten_collisions → merge_entries → copy_files → write_toml`, honoring `force`. When `move_loose` is `True`, the chain SHALL be `discover_files(exclude raw/) → check_raw_collisions → move_to_raw → discover_files → check_flatten_collisions → merge_entries → copy_files → write_toml`, still honoring `force` and never prompting (SCN phase order: MOVE before COPY).

#### Scenario: Apply never blocks on input

- GIVEN a TOML directory with unregistered files and stdin closed
- WHEN `sofer_scan_apply` runs
- THEN files SHALL be copied and the TOML updated
- AND the call SHALL never block on `input()`

#### Scenario: Apply with move_loose chains the MOVE phase (unchanged scenarios preserved)

- GIVEN a TOML directory with loose supported files outside `raw/`/`cache/`/`EXCLUSIONS`
- WHEN `sofer_scan_apply` runs with `move_loose=True`
- THEN each loose file SHALL be MOVED into `raw/<relative_to(base_dir)>`
- AND the same files SHALL be copied into `cache/` (flattened) and registered
- AND the loose originals SHALL no longer exist at their old paths

## NEW Requirements

### Requirement: Scan extensions filter (MSP-R14)

> Added by change `fix-scan-parity-mcp` (closes #154).

`sofer_scan_dry_run` and `sofer_scan_apply` SHALL accept an `extensions: list[str] | None = None` argument. When omitted, all supported formats SHALL be scanned (current behavior). When supplied, only files whose suffix matches one of the given extensions SHALL be discovered, moved, and copied. Suffixes SHALL be accepted with or without a leading dot, case-insensitively; any suffix not in `SUPPORTED_FORMATS` SHALL be refused with a clear error before any mutation. The filter SHALL apply to BOTH phases when `move_loose=True`.

#### Scenario: Filter restricts discovery

- GIVEN a scan tool call with `extensions=["csv"]` and a directory containing both `.csv` and `.xlsx` loose files
- WHEN the tool runs
- THEN only the `.csv` files SHALL be discovered/registered/copied
- AND the `.xlsx` files SHALL be untouched

#### Scenario: Unsorted suffix forms accepted

- GIVEN `extensions=["csv", ".parquet"]`
- WHEN the tool runs
- THEN both `csv` and `parquet` files SHALL be included

#### Scenario: Unsupported extension refused

- GIVEN `extensions=["txt"]`
- WHEN the tool runs
- THEN an `ok:false` refusal SHALL be returned before any mutation
- AND the error SHALL name the unsupported suffix and the supported set

### Requirement: Scan Phase-1 move opt-in (MSP-R15)

> Added by change `fix-scan-parity-mcp` (closes #152).

`sofer_scan_dry_run` and `sofer_scan_apply` SHALL accept a `move_loose: bool = False` argument. It is an explicit opt-in: `False` SHALL keep the cache-only behavior (never a silent move), and `True` shall run the Phase-1 MOVE (see MST-R06) before the cache copy. Collisions against existing `raw/` destinations SHALL abort atomically before any move (`registered: 0`, TOML untouched). `sofer_scan_apply` SHALL report `moved: int` in a successful envelope (declared in `output_schema`). `sofer_scan_dry_run` with `move_loose=True` SHALL preview the moves with no mutation; without it, the dry-run SHALL report the loose file count and name the `move_loose=True` opt-in as a hint.

#### Scenario: Dry-run previews moves without mutation

- GIVEN a loose file outside `raw/`/`cache/`
- WHEN `sofer_scan_dry_run` runs with `move_loose=True`
- THEN the output SHALL show `-> raw/<rel>`
- AND no file SHALL be moved, `raw/` SHALL NOT be scaffolded, and the TOML SHALL be untouched

#### Scenario: Collision aborts before any move

- GIVEN a loose file whose `raw/` destination already exists
- WHEN `sofer_scan_apply` runs with `move_loose=True`
- THEN an `ok:false` refusal SHALL be returned naming the collision
- AND the loose file SHALL remain at its original path and the TOML SHALL be untouched

#### Scenario: Default leaves files loose

- GIVEN loose supported files and `move_loose` omitted
- WHEN `sofer_scan_apply` runs
- THEN the loose files SHALL remain in place (no `raw/` writes)
- AND the cache copy/registration SHALL behave as before