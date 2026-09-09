# Verify Report — fix-package-artifact-manifest (PR 1 only)

**Issue**: GitHub #122 (child of epic #115) · **Branch**: `fix/122-artifact-manifest`
**Verified commit**: `15a2762` (PR 1 — manifest core + prepare writes it; PR 2 NOT implemented, out of scope)
**Date**: 2026-09-09 (verification run against the archived change)
**Last full commit message claim**: 1467 passed / 6 skipped — independently reproduced (below).

## Verdict by section

| Section | Verdict | Evidence |
|---|---|---|
| 1. Spec conformance (PRP-11) | **PASS** | 2/2 scenarios covered by passing tests; multi-sheet also verified against real prepare output |
| 2. Tasks conformance (Phases 1–2) | **PASS** (1.3 partial — see notes) | Phases 1–2 done; Phase 3 correctly absent (PR 2) |
| 3. Strict TDD evidence | **NOT ACTIVE** (config `strict_tdd: false`) — failing-first nature corroborated | no separate RED commit; natural import-level RED |
| 4. Review workload guard | **PASS** (with 400-line note) | 500 changed lines vs forecast 450–650; chained-PR split respected |
| 5. Sanity checks | **PASS** (all green, exact outputs below) | pytest ×3, ruff, mypy, diff --check |
| 6. Gaps/risks | Honest list below (no CRITICAL for PR 1) | 3 WARNINGs filed |

**Overall**: PASS for PR 1 scope (PASS-WITH-NOTES). #122 as a whole is NOT closed — PR 2 (publish consumption/enforcement, PUB-12) is pending and the archive record must be extended. No CRITICAL blockers were found within the verified scope.

---

## 1. Spec conformance — PRP-11 (openspec/specs/prepare/spec.md)

- **Scenario "Manifest written by prepare with staged statuses"** → `test_prepare_writes_manifest_file` (tests/test_manifest.py): drives the real `sofer.prepare.prepare(cfg, out)`, asserts `rc == 0`, `output_dir/manifest.json` exists, decodes via `PackageManifest.from_json`, `data.parquet`, `README.md`, `LICENSE` present, parquet entry `staged`. **PASSING**.
- **Scenario "Multi-sheet sources recorded per sheet"** → `test_build_manifest_multi_sheet_expansion` (tests/test_manifest.py): exact-list assertion `["book__Sheet1.parquet", "book__Sheet2.parquet"]`. **PASSING** (see risk R2 — the committed test exercises the `__` naming branch, which prepare never produces on disk; the real single-underscore layout was verified empirically below and works via the PUB-10 fallback glob).
- **Empirical multi-sheet check (scratch, read-only)**: built a real `Report.XLSX` with sheets `Ventas`/`Costos`, ran `prepare`, obtained `report_ventas.parquet` + `report_costos.parquet` (single underscore, collapsed normalization), then `build_package_manifest` listed **both** per-sheet entries as `staged`. PRP-11 scenario 2 holds against real prepare output.
- Manifest write placement: only after all gates pass (overwrite protection, case-fold collisions, cross-file schema, codebook generation — `return 1` at prepare.py:705/736/790/889, all before the step-10b write). A failed prepare never writes a manifest. Matches "end of a successful run".

**PUB-12 (openspec/specs/publish/spec.md)**: 7 scenarios synced into base spec with "enforcement in PR 2" — correct per the plan; no PUB-12 test coverage yet (spec-ahead-of-tests window until PR 2, note R7).

## 2. Tasks conformance (tasks.md — archived verbatim, all boxes `- [ ]`)

Every line in tasks.md is still `- [ ]` even for completed phases (stale checkboxes — note N1). Disposition per line:

