# Proposal: fix-prepare-multisheet-xlsx-copy

## Summary

`sofer prepare` with multisheet `.xlsx` leaks the original workbook into `build/` alongside per-sheet parquet. Fix the staging guard to match normalized keys.

## Motivation

- Bug: `DATA_GOT_ALL.xlsx` (`aristas`/`nodos`) → `build/` has `DATA_GOT_ALL.xlsx` (93991 B) + 3 parquet; `final/` only parquet. `build/` must not contain source.
- Root cause: `_converters.py:70` `re.sub(r"__+", "_", s)` collapses `stem__sheet` → `stem_sheet`. Guards at `prepare.py:851-852`/`603`/`364` check only `__` → always `False` → `copy_to_mirror` copies original. `_mirror.py` already has `stem_*.parquet` fallback (PUB-10); `prepare.py` misaligned.
- Single-sheet `dataset.xlsx` unaffected (`k == norm_key`).

## Intent

Prevent staging original `.xlsx` when any sheet converted. `build/` SHALL contain only normalized `.parquet` per sheet.

## Scope

### In Scope
- Fix `prepare.py:848-852`, `:603`, `:364` to `__` + `_` (mirror `_mirror.py` fallback)
- No `_converters.py` change, no new config; regression test

### Out of Scope
- Preserving `__` (deferred migration) — details below

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `prepare` (PRP-02): XLSX multisheet guard must recognize single-underscore normalized keys

## Approach

### Option 1 — Minimal guard fix (Recommended)
Check `__` + `_` (`k.startswith(stem+"_") && k!=norm_key`), glob `__*.parquet` + `_*.parquet` fallback. 3 sites in `prepare.py`.

*Pros*: 3 lines, compat, aligns with `_mirror.py` PUB-10. *Cons*: leaves `__` collapse debt.

### Option 2 — Preserve `__`
Keep `__` in `normalize_parquet_remote`. *Pros*: semantic. *Cons*: breaks caches, needs migration — deferred.

### Option 3 — `converted` membership
Check `converted` set directly. = Option 1, extra indirection.

**Recommendation: Option 1**.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/prepare.py:364-377` | Modified | Cross-file schema sheet match `__`+`_` |
| `src/sofer/prepare.py:603-609` | Modified | Overwrite glob fallback |
| `src/sofer/prepare.py:848-852` | Modified | Staging `is_converted` guard |
| `src/sofer/_mirror.py` | None | Reference (already correct) |
| `openspec/specs/prepare/spec.md` | Modified | PRP-02 guard clarification |
| `tests/test_prepare.py` | Modified | Multisheet leak regression |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| False positive `stem_foo.parquet` | Low | Require `k != norm_key` + XLSX-only branch |
| Single-sheet regression | Low | Keep `k == norm_key`; existing test |
| Stale `build/` masks fix | Med | Test clean `build/` has no `*.xlsx` |

## Out of Scope

- Preserving `__` boundary (migration with cache invalidation)
- New `[tool.sofer]` defaults, `publish` (`final/` correct), sheet dedup

## Rollback Plan

Revert 3 sites to `__`-only. Delete `build/DATA_GOT_ALL.xlsx`. Single commit.

## Dependencies

None — `normalize_parquet_remote` + stdlib.

## Success Criteria

- [ ] Multisheet `DATA_GOT_ALL.xlsx` → `build/` only `data_got_all_*.parquet`, no `*.xlsx`
- [ ] Single-sheet `dataset.xlsx` → single `dataset.parquet`
- [ ] Overwrite guard detects sheet via fallback; `--force` required
- [ ] `pytest -q` + `mypy` green
