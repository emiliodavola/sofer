# Delta for publish

## ADDED Requirements

### Requirement: Package artifact manifest with explicit publishable/intermediate boundary (PUB-12)

> Added by change `fix-package-artifact-manifest`.

The publish flow SHALL operate on one machine-readable package manifest
listing every artifact of the selected build profile — `source` (the real
config path), `artifact_type`, `path`, and `status` — with artifacts
classified as **publishable** (parquet incl. multi-sheet expansion, csv when
keep_csv, README, LICENSE, codebook.md, codebooks/**) or **intermediate**
(profiles, renders, per-sheet intermediates, schema/card inputs). `prepare`
writes the manifest into the output dir; publish dry-run and confirm SHALL
read the SAME manifest to plan and to enforce contents (no divergence).

Missing **required** artifacts SHALL block confirm with a stable `error_code`
and a concrete recovery (re-run prepare); optional artifacts absent SHALL be
marked `optional` and SHALL NOT emit the "missing artifact" warning (no
silent omission, no false warning). Staleness SHALL key on the real config
path (custom TOML names and multi-sheet Excel outputs included). Local
delivery SHALL honor `force`. Remote inspection failures SHALL fail closed
(unchanged PUB-05).

(Previously: the package boundary was implicit — plan_remote_files derived
the dry-run set and codebook_remotes were collected from the output dir,
with a warning when codebooks were absent that could be a false positive for
optional artifacts.)

#### Scenario: Manifest lists exact publishable set for single-sheet source

- GIVEN a single-CSV dataset and a fresh prepare
- THEN `output_dir/manifest.json` SHALL list each parquet, README.md, LICENSE, and codebook.md as `staged`
- AND profiles/renders present in the tree SHALL be `intermediate` (never publishable)

#### Scenario: Multi-sheet Excel expansion is manifest-correct

- GIVEN an XLSX source converted to `stem__sheet.parquet` sheets
- THEN every sheet parquet SHALL appear in the manifest with its per-sheet path

#### Scenario: Missing required artifact blocks confirm with recovery

- GIVEN a manifest missing a required codebook that the profile promises
- WHEN confirm runs
- THEN it SHALL fail with a stable `error_code` and a `recovery` naming re-run prepare

#### Scenario: Optional absent artifact does not warn

- GIVEN a profile whose renders are optional and absent
- WHEN dry-run/confirm run
- THEN no "missing" warning SHALL be emitted for the optional artifact and its manifest entry SHALL read `optional`

#### Scenario: Dry-run and confirm share one manifest

- GIVEN a prepared package
- WHEN dry-run plans and confirm uploads
- THEN both SHALL consume the same `manifest.json` entries (structure, not re-derived sets)

#### Scenario: Custom config TOML name invalidates the package

- GIVEN a dataset configured via `custom-name.toml`
- WHEN the TOML is modified after the newest parquet
- THEN the package SHALL be treated as stale

#### Scenario: Local delivery overwrite protection honors force

- GIVEN a local target with an existing conflicting file
- WHEN `force=false`
- THEN the delivery SHALL refuse to overwrite
- AND with `force=true` it SHALL overwrite