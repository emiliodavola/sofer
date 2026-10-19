# Delta for publish

> **Change** `2026-10-19-fix-manifest-authority` · issue **#349** · applies to the
> canonical spec at `openspec/specs/publish/spec.md` (PUB-12).

---

## MODIFIED Requirements

### Requirement: Package artifact manifest with explicit publishable/intermediate boundary (PUB-12) — Modified 2026-10-19, fix-manifest-authority

The publish flow SHALL operate on one machine-readable package manifest listing every artifact of the selected build profile — `source` (the real config path), `artifact_type`, `path`, `status`, and `classification` — with artifacts classified as **publishable** (parquet incl. multi-sheet expansion, csv when keep_csv, README, LICENSE, codebook.md, codebooks/**) or **intermediate** (profiles, renders, per-sheet intermediates, schema/card inputs).

**The durable manifest is the object of record.** `prepare` SHALL write `manifest.json` into the output directory, and every later phase that adds a package artifact (`codebook_all`, `profile_all`, `render_all`) SHALL refresh it at the end of a successful run, so the file on disk is always the one a recount of the same tree would produce. A phase SHALL refresh only a directory that already owns a manifest: no phase SHALL create a package record for a tree `prepare` never prepared. publish dry-run and confirm SHALL read the SAME manifest — the durable file — to plan and to enforce contents (no divergence); `publish` SHALL NOT recompute the manifest while the durable file exists. A package that carries no durable manifest (a tree prepared before this change) SHALL be recomputed, and the recompute SHALL be announced verbatim: `[!] No durable package manifest in <dir> - recomputed from the tree (a package prepared before #349).`

**Divergence from the tree SHALL be the backstop, not the mechanism.** The record SHALL declare, path for path, the deliverable set a recount of the same tree produces — the `publishable` entries whose `status` is `staged` and whose `path` is a file path. A record that omits a delivered file, or promises one the delivery no longer holds, SHALL refuse the `hf` confirm with the stable marker `STALE_MANIFEST` — the block naming the record, the undeclared paths, the withdrawn paths and the recovery — BEFORE any network call and before staging; a dry-run and the local target SHALL print the same block as a warning and continue to plan. The comparison SHALL be over paths, never content: the record carries no hashes, so an in-place edit of a declared file is NOT a divergence and SHALL NOT refuse a delivery. `intermediate` entries SHALL NOT be compared — a local-only layer is regenerable churn, not a delivery fact. A record SHALL promise the **presence** of a recursive remote's tree as well as of its files: a tree the delivery no longer holds SHALL be reported under `withdrawn` even though the tree itself is never a delivered file. A record that cannot be read SHALL be refused the same way — before any network call and before staging, with the stable marker `UNREADABLE_MANIFEST` naming the record and the error; a dry-run and the local target SHALL print that block as a warning, recount for the preview and continue to plan. A record SHALL NOT be refused for a `keep_csv` delivery: the record describes the package tree, and the original CSVs such a delivery adds are read from the configuration, never declared by it. The recovery SHALL read `re-run the build chain (`sofer prepare --force --all-files`) and retry.`

Missing **required** artifacts SHALL block confirm with a stable `error_code` and a concrete recovery (re-run prepare); optional artifacts absent SHALL be marked `optional` and SHALL NOT emit the "missing artifact" warning (no silent omission, no false warning). Staleness SHALL key on the real config path (custom TOML names and multi-sheet Excel outputs included). Local delivery SHALL honor `force`. Remote inspection failures SHALL fail closed (unchanged PUB-05).

`classification` SHALL be the serialized delivery axis, independent of `status`: every entry SHALL carry `publishable` or `intermediate`, a manifest written before the field existed SHALL load with `publishable` as the default (the field is additive), and no `intermediate` entry SHALL ever be part of the delivery set or be `missing` — the absence of a local-only layer is never a publication blocker. `profiles` and `renders` SHALL be `intermediate` and SHALL be probed where `profile_all`/`render_all` actually write them (the artifact cache, `<root>/<output_dir>/<dir>`), with the dataset root accepted as the explicit-location fallback, and the recorded `path` SHALL be relative to the root.

The delivered set SHALL be the `publishable` entries whose `status` is `staged` **and whose `path` is a file path** (no trailing slash). For those it SHALL equal the files the copy path stages for the same tree. A recursive remote SHALL be recorded as ONE directory entry whose `path` ends with `/`, because its files are enumerated at copy time: it SHALL NOT be counted as a delivered file, and a tree that stages zero files SHALL contribute nothing to the delivered set. The manifest SHALL NOT count a local-only layer as part of the upload, and SHALL NOT present a directory entry as an uploaded file (`2026-10-18-fix-manifest-publishable-intermediate`, issue #346).

#### Scenario: The durable manifest follows every phase that adds artifacts (#349) — Added

- GIVEN a package `prepare` wrote, with its `manifest.json`
- WHEN `codebook_all`, `profile_all` or `render_all` completes
- THEN the file on disk SHALL equal a recount of the same tree (`from_dir(output_dir)` == `build_package_manifest(cfg, output_dir)`)
- AND a phase that wrote to the shared artifact cache SHALL NOT create a manifest in a directory that does not already own one

#### Scenario: Publish plans and enforces with the durable file (#349) — Added

- GIVEN a durable manifest that declares a required artifact a recount would not declare
- WHEN the confirm runs
- THEN the enforcement SHALL see that entry, proving the file is the object of record rather than a fresh recomputation

#### Scenario: A record that omits a delivered file refuses the upload before the network (#349) — Added

- GIVEN a package whose tree delivers a file the durable manifest does not declare
- WHEN `publish --target hf` confirms
- THEN it SHALL print the `STALE_MANIFEST` block naming the undeclared paths and the recovery
- AND it SHALL return 1 without staging and without any network call

#### Scenario: A withdrawn declared file refuses the upload (#349) — Added

- GIVEN a record that declares a file the delivery no longer holds
- WHEN the confirm runs
- THEN the block SHALL name it under `withdrawn` and the upload SHALL be refused

#### Scenario: An undeclared delivered file warns but still plans a dry-run (#349) — Added

- GIVEN the same divergence
- WHEN `publish --dry-run` runs
- THEN the `STALE_MANIFEST` block SHALL print as a warning
- AND the dry-run SHALL still print its plan and exit 0

#### Scenario: An in-place edit of a declared file is not a divergence (#349) — Added

- GIVEN a record and a tree that declare the same deliverable paths
- WHEN a declared file is rewritten with different content
- THEN the confirm SHALL proceed: the record describes the set, not the bytes

#### Scenario: A manifest written before the field existed still loads (#346) — Modified 2026-10-19

- GIVEN a `manifest.json` whose entries carry no `classification`
- WHEN it is read
- THEN every entry SHALL read `publishable` — including a legacy `profile`/`render` entry, which a consumer needing the true class SHALL re-derive by rebuilding the manifest
- AND `publish` SHALL rebuild it only for a package that carries **no** durable manifest (the pre-#349 tree), never while the durable file exists
- AND re-reading and re-writing the result SHALL be byte-identical (the new form is a fixed point); a legacy input is not preserved byte-for-byte, because reading it records the classification
