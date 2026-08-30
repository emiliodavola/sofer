# Archive Report: fix-prepare-multisheet-xlsx-copy

**Change**: `fix-prepare-multisheet-xlsx-copy`
**Date archived**: 2026-08-30
**Artifact store**: hybrid (openspec + Engram)
**Status**: archived — SDD cycle complete
**Verify verdict**: PASS (verify-report #712)

## Summary

`sofer prepare` with multisheet `.xlsx` leaked the original workbook into `build/` alongside per-sheet Parquet because `src/sofer/_converters.py:70` collapses `stem__sheet` → `stem_sheet` (`re.sub(r"__+", "_", s)`) while guards at `prepare.py:848/603/364` checked `__` only and always missed normalized keys. Fixed all 3 guards to dual `__`+`_` (XLSX-only, `k != norm_key` / `c.stem != stem`) aligning with `src/sofer/_mirror.py:239-252` PUB-10 fallback. Single-sheet `k == norm_key` short-circuit preserved. No `_converters.py` change; `__` preservation deferred to future migration.

## Files Changed

| File | Action | Details |
|------|--------|---------|
| `src/sofer/prepare.py:364-379` | Modified | `_assert_cross_file_schema` grouping: added `k.startswith(norm_stem+"_") and k != norm_key` and `k.startswith(legacy_key+"_") and k != legacy_key` forms |
| `src/sofer/prepare.py:603-622` | Modified | `_check_local_overwrite` XLSX branch: `glob __*.parquet` primary (sorted, is_file) + fallback `glob _*.parquet` filtered `c.stem != stem` (mirrors `_mirror.py` PUB-10) + single-sheet candidate |
| `src/sofer/prepare.py:848-869` | Modified | `is_converted` staging guard: XLSX-only dual predicate `k == norm_key or k.startswith(norm_stem+"__") or (k.startswith(norm_stem+"_") and k != norm_key)`; non-XLSX keeps `k == norm_key` equality |
| `src/sofer/_converters.py:70` | None | Unchanged — `__+`→`_` collapse preserved |
| `src/sofer/_mirror.py:239-252` | None | Reference — PUB-10 fallback pattern |
| `tests/test_prepare.py` | Modified | +167 lines, 7 new tests: `TestMultisheetLeakRegression`, `TestSingleSheetPreserved`, `TestOverwriteFallbackSingleUnderscore` (3), `TestSchemaGroupingSingleUnderscore` (2) |
| `openspec/specs/prepare/spec.md` | Modified | PRP-02 delta synced: `Modified 2026-08-30, fix-prepare-multisheet-xlsx-copy` — 13 scenarios, guards now match both `__` and `_`, notes `__+`→`_` collapse and leak fix |
| `openspec/changes/fix-prepare-multisheet-xlsx-copy/specs/prepare/spec.md` | Delta | MODIFIED Requirement PRP-02 — source of merge |

## Delivery

| Field | Value |
|-------|-------|
| Estimated changed lines | ~90 prod+tests+spec (actual 191 = 30 prod + 167 tests, delta spec pre-existing) |
| 400-line budget risk | Low |
| Chained PRs | No — single PR, single commit |
| Delivery strategy | auto-forecast |
| Review scope | Single work unit — 3 sites + tests atomic |

## Spec Sync

| Domain | Action | Details |
|--------|--------|---------|
| prepare | Updated | MODIFIED PRP-02 replaced in `openspec/specs/prepare/spec.md` (1 modified requirement, 13 scenarios: 4 new/updated vs 2026-08-29 baseline) — preserved PRP-01, PRP-02a, PRP-02b, PRP-03..PRP-08 |

Delta `specs/prepare/spec.md` → canonical `specs/prepare/spec.md`. Other requirements unchanged. No REMOVED/RENAMED deltas.

## Task Completion

| Phase | Tasks | Status |
|-------|-------|--------|
| 1 Foundation | 1.1, 1.2 | 2/2 ✅ |
| 2 Core Implementation | 2.1, 2.2, 2.3 | 3/3 ✅ |
| 3 Testing | 3.1, 3.2, 3.3, 3.4 | 4/4 ✅ |
| 4 Verification & Cleanup | 4.1, 4.2, 4.3 | 3/3 ✅ |
| **Total** | **12** | **12/12 ✅** |

**Reconciliation note**: `tasks.md` initially had 12 unchecked boxes when archive started (persisted artifact stale; `apply-progress` #711 and `verify-report` #712 already proved 12/12 complete). Per orchestrator instruction ("Also update tasks.md checkboxes to checked? Archive should reflect completion") and SDD archive exceptional-repair clause, archive reconciled all 12 boxes to `[x]` before spec sync. Proof: `apply-progress` shows 2.1-2.3 + 3.1-3.4 checked (7 tasks) and verify-report completeness table shows 12/12 with all phases checked (gate `uv run pytest` + `uv run mypy` green, manual temp-build leak check PASS). No unchecked implementation tasks remain in archived artifact.

## Verification Evidence

- **Test command**: `uv run pytest tests/ -q` → 1029 passed, 2 skipped, 13 warnings (DeprecationWarning `_infer_type` pre-existing) — exit 0 — hash `sha256:0c87919c13b7831e25792f5f6f3c21dc6b92d00ac155a33499ee3de349aa53ea`
- **Focus**: `uv run pytest tests/test_prepare.py -q` → 42 passed — exit 0
- **Build**: `uv run mypy src/` → `Success: no issues found in 27 source files` — exit 0 — hash `sha256:e7c982786727c1ea6b0e5e0346e1e60ba39748267137c4655285186d19e1c5e8`
- **Manual leak check** (verify-report § Build & Tests): temp `openpyxl` `DATA_GOT_ALL.xlsx` (aristas/nodos) via `prepare` into clean `tmp/build` → `[~] ... -> data_got_all_aristas.parquet`, `[~] ... -> data_got_all_nodos.parquet`, `build/* = [data_got_all_aristas.parquet, data_got_all_nodos.parquet, LICENSE, README.md]`, `glob *.xlsx == []` — MANUAL CHECK PASS
- **Manual**: `raw.xlsx` `convert_to_parquet=false` → staged as `raw.xlsx` no parquet — PASS; `bad.tsv` failure fallback → warning + staged — PASS
- **Spec compliance**: 13/13 scenarios COMPLIANT (11 via `test_prepare.py`, 1 via `test_mirror.py`, 2 via manual + analog coverage)
- **Critical issues**: 0; Warnings: W1 stale `build/DATA_GOT_ALL.xlsx` not auto-cleaned (manual delete required), W2 `convert_to_parquet=false` XLSX lacks dedicated automated test (non-blocking)

## Rollback Plan

Revert 3 predicates/globs in `src/sofer/prepare.py` to `__`-only:

- `848-869`: `if suffix == ".xlsx"` dual → `any(k == norm_key or k.startswith(norm_stem+"__") for k in converted)`
- `603-622`: `primary` + fallback `__`/`_*.parquet` → `for p in search_dir.glob(f"{stem}__*.parquet")`
- `364-379`: remove `or (k.startswith(...+"_") and k != ...)` forms

Delete stale `build/DATA_GOT_ALL.xlsx` / `build/data_got_all.xlsx` if present. Single commit revert; normalized `_` files on disk remain valid; `final/` stays correct via `_mirror.py` fallback. No migration or cache invalidation required.

## Lessons & Follow-ups

- **Gotcha**: `normalize_parquet_remote` collapses `__`→`_` so any guard checking `__` alone silently fails for all multisheet XLSX — alignment with `_mirror.py` PUB-10 is mandatory.
- **Guard scope**: `_` fallback MUST be XLSX-only + `k != norm_key` / `c.stem != stem` to avoid `train` vs `train_extra` false positives on CSV/TSV.
- **Stale artifact**: `prepare` never auto-deletes prior leaky `build/*.xlsx`; verification used temp dir; production `C:/Users/elaze/Desktop/test/build` stale file must be deleted manually.
- **Follow-up (non-blocking)**: Add `test_raw_xlsx_convert_false` to `test_prepare.py` to harden W2 for CI; migrate `tests/test_codebook.py` away from deprecated `_infer_type` (13 warnings).
- **Deferred**: Preserving `__` in normalized keys requires cache/migration proposal — intentionally not in this change.

## Engram Traceability

| Artifact | Observation ID | sync_id |
|----------|---------------|---------|
| proposal | #707 | obs-d2c28dc8efc68431 |
| spec (delta) | #708 | obs-fe4920463f1bc454 |
| design | #709 | obs-311cb10b87d79dbb |
| tasks | #710 | obs-5c75ab3be7a864f8 |
| apply-progress | #711 | obs-3ab751055e03c094 |
| verify-report | #712 | obs-9566fcd208c3cf34 |
| archive-report | (this) | sdd/fix-prepare-multisheet-xlsx-copy/archive-report |

Delta spec file: `openspec/changes/fix-prepare-multisheet-xlsx-copy/specs/prepare/spec.md` → canonical `openspec/specs/prepare/spec.md`.
Archived to: `openspec/changes/archive/2026-08-30-fix-prepare-multisheet-xlsx-copy/`

## Source of Truth Updated

- `openspec/specs/prepare/spec.md` now reflects normalized `__+`→`_` and dual-guard behavior; PRP-02 is the single modified requirement in this change.
