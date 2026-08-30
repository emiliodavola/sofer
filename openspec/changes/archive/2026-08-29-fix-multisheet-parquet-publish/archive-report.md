# Archive Report: fix-multisheet-parquet-publish

**Change**: 2026-08-29-fix-multisheet-parquet-publish
**Branch**: fix/multisheet-parquet-publish
**Archived**: 2026-08-29
**Archived to**: `openspec/changes/archive/2026-08-29-fix-multisheet-parquet-publish/`
**Mode**: hybrid (Engram + openspec)
**Verdict**: PASS WITH WARNINGS — 0 critical, 3 warnings, ready for PR to dev

---

## 1. Intent

`prepare` expands multi-sheet `.xlsx` to `stem__{sanitized}.parquet` per sheet; `publish` plan (`_mirror.planned_remotes`) emitted single `stem.parquet` and only `_copy_package` globbed correctly. Diff/dry-run, overwrite protection, split validation, and `build_dataset_card` referenced a phantom remote, hid sheets, and mis-guarded Hub files. Fix plan-vs-mirror without workbook I/O via `expanded_planned_remotes(cfg, keep_csv, staging_dir)` globbing `staging_dir/<dir>/<stem>__*.parquet` sorted, fallback to logical placeholder.

## 2. Phases

| Phase | Artifact | ID / Path | Status |
|-------|----------|-----------|--------|
| Proposal | `sdd/2026-08-29-fix-multisheet-parquet-publish/proposal` + `proposal.md` | #684 | done — 68 lines, intent/scope/approach, risks/rollback, success criteria |
| Spec | `sdd/2026-08-29-fix-multisheet-parquet-publish/spec` + `specs/{2 domains}/spec.md` | #686 | done — 2 deltas, 4 requirements (PUB-10 ADDED, PUB-01 MODIFIED, PUB-09 MODIFIED, RC-Universal-Card MODIFIED), 19 scenarios |
| Design | `sdd/2026-08-29-fix-multisheet-parquet-publish/design` + `design.md` | #688 | done — 80 lines, mirror-grounded expansion, decisions (helper in _mirror, glob vs workbook/manifest), flow, contracts, testing strategy |
| Tasks | `sdd/2026-08-29-fix-multisheet-parquet-publish/tasks` + `tasks.md` | #690 | done — 13/13 [x], 4 phases, 400-line budget risk Low, single PR |
| Apply-progress | `sdd/2026-08-29-fix-multisheet-parquet-publish/apply-progress` + `apply-progress.md` | — | done — commit 1142de5 + d3a7172, 13/13 tasks, deviations documented (single-underscore fallback) |
| Verify-report | `sdd/2026-08-29-fix-multisheet-parquet-publish/verify-report` + `verify-report.md` | #694 | PASS WITH WARNINGS — 976 passed, 2 skipped, ruff+mypy green, 19/19 scenarios (18 COMPLIANT, 1 PARTIAL), 0 critical |

**Task Completion Gate**: `tasks.md` 13/13 checked — no stale unchecked tasks. Verified via file `archive/tasks.md` and Engram #690.

## 3. Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| publish | Updated | 1 ADDED (PUB-10 expanded planned remotes via mirror scan, 3 scenarios) + 2 MODIFIED (PUB-01 hf target via expanded remotes — 8→9 scenarios; PUB-09 delegation invariant — expanded ground truth, 2 scenarios) |
| repo-compliance | Updated | 1 MODIFIED (RC-Universal-Card via expanded when staging available else fallback, 2→5 scenarios: tsv, xlsx N, Structure, Fallback, configs==Structure) |

**Source of Truth Updated**:
- `openspec/specs/publish/spec.md` — PUB-01 and PUB-09 replaced, PUB-10 appended (preserves PUB-02, PUB-03, PUB-04, PUB-05, PUB-07, PUB-08)
- `openspec/specs/repo-compliance/spec.md` — §4.20 RC-Universal-Card replaced (preserves §§1-4.19, 5-8)

No REMOVED or RENAMED requirements; no destructive delta — preserved all other requirements per archive skill merge contract.

## 4. Archive Contents

- proposal.md ✅ (68 lines)
- specs/publish/spec.md ✅ (91 lines delta, 3 requirements: PUB-10 ADDED, PUB-01/PUB-09 MODIFIED, 14 scenarios)
- specs/repo-compliance/spec.md ✅ (34 lines delta, 1 requirement: RC-Universal-Card MODIFIED, 5 scenarios)
- design.md ✅ (80 lines)
- tasks.md ✅ (13/13 complete)
- apply-progress.md ✅ (13/13, deviations: single-underscore fallback, recursive * simplification)
- verify-report.md ✅ (PASS WITH WARNINGS, 19/19, 976 tests green)
- exploration.md ✅ (exploratory context)
- archive-report.md ✅ (this file)

**Active changes directory** no longer contains `2026-08-29-fix-multisheet-parquet-publish` — moved to `archive/2026-08-29-fix-multisheet-parquet-publish/`.

