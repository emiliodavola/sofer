# Design: Fix Quality Checks Reporting Bugs

## Technical Approach

Four targeted, independent fixes across 2 source files (`cli.py`, `quality.py`)
totaling ~12 lines of production code. No new modules, no API surface changes.

## Architecture Decisions

### Decision: File-scoped duplicate hashing

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Add `fname` to hash key | Simple, 1-line change | ✅ Chosen |
| Clear `_dup_hashes` per file | Requires cleanup in `_process_file`, same effect | ❌ Rejected — more invasive |

**Choice**: Prefix hash key with `f"{fname}|"`.
**Rationale**: `_process_file` already tracks `self._current_file`; minimal
change to `_distribute_row` line 308.

### Decision: Skip zero-row files via `_file_row_count`

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Check `self._file_row_count[fname] == 0` | Uses existing accumulator | ✅ Chosen |
| Add `len(_col_nonempty) == 0` guard | Fragile proxy (header with no data would hit empty set anyway) | ❌ Rejected |

**Choice**: In `_check_empty_columns` and `_check_cross_file_types`, skip
files where `_file_row_count[fname] == 0`.
**Rationale**: `_file_row_count` is already populated per file in
`_process_file`. A zero-row file has no data to check.

### Decision: Copy ran_checks in cli.py, not quality.py

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Copy in `cli.py` | Keeps `QualityValidator` output portable | ✅ Chosen |
| Set `report.ran_checks` inside `QualityValidator.run()` | Couples quality runner to DatasetValidator's report | ❌ Rejected |

**Choice**: After `quality.run()`, add `report.ran_checks = quality_report.ran_checks`.
**Rationale**: `QualityValidator` already sets `self._report.ran_checks` on
line 147; the bug is that `_cmd_validate` and `_cmd_upload` never propagate it
to the `DatasetValidator`'s report.

## Data Flow

```
QualityValidator.run()
  ├── _process_file("a.csv")
  │     └── _distribute_row → hash key = f"{fname}|{row_str}"
  ├── _process_file("b.csv")
  │     └── _file_row_count["b.csv"] = 0  (header-only)
  ├── _check_empty_columns()
  │     └── skip if _file_row_count[f] == 0  ← NEW guard
  ├── _check_cross_file_types()
  │     └── skip if _file_row_count[f] == 0  ← NEW guard
  └── returns quality_report (with ran_checks set)

_cmd_validate()
  ├── report = validator.run_all()
  ├── quality_report = quality.run()
  ├── report.ran_checks = quality_report.ran_checks  ← NEW (1 line)
  ├── report.quality_results = quality_report.quality_results
  └── report.print_summary() → _count_passed_quality(ran_checks=non-empty) → >0 passed
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/cli.py:61` | Modify | Add `report.ran_checks = quality_report.ran_checks` in `_cmd_validate` |
| `src/sofer/cli.py:95` | Modify | Same line in `_cmd_upload` |
| `src/sofer/quality.py:308` | Modify | Hash key from `row_str` to `f"{fname}|{row_str}"` |
| `src/sofer/quality.py:355-365` | Modify | Guard `_check_empty_columns` per-file with `_file_row_count[fname] > 0` |
| `src/sofer/quality.py:472-478` | Modify | Guard `_check_cross_file_types` per-file with `_file_row_count[fname] > 0` |
| `tests/test_quality.py` | Modify | Add test fixtures: header-only CSV, identical rows across files |
| `tests/test_cli.py` | Modify | Assert `passed > 0` in validate summary output |

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `_check_duplicates` scoping | Test with two files sharing identical row content |
| Unit | `_check_empty_columns` zero-row guard | Test with header-only CSV fixture |
| Unit | `_check_cross_file_types` zero-row guard | Test with one data file + one header-only file |
| Integration | `_count_passed_quality` returns >0 | Mock or full validate run, capture stdout |

## Migration / Rollout

No migration required. No config changes, no API breakage.
