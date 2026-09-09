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

## PR 2 — publish consumes and enforces the manifest (same archive record)

Extends this archive: publish dry-run and confirm now derive their plan and
enforcement from the same `build_package_manifest` object (PUB-12) — the
"cannot diverge" acceptance is structural.

### What landed

- `run_publish` builds the manifest (keep_csv=False: the manifest describes
  the BUILD; keep_csv CSVs are delivery-only from the source) and passes it
  to `_repo_diff_summary` (which surfaces `! MISSING` lines for required
  absent artifacts) plus a new PUB-12 gate before staging: any
  `required_missing()` (parquet, card, license; codebooks when
  `codebooks_required`) blocks with `error_code`-style output and the
  recovery `sofer prepare --force --all-files`.
- PUB-08 rewritten: the "No codebooks found" warning is no longer emitted
  for manifest-required codebooks (blocked instead) nor for optional absent
  codebooks (no false warning); only manifest-less legacy builds keep the
  advisory.
- `manifest.build_package_manifest` handles recursive entries (directory
  presence, never a per-file MISSING) and gained `codebooks_required`
  (optional-by-default, MISSING when the flow promised them).
- `publish` gained `codebooks_required: bool = False` for the MCP canonical
  chain (PR 2 of #117 pattern) — wired but default-off in the CLI.

### Tests

- `tests/test_manifest.py`: codebooks_required statuses (optional vs
  missing).
- `tests/test_publish.py`: `test_fresh_bare_prepare_build_delivers_without_false_warning`
  (updated PUB-08 expectation: optional absent codebooks never warn) and
  `test_not_found_files_skipped_in_staging` (updated: a declared source whose
  staged artifact is missing now BLOCKS with the recovery, per PUB-12).
  Existing suite re-run green.

### Verification

- Full suite: **1468 passed, 6 skipped**.
- `ruff check`, `ruff format --check`, `mypy src/` (32 files), `git diff --check` clean.
