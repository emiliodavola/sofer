# Design: fix-prepare-multisheet-xlsx-copy

## Technical Approach

Align `src/sofer/prepare.py` with `src/sofer/_mirror.py:expanded_planned_remotes` (PUB-10). Root cause: `_converters.py:70` collapses `stem__sheet` → `stem_sheet` via `re.sub(r"__+", "_", s)`, but `prepare.py:848,603,364` check `__` only and always miss multisheet keys — `copy_to_mirror` then leaks the workbook into `build/`. Fix adds `__`+`_` matching at each site (XLSX-only, `k != norm_key` guard). No `_converters.py` change; single-sheet `k == norm_key` preserved. Maps to proposal Option 1 and spec PRP-02 delta.

## Architecture Decisions

| Decision | Options | Tradeoff | Choice |
|----------|---------|----------|--------|
| Guard predicate | (A) `startswith(stem+"_")` alone (B) `__` + `_` dual | A covers both but hides intent; B mirrors `_mirror.py` primary+fallback and is auditable | **B: dual** — `k==norm_key \|\| k.startswith(s+"__") \|\| (k.startswith(s+"_") && k!=norm_key)` |
| Overwrite detection | FS glob vs `converted` dict | Dict only covers current run; FS is ground truth for prior-run PRP-07 | **FS glob** at `603`; dict check at `848` unchanged |
| Fallback scope | All suffixes vs XLSX-only | `_` on CSV risks `train` vs `train_extra` false positive | **XLSX-only** branches; CSV/TSV/JSONL unchanged |
| Normalize fix | Preserve `__` in `_converters.py:70` vs fix guards | Preserving `__` is semantic but breaks caches, needs migration | **Guard fix now**; `__` preservation deferred |

## Data Flow

```
_converters.convert_file_to_parquet (XLSX: stem__sheet)
        ▼ tmpdir/*.parquet
prepare loop [712-768]: normalized = normalize_parquet_remote(dir/stem__sheet.parquet)
        │  re.sub("__+","_") → stem_sheet.parquet
        ▼
converted: dict[normalized, (Path, local, remote)]
  ├─► 848 is_converted → skip copy_to_mirror(original)
  ├─► 603 _check_local_overwrite glob → refuse without --force
  └─► 364 _assert_cross_file_schema → group sheets per split
        ▼ (if not converted) copy_to_mirror(local, output_dir, remote) ← LEAK when guard misses
```

```
convert XLSX → {stem__aristas, stem__nodos} → normalize → {stem_aristas.parquet, stem_nodos.parquet}
is_converted?(norm_key=stem.parquet)
  BEFORE: k==norm_key || k.startswith("stem__") → False → copies stem.xlsx ✗
  AFTER:  + (k.startswith("stem_") && k!=norm_key) → True → SKIP ✓
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/prepare.py:848-854` | Modify | Site 1 — `is_converted` staging guard: dual `__`+`_` predicate |
| `src/sofer/prepare.py:603-619` | Modify | Site 2 — `_check_local_overwrite` XLSX branch: `glob __*.parquet` primary, fallback `glob _*.parquet` filtered `c.stem != stem` (mirrors `_mirror.py:239-252`) |
| `src/sofer/prepare.py:364-379` | Modify | Site 3 — `_assert_cross_file_schema` grouping: add `_` forms for `norm_stem` and `legacy_key` |
| `src/sofer/_mirror.py:239-252` | None | Reference PUB-10 fallback; no change |
| `src/sofer/_converters.py:70,94` | None | Unchanged; `__+→_` collapse stays |
| `tests/test_prepare.py` | Modify | Leak regression + overwrite fallback + single-sheet still-one-file |
| `openspec/specs/prepare/spec.md` | Modified | PRP-02 delta (already in change) |

### Function Map

| Function | File:Line | Role |
|----------|-----------|------|
| `prepare()` staging loop | `prepare.py:846-862` | Site 1 — prevents leak |
| `_check_local_overwrite()` | `prepare.py:571-639` | Site 2 — PRP-07 refusal |
| `_assert_cross_file_schema()` | `prepare.py:329-444` | Site 3 — sheet grouping |
| `expanded_planned_remotes()` | `_mirror.py:180-268` | Reference PUB-10 pattern |
| `normalize_parquet_remote()` | `_converters.py:37-73` | Root cause `:70` (unchanged) |
| `sanitize_sheet_name()` | `_converters.py:76-99` | Sheet sanitization (unchanged) |
| `convert_file_to_parquet()` | `_converters.py:541-593` | XLSX → `stem__sheet` before normalize |

## Interfaces / Contracts

No new public API. PRP-02 predicate change:

```python
# Before — misses normalized keys:
k == norm_key or k.startswith(norm_stem + "__")

# After — _mirror.py:239-252 fallback:
k == norm_key or k.startswith(norm_stem + "__") or (k.startswith(norm_stem + "_") and k != norm_key)
# _check_local_overwrite: glob __*.parquet primary, then _*.parquet filtered c.stem != stem
# _assert_cross_file_schema: also (k.startswith(legacy_key+"_") and k != legacy_key)
```

Invariant: single-sheet XLSX → `k == norm_key` exactly one file; guard short-circuits, never checks `_`.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit (new) | Leak regression: `DATA_GOT_ALL.xlsx` → clean `build/` only `data_got_all_*.parquet`, no `*.xlsx` | Temp `DatasetConfig` + `openpyxl` XLSX; assert `glob("*.xlsx")==[]` |
| Unit (new) | Overwrite fallback: `report_ventas.parquet` exists → without `--force` exit 1, with `--force` overwrites | Seed single-underscore parquet, call `prepare(force=…)` |
| Unit (new) | Schema grouping: `converted` has `data_got_all_aristas.parquet` → grouped | Synthetic `converted` dict |
| Regression | Single-sheet still → one `dataset.parquet` | Existing suite + explicit case |
| Gate | `uv run pytest tests/ -q` + `uv run mypy src/` green | `tasks.md` T2.3 |

Adversarial: `_` fallback is XLSX-only and requires `k != norm_key` / `c.stem != stem` to avoid `stem_foo.parquet` false positives. Leak test uses clean `build/`.

## Migration / Rollout

No migration. Single commit (3 sites + tests). No new config.

**Rollback**: revert 3 predicates/globs to `__`-only; delete stale `build/DATA_GOT_ALL.xlsx`. Normalized `_` files on disk remain valid; `final/` stays correct via `_mirror.py` fallback.

## Open Questions

- [ ] None blocking — `__` preservation deferred to future proposal (T3.1). Confirm `openpyxl` in CI (already a test dep).
