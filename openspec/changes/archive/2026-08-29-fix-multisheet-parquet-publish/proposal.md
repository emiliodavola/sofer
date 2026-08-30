# Proposal: fix-multisheet-parquet-publish

## Intent

`prepare` expands multi-sheet `.xlsx` to `stem__{sanitized}.parquet` per sheet; `publish` plan (`_mirror.planned_remotes`) emits single `stem.parquet` and only `_copy_package` globs correctly. Diff/dry-run, overwrite protection, split validation, and `build_dataset_card` reference a phantom remote, hide sheets, and mis-guard Hub files. Fix plan-vs-mirror without workbook I/O.

## Scope

### In Scope
- Helper `expanded_planned_remotes(cfg, keep_csv, staging_dir)` in `src/sofer/_mirror.py`: for convertible `.xlsx` (not recursive, `convert_to_parquet` true) glob `staging_dir/<dir>/<stem>__*.parquet`; emit normalized remotes, fallback to placeholder when mirror absent.
- Apply in `src/sofer/publish.py`: `_repo_diff_summary`, `_check_overwrite_protection`, `_print_split_mapping_validation`/`detect_splits`, dry-run.
- Apply in `src/sofer/repo_compliance.py:build_dataset_card` (Dataset Structure + `configs.data_files`).
- Reuse `sanitize_sheet_name` + `normalize_parquet_remote`; no duplication.
- Preserve single-sheet invariant (no `__` → no phantom), recursive skip, `keep_csv` CSV-only.

### Out of Scope
- Workbook I/O at plan time; new CLI flags; manifest file; `prepare` loop or ` _formats` changes; single-sheet naming.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `publish`: PUB-01/PUB-09 — diff, copy, protection, splits share one expanded remote set.
- `repo-compliance`: RC-Universal-Card — card lists N expanded parquet remotes for multi-sheet xlsx.

## Approach

Mirror-grounded expansion (A+C). Keep `planned_remotes` as logical placeholder for dry-run before prepare. Add `expanded_planned_remotes` that returns ground-truth when `staging_dir` exists, else placeholder. Dedup/normalization already in staged filenames, so no `openpyxl` needed. `_copy_package` switches from inline glob to shared helper.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/_mirror.py` | Modified | Add `expanded_planned_remotes`; doc `planned_remotes` as logical |
| `src/sofer/publish.py` | Modified | Use expanded remotes in diff, protection, splits, dry-run |
| `src/sofer/repo_compliance.py` | Modified | Card + `configs.data_files` via expanded helper |
| `src/sofer/_converters.py` | Unchanged | Reused sanitizer |
| `tests/test_mirror.py` | Modified | xlsx expansion cases |
| `tests/test_publish.py` | Modified | Multisheet mock (2+ sheets) + regression |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Caller uses raw `planned_remotes` | Med | Helper + lint comment; test `diff==staged` |
| Protection all-or-nothing | Med | Expand before guard; per-sheet check |
| Card/configs mismatch | Low | Same helper for both |
| Dry-run before prepare | Low | Fallback placeholder; no phantom sheets |
| Recursive/keep_csv edge | Low | Gate on `CONVERTIBLE_SUFFIXES`, `not recursive`, csv-only |

## Rollback Plan

Revert branch commits; placeholder remains compatible. No migration. Cherry-revert helper + call sites if shipped.

## Dependencies

- `sanitize_sheet_name`, `normalize_parquet_remote` (existing)
- Staging mirror layout via `copy_to_mirror`

## Success Criteria

- [ ] Multi-sheet (2 sheets) shows N `__sheet` remotes in diff, copy, protection, splits, card
- [ ] Single-sheet stays `stem.parquet` (no phantom)
- [ ] Protection guards per sheet
- [ ] No workbook I/O in planning (glob only)
- [ ] `uv run pytest tests/test_mirror.py tests/test_publish.py -q` green
