# Tasks: fix-prepare-multisheet-xlsx-copy

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~90 (prod ~15 + tests ~60 + spec already done) |
| 400-line budget risk | Low |
| 2000-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR (one commit) |
| Delivery strategy | auto-forecast (≈ auto-chain) |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

> Single PR is correct: ~90 lines ≪ 400. If this change ever exceeded 400 lines, chained PRs would be recommended per review-budget guard; `size:exception` not needed.

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Fix 3 `prepare.py` guards + regression tests + verify | PR 1 | Base `main`; single commit; tests with code; rollback revert 3 predicates |

Work-unit commits guidance: one work-unit commit — all 3 sites + tests together (atomic leak fix). Keep tests/docs with code. Commit message explains outcome ("prevent XLSX leak into build/"), not file list. Future `__`-preservation migration is a separate unit.

## Phase 1: Foundation

- [x] 1.1 Align predicate with `src/sofer/_mirror.py:239-252` PUB-10 dual `__`+`_` pattern (reference, no edit)
- [x] 1.2 Confirm `src/sofer/_converters.py:70` `re.sub(r"__+", "_", s)` collapse stays unchanged; single-sheet `k == norm_key` short-circuit preserved

## Phase 2: Core Implementation (depends on Phase 1)

- [x] 2.1 Fix `src/sofer/prepare.py:848-854` `is_converted` guard: `k == norm_key or k.startswith(stem+"__") or (k.startswith(stem+"_") and k != norm_key)` XLSX-only
- [x] 2.2 Fix `src/sofer/prepare.py:603-619` `_check_local_overwrite` XLSX branch: `glob __*.parquet` primary + fallback `glob _*.parquet` filtered `c.stem != stem` + `norm_key` candidate
- [x] 2.3 Fix `src/sofer/prepare.py:364-379` `_assert_cross_file_schema` grouping: add `k.startswith(norm_stem+"_") and k != norm_key` and `k.startswith(legacy_key+"_") and k != legacy_key` forms

## Phase 3: Testing

- [x] 3.1 Add `tests/test_prepare.py` leak regression: `DATA_GOT_ALL.xlsx` (aristas/nodos) into clean `build/` → only `data_got_all_*.parquet`, `glob("*.xlsx")==[]`
- [x] 3.2 Add overwrite fallback test: seed `report_ventas.parquet` (`_`) → `prepare(force=False)` exit 1, `force=True` overwrites
- [x] 3.3 Add schema grouping test (single-underscore key) + single-sheet `dataset.xlsx` → exactly one `dataset.parquet`, no `dataset_*.parquet`
- [x] 3.4 Gate: `uv run pytest tests/ -q` and `uv run mypy src/` green

## Phase 4: Verification & Cleanup

- [x] 4.1 Manual clean-`build/` check: `sofer prepare` multisheet → `build/` has no `*.xlsx` (xref `C:/Users/elaze/Desktop/test/build` stale artifact)
- [x] 4.2 Confirm `openspec/specs/prepare/spec.md` PRP-02 delta present; no extra docs/config
- [x] 4.3 Note `__` preservation deferral for future migration proposal (no code now)
