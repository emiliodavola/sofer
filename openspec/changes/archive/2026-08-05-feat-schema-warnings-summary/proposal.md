# Proposal: Schema Warnings Summary & File-Level Schema Opt-Out

## Intent
`build_schema_report()` prints one `[!] Duplicate column 'X' across files...` line per duplicate. For datasets with 80+ label/lookup tables (e.g., census microdata), this produces 80+ lines of noise that bury real schema issues. Two changes: (1) threshold-governed duplicate summary (accumulate, print single `[i]` summary when >threshold), (2) per-file `include_in_schema` opt-out on `[[file]]` entries so label tables don't contribute columns to the Dataset Card while still being uploaded.

## Scope

### In Scope
- `schema_dup_threshold` config key (default 3) in `config.py:_DEFAULTS`, exported as `SCHEMA_DUP_THRESHOLD`
- `build_schema_report()`: accumulate duplicates in `_dup_map`, print summary when count > threshold (top 5 + tip about `include_in_schema`)
- `build_schema_report()`: skip files where `entry.include_in_schema is False`
- New `include_in_schema: bool = True` on `FileEntry`, parsed from `[[file]]` TOML in `from_toml()`
- Warning when ALL files have `include_in_schema = false`

### Out of Scope
- Auto-detection heuristics for label/lookup tables
- Changing ColumnSchema return type or downstream consumers

## Approach
- **config.py**: `"schema_dup_threshold": 3` → `SCHEMA_DUP_THRESHOLD`
- **model.py**: `FileEntry.include_in_schema: bool = True` + `from_toml` parse
- **repo_compliance.py**: file loop skips `include_in_schema=False`; `_dup_map` dict accumulates duplicates; end-of-function summary print with top-5 columns + tip when count > threshold; all-excluded warning

## Affected Areas
- `src/sofer/config.py` — new config key
- `src/sofer/model.py` — FileEntry field + from_toml parse
- `src/sofer/repo_compliance.py` — duplicate accumulation, summary, schema opt-out
- `openspec/specs/repo-compliance/spec.md` — §3.3 delta

## Risks
- Backward-compatible: `include_in_schema` defaults True, threshold defaults 3 → unchanged behavior
- ≤threshold still prints individual lines → zero information loss
- All-excluded warning: single advisory line, suppressed when ≥1 file included

## Success Criteria
- `schema_dup_threshold` readable from `[tool.sofer]` (default 3)
- ≤threshold → individual `[!]` lines; >threshold → single `[i]` summary + top 5 + tip
- `include_in_schema = false` files excluded from schema, still uploaded
- Warning when ALL files excluded
- All existing tests pass
