# Proposal: Fix Quality Checks Reporting Bugs

## Intent

Four bugs in `QualityValidator` produce false reports: (1) `ran_checks` never
surfaces to `ValidationReport`, making `_count_passed_quality` always report "0
passed"; (2) cross-file duplicate hashing flags rows in different files as
duplicates; (3) zero-row files (header-only CSVs) falsely trigger
`cross_file_types` and `empty_columns` warnings against data-bearing files.
These corrode trust in `sofer validate` / `sofer upload` output.

## Scope

### In Scope
- Propagate `QualityValidator._ran_checks` into `ValidationReport.ran_checks`
  (1 line in `cli.py` per command)
- Scope `_dup_hashes` per file so "Row 1 = Row 1" across files is never a
  duplicate (key = `f"{fname}|{row_str}"`)
- Skip zero-row files in `_check_cross_file_types` and `_check_empty_columns`

### Out of Scope
- Bloom-filter or streaming duplicate detection (P1)
- Full-file encoding scans (P1)
- Any structural (non-quality) check changes

## Capabilities

### Modified Capabilities
- `data-quality`: Fix `ran_checks` propagation to `ValidationReport`; scope
  duplicate detection per file; guard zero-row files in cross-file type and
  empty-column checks

## Approach

Three targeted fixes in `cli.py` (2 lines) and `quality.py` (~10 lines). No
new modules, no API changes. All changes are additive guards + one scoping fix.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/cli.py:61,95` | Modify | Copy `quality_report.ran_checks` into `report.ran_checks` |
| `src/sofer/quality.py:160` | Modify | Add `fname` to duplicate hash key |
| `src/sofer/quality.py:355-365` | Modify | Guard `_check_empty_columns` against zero-row files |
| `src/sofer/quality.py:466-484` | Modify | Guard `_check_cross_file_types` against zero-row files |
| `tests/test_quality.py` | Modify | Add regression tests for all 4 bugs |
| `tests/test_cli.py` | Modify | Assert `passed > 0` after validate |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Test gap for zero-row scenario | Low | Create a header-only CSV fixture explicitly |
| `ran_checks` propagation breaks upload path | Low | Both `_cmd_validate` and `_cmd_upload` touched identically |

## Rollback Plan

Revert 4 commits: the 3 fixes are independent. Each can be reverted in
isolation without breaking others.

## Dependencies

None. No new packages, no config changes.

## Success Criteria

- [ ] `sofer validate` reports `> 0 passed` when quality checks run
- [ ] Identical rows in different files do NOT produce duplicate warnings
- [ ] Header-only CSV files (0 data rows) do NOT trigger cross-file type or
      empty-column warnings
- [ ] 422 existing tests still pass; new regression tests cover all 4 bugs