- `- [ ] 1.1` (+ module docstring): **DONE** — `ArtifactStatus`, `ManifestEntry`, `PackageManifest` with to_dict/from_dict/from_json/json_bytes/from_dir; module docstring present (AGENTS rule 2).
- `- [ ] 1.2` classify per profile, multi-sheet `stem__sheet.parquet` expansion via `expanded_planned_remotes`: **DONE** — `build_package_manifest` (manifest.py), publishable vs intermediate verified above.
- `- [ ] 1.3` `required(cfg)` vs `optional(cfg)` resolution (“codebooks required when the profile promises them”): **PARTIAL** — requiredness is a static tuple (`_ROOT_PUBLISHABLE`); there is no cfg-derived “profile promises codebooks” resolution. The vocabulary ships, but the promised-profile concept is deferred to PR 2 (it is only meaningful once publish enforces missing-required). Flagged as scope/reconciliation discrepancy (note N2), not a defect for PR 1.
- `- [ ] 2.1` Red: prepare writes manifest (single-sheet exact set; multi-sheet per-sheet): **DONE** — `test_prepare_writes_manifest_file` + expansion test; phrasing “Red” (see §3).
- `- [ ] 2.2` Green: manifest written at end of prepare with staged statuses; stable JSON keys: **DONE** — prepare.py step 10b; `json_bytes()` uses `sort_keys=True` + deterministic entry sort; byte-stable roundtrip locked by `test_manifest_json_roundtrip_stable`.
- `- [ ] 3.1`–`3.6` (publish consumes/enforces): **NOT-YET — PR 2**, correctly absent from this commit (zero `src/sofer/publish.py` changes). Not failures.
- `- [ ] 4.1` spec sync PRP-11 + PUB-12: **DONE** (this commit adds both to base specs).
- `- [ ] 4.2` full gates: **DONE** — suite 1467/6, mypy clean, ruff clean, format/diff clean (see §5).
- `- [ ] 4.3` archive: **PARTIAL** — archive-report written and dir moved to `openspec/changes/archive/2026-09-09-…/`; the PR-merge authorization gate (explicit user authorization per archive-report) is outside this verification.

**Checkbox rule**: no clean “archive-ready” claim for #122 end-to-end — PR 2 (Phases 3) remains; this verify report does not turn incomplete tasks into a clean pass. For PR 1's slice, all Phase 1–2 outcomes are evidenced.

## 3. Strict TDD evidence

