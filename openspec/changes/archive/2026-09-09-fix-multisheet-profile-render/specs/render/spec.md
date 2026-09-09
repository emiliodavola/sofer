# Delta for render

## MODIFIED Requirements

### Requirement: Batch render via --all-files (RND-04)

When `--all-files` is set the system MUST iterate `[[file]]` entries via `DatasetConfig.from_toml`; for each entry it MUST resolve its `metadata.yaml` location and `rel_stem` exactly as PRF-05 (base_dir.resolve(), data_dir, relative_to, PurePath suffixes). For non-`.xlsx` entries and single-sheet `.xlsx` it MUST write one `README.md` at `(render_dir / rel_stem).with_suffix(.README.md)`. For `.xlsx` with N>1 sheets it MUST expand to N renders at `renders/<rel>/<stem>__<sanitized>.README.md` using the identical `sanitize_sheet_name` + `seen` dedup `_{n}` and `__<sanitized>` insertion as profile (parity with `codebook`/`prepare` `stem__sheet`). The collision map MUST be built from sheet-expanded outputs normalized via `re.sub(r"__+", "_", str(path))`; MUST write non-colliding READMEs first (sourcing each `metadata.yaml` from `profiles_dir` mirroring `write_root`), then MUST raise `ValueError` naming every colliding source as `<path>::<sheet>` and MUST NOT write colliding outputs. Option B `--output` anchoring, `profile_dir`/`render_dir` containment, and `[[file]]` validation MUST mirror PRF-05 with `render_dir`.

(Previously: single README per TOML entry; `.xlsx` emitted only first-sheet metadata; collision key ignored sheet suffixes.)

#### Scenario: Batch N-renders

- GIVEN `dataset.toml` with two `[[file]]` entries each with `metadata.yaml`
- WHEN `sofer render dataset.toml --all-files` executes
- THEN two `renders/<rel_stem>.README.md` SHALL exist

#### Scenario: Multisheet workbook 2 sheets yields 2 READMEs

- GIVEN `report.xlsx` with sheets `Sales` and `Inventory` already profiled to `profiles/report__sales.metadata.yaml` and `__inventory.metadata.yaml`
- WHEN `sofer render dataset.toml --all-files` executes
- THEN `renders/report__sales.README.md` and `renders/report__inventory.README.md` SHALL exist
- AND each README SHALL render only that sheet's schema and provenance

#### Scenario: Single-sheet xlsx stays suffix-less

- GIVEN an `.xlsx` with 1 sheet already profiled as `profiles/<stem>.metadata.yaml`
- WHEN batch render processes it
- THEN exactly one file `renders/<stem>.README.md` SHALL be written

#### Scenario: sanitize_sheet_name parity

- GIVEN sheets `DATA GOT Año` and `""` → `sheet`
- WHEN sanitized for render stems
- THEN results SHALL equal `sanitize_sheet_name` from `_converters.py` (`data_got_ano`, `sheet`)
- AND dedup SHALL match profile `seen` `_{n}` logic

#### Scenario: Dedup _{n} preserved

- GIVEN `report.xlsx` sheets `Ventas`, `VENTAS`, `ventas`
- WHEN render expands
- THEN stems SHALL be `__ventas`, `__ventas_2`, `__ventas_3` matching profile outputs

#### Scenario: Sheet-aware collision via normalized __+→_

- GIVEN `renders/report__ventas.README.md` from `a__ventas.xlsx::Ventas` and `renders/a_ventas.README.md` from `a_ventas.csv`
- WHEN expanded outputs normalize to same key
- THEN system SHALL treat them as colliding
- AND `ValueError` SHALL name both sources with sheet suffix

#### Scenario: Collision detection partial-write

- GIVEN two entries resolving to same `renders/x.README.md` plus one non-colliding
- WHEN batch executes
- THEN non-colliding SHALL be written and `ValueError` SHALL name colliding sources

#### Scenario: Custom --output

- GIVEN `--output /tmp/out`
- WHEN batch executes
- THEN outputs SHALL be under `/tmp/out/renders/` with no `cache/` mutation
- AND metadata resolved from `/tmp/out/profiles/`

#### Scenario: Config override to docs/renders

- GIVEN `render_dir = "docs/renders"`
- WHEN batch executes
- THEN outputs SHALL be under `docs/renders/<rel_stem>.README.md`

#### Scenario: TOML without [[file]] fails

- GIVEN TOML without `[[file]]`
- WHEN `--all-files` executes
- THEN system SHALL fail non-zero mentioning `[[file]]`

#### Scenario: MCP containment for render_dir

- GIVEN MCP `sofer_render` with escaping `output`
- WHEN validation runs
- THEN request SHALL be rejected without writing

#### Scenario: Missing metadata.yaml skipped

- GIVEN `[[file]]` for `raw/a.csv` where `profiles/a.metadata.yaml` does not exist
- WHEN batch render runs
- THEN a warning SHALL be emitted and no README SHALL be written for that entry
