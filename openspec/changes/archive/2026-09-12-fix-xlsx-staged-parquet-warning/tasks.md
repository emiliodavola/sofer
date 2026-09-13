# Tasks: fix-xlsx-staged-parquet-warning

Closes #150: `sofer_prepare` prints a misleading `[!]` warning for multi-sheet
XLSX (`Staged Parquet '<base>.parquet' not found … falling back to CSV
inference.`) even though per-sheet Parquets exist under collapsed
single-underscore names. Fix = dual-layout staged lookup (one shared
module-private helper, AGENTS.md rule 4, mirroring
`_mirror.expanded_planned_remotes` / `prepare._check_local_overwrite`) + two
shared warning-template constants with a format-generic tail, applied at all
four print sites. Strict TDD off (`config.yaml strict_tdd: false`); spec delta
(`RC-R22` + §4.19 amendment + RC-R14 prose tail) already written in the
proposal phase. Branch: `fix/150-xlsx-staged-warning`.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~615 total — ~265 executable (~95 code `repo_compliance.py` +45/−50; ~170 tests) + ~350 docs (spec delta ~180 already in place from proposal, tasks.md ~120, verify.md ~50). Executable review surface ~265, inside the 400-line budget; doc bulk is change artifacts (fix-residual-parity precedent) and the session review budget is 800 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending (not needed — single PR; chaining deferred until selected) |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low
```

> Forecast math note (explicit, per parent instruction): raw total with docs
> ~615 exceeds the canonical 400, but the line-by-line review load is the
> executable surface (~265 code+tests, additions+deletions) which sits well
> inside the budget; the ~350 doc lines are SDD artifacts, ~180 of which (spec
> delta) were already reviewed at proposal. Same accounting as the archived
> fix-residual-parity forecast (~385 total → Low, single PR). Nothing changed
> this math → Low / single PR / Decision: No stand.

### Suggested Work Units

| Unit | Goal | Likely PR | Boundaries (start → finish · verify · rollback) |
|------|------|-----------|------------------------------------------------|
| 1 | Implementation: `_staged_xlsx_sheet_parquets` + 2 warning constants + 4-site swaps in `src/sofer/repo_compliance.py` | PR 1 | 1.1 → 1.7 · `uv run pytest tests/test_repo_compliance.py -q` (existing warn-path tests green) · single-commit `git revert` |
| 2 | Tests: promote `_stage_parquet` to module level + `_make_xlsx` + `TestBuildSchemaReportXlsxStaged` (4) in `tests/test_repo_compliance.py` | PR 1 | 2.1 → 2.6 · `-k TestBuildSchemaReportXlsxStaged` 4 passed · revert with unit 1 |
| 3 | Gates: full suite + ruff + format + mypy + `git diff --check` | PR 1 | 3.1 → 3.4 · all green · revert with units 1+2 |
| 4 | OpenSpec lifecycle: apply-progress, verify.md, canonical spec sync, archive, bounded review | PR 1 | 4.1 → 4.4 (parent-owned) · canonical `openspec/specs/repo-compliance/spec.md` reflects RC-R22 · docs-only revert |

Out of scope boundaries to respect during unit 1: do NOT touch
`src/sofer/_mirror.py` or `src/sofer/prepare.py` — cross-module consolidation
onto the new helper is a tracked follow-up (their behavior is already correct
and test-covered). No CLI/MCP/config surface; no README/README_ES sync
(grep-verified: no documented warning string, AGENTS.md rule 13 not triggered).

## Phase 1: Implementation — helper + constants + site swaps (`src/sofer/repo_compliance.py`)

- [x] 1.1 Add the two module-level warning-template constants `_WARN_STAGED_PARQUET_MISSING` and `_WARN_STAGED_PARQUET_UNREADABLE` immediately above `_build_schema_report_impl` (~L436): double-quoted format strings with `{key}` (and `{failure_class}` at the two unreadable sites) slots, exact tails `falling back to original-file inference.`, preserving the leading `"  [!] "` prefix (exactly two spaces) byte-for-byte. <!-- sdd-owner: implementation -->
  - **Evidence:** Added `_WARN_STAGED_PARQUET_MISSING` / `_WARN_STAGED_PARQUET_UNREADABLE` above `_build_schema_report_impl`; tails `falling back to original-file inference.`; `"  [!] "` prefix byte-exact.
- [x] 1.2 Add module-private `_staged_xlsx_sheet_parquets(staging_dir: Path, parquet_key: str) -> list[Path]` before `_build_schema_report_impl` exactly per design §3.1: derive `base_parent`/`base_stem` via `PurePosixPath`; guard `search_dir.is_dir()` (return `[]` when missing); primary `sorted(search_dir.glob(f"{base_stem}__*.parquet"))` filtered to files, returned when non-empty; else fallback `sorted(search_dir.glob(f"{base_stem}_*.parquet"))` filtered to files AND `p.stem != base_stem` (bare `stem.parquet` excluded). Full docstring documenting the dual layout, the `c.stem != stem` exclusion, and the `[]`-on-no-match contract; uses only existing imports (`Path`, `PurePosixPath`) — no new imports. <!-- sdd-owner: implementation -->
  - **Evidence:** `_staged_xlsx_sheet_parquets` per design §3.1 (dual-layout glob, `c.stem != base_stem` exclusion, `[]` on missing dir); no new imports.
- [x] 1.3 First XLSX glob site (~L507-522): replace the `base_parent`/`base_stem`/`search_dir` derivation + `is_dir()`-gated `stem__*` glob with `sheet_paths = _staged_xlsx_sheet_parquets(staging_dir, parquet_key)` followed by an unconditional `single = staging_dir / PurePosixPath(parquet_key)` appended only when `single.is_file()`; keep the existing decision shape `if sheet_paths: parquet_path = sheet_paths[0]; use_parquet = True; origin_name = parquet_key`. Behavior-neutral: the `is_dir()` gate moves into the helper; `single.is_file()` is False when the parent dir is absent. <!-- sdd-owner: implementation -->
  - **Evidence:** First XLSX glob site delegates to the helper; unconditional `single.is_file()` base append preserved.
- [x] 1.4 First XLSX warn site (~L531-533): swap the inline f-string to `print(_WARN_STAGED_PARQUET_MISSING.format(key=parquet_key))`, keeping the `elif parquet_key not in _warned_missing:` guard and the `_warned_missing.add(parquet_key)` line (warn-once contract preserved). <!-- sdd-owner: implementation -->
  - **Evidence:** First XLSX warn site -> `_WARN_STAGED_PARQUET_MISSING.format(key=parquet_key)`; warn-once guard + add kept.
- [x] 1.5 Non-XLSX branch (~L536-547): logic untouched — only the print swaps to `_WARN_STAGED_PARQUET_MISSING.format(key=parquet_key)`; keep `candidate.exists()` → single-file read vs. warn-once + source fallback unchanged so `test_missing_parquet_warns_once_and_falls_back_to_csv` / `test_missing_parquet_warns_once_per_unique_key` stay green unmodified. <!-- sdd-owner: implementation -->
  - **Evidence:** Non-XLSX branch logic untouched; print swapped to the shared missing template.
- [x] 1.6 Second XLSX collection (~L548-561): replace the duplicated derivation + `stem__*` glob with `xlsx_sheet_paths = _staged_xlsx_sheet_parquets(staging_dir, parquet_key)` + the same unconditional single-file append; remove the now-dead duplicate comments. The per-sheet loop guard (~L577) and the `use_parquet` flag now derive from the identical helper call, so the flag and the loop's file list can never disagree. <!-- sdd-owner: implementation -->
  - **Evidence:** Second XLSX collection delegates to the helper; dead duplicate comments removed.
- [x] 1.7 Swap the two unreadable prints: single-file site (~L571-573) → `_WARN_STAGED_PARQUET_UNREADABLE.format(key=parquet_key, failure_class=failure_class)`; per-sheet site (~L588-590) → `.format(key=sheet_origin, failure_class=failure_class)`; keep the `_warned_unreadable` warn-once guards and `continue` flow. Leave untouched: per-sheet loop internals (`sheet_origin = sheet_path.relative_to(staging_dir).as_posix()`, `row_counts.setdefault(entry.remote + f"::{sheet_origin}", pf_s.metadata.num_rows)` at ~L594), single-file read (~L646), first-sheet-only source fallback (`ws_f = wb_f[wb_f.sheetnames[0]]` at ~L704 — documented-unchanged degradation), `_read_parquet_sample` / `_classify_parquet_read_failure`. <!-- sdd-owner: implementation -->
  - **Evidence:** Both unreadable prints -> `_WARN_STAGED_PARQUET_UNREADABLE.format(key=..., failure_class=...)`; per-sheet loop internals untouched.

Evidence 1.1-1.7: `uv run pytest tests/test_repo_compliance.py -q` — the two
existing warn-path tests (`test_missing_parquet_warns_once_and_falls_back_to_csv`,
`test_missing_parquet_warns_once_per_unique_key`) and `TestStagedParquetRemoteRelativeLookup`
stay green; `uv run ruff check src/sofer/repo_compliance.py` clean. Warning
strings now come only from the two constants — grep `falling back to CSV` in
`src/sofer/` must return zero hits.

## Phase 2: Tests — `TestBuildSchemaReportXlsxStaged` (`tests/test_repo_compliance.py`)

- [x] 2.1 Promote the `TestStagedParquetRemoteRelativeLookup._stage_parquet` static method body (~L2044-2057) to a module-level `_stage_parquet(stage: Path, remote_key: str, table: object) -> None` helper (pyarrow-direct `pq.write_table` at the remote-relative key, `test_clean.py:56-73` style), and leave the old static method as a one-line delegation so all existing `self._stage_parquet` call sites keep working (AGENTS.md rule 4). <!-- sdd-owner: implementation -->
  - **Evidence:** `_stage_parquet` promoted to module-level; static method now one-line delegation; all existing `self._stage_parquet` call sites green.
- [x] 2.2 Add a module-local `_make_xlsx(path: Path, sheets: dict[str, list[list[object]]]) -> None` copy in `tests/test_repo_compliance.py` — identical to the existing 5-file convention (`test_clean.py:32`, openpyxl, header-first rows); no new dependencies (openpyxl + pyarrow already present). <!-- sdd-owner: implementation -->
  - **Evidence:** Module-local `_make_xlsx(path, sheets)` added (matches test_clean.py:32 convention).
- [x] 2.3 `test_multi_sheet_collapsed_staged_parquets_stay_silent` (RC-R22 scenario 1): `DATA_GOT_ALL.xlsx` via `_make_xlsx` with sheets `aristas` (`["id","src"]`, 1 row) + `nodos` (`["id","label"]`, 1 row); stage collapsed `data_got_all_aristas.parquet` / `data_got_all_nodos.parquet` only (NO base `data_got_all.parquet`); `FileEntry(local=xlsx, remote="DATA_GOT_ALL.xlsx")` (capitalized remote pins case-insensitive suffix + verbatim-remote keys); `build_schema_report_with_rows(cfg, staging_dir=stage)`; assert `capsys` out has no `[!]`, origins == `{"data_got_all_aristas.parquet", "data_got_all_nodos.parquet"}`, and `row_counts == {"DATA_GOT_ALL.xlsx::data_got_all_aristas.parquet": 1, "DATA_GOT_ALL.xlsx::data_got_all_nodos.parquet": 1}` (exact `::` keys per the ~L594 contract). <!-- sdd-owner: implementation -->
  - **Evidence:** `test_multi_sheet_collapsed_staged_parquets_stay_silent` — no `[!]`, origins == collapsed keys, exact `::` row_counts.
- [x] 2.4 `test_multi_sheet_spec_layout_double_underscore_stays_silent` (RC-R22 scenario 2): `report.xlsx` (sheets `ventas`, `costos`); stage `report__ventas.parquet` + `report__costos.parquet` only (no single-underscore near-neighbors); remote `report.xlsx`; assert no `[!]`, both double-underscore keys appear in origins, `row_counts` keyed `report.xlsx::report__ventas.parquet` / `report.xlsx::report__costos.parquet` — dual-modality regression guard for `test_mirror`/`TestExpandedCard` stubs (primary-wins is structurally guaranteed by the helper). <!-- sdd-owner: implementation -->
  - **Evidence:** `test_multi_sheet_spec_layout_double_underscore_stays_silent` — primary layout resolves; `report.xlsx::report__*.parquet` keys.
- [x] 2.5 `test_single_sheet_staged_parquet_stays_silent` (RC-R22 scenario 3): single-sheet `report.xlsx`; stage bare `report.parquet` only (artifact == key); assert no `[!]`, `origins == {"report.parquet"}`, and `row_counts == {"report.xlsx::report.parquet": n}` — pins that the base file flows through the single-item per-sheet loop (RC-R07 `::` keying unchanged, NOT "fixed"). <!-- sdd-owner: implementation -->
  - **Evidence:** `test_single_sheet_staged_parquet_stays_silent` — pin `report.xlsx::report.parquet` row-count key.
- [x] 2.6 `test_multi_sheet_missing_staged_parquet_still_warns_once` (RC-R22 scenario 5): multi-sheet `DATA_GOT_ALL.xlsx` written via REAL openpyxl `_make_xlsx` (fallback re-reads the source), empty/unmatching `stage`; assert exactly one `[!]` line containing `data_got_all.parquet` AND `original-file inference` (pins the reword); `row_counts == {"DATA_GOT_ALL.xlsx": 1}`; origins == `{"DATA_GOT_ALL.xlsx"}`; sheet-2 column (`label`) absent — first-sheet-only degradation asserted as documented-unchanged. <!-- sdd-owner: implementation -->
  - **Evidence:** `test_multi_sheet_missing_staged_parquet_still_warns_once` — one `[!]`, `data_got_all.parquet` + `original-file inference`, first-sheet-only fallback asserted.

Evidence 2.1-2.6 (staging helpers + new class inserted between
`TestStagedParquetRemoteRelativeLookup` end ~L2211 and `TestDataFieldsFileColumn`
~L2213):
`PYTHONIOENCODING=utf-8 uv run pytest tests/test_repo_compliance.py -k TestBuildSchemaReportXlsxStaged -q` → **4 passed**;
`PYTHONIOENCODING=utf-8 uv run pytest tests/test_repo_compliance.py -q` → full
file green including the unmodified warn-path tests (`test_missing_parquet_*`).

Acceptance mapping (AGENTS.md rule 6) — new class covers RC-R22 scenarios
1, 2, 3, 5; scenario 4 (non-XLSX miss) is covered by the two existing
unmodified tests:

| RC-R22 scenario | Test |
|---|---|
| Multi-sheet collapsed single-underscore stays silent | 2.3 (new) |
| Spec-layout double-underscore still recognized | 2.4 (new) |
| Single-sheet XLSX stays silent | 2.5 (new) |
| Genuine non-XLSX miss warns once | existing `test_missing_parquet_warns_once_and_falls_back_to_csv` + `test_missing_parquet_warns_once_per_unique_key` |
| Genuine multi-sheet XLSX miss warns once, corrected tail | 2.6 (new) |

## Phase 3: Verification + gates

- [x] 3.1 Fast loop: `PYTHONIOENCODING=utf-8 uv run pytest tests/test_repo_compliance.py -q` (new 4 + existing warn-path + relative-lookup tests). <!-- sdd-owner: implementation -->
  - **Evidence:** `PYTHONIOENCODING=utf-8 uv run pytest tests/test_repo_compliance.py -q` -> 185 passed (incl. untouched warn-path tests).
- [x] 3.2 Full suite (additive, no new dependencies): `PYTHONIOENCODING=utf-8 uv run pytest tests/ -q`. <!-- sdd-owner: implementation -->
  - **Evidence:** `PYTHONIOENCODING=utf-8 uv run pytest tests/ -q` -> 1528 passed, 6 skipped, 13 warnings.
- [x] 3.3 Quality gates: `uv run ruff check src/ tests/`, `uv run ruff format --check src/ tests/`, `uv run mypy src/` (CI runs mypy under Python 3.13; do not add mypy to the version matrix per AGENTS.md rule 12), and `git diff --check`. <!-- sdd-owner: implementation -->
  - **Evidence:** `uv run ruff check src/ tests/` clean; `uv run ruff format --check src/ tests/` 65 files already formatted; `uv run mypy src/` Success (32 files); `git diff --check` clean.
- [x] 3.4 Confirm spec-δ completeness: every RC-R22/amended scenario has a test (4 new + 2 existing); `_make_xlsx`/`_stage_parquet` are single-source helpers; no hardcoded values introduced outside the two warning constants (AGENTS.md rules 1, 6). <!-- sdd-owner: implementation -->
  - **Evidence:** RC-R22 s1/s2/s3/s5 -> 4 new tests; s4 -> existing `test_missing_parquet_warns_once_and_falls_back_to_csv` + `test_missing_parquet_warns_once_per_unique_key`; helpers are single-source; only new literals are the two warning constants.

Evidence 3.1-3.4: record actual command output (not placeholders) — full-suite
pass/fail counts, ruff/format/mypy clean, `git diff --check` silent. These
results feed `verify.md` in unit 4.

## Phase 4: OpenSpec lifecycle + bounded review (parent-owned, after implementation)

- [x] 4.1 Verify the change-local spec delta is in place and complete (`openspec/changes/fix-xlsx-staged-parquet-warning/specs/repo-compliance/spec.md`: NEW RC-R22 with 5 scenarios, RC-Universal §4.19 XLSX-scenario prose amended to dual-layout wording, RC-R14 prose tail aligned); update apply-progress. <!-- sdd-owner: parent -->
- [x] 4.2 Populate `openspec/changes/fix-xlsx-staged-parquet-warning/verify-report.md` with the §3 gate results (full suite + ruff + format + mypy + `git diff --check`). <!-- sdd-owner: parent -->
- [x] 4.3 Sync the delta into canonical `openspec/specs/repo-compliance/spec.md` on merge to `dev` (RC-R22 appended after RC-R21; §4.19 XLSX-paragraph amended; RC-R14 prose tail replaced) — AGENTS.md rule 12 branch flow; README/README_ES intentionally untouched. <!-- sdd-owner: parent -->
- [x] 4.4 Post-apply bounded review of the PR diff (helper + constants + four-site swaps + `TestBuildSchemaReportXlsxStaged`), then archive the change. Rollback is a single-commit revert of `repo_compliance.py` + test edits plus deletion of the change-local spec delta — no data migration, config, or on-disk artifact touched. <!-- sdd-owner: parent -->

## Follow-ups (out of scope, tracked)

- Unify `_mirror.expanded_planned_remotes` (`_mirror.py:238-248`) and
  `prepare._check_local_overwrite` (`prepare.py:620-624`) onto the new
  `_staged_xlsx_sheet_parquets` (or a shared `_mirror`-level helper) in a later
  change — identical logic, already correct and test-covered; touching them
  widens the blast radius beyond issue #150.
- Optionally modernize RC-R14 eligibility prose ("CSV remote") — superseded by
  RC-Universal §4.19; left untouched to keep this delta minimal.