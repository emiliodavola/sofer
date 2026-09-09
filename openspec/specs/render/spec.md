# Render Specification

## Purpose

The `render` command turns a `metadata.yaml` document into a human-readable
`README.md`. It renders strictly from the metadata document and never presents
inference as fact.

## Requirements

### Requirement: render command surface (RND-01)

The system SHALL register a `sofer render <package>` subcommand accepting a
package path as its positional argument. The path MAY be a directory
(containing a `metadata.yaml`) or a direct path to a `metadata.yaml` file. The
handler SHALL resolve the argument as follows: if the path is a directory, read
`<dir>/metadata.yaml`; if it is a file, read that file directly; if neither
resolves to a readable `metadata.yaml`, fail with a clear, non-traceback error
and a non-zero exit code.

#### Scenario: render accepts a directory

- GIVEN `sofer render ./build/` where `./build/metadata.yaml` exists
- WHEN the command executes
- THEN the handler SHALL read `./build/metadata.yaml`

#### Scenario: render accepts a direct metadata.yaml path

- GIVEN `sofer render ./build/metadata.yaml`
- WHEN the command executes
- THEN the handler SHALL read `./build/metadata.yaml` directly

#### Scenario: missing metadata.yaml errors cleanly

- GIVEN `sofer render ./` where `./metadata.yaml` does not exist
- WHEN the command executes
- THEN a clear error message SHALL be printed
- AND the exit code SHALL be non-zero

### Requirement: README rendered from metadata (RND-02)

The `render` command SHALL read `metadata.yaml` and generate `README.md` from its
contents — never from a hand-written template that ignores the metadata.

#### Scenario: render produces README from metadata

- GIVEN a valid `metadata.yaml`
- WHEN `sofer render` executes
- THEN a `README.md` SHALL be written
- AND its content SHALL reflect the metadata document's fields

### Requirement: Inference states rendered distinctly (RND-03)

The `render` command SHALL render inference states distinctly: `confirmed` as a
plain label, `inferred` as `"<type> (inferred, NN%)"` with the confidence
percentage, and `unknown` as `"unknown"`. The percentage SHALL be computed as
`round(confidence × 100)` — rounded to the nearest integer percent using
Python's `round()` (round-half-to-even), never truncated (no `int()`/floor),
so e.g. `confidence = 0.78` renders as `78%`.

#### Scenario: Confirmed renders plain

- GIVEN a column with semantic status `confirmed`
- WHEN README is rendered
- THEN the column's type SHALL appear as a plain label with no qualifier

#### Scenario: Inferred renders with confidence

- GIVEN a column with semantic status `inferred` and `confidence = 0.78`
- WHEN README is rendered
- THEN the column's type SHALL render as `email (inferred, 78%)`

#### Scenario: Unknown renders as unknown

- GIVEN a column with no semantic type (status `unknown`)
- WHEN README is rendered
- THEN the field SHALL render as `unknown` — not blank and not fabricated

---

### Requirement: Batch render via --all-files (RND-04)

When `--all-files` is set the system MUST iterate `[[file]]` entries via `DatasetConfig.from_toml`; for each entry it MUST resolve its `metadata.yaml` location and `rel_stem` exactly as PRF-05 (`base_dir.resolve()`, `data_dir`, `relative_to`, PurePath suffixes). For non-`.xlsx` entries and single-sheet `.xlsx` it MUST write one `README.md` at `(render_dir / rel_stem).with_suffix(.README.md)`, namespaced under `render_dir` as `<write_root>/renders/<rel_stem>.README.md` (or `.md` suffix per PurePath logic). For `.xlsx` with N>1 sheets it MUST expand to N renders at `renders/<rel>/<stem>__<sanitized>.README.md` using the identical `sanitize_sheet_name` + `seen` dedup `_{n}` and `__<sanitized>` insertion as profile (parity with `codebook`/`prepare` `stem__sheet`). The collision map MUST be built from sheet-expanded outputs normalized via `re.sub(r"__+", "_", str(path))`, MUST write non-colliding READMEs first (sourcing each `metadata.yaml` from `profiles_dir` mirroring `write_root`), then MUST raise `ValueError` naming every colliding source as `<path>::<sheet>` and MUST NOT write colliding outputs. Option B `--output` anchoring, `profile_dir`/`render_dir` containment, and `[[file]]` validation MUST mirror PRF-05 with `render_dir` in place of `profile_dir`. Entries whose `metadata.yaml` is missing MUST be skipped with a warning and no README.

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

#### Scenario: Missing metadata.yaml skipped

- GIVEN `[[file]]` for `raw/a.csv` where `profiles/a.metadata.yaml` does not exist
- WHEN batch render runs
- THEN a warning SHALL be emitted and no README SHALL be written for that entry

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

### Requirement: Single-file force guard (RND-05)

Single-file `sofer render <package>` MUST raise `FileExistsError` containing `use --force to overwrite` when dest exists without `--force`; with `--force` it MUST overwrite.

#### Scenario: Guard without --force

- GIVEN `out/renders/a.README.md` exists
- WHEN `sofer render ./build/a` without `--force` runs
- THEN `FileExistsError` SHALL be raised

#### Scenario: Overwrite with --force

- GIVEN same dest exists
- WHEN `sofer render ./build/a --force` runs
- THEN file SHALL be overwritten
