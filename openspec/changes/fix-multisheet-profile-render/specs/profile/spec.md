# Delta for profile

## MODIFIED Requirements

### Requirement: Batch profile via --all-files (PRF-05)

When `--all-files` is set the system MUST iterate `[[file]]` via `DatasetConfig.from_toml`; for each entry it MUST derive `rel_stem` as `local.relative_to(data_dir)` if inside `data_dir=base_dir/config.OUTPUT_DIR` else `relative_to(base_dir)` (`base_dir` resolved). For non-`.xlsx` and single-sheet `.xlsx` it MUST write one `metadata.yaml` at `(profile_dir/rel_stem).with_suffix(PurePath.suffixes last→`.metadata.yaml`)`. For `.xlsx` N>1 it MUST read all sheets via `_read_xlsx_sheets`, sanitize each via `sanitize_sheet_name` (lower→NFKD→ascii→space→_→`[^a-z0-9_-]`→_→`__+`→_→strip, empty→`sheet`) with `seen` `_{n}`, write N files `profiles/<rel>/<stem>__<sanitized>.metadata.yaml`. MUST pre-compute expanded map `re.sub(r"__+","_",path) → [sources]` so `a__ventas`≈`a_ventas`; write non-colliding first, then MUST raise `ValueError` naming colliding sources as `<path>::<sheet>` and MUST NOT write them. `--output` Option B (relative→`cfg._base_dir`, writes `<output>/profiles/`, no `cache/` mutation), containment via `_validate_output_targets`, and `[[file]]` fail-fast MUST hold.

(Previously: single output per TOML entry; `.xlsx` emitted only `next(iter(sheets))`; collision ignored sheet suffixes.)

#### Scenario: Batch N-files

- GIVEN `dataset.toml` with `[[file]]` for `raw/a.csv` and `raw/b.csv`
- WHEN `sofer profile dataset.toml --all-files` executes
- THEN `<write_root>/profiles/a.metadata.yaml` and `b.metadata.yaml` SHALL exist

#### Scenario: Nested path preserved via rel_stem

- GIVEN `[[file]]` for `raw/Labels/etiquetas_a.csv`
- WHEN batch executes
- THEN `profiles/Labels/etiquetas_a.metadata.yaml` SHALL be generated

#### Scenario: Multisheet workbook 2 sheets yields 2 profiles

- GIVEN `report.xlsx` with sheets `Sales` (id,amount) and `Inventory` (sku,qty) under `raw/`
- WHEN `sofer profile dataset.toml --all-files` executes
- THEN `profiles/report__sales.metadata.yaml` and `profiles/report__inventory.metadata.yaml` SHALL exist
- AND each file's schema SHALL reflect only that sheet's headers and row counts

#### Scenario: Single-sheet xlsx stays suffix-less

- GIVEN an `.xlsx` with 1 sheet `Data`
- WHEN batch or `generate_all_profiles` processes it
- THEN exactly one file `profiles/<stem>.metadata.yaml` SHALL be written
- AND the file SHALL be byte-identical to the pre-change single-sheet output

#### Scenario: sanitize_sheet_name applied

- GIVEN sheets named `DATA GOT Año` and `Ventas 2024!`
- WHEN sanitized for the stem
- THEN results SHALL be `data_got_ano` and `ventas_2024`
- AND empty/whitespace-only names SHALL fallback to `sheet`

#### Scenario: Dedup via seen _{n}

- GIVEN an `.xlsx` with sheets `Ventas` and `VENTAS` (both → `ventas`)
- WHEN profiles are emitted
- THEN outputs SHALL be `__ventas.metadata.yaml` and `__ventas_2.metadata.yaml`
- AND a third duplicate SHALL be `__ventas_3.metadata.yaml`

#### Scenario: Sheet-aware collision via normalized __+→_

- GIVEN `data/a__ventas.xlsx` sheet `Ventas` (→ `profiles/a__ventas.metadata.yaml`) and `data/a_ventas.csv` (→ `profiles/a_ventas.metadata.yaml` normalized `__+`→`_`)
- WHEN `--all-files` expands sheets and builds the collision map
- THEN the normalized key SHALL collide
- AND system SHALL raise `ValueError` naming both sources with `::Ventas` suffix and write neither

#### Scenario: Same-stem collision errors after partial write

- GIVEN `raw/x.csv` and `raw/x.parquet` mapping to `profiles/x.metadata.yaml` plus `raw/ok.csv`
- WHEN batch executes
- THEN `profiles/ok.metadata.yaml` SHALL be written
- AND `ValueError` SHALL name both colliding sources and colliding path

#### Scenario: Custom --output anchoring (Option B)

- GIVEN `sofer profile dataset.toml --all-files --output /tmp/out`
- WHEN batch executes
- THEN outputs SHALL be under `/tmp/out/profiles/` and `cache/` SHALL be untouched

#### Scenario: Custom --output relative anchored to base_dir

- GIVEN `dataset.toml` in `/proj/` and `--output rel/out`
- WHEN batch executes
- THEN writes SHALL go to `/proj/rel/out/profiles/` not CWD

#### Scenario: Config override to docs/profiles

- GIVEN `pyproject.toml` sets `profile_dir = "docs/profiles"`
- WHEN batch executes
- THEN outputs SHALL be under `docs/profiles/<rel_stem>.metadata.yaml`

#### Scenario: TOML without [[file]] fails

- GIVEN TOML with no `[[file]]`
- WHEN `--all-files` executes
- THEN system SHALL fail with non-zero exit and message mentioning `[[file]]`

#### Scenario: MCP containment for profile_dir

- GIVEN MCP `sofer_profile` with `output` escaping server root via `profile_dir`
- WHEN `_validate_output_targets` runs
- THEN request SHALL be rejected without writing
