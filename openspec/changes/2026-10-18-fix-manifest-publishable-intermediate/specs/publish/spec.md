# Delta for publish

> **Change** `2026-10-18-fix-manifest-publishable-intermediate` (issue **#346**) ·
> branch `fix/346-manifest-publishable-intermediate` from `dev@d07557e`, rebased
> onto `dev@e23a6e8` · store **hybrid**.
>
> **One modified requirement, three added scenarios.** PUB-12 gains the serialized
> `classification` field, the layer probe rule and the delivered-set identity.
>
> **Rule-6 resolution.** `publish` is a permanent declared-backlog spec
> (`openspec/test-mapping-registry.md:38`), so the new scenarios are unmapped and
> the registry is not edited; `scripts/check_test_mapping.py` still exits 0.

## MODIFIED Requirements

### Requirement: Package artifact manifest with explicit publishable/intermediate boundary (PUB-12) — Modified 2026-10-18, fix-manifest-publishable-intermediate

The publish flow SHALL operate on one machine-readable package manifest listing every artifact of the selected build profile — `source` (the real config path), `artifact_type`, `path`, `status`, and `classification` — with artifacts classified as **publishable** (parquet incl. multi-sheet expansion, csv when keep_csv, README, LICENSE, codebook.md, codebooks/**) or **intermediate** (profiles, renders, per-sheet intermediates, schema/card inputs). `prepare` writes the manifest into the output dir; publish dry-run and confirm SHALL read the SAME manifest to plan and to enforce contents (no divergence).

Missing **required** artifacts SHALL block confirm with a stable `error_code` and a concrete recovery (re-run prepare); optional artifacts absent SHALL be marked `optional` and SHALL NOT emit the "missing artifact" warning (no silent omission, no false warning). Staleness SHALL key on the real config path (custom TOML names and multi-sheet Excel outputs included). Local delivery SHALL honor `force`. Remote inspection failures SHALL fail closed (unchanged PUB-05).

`classification` SHALL be the serialized delivery axis, independent of `status`: every entry SHALL carry `publishable` or `intermediate`, a manifest written before the field existed SHALL load with `publishable` as the default (the field is additive), and no `intermediate` entry SHALL ever be part of the delivery set or be `missing` — the absence of a local-only layer is never a publication blocker. `profiles` and `renders` SHALL be `intermediate` and SHALL be probed where `profile_all`/`render_all` actually write them (the artifact cache, `<root>/<output_dir>/<dir>`), with the dataset root accepted as the explicit-location fallback, and the recorded `path` SHALL be relative to the root. The delivery set SHALL be derivable as `classification == publishable AND status == staged`, and that set SHALL equal what the copy path stages for the same tree: the manifest SHALL NOT describe an artifact the copy path cannot stage, and SHALL NOT count a local-only layer as part of the upload (`2026-10-18-fix-manifest-publishable-intermediate`, issue #346).

(Previously: the package boundary was implicit — plan_remote_files derived the dry-run set and codebook_remotes were collected from the output dir, with a warning when codebooks were absent that could be a false positive for optional artifacts. Then: the boundary was demanded but only `.status` was serialized, so `profile`/`render` entries were indistinguishable from deliverable artifacts in the JSON and were probed at a root nothing writes to.)

#### Scenario: Manifest lists exact publishable set for single-sheet source

- GIVEN a single-CSV dataset and a fresh prepare
- THEN `output_dir/manifest.json` SHALL list each parquet, README.md, LICENSE, and codebook.md as `staged`
- AND profiles/renders present in the tree SHALL be `intermediate` (never publishable)

#### Scenario: Local-only layers are never publishable (#346) — Added

- GIVEN a prepared package whose `cache/profiles` and `cache/renders` hold the layers `profile_all`/`render_all` wrote
- WHEN the manifest is built
- THEN the `profile` and `render` entries SHALL read `classification: intermediate` with paths under `cache/`
- AND the `publishable` **staged** entries SHALL equal, path for path, the files the copy path stages for that tree

#### Scenario: An absent optional artifact is publishable but not delivered (#346) — Added

- GIVEN a package with no `codebook.md` (no `--all-files` prepare ran)
- WHEN the manifest is built
- THEN that entry SHALL be `classification: publishable` with `status: optional`
- AND it SHALL NOT appear in the delivered set (`publishable` AND `staged`), so the delivery count never overstates the upload

#### Scenario: A manifest written before the field existed still loads (#346) — Added

- GIVEN a `manifest.json` whose entries carry no `classification`
- WHEN it is read
- THEN every entry SHALL read `publishable`
- AND the JSON roundtrip SHALL stay byte-stable
