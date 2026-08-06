# Design: Schema Warnings Summary & File-Level Schema Opt-Out

## Technical Approach

Three independent changes on the same three files, each self-contained:

1. **config.py**: New `schema_dup_threshold` tool-wide config key (default `3`), exported as `SCHEMA_DUP_THRESHOLD`.
2. **model.py**: `include_in_schema: bool = True` on `FileEntry` + `from_toml()` parse.
3. **repo_compliance.py**: Accumulate duplicates in `_dup_map`, post-loop summary routed by threshold; skip `include_in_schema=False` files; all-excluded warning.

Backward compatibility: all new fields default to existing behavior.

## Architecture Decisions

### Decision: Accumulate duplicates instead of inline print

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Print inline (current) | Zero memory, but no way to count or group duplicates | Reject |
| Accumulate + count at end | ~O(D) memory (D = duplicate count), enables threshold routing without second pass | **Accept** |

**Rationale**: Threshold routing requires knowing the total duplicate count BEFORE printing. A second pass is wasteful; a single `_dup_map: dict[str, list[str]]` is cheap (even 100+ duplicates = a few KB).

### Decision: `_dup_map` uses `setdefault` pattern

```python
_dup_map.setdefault(col_name, []).append(origin_name)
```

**Rationale**: Same accumulation site for both Parquet and CSV code paths. `setdefault` avoids `if col_name not in _dup_map` boilerplate. Single dict with list values compactly encodes both count (`len(v)`) and filenames (summary display).

### Decision: `schema_dup_threshold` in `config.py`, not `DatasetConfig`

| Option | Tradeoff | Decision |
|--------|----------|----------|
| `config.py` (tool-wide) | One setting controls all datasets; user overrides once | **Accept** |
| `DatasetConfig` (per-dataset) | More granular, but duplicate warning verbosity is a UX preference, not dataset metadata | Reject |

**Rationale**: Whether 80 warnings are noise or signal is the same answer for all datasets. Dataset-specific threshold would be over-engineering.

### Decision: `include_in_schema` on `FileEntry`, not `DatasetConfig`

| Option | Tradeoff | Decision |
|--------|----------|----------|
| `FileEntry` field | Per-file granularity — mix data files and label tables in one config | **Accept** |
| `DatasetConfig` flag | All-or-nothing; can't have one data file + 80 label tables | Reject |

**Rationale**: A census dataset config declares 1 data file + 80 label tables. A togglable `DatasetConfig` flag forces the user to split into two configs. `FileEntry.include_in_schema` keeps one config.

## Data Flow

```
build_schema_report(cfg)
│
├─ _dup_map = {}                                    # init accumulator
│
├─ for entry in cfg.files:
│   ├─ ↓ entry.include_in_schema? → no → continue   # opt-out
│   ├─ ↓ .csv / not recursive?   → no → continue    # existing skip
│   ├─ [Parquet or CSV read]
│   ├─ for col in headers:
│   │   ├─ ↓ col in seen_names?
│   │   │   ├─ yes → _dup_map.setdefault(col, []).append(origin) → continue
│   │   │   └─ no  → infer, append ColumnSchema
│
├─ n_dups = sum(len(v) for v in _dup_map.values())
├─ if n_dups > 0:
│   ├─ n_dups ≤ SCHEMA_DUP_THRESHOLD → individual [!] warnings
│   └─ n_dups > SCHEMA_DUP_THRESHOLD → [i] summary (top 5 + tip)
│
├─ if not columns and _any_include_in_schema_true:
│   └─ warn "All files excluded from schema"
│
└─ return columns
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/config.py` | Modify | Add `"schema_dup_threshold": 3` to `_DEFAULTS`; export `SCHEMA_DUP_THRESHOLD` constant |
| `src/sofer/model.py` | Modify | Add `include_in_schema: bool = True` to `FileEntry` dataclass; parse in `from_toml()` |
| `src/sofer/repo_compliance.py` | Modify | `_dup_map` accumulation, threshold-routed summary, `include_in_schema` skip, all-excluded warning |

No files deleted. No new files.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `SCHEMA_DUP_THRESHOLD` loads from `pyproject.toml` | Temp TOML or config override in test |
| Unit | `FileEntry` default and `from_toml()` parse | Dataclass instantiation tests |
| Unit | Duplicate summary: ≤threshold → individual; >threshold → summary | Parametrized pytest with mock columns |
| Unit | `include_in_schema=False` skips file | Test `build_schema_report` with mixed entries |
| Integration | All-files-excluded warning | Config with all `include_in_schema=false` |
| Regression | Existing tests pass (422) | `uv run pytest tests/ -q` |

## Migration / Rollout

No migration required. `include_in_schema` defaults `True`, `schema_dup_threshold` defaults `3` — existing datasets behave identically. Users opt in by setting `include_in_schema = false` on label-table `[[file]]` entries.

## Open Questions

None — design is self-contained with no external dependencies.
