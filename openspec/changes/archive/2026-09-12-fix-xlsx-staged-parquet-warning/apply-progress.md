# Apply Progress: fix-xlsx-staged-parquet-warning

**Change**: `fix-xlsx-staged-parquet-warning` (closes #150)
**Branch**: `fix/150-xlsx-staged-warning` @ HEAD 4a9e0d4 (clean except untracked change dir)
**Phase**: apply — implementation + tests + gates. Strict TDD off (`openspec/config.yaml strict_tdd: false`); tests follow the RC-R22 spec scenarios; RED-first used where practical (each new test was written before its green run; new failures were triaged before the code path was accepted).
**Date/run**: single apply pass; no prior apply-progress existed (this file is the first).

## Structured status consumed

Authoritative native status (from sdd-status): `applyState: ready` for apply (`verify/sync/archive blocked` until evidence). `changeName` was null in the status JSON but the parent prompt pinned the active change (`fix-xlsx-staged-parquet-warning`) with `nextRecommended: verify`; `actionContext.mode: repo-local`, `allowedEditRoots: ["C:\\Users\\elaze\\Desktop\\sofer"]` — every edited file is inside the workspace root, no warnings to act on.

- `actionContext.mode`: **repo-local** · warnings: none.
- Delivery decision provided by parent: **single PR, chain_strategy none, 400-line budget risk Low, Decision needed: No** → no size exception or chain strategy required.

## Files changed (only allowed set)

| File | Change | Status |
|------|--------|--------|
| `src/sofer/repo_compliance.py` | +`_WARN_STAGED_PARQUET_MISSING` / `_WARN_STAGED_PARQUET_UNREADABLE` constants; +`_staged_xlsx_sheet_parquets` helper; both XLSX glob sites delegate; four print sites use the constants | modified (106 diff lines: ~+63/−43 net) |
| `tests/test_repo_compliance.py` | `_stage_parquet` promoted to module-level (static method delegates); +`_make_xlsx`; +`TestBuildSchemaReportXlsxStaged` (4 tests) | modified (185 diff lines) |
| `openspec/changes/fix-xlsx-staged-parquet-warning/apply-progress.md` | this file | new |
| `openspec/changes/fix-xlsx-staged-parquet-warning/tasks.md` | 17 implementation tasks `[x]` + evidence lines; 4 parent rows untouched | updated |

NOT touched (constraint): `src/sofer/_mirror.py`, `src/sofer/prepare.py`, canonical `openspec/specs/...`, README/README_ES, no commits/pushes/PRs, no archive.

File hashes (post-edit, for the verify phase):
- `src/sofer/repo_compliance.py` → `a4882f9952bb856607cb23b2d8744bca7df0261c5bc4e234917767363580c939`
- `tests/test_repo_compliance.py` → `02dadf5d4084bee053434301578739607dcb3138e5a06bd53d2bd3b9e390a51b`

Diff surface: `git diff --stat` → `2 files changed, 248 insertions(+), 43 deletions(-)`. Executable review load ~291 changed lines, well inside the 400-line budget and the 800-line session review budget; single PR (chain_strategy: none / pending).

## Unit 1 — implementation in `src/sofer/repo_compliance.py` (tasks 1.1–1.7)

All seven edits applied; behavior-neutral refactors per design §3.3:

- 1.1 Two module-level constants above `_build_schema_report_impl` (was ~L436), exact `"  [!] "` two-space prefix, tails `falling back to original-file inference.`.
- 1.2 `_staged_xlsx_sheet_parquets(staging_dir, parquet_key) -> list[Path]` per design §3.1: `PurePosixPath` parent/stem derivation; `search_dir.is_dir()` guard → `[]`; primary `stem__*.parquet` sorted + file-filtered, returned when non-empty; else fallback `stem_*.parquet` sorted + file-filtered + `p.stem != base_stem`. No new imports (`Path`, `PurePosixPath` already imported).
- 1.3 First XLSX glob site: `sheet_paths = _staged_xlsx_sheet_parquets(staging_dir, parquet_key)`; unconditional `single = staging_dir / PurePosixPath(parquet_key)` appended `if single.is_file()`; decision shape `if sheet_paths: parquet_path = sheet_paths[0]; use_parquet = True; origin_name = parquet_key` preserved. `is_dir()` gate moved into the helper (behavior-neutral: `single.is_file()` is False when the parent dir is absent).
- 1.4 First XLSX warn site → `print(_WARN_STAGED_PARQUET_MISSING.format(key=parquet_key))`; `elif parquet_key not in _warned_missing:` + `_warned_missing.add(parquet_key)` kept.
- 1.5 Non-XLSX branch logic untouched; only the print swapped to the shared missing template (`test_missing_parquet_warns_once_*` stay byte-identical in expectations).
- 1.6 Second XLSX collection → `xlsx_sheet_paths = _staged_xlsx_sheet_parquets(staging_dir, parquet_key)` + same unconditional single append; dead duplicate derivation/comments removed. Both sites now derive from the identical helper call so `use_parquet` and the per-sheet loop list cannot disagree.
- 1.7 Both unreadable prints → `_WARN_STAGED_PARQUET_UNREADABLE.format(key=..., failure_class=failure_class)` (single-file keyed `parquet_key`, per-sheet keyed `sheet_origin`); `_warned_unreadable` guards and `continue` preserved. Per-sheet loop internals (`sheet_origin`, `row_counts.setdefault(entry.remote + f"::{sheet_origin}", ...)` ~L594), single-file read (~L646), first-sheet-only fallback (`ws_f = wb_f[wb_f.sheetnames[0]]` ~L704), `_read_parquet_sample`/`_classify_parquet_read_failure` untouched.

**Evidence (unit 1)**:

```
$ grep -rn "CSV inference" src/sofer/ --include="*.py"   → zero source hits (only a stale __pycache__ .pyc)
$ grep -rn "falling back to CSV" src/sofer/ --include="*.py"
  src/sofer/repo_compliance.py:385 / :503 / :894   → pre-existing DOCSTRING prose of _read_parquet_sample
  and the build_schema_report* docstrings ("before falling back to CSV reading.") — NOT warning tails;
  untouched by this change; all four print sites are reworded.
$ PYTHONIOENCODING=utf-8 uv run pytest tests/test_repo_compliance.py -q  → 185 passed (161 inherited + 4 new)
```

The two existing warn-path tests (`test_missing_parquet_warns_once_and_falls_back_to_csv`, `test_missing_parquet_warns_once_per_unique_key`) and `TestStagedParquetRemoteRelativeLookup` are green unmodified — preserved exactly: `[!]` prefix, `Staged Parquet '<key>' not found` fragment, warn-once-by-key semantics, error classification.

## Unit 2 — tests in `tests/test_repo_compliance.py` (tasks 2.1–2.6)

- 2.1 Promoted `_stage_parquet` body to module-level `_stage_parquet(stage, remote_key, table)`; `TestStagedParquetRemoteRelativeLookup._stage_parquet` is now a one-line delegation → all existing `self._stage_parquet` call sites keep working (verified: 185 passed includes those tests).
- 2.2 Module-local `_make_xlsx(path, sheets)` — byte-pattern copy of `test_clean.py:32` convention (openpyxl, header-first rows). No new dependencies.
- 2.3 `test_multi_sheet_collapsed_staged_parquets_stay_silent` — `DATA_GOT_ALL.xlsx` (aristas/nodos), collapsed `data_got_all_aristas.parquet` / `data_got_all_nodos.parquet` staged **only**, no base; capitalized remote pins case-insensitive suffix + verbatim-remote keying. Asserts: no `[!]`; origins `{"data_got_all_aristas.parquet", "data_got_all_nodos.parquet"}`; row_counts exactly `{"DATA_GOT_ALL.xlsx::data_got_all_aristas.parquet": 1, "DATA_GOT_ALL.xlsx::data_got_all_nodos.parquet": 1}` (`::` keys per ~L594 contract); `src`/`label` present with `hf_dtype == "int64"`.
  - RED note: first run failed because shared `id` across both sheet parquets triggered the pre-existing duplicate-column `[!]` warning; fixed by staging distinct per-sheet columns (keeps the strict "no `[!]`" assertion focused on the base-key silence — the XLSX-side sheets still mirror the reproducer).
- 2.4 `test_multi_sheet_spec_layout_double_underscore_stays_silent` — `report.xlsx` (ventas/costos), only `report__ventas.parquet` + `report__costos.parquet` staged; no `[!]`; origins and `report.xlsx::report__*.parquet` row keys asserted (dual-modality guard for `test_mirror`/`TestExpandedCard` stubs; primary-wins structurally guaranteed by the helper).
- 2.5 `test_single_sheet_staged_parquet_stays_silent` — bare `report.parquet` staged only; no `[!]`; `origins == {"report.parquet"}`; `row_counts == {"report.xlsx::report.parquet": 3}` — pins the base-file-through-single-item-loop contract (RC-R07 `::` keying unchanged, NOT "fixed").
- 2.6 `test_multi_sheet_missing_staged_parquet_still_warns_once` — **real openpyxl** `DATA_GOT_ALL.xlsx` (fallback re-reads source), empty `stage`; exactly one `[!]` line containing `data_got_all.parquet` AND `original-file inference`, `CSV` absent from it; `row_counts == {"DATA_GOT_ALL.xlsx": 1}`; origins `{"DATA_GOT_ALL.xlsx"}`; sheet-2 column `label` absent (first-sheet-only degradation asserted as documented-unchanged).

**Evidence (unit 2)**:

```
$ PYTHONIOENCODING=utf-8 uv run pytest tests/test_repo_compliance.py -k TestBuildSchemaReportXlsxStaged -q
  ....            [100%]   → 4 passed, 181 deselected
$ PYTHONIOENCODING=utf-8 uv run pytest tests/test_repo_compliance.py -q
  185 passed in 1.05s
```

**Acceptance mapping (AGENTS.md rule 6 / config.yaml) — RC-R22 scenario → test:**

| RC-R22 scenario | Test |
|---|---|
| Multi-sheet collapsed single-underscore stays silent | `test_multi_sheet_collapsed_staged_parquets_stay_silent` (new) |
| Spec-layout double-underscore still recognized | `test_multi_sheet_spec_layout_double_underscore_stays_silent` (new) |
| Single-sheet XLSX stays silent | `test_single_sheet_staged_parquet_stays_silent` (new) |
| Genuine non-XLSX single-file miss warns once | existing `test_missing_parquet_warns_once_and_falls_back_to_csv` + `test_missing_parquet_warns_once_per_unique_key` (green, unmodified) |
| Genuine multi-sheet XLSX miss warns once, corrected tail | `test_multi_sheet_missing_staged_parquet_still_warns_once` (new) |

Every RC-R22 scenario has exactly one test (s4 covered by the two existing warns-once tests taken together, per tasks.md acceptance mapping); every §4.19/RC-R14 amended scenario remains covered by existing suites.

## Unit 3 — verification + gates (tasks 3.1–3.4)

**3.1 Fast loop** — `PYTHONIOENCODING=utf-8 uv run pytest tests/test_repo_compliance.py -q` → **`185 passed in 1.05s`** (4 new + 181 inherited incl. warn-path and relative-lookup tests).

**3.2 Full suite** — `PYTHONIOENCODING=utf-8 uv run pytest tests/ -q` →

```
1528 passed, 6 skipped, 13 warnings in 43.25s
```

Baseline was 1524 passed / 6 skipped (per pre-change state); delta = exactly the 4 new tests. Additive only; no new dependencies (openpyxl + pyarrow already present).

**3.3 Quality gates**:

```
$ uv run ruff check src/ tests/            → All checks passed!
$ uv run ruff format --check src/ tests/   → 65 files already formatted
$ uv run mypy src/                         → Success: no issues found in 32 source files
$ git diff --check                         → silent (clean)
```

No `ruff format` application was needed. mypy run locally under the project's default interpreter; CI runs mypy under Python 3.13 per AGENTS.md rule 12 (no version-matrix change made).

**3.4 Spec-delta/test coverage completeness** — confirmed: 4 new tests + 2 existing cover all 5 RC-R22 scenarios; `_make_xlsx`/`_stage_parquet` are single-source test helpers (no duplication — the old static method delegates); the only new hardcoded strings are the two module-level warning constants (AGENTS.md rule 1: everything else reads config/params).

## Deviations from design

| # | Deviation | Rationale | Impact |
|---|-----------|-----------|--------|
| D1 | Test 2.3 staged parquets use per-sheet distinct columns (`src` / `label`) instead of the reproducer's shared `id` | Shared `id` across both sheet parquets triggers the pre-existing duplicate-column `[!]` warning, breaking the strict "no `[!]`" assertion the spec scenario demands; the base-key silence is the scenario's subject | None — origins, `::` row keys, and dtype assertions are unchanged; XLSX sheet names/rows still mirror DATA_GOT_ALL |
| D2 | Test 2.3 `src`/`label` asserted `hf_dtype == "int64"` via explicit int64 parquet schemas (design §6.2 reads the same) | Explicit int64 schema pins the parquet-type propagation path (never the CSV float64 fallback), matching the design table's "int64 hf_dtype" | None |
| D3 | `tasks.md` count is 17 implementation-owned tasks, not 16 | 1.x(7) + 2.x(6) + 3.x(4) = 17; all 17 marked `[x]` with evidence; the 4 parent rows (4.x) remain unchecked | None |

No production-code deviation from design §3: helper, constants, four-site swaps, and unchanged regions (per-sheet loop, single-file read, first-sheet-only fallback, `::` keying) are exactly as designed.

## Remaining tasks (unchecked, parent-owned — deferred lifecycle actions)

```
- [ ] 4.1 Verify the change-local spec delta is in place and complete (...); update apply-progress. <!-- sdd-owner: parent -->
- [ ] 4.2 Populate openspec/changes/fix-xlsx-staged-parquet-warning/verify.md with the §3 gate results (...). <!-- sdd-owner: parent -->
- [ ] 4.3 Sync the delta into canonical openspec/specs/repo-compliance/spec.md on merge to dev (...). <!-- sdd-owner: parent -->
- [ ] 4.4 Post-apply bounded review of the PR diff (...), then archive the change. <!-- sdd-owner: parent -->
```

## Workload / PR boundary

Single PR (`chain_strategy: none`/pending, per tasks.md forecast + parent delivery decision). Changed-lines surface: `git diff --stat` → 248 insertions / 43 deletions across the 2 allowed files (~291 changed), inside the 400-line canonical budget and the 800-line session review budget. Review-load note: the ~350 doc delta already existed at proposal; executable review surface is the ~291 lines above.

## Rollback note

Single-commit revert of `src/sofer/repo_compliance.py` + `tests/test_repo_compliance.py` plus deletion of the change-local spec delta; no data migration, config, or on-disk artifact touched.

## Output contract

- **status**: complete (apply ready → done; verify/sync/archive remain blocked by design — parent-owned)
- **next_recommended**: `verify` (evidence above feeds `openspec/changes/fix-xlsx-staged-parquet-warning/verify.md`, parent task 4.2)
- **skill_resolution**: `none` (no executor/phase skill path injected; strict-TDD OFF so the strict-TDD support file is not applicable; degraded fallback not required)
- **windows note**: all pytest runs used `PYTHONIOENCODING=utf-8`; no CRLF warnings emitted (repo files are LF; `git config core.autocrlf` = input).