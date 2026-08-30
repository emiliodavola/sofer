# Apply Progress: fix-prepare-multisheet-xlsx-copy

**Change**: fix-prepare-multisheet-xlsx-copy
**Mode**: Standard (strict_tdd false)
**Delivery**: single PR, auto-forecast, ~90 lines
**Date**: 2026-08-30

## Implemented Tasks

### Phase 2: Core Implementation
- [x] 2.1 Fix `src/sofer/prepare.py:848-854` `is_converted` guard: dual `__`+`_` predicate, XLSX-only branch `k == norm_key or k.startswith(stem+"__") or (k.startswith(stem+"_") and k != norm_key)`; non-XLSX keeps `k == norm_key` equality (preserves single-sheet short-circuit).
- [x] 2.2 Fix `src/sofer/prepare.py:603-619` `_check_local_overwrite` XLSX branch: `glob __*.parquet` primary sorted + fallback `glob _*.parquet` filtered `c.stem != stem` (mirrors `_mirror.py:239-252` PUB-10), plus single-sheet candidate.
- [x] 2.3 Fix `src/sofer/prepare.py:364-379` `_assert_cross_file_schema` grouping: added `k.startswith(norm_stem+"_") and k != norm_key` and `k.startswith(legacy_key+"_") and k != legacy_key` forms.

### Phase 3: Testing
- [x] 3.1 Leak regression `TestMultisheetLeakRegression`: `DATA_GOT_ALL.xlsx` (aristas/nodos) into clean `build/` → only `data_got_all_*.parquet`, `glob("*.xlsx")==[]`.
- [x] 3.2 Overwrite fallback `TestOverwriteFallbackSingleUnderscore`: seed `report_ventas.parquet` (`_`) → `prepare(force=False)` exit 1, `force=True` overwrites; direct `_check_local_overwrite` + false-positive guard.
- [x] 3.3 Schema grouping `TestSchemaGroupingSingleUnderscore` (single-underscore key) + `TestSingleSheetPreserved` → exactly one `dataset.parquet`, no `dataset_*.parquet`.
- [x] 3.4 Gate: `uv run pytest tests/ -q` (1029 passed, 2 skipped) and `uv run mypy src/` (Success) green; manual clean-build check passed (temp build no .xlsx).

## Pending (deferred to orchestrator/verify)
- [ ] 4.1 Manual clean-build check already executed (temp dir, no *.xlsx) — redo in verify if needed
- [ ] 4.2 Confirm spec delta present (already in change)
- [ ] 4.3 `__` preservation deferral (no code)

## Files Changed
| File | Action | What |
|------|--------|------|
| `src/sofer/prepare.py` | Modified | 3 guards aligned with `_mirror.py` PUB-10; XLSX-only `k != norm_key` guard |
| `tests/test_prepare.py` | Modified | 7 new tests: leak, single-sheet, overwrite fallback (3), schema grouping (2) |
| `src/sofer/_converters.py` | None | Unchanged (re.sub `__+`→`_` stays) |

## Verification
- `uv run pytest tests/test_prepare.py -q` → 42 passed
- `uv run pytest tests/ -q` → 1029 passed, 2 skipped, 13 warnings
- `uv run mypy src/` → Success: no issues in 27 files
- Manual: `DATA_GOT_ALL.xlsx` (aristas/nodos) → temp build has `data_got_all_aristas.parquet`, `data_got_all_nodos.parquet`, no `*.xlsx` (verified via python -c prepare)

## Risks
- `_` fallback could false-positive `stem_foo.parquet` unrelated to XLSX sheets → mitigated by `k != norm_key` / `c.stem != stem` and XLSX-only branching.
- Single-sheet regression prevented by `k == norm_key` short-circuit preserved.
- Stale `build/DATA_GOT_ALL.xlsx` from prior run not auto-cleaned; verify step should delete stale artifact if present (`C:/Users/elaze/Desktop/test/build` stale artifact xref).

## Deviations
None — implementation matches design.md triple-site predicate and `_mirror.py` fallback pattern.

## Next Recommended
`sdd-verify`
