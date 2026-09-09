# Tasks: fix-package-artifact-manifest (#122)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 450–650 (manifest.py ~200 + prepare/publish integration + tests) |
| 400-line budget risk | Medium-High |
| Chained PRs recommended | Yes |
| Suggested split | Unit 1 PR (manifest.py + prepare write + spec sync PRP-11/PUB-12) → Unit 2 PR (publish consume/enforce + tests) |
| Decision needed | After design approval |

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | `src/sofer/manifest.py` (status vocabulary, entries, builder, JSON) + prepare writes manifest + spec sync | PR 1 | core contract; no behavior change yet |
| 2 | publish dry-run/confirm consume the manifest, missing-required blocks, false-warning fix, local-force and divergence tests | PR 2 | consumes Unit 1; full suite |

## Phase 1: Manifest core (`manifest.py`)

- [ ] 1.1 `ArtifactStatus` (staged/expected/optional/missing) + `ManifestEntry(source, artifact_type, path, status)` + `PackageManifest(entries, to_dict / from_json / json_bytes)` — module docstring per AGENTS.md rule 2.
- [ ] 1.2 `build_package_manifest(cfg, output_dir, staging_dir)`: classify per profile — publishable (parquet incl. `stem__sheet.parquet` expansion, csv when keep_csv, README/License/codebook.md/codebooks/**), intermediate (profiles/renders/per-sheet intermediates/schema-card inputs).
- [ ] 1.3 `required(cfg)` vs `optional(cfg)` resolution: codebooks required when the profile promises them; profiles/renders optional unless requested.

## Phase 2: Prepare writes the manifest (PRP-11)

- [ ] 2.1 Red: prepare writes `output_dir/manifest.json` (single-sheet exact set; multi-sheet per-sheet entries).
- [ ] 2.2 Green: write manifest at end of prepare (staged statuses); stable JSON keys.

## Phase 3: Publish consumes and enforces (PUB-12)

- [ ] 3.1 Red: dry-run diff rendered from manifest entries (structure, not re-derived sets).
- [ ] 3.2 Red: missing required codebook blocks confirm (`error_code` + recovery naming re-run prepare).
- [ ] 3.3 Red: optional absent artifact emits NO "missing" warning (entry reads `optional`).
- [ ] 3.4 Red: dry-run ≡ confirm contents (same manifest object; divergence test).
- [ ] 3.5 Red: custom TOML name staleness; local force honors; remote inspection fail-closed unchanged.
- [ ] 3.6 Green: wire into `plan_remote_files` / confirm path; remove the false-warning branch.

## Phase 4: Verification + archive

- [ ] 4.1 Sync PRP-11 + PUB-12 into base specs; README package semantics note.
- [ ] 4.2 Full gates: suite + ruff + format + mypy + diff --check (+ venv 3.14 spot-check for fastmcp-sensitive tests if touched).
- [ ] 4.3 Archive: archive-report, move to `openspec/changes/archive/2026-09-09-fix-package-artifact-manifest/`, commit `chore(sdd): archive fix-package-artifact-manifest — sync PRP-11/PUB-12 to base`, PR(s) → dev (following the two-unit split; green CI + explicit user authorization before merge).

## Out of scope reminders

- No changes to scan transactionality, MCP credentials/containment, `sofer_build`, production uploads, or `SOFER_TRACE.md`.