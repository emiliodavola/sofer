# Delta for profile

## ADDED Requirements

### Requirement: Batch profile via --all-files (PRF-05)

When `--all-files` is set the system MUST iterate `[[file]]` entries via `DatasetConfig.from_toml`; for each entry it MUST write one `metadata.yaml` namespaced by `rel_stem` under `profile_dir` as `<write_root>/profiles/<rel_stem>.metadata.yaml`. `rel_stem` MUST be `local.relative_to(data_dir)` when inside `data_dir = base_dir / config.OUTPUT_DIR`, otherwise `local.relative_to(base_dir)`, with output computed as `(profile_dir / rel_stem).with_suffix(PurePath.suffixes replacement)` (only last suffix → `.metadata.yaml`). The system MUST pre-compute the collision map `output → [sources]` before any write, MUST write non-colliding outputs first, then MUST raise `ValueError` naming every colliding source and MUST NOT write colliding outputs nor a root index. `--output` anchoring MUST follow Option B: relative dirs anchor to `cfg._base_dir`, writes go to `<output>/profiles/`, never mutating `cache/`. TOML without `[[file]]` MUST fail fast.

#### Scenario: Batch N-files

- GIVEN `dataset.toml` with `[[file]]` for `raw/a.csv` and `raw/b.csv`
- WHEN `sofer profile dataset.toml --all-files` executes
- THEN `<write_root>/profiles/a.metadata.yaml` and `b.metadata.yaml` SHALL exist

#### Scenario: Nested path preserved via rel_stem

- GIVEN `[[file]]` for `raw/Labels/etiquetas_a.csv`
- WHEN batch executes
- THEN `profiles/Labels/etiquetas_a.metadata.yaml` SHALL be generated

#### Scenario: Same-stem collision errors after partial write

- GIVEN `raw/x.csv` and `raw/x.parquet` mapping to `profiles/x.metadata.yaml`
- WHEN batch executes
- THEN non-colliding outputs SHALL be written
- AND `ValueError` SHALL name both sources and colliding path

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

### Requirement: Single-file force guard (PRF-06)

Single-file `sofer profile <dataset>` MUST check `dest.exists()` before write; without `--force` it MUST raise `FileExistsError` with message containing `use --force to overwrite` and the destination path; with `--force` it MUST overwrite.

#### Scenario: Guard without --force

- GIVEN `out/profiles/a.metadata.yaml` exists
- WHEN `sofer profile raw/a.csv --output out` without `--force` runs
- THEN `FileExistsError` SHALL be raised and file SHALL be unchanged

#### Scenario: Overwrite with --force

- GIVEN same existing dest
- WHEN `sofer profile raw/a.csv --output out --force` runs
- THEN file SHALL be overwritten and exit 0
