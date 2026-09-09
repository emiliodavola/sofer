# Proposal — fix-package-artifact-manifest

**Issue**: GitHub #122 (final delivery slice of epic #115)
**Date**: 2026-09-09
**Status**: proposed

## Problem

The package boundary is implicit. A real trace showed codebooks, profiles,
and renders produced in `cache/` while `build/` contained only Parquet,
README, and LICENSE; publish completed with a warning that codebooks were
missing. An agent cannot tell whether that is intended (optional artifacts)
or an incomplete build (required artifacts silently absent). Decisions that
must never diverge — dry-run plan vs confirm upload, staged vs published
sets — are recomputed from different sources today.

## Expected behaviour (from #122)

- Package boundary explicit: every artifact classified as **publishable** or
  **intermediate**.
- `build/` contains exactly what the selected build profile promises.
- A machine-readable manifest lists `source`, `artifact_type`, `path`,
  `status`.
- Missing **required** artifacts block publish with a concrete recovery call.
- Optional artifacts visibly marked optional; no successful operation
  silently omits a promised output.
- Staleness uses the real config path (custom TOML names, multi-sheet Excel).
- Local delivery honors `force`.
- Unknown remote Hub state fails closed (already landed with #133).
- Dry-run and confirm operate on the same manifest.

## What already exists (verified on dev)

- `_needs_prepare` keys staleness on `cfg._config_path` (custom TOML name
  sentinel `Path()` → default fallback) and per-source mtimes — stale-
  invalidation for custom names is already correct.
- Remote inspection failures fail closed (`PUB-05`, #133).
- Local delivery already threads `force` through `copy_to_mirror`.
- `plan_remote_files` builds the dry-run diff from
  `expanded_planned_remotes` (staging, PUB-10) plus `codebook_remotes`
  collected from the output dir.

## Approach

1. **New `src/sofer/manifest.py`**: `ArtifactStatus` (staged / expected /
   optional / missing), `ManifestEntry` (`source`, `artifact_type`, `path`,
   `status`), `PackageManifest` (list + `to_dict` → stable JSON), and
   `build_package_manifest(cfg, output_dir, staging_dir)` that classifies
   every artifact of the selected build profile:
   - publishable: parquet (incl. multi-sheet `stem__sheet.parquet` expansion),
     csv when `keep_csv`, `README.md`, `LICENSE`, `codebook.md`,
     `codebooks/**/*.md` (RC-C01);
   - intermediate: schema/card inputs, profiles, renders, per-sheet parquet
     intermediates — and whatever else the build profile marks non-uploaded.
2. **prepare** writes `output_dir/manifest.json` (canonical package contents,
   consumed afterwards). **publish** dry-run and confirm both read that file:
   - dry-run diff renders from the manifest (single source of truth);
   - missing **required** entries block confirm with `error_code` + the
     concrete recovery (e.g. re-run prepare) — this replaces the current
     "codebooks missing" false warning (optional artifacts no longer warn).
3. **Tests**: exact build/ and publish file sets for single-sheet and
   multi-sheet sources; custom TOML name staleness; local force; dry-run ≡
   confirm contents (same manifest object); missing-required blocks; no
   false warning for optional; unknown remote still fail-closed.

## Out of scope

- Dataset identity / CWD, scan transactionality, MCP credential/containment
  except manifest-sensitive redaction, `sofer_build` tool, actual production
  uploads in tests, `SOFER_TRACE.md`.

## Key decisions

- **One manifest object, one decision path**: prepare writes it, dry-run and
  confirm read it — the "cannot diverge" acceptance is structural.
- **Status vocabulary is the source of truth** for the false-warning fix:
  an optional artifact absent is `optional`, never a "missing" warning; a
  required artifact absent is `missing` and blocks.
- Manifest is **machine-readable but human-summarizable**: JSON + the same
  summary lines the CLI/MCP print today.