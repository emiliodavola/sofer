# Tasks: Schema Warnings Summary & File-Level Schema Opt-Out

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~110 (~50 prod + ~60 tests) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |
| Chain strategy | size-exception |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Config, model, duplicate summary, tests | PR 1 | All three files changed together; tests included |

## Phase 1: Config foundation

- [x] 1.1 Add `"schema_dup_threshold": 3` to `_DEFAULTS` dict in `src/sofer/config.py`
- [x] 1.2 Export `SCHEMA_DUP_THRESHOLD: int = _tool["schema_dup_threshold"]` constant in `src/sofer/config.py`
- [x] 1.3 RED → GREEN: Test default value (3) and custom TOML override in `tests/test_repo_compliance.py`

## Phase 2: FileEntry.include_in_schema

- [x] 2.1 RED: Write tests in `tests/test_model.py` for `include_in_schema` default (`True`), TOML parse (`false`), and `from_toml()` field-absent case
- [x] 2.2 GREEN: Add `include_in_schema: bool = True` to `FileEntry` dataclass in `src/sofer/model.py`; parse in `from_toml()`
- [x] 2.3 RED → GREEN: Test in `tests/test_repo_compliance.py` — file with `include_in_schema=False` skipped in `build_schema_report()`
- [x] 2.4 GREEN: Skip `include_in_schema=False` files in `build_schema_report()` loop in `src/sofer/repo_compliance.py`
- [x] 2.5 RED → GREEN: Test all files excluded → warning + empty list; GREEN: print warning before `return columns`

## Phase 3: Duplicate summary

- [x] 3.1 GREEN: Replace inline `print("[!] Duplicate column...")` with `_dup_map: dict[str, list[str]]` accumulation using `setdefault` in `build_schema_report()` (both Parquet and CSV paths)
- [x] 3.2 GREEN: Add post-loop summary block: `n_dups ≤ SCHEMA_DUP_THRESHOLD` → individual `[!]` lines; `> SCHEMA_DUP_THRESHOLD` → single `[i]` summary with top-5 columns + tip referencing `include_in_schema`
- [x] 3.3 RED → GREEN: Parametrized test — ≤threshold individual lines; >threshold summary; zero duplicates silent; summary includes "top 5" + tip message

## Phase 4: Verify

- [x] 4.1 Full test suite: `uv run pytest tests/ -q`
- [x] 4.2 Ruff: `uv run ruff check src/ tests/`
- [x] 4.3 Mypy: `uv run mypy src/`
