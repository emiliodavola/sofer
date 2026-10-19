# Delta for prepare

> **Change** `2026-10-19-fix-manifest-authority` · issue **#349** · applies to the
> canonical spec at `openspec/specs/prepare/spec.md` (PRP-11).

---

## MODIFIED Requirements

### Requirement: Prepare writes the package manifest (PRP-11) — Modified 2026-10-19, fix-manifest-authority

`prepare` SHALL write `manifest.json` into the output directory alongside the staged artifacts, one entry per artifact of the selected build profile with `source` (real config path), `artifact_type`, `path`, `status` (`staged` | `expected` | `optional` | `missing`), and `classification` (`publishable` | `intermediate`, see PUB-12). `path` SHALL be relative to the output dir for a package artifact, and relative to the dataset root — or absolute when the intermediate layer lies outside it — for a `profile`/`render` layer (PUB-12 names the same root). The multi-sheet Excel expansion SHALL be reflected (`stem__sheet.parquet` per sheet). A recursive remote SHALL be recorded as ONE directory entry whose `path` ends with `/` (its files are enumerated at copy time, never by the manifest), so no reader counts a tree as one delivered file.

`prepare` SHALL be the **creator** of that manifest, not its only writer: it SHALL write it through the one shared writer (`sofer.manifest.write_manifest`), and every later phase that adds a package artifact SHALL refresh the same file through `sofer.manifest.refresh_manifest` at the end of a successful run (PUB-12). A refresh SHALL rewrite the manifest only in a directory that already owns one, so a phase that wrote to the shared artifact cache cannot invent a package record for a tree `prepare` never prepared.

(Previously: prepare produced artifacts without a machine-readable contents declaration. Then: the entry carried only `source`/`artifact_type`/`path`/`status`, and a recursive remote was recorded as a bare path indistinguishable from a file. Then: prepare was the only writer of the file, so the durable document was a prepare-time snapshot that later phases invalidated without a marker — issue #349.)

#### Scenario: Manifest written by prepare with staged statuses

- GIVEN a successful prepare
- THEN `output_dir/manifest.json` SHALL exist and decode as JSON with the documented stable keys (`source`, `artifact_type`, `path`, `status`, `classification`)
- AND a recursive remote's entry SHALL end its `path` with `/`

#### Scenario: Prepare creates the record that later phases refresh (#349) — Added

- GIVEN a successful prepare
- WHEN a later phase that adds a package artifact completes
- THEN the file `prepare` created SHALL have been rewritten in place, never recreated elsewhere
- AND no phase other than prepare SHALL create a `manifest.json` where none existed