## 5. File Changes (single work-unit commit 1142de5 + verify commit d3a7172)

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/_mirror.py` | Modified | Added `expanded_planned_remotes(cfg, keep_csv, staging_dir)` — gated `.xlsx` via `_is_convertible_entry`+`convert_to_parquet`, glob `staging_dir/<dir>/<stem>__*.parquet` sorted, fallback to `planned_remotes`, reuse `normalize_parquet_remote`, no workbook I/O; documented `planned_remotes` as logical placeholder; backward-compat single-underscore fallback |
| `src/sofer/publish.py` | Modified | `_repo_diff_summary(cfg, existing, keep_csv, codebook_remotes, staging_dir)` derives via `expanded_planned_remotes` when mirror exists, marks recursive `*`, shares set with protection/splits; `_check_overwrite_protection` accepts expanded `planned_files` per-sheet; `_copy_package` iterates expanded remotes via `copy_to_mirror` (drops inline glob); dry-run/split paths consume expanded count N |
| `src/sofer/repo_compliance.py` | Modified | `build_dataset_card(..., keep_csv=False, staging_dir=None)` uses `expanded_planned_remotes` for `configs.data_files` + `Dataset Structure` when `staging_dir.is_dir()` else fallback; row_counts verbatim key preserved, no local path leak |
| `src/sofer/prepare.py` | Modified | Pass `staging_dir=output_dir` to `build_dataset_card` so card reflects expanded N |
| `tests/test_mirror.py` | Modified | Added `TestExpandedPlannedRemotes` (9 cases: multi expands N, single stays single, fallback None/not-dir, recursive/keep_csv invariants, no openpyxl, nested) |
| `tests/test_publish.py` | Modified | Added `TestMultiSheetPublish` (2-sheet mock staging `report__ventas`/`report__costos`, diff lists 2, per-sheet protection, stages N, splits 2, dry-run N) + `TestSingleSheetRegression` (no phantom `__`) |
| `tests/test_repo_compliance.py` | Modified | Added `TestExpandedCard` (N remotes with staging, fallback without, configs==Structure, no local path leak) |

2 commits on branch `fix/multisheet-parquet-publish`: `1142de5 fix(publish): expand multi-sheet xlsx via mirror-grounded remotes` + `d3a7172 chore(sdd): add verify-report`.

## 6. Test Evidence

```
uv run pytest tests/test_mirror.py tests/test_publish.py tests/test_repo_compliance.py -q
266 passed in 2.24s

uv run pytest tests/ -q
976 passed, 2 skipped, 13 warnings in 14.21s
Warnings: 13 DeprecationWarning from tests/test_codebook.py (_infer_type deprecated -> infer_column_type), non-blocking

uv run ruff check src/ tests/
All checks passed!

uv run mypy src/
Success: no issues found in 27 source files
```

19/19 delta scenarios covered (18 COMPLIANT, 1 PARTIAL — RC tsv as parquet via same normalization path, no dedicated tsv card unit). Full suite green. Manual verification via mocked `HfApi` + `tmp_path` staging confirms expanded==staged, diff/protection/splits agree.

## 7. Warnings (non-blocking, per verify-report id 694)

1. **Backward-compat single-underscore fallback in `expanded_planned_remotes`** — `src/sofer/_mirror.py:244-252` adds `stem_*.parquet` fallback when `__` glob empty. Deviation from spec strict `__*.parquet` is documented and keeps existing `prepare` output working (current `_converters` normalizes `__` to `_`), but should be removed or reconciled once `normalize_parquet_remote` stops collapsing `__`. Low risk.
2. **RC tsv card scenario lacks explicit tsv unit test** — compliance PARTIAL. Underlying code path identical to csv/xlsx (`CONVERTIBLE_SUFFIXES`), but no dedicated `data/x.tsv -> data/x.parquet` card assertion. Add parametrized test to `test_repo_compliance.py`.
3. **Open question not yet resolved** — `build_dataset_card` caller in `prepare.py` now passes `staging_dir=output_dir` (verified `src/sofer/prepare.py:826,836`), but local-target card ground truth vs destination remains open per design.

No CRITICAL issues — archive not blocked; warnings recorded as intentional-with-warnings per strict-vs-OpenSpec policy.

## 8. Breaking Change Note

None — bugfix preserves placeholder compatibility pre-prepare (`report.parquet` when mirror absent). Post-prepare, multi-sheet now correctly shows N `__sheet` remotes in diff, copy, protection, splits, and card — previously phantom-hid sheets. Single-sheet invariant unchanged. Users with legacy single-underscore sheet files (`report_ventas.parquet`) still work via fallback. Large XLSX not stressed (glob cheap, prepare handles `read_only,data_only`).

## 9. Next Steps (follow-up)

- **Test: add tsv card parametrized case** — `tests/test_repo_compliance.py` for `data/x.tsv` → `data/x.parquet` explicit assertion to reach 19/19 fully COMPLIANT.
- **Chore: reconcile single-underscore fallback** — document removal plan when `normalize_parquet_remote` collapse fixed; currently non-breaking.
- **Consider `uv run ruff format --check` in CI** — 51 files already formatted, not gating.

## 10. SDD Cycle Complete

The change has been fully planned, implemented, verified (PASS WITH WARNINGS), and archived. Main specs now reflect multi-sheet mirror-grounded expansion. Branch retains commits and is ready for PR to `dev` (fix/multisheet-parquet-publish → dev).

**Traceability**: Engram IDs 684/686/688/690/694 + filesystem archive `openspec/changes/archive/2026-08-29-fix-multisheet-parquet-publish/` is audit trail — never delete or modify archived changes.

---

*Generated by sdd-archive sub-agent (muse-spark-1.2-contributor) — hybrid persistence, Task Completion Gate passed, CRITICAL=0.*
