# Archive Report — fix-package-artifact-manifest (PR 1)

**Archived**: 2026-09-09
**Issue**: GitHub #122 (child of epic #115)
**Branch**: `fix/122-artifact-manifest`
**Scope of this archive**: PR 1 only (manifest core + prepare writes it).

## Summary

PR 1 of #122 ships the package manifest contract: `src/sofer/manifest.py`
defines the status vocabulary (`staged | expected | optional | missing`),
`ManifestEntry(source, artifact_type, path, status)`, `PackageManifest`
(stable JSON, roundtrip, `from_dir`), and
`build_package_manifest(cfg, output_dir)` which classifies every artifact of
the selected build profile — publishable (parquet incl. multi-sheet
`stem__sheet.parquet` expansion via `expanded_planned_remotes`, csv when
keep_csv, README/LICENSE/codebook.md, codebooks/**) vs intermediate
(profiles, renders under the dataset root). `prepare` now writes
`manifest.json` into the output dir (PRP-11). Consumption and enforcement by
publish dry-run/confirm (PUB-12: missing-required blocks, no false warning,
dry-run ≡ confirm) is PR 2.

## Spec Sync

- **`openspec/specs/prepare/spec.md` — ADDED `PRP-11`** (Prepare writes the
  package manifest) with 2 scenarios.
- **`openspec/specs/publish/spec.md` — ADDED `PUB-12`** (Package artifact
  manifest with explicit publishable/intermediate boundary) with 7
  scenarios — enforcement scenarios land with PR 2.

## Verification Evidence

- `tests/test_manifest.py` (6 tests): exact single-sheet publishable set;
  missing required data is `missing`; optional profile/render classification
  (never a missing warning); multi-sheet per-sheet expansion; JSON stable
  roundtrip; prepare integration writes `manifest.json` with staged statuses.
- Adapted `tests/test_publish.py` upload-accounting test: `manifest.json` is
  build metadata never part of the upload plan, so the staged count excludes
  it (staged ≠ publishable by design).
- Full suite: **1467 passed, 6 skipped** (was 1461) on
  `fix/122-artifact-manifest`.
- `ruff check` clean; `ruff format --check` clean; `mypy src/` clean
  (32 source files now); `git diff --check` clean.

## Archive Mechanics

- Change directory moved: `openspec/changes/fix-package-artifact-manifest/`
  → `openspec/changes/archive/2026-09-09-fix-package-artifact-manifest/`.
- PR 2 (publish consumes/enforces the manifest) will extend this record, then
  #122 closes post-merge with per-criterion evidence.