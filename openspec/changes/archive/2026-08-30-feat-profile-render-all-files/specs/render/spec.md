# Delta for render

## ADDED Requirements

### Requirement: Batch render via --all-files (RND-04)

When `--all-files` is set the system MUST iterate `[[file]]` entries via `DatasetConfig.from_toml`; for each entry it MUST resolve its `metadata.yaml` and write one `README.md` namespaced by `rel_stem` under `render_dir` as `<write_root>/renders/<rel_stem>.README.md` (or `.md` suffix per PurePath logic). `rel_stem` derivation, collision map, partial-write-then-ValueError, Option B `--output` anchoring, and `[[file]]` validation MUST mirror PRF-05 with `render_dir` in place of `profile_dir`.

#### Scenario: Batch N-renders

- GIVEN `dataset.toml` with two `[[file]]` entries each with `metadata.yaml`
- WHEN `sofer render dataset.toml --all-files` executes
- THEN two `renders/<rel_stem>.README.md` SHALL exist

#### Scenario: Collision detection

- GIVEN two entries resolving to same `renders/x.README.md`
- WHEN batch executes
- THEN non-colliding SHALL be written and `ValueError` SHALL name colliding sources

#### Scenario: Custom --output

- GIVEN `--output /tmp/out`
- WHEN batch executes
- THEN outputs SHALL be under `/tmp/out/renders/` with no `cache/` mutation

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
- THEN request SHALL be rejected

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
