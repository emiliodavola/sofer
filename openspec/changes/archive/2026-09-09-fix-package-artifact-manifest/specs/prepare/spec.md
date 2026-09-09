# Delta for prepare

## ADDED Requirements

### Requirement: Prepare writes the package manifest (PRP-11)

> Added by change `fix-package-artifact-manifest`.

`prepare` SHALL write `manifest.json` into the output directory alongside
the staged artifacts, one entry per artifact of the selected build profile
with `source` (real config path), `artifact_type`, `path` (relative to the
output dir), and `status` (`staged` | `expected` | `optional` | `missing`).
The multi-sheet Excel expansion SHALL be reflected (`stem__sheet.parquet`
per sheet). The manifest is the single source of truth consumed by publish
dry-run and confirm.

(Previously: prepare produced artifacts without a machine-readable contents
declaration.)

#### Scenario: Manifest written by prepare with staged statuses

- GIVEN a successful prepare
- THEN `output_dir/manifest.json` SHALL exist and decode as JSON with the documented stable keys

#### Scenario: Multi-sheet sources recorded per sheet

- GIVEN an XLSX entry converted to per-sheet parquet
- THEN the manifest SHALL contain one entry per sheet with its exact relative path