- `openspec/config.yaml`: `strict_tdd: false` (global context: “Strict TDD disabled… red-green-refactor not enforced per mem #441”). No project-local `.pi/gentle-ai/support/strict-tdd-verify.md` override exists; no global support file discovered. **Strict TDD is NOT active for this repo** — no TDD Cycle Evidence table is therefore required; none exists in the change artifacts.
- Failing-first nature: corroborated structurally — `sofer.manifest` did not exist at parent `3adcb27`; the file is added by `15a2762`, so `tests/test_manifest.py`’s `from sofer.manifest import …` would have raised `ModuleNotFoundError` before the commit. RED is at natural-import level, not a separate RED commit (both files landed in one commit). Tasks 2.1/3.x are phrased Red/Green but were not executed as separate failing commits.
- Assertion-quality audit (performed anyway): the 6 tests use real, non-tautological assertions (exact path-list equality, `next()`-driven presence, status enums, byte-identical roundtrip); no ghost loops, no type-only assertions, no smoke-only tests. `test_build_manifest_optional_profile_intermediate` correctly fails if the render layer ever disappears (requires ≥1 `render` entry).

## 4. Review workload guard

- Forecast (tasks.md): 450–650 changed lines; 400-line budget risk “Medium-High”; chained PRs recommended (Unit 1 = manifest + prepare + spec sync; Unit 2 = publish consume/enforce).
- This commit: **11 files changed, 499 insertions(+), 1 deletion(−) = 500 changed lines** → within the 450–650 forecast; the archive rename contributes 0 (rename-detected).
- 400-line budget exceeded (500 > 400) but the deviation is pre-declared in the forecast and mitigated by the agreed chain: PR 1 contains only Unit 1 (manifest.py 235 + test_manifest.py 134 + prepare.py 8 + test_publish.py 5 + spec sync 68 + archive-report 50). No scope creep: zero publish.py source changes, no PUB-12 enforcement, no out-of-scope modules.
- Verdict: guard respected; the chained-PR split matches the returned PR boundary.

## 5. Sanity checks (exact outputs, run during verification)

- `uv run pytest tests/test_manifest.py -q` → `......  [100%]` / **`6 passed in 0.78s`**
- `uv run pytest tests/test_publish.py -q` → `75 passed in 1.30s` (includes the adapted manifest-exclusion accounting test)
- `uv run ruff check src/sofer/manifest.py src/sofer/prepare.py tests/test_manifest.py` → **`All checks passed!`** (exit 0)
- `uv run pytest tests/ -q` → **`1467 passed, 6 skipped, 13 warnings in 38.34s`** — matches the commit/archive claim exactly (1461 baseline + 6).
- `uv run mypy src/` → **`Success: no issues found in 32 source files`**
- `git show 15a2762 --check` → clean (no whitespace errors)
- Scratch (system temp, repo untouched): real multi-sheet prepare → 2 parquets staged (`report_ventas.parquet`/`report_costos.parquet`) → manifest lists both `staged`; `prepare --force` prune experiment (see R1).

## 6. Gaps / risks — honest list

**PR 2 (explicitly not covered by PR 1, per scope):**
- Publish consumption: `plan_remote_files`/dry-run still derive the set independently of the manifest; the structural “dry-run ≡ confirm, same manifest object” guarantee (PUB-12) is not yet in place.
- Missing-required blocking with stable `error_code` + recovery naming (re-run prepare) — not implemented anywhere yet.
- The PUB-08 codebook-absence warning can still be a false positive for optional codebooks (this commit does not remove it).
- PUB-12's 7 scenarios have no tests yet (spec published ahead of enforcement; AGENTS rule-6 mapping incomplete until PR 2).

**Real findings within PR 1 (all WARNING-level, none CRITICAL):**
- **R1 (manifest not orphan-owned)**: `allowed_output_remotes`/`prune_orphans` (src/sofer/_clean.py) do not include `manifest.json`, so a `prepare --force` re-run deletes the *previous* manifest at step 8b and re-creates it at step 10b. End state is correct today (all gates precede the prune; no `return` between prune and rewrite), but “the single source of truth” is treated as an unowned orphan — a latent inconsistency for PR 2's consume paths. Recommend adding `MANIFEST_NAME` to the allowlist, or documenting the prune-and-rewrite contract.
- **R2 (multi-sheet test asserts a layout prepare never produces)**: `test_build_manifest_multi_sheet_expansion` writes `book__Sheet1.parquet` style names (double underscore), while prepare actually stages collapsed single-underscore names (`report_ventas.parquet`). The per-sheet classification works against real output via the `_` fallback glob in `expanded_planned_remotes` (verified empirically), but that fallback branch is not locked by any committed test — a regression there would silently break PRP-11 scenario 2 for real packages. Recommend an integration test that runs prepare on a real multi-sheet workbook (or writes `_`-named files) and asserts the manifest.
- **R3 (fallback alias exposure, inherited from PUB-10)**: the `stem_*.parquet` fallback can absorb unrelated files sharing the stem prefix (e.g., a stale `report_old.parquet` while `report.xlsx` is single-sheet). Pre-existing helper behavior, not introduced by PR 1, but the manifest inherits it — PR 2 should treat “looks like a sheet file” defensively.
- **N1 (checkbox hygiene)**: all 14 task checkboxes remain `- [ ]` in the archived tasks.md including completed Phases 1–2/4.1–4.2. No apply-progress artifact exists in the archive (graceful handling: completion proven via tests + code + archive-report; a `TDD Cycle Evidence` table is likewise absent — acceptable since strict TDD is disabled). Recommend checkbox reconciliation before extending the record for PR 2.
- **N2 (1.3 partial)**: `required(cfg)`/`optional(cfg)` profile-promise resolution is not implemented (static requiredness only). Deferred to PR 2 by necessity; record it as remaining scope.
- **N3 (vocabulary use)**: `ArtifactStatus.EXPECTED` is defined but never emitted; `codebooks/` contributes a synthetic `OPTIONAL` entry with a trailing-slash directory path. Both are fine for PR 1 but need defined semantics in PR 2.
- **N4 (Windows/source field)**: manifest entry `path`s are POSIX (`as_posix()`); the `source` field is the native config path (backslashes on Windows). Roundtrip-consistent and opaque; worth documenting for cross-platform consumers.
- **N5**: `manifest.json` is never staged for upload (staging copies only planned remotes + codebooks), confirming the `test_publish.py` accounting adjustment is honest.

## Persistence

- This report: `openspec/changes/archive/2026-09-09-fix-package-artifact-manifest/verify-report.md` (written; not committed — per verify-executor contract the phase artifact is persisted, no commit).
- Engram: observation saved with topic key `sdd/fix-package-artifact-manifest/verify-report` (hybrid store).