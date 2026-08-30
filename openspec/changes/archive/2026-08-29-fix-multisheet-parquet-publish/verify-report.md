```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:08d3cb79821b7923034118927849353cb8493673c427d40b45f4fc8160a6a927
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 4/4
scenarios: 19/19
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:490cc4ac98035f912bfb6381bcaceea0e555738b0b3309630592b44bcd692f24
build_command: uv run ruff check src/ tests/ && uv run mypy src/
build_exit_code: 0
build_output_hash: sha256:6f35ba4fa5cbdda57a1c41cf74dee51605c863d56b3a76913a5ae19492c51142
```

## Verification Report

**Change**: 2026-08-29-fix-multisheet-parquet-publish
**Branch**: fix/multisheet-parquet-publish
**Version**: N/A (delta change)
**Mode**: Standard (strict_tdd=false, test_command `uv run pytest tests/ -q`)

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 13 |
| Tasks complete | 13 |
| Tasks incomplete | 0 |

| Dimension | Artifact | Status | Evidence |
|-----------|----------|--------|----------|
| Proposal | `openspec/changes/2026-08-29-fix-multisheet-parquet-publish/proposal.md` | ✅ exists | 68 lines, intent/scope/approach match implementation |
| Spec - publish (delta) | `specs/publish/spec.md` | ✅ exists | 91 lines, 3 requirements (PUB-10 ADDED, PUB-01 MODIFIED, PUB-09 MODIFIED) with 14 scenarios |
| Spec - repo-compliance (delta) | `specs/repo-compliance/spec.md` | ✅ exists | 34 lines, 1 requirement (RC-Universal-Card MODIFIED) with 5 scenarios |
| Design | `openspec/changes/2026-08-29-fix-multisheet-parquet-publish/design.md` | ✅ exists | 80 lines, decisions/flow/modules correct |
| Tasks | `openspec/changes/2026-08-29-fix-multisheet-parquet-publish/tasks.md` | ✅ 13/13 [x] | Phases 1-4 complete |
| Apply progress | `apply-progress.md` + Engram `sdd/2026-08-29-fix-multisheet-parquet-publish/apply-progress` | ✅ exists | 13/13 tasks, deviations documented |

**Task breakdown (all [x]):**

- 1.1 `expanded_planned_remotes(cfg, keep_csv, staging_dir)` in `src/sofer/_mirror.py` — gated `.xlsx`, glob `staging_dir/<dir>/<stem>__*.parquet` sorted, fallback to `planned_remotes`, reuse `normalize_parquet_remote`, no workbook I/O
- 1.2 Document `planned_remotes` as logical placeholder, Path import handling
- 2.1 `_repo_diff_summary(cfg, existing, keep_csv, codebook_remotes, staging_dir)` derives via `expanded_planned_remotes` when mirror exists, marks recursive `*`, shares set
- 2.2 `_check_overwrite_protection` expanded `planned_files` per-sheet, wired caller to pass expanded list; dry-run and hf paths
- 2.3 `_copy_package` iterates expanded remotes via `copy_to_mirror`, drop inline `__*.parquet` glob duplication; preserve `keep_csv` CSV-only and recursive path
- 2.4 Wire dry-run/split paths: `_print_split_mapping_validation` and `detect_splits` consume expanded count N
- 2.5 `build_dataset_card(..., keep_csv=False, staging_dir=None)` uses `expanded_planned_remotes` for `configs.data_files` + Dataset Structure when `staging_dir.is_dir()`
- 3.1 Unit `tests/test_mirror.py`: multi-sheet expands to N `__` remotes, single stays single, fallback, recursive/`keep_csv` invariants, no openpyxl
- 3.2 Unit `tests/test_repo_compliance.py`: card with 2-sheet staging shows N in `configs.data_files` and Structure, fallback without staging, configs==Structure, no local path
- 3.3 Integration `tests/test_publish.py`: 2-sheet mock staging, diff lists 2, per-sheet protection, copy stages N, detect_splits count 2, dry-run lists N
- 3.4 Regression single `single.parquet` shows no phantom `__`, full suite green
- 4.1 Module docstrings updated, `uv run ruff check src/ tests/ && uv run mypy src/` green
- 4.2 No hardcoded delimiters/encodings, no duplicated logic

### Build & Tests Execution

**Build**: ✅ Passed
```text
uv run ruff check src/ tests/
All checks passed!

uv run mypy src/
Success: no issues found in 27 source files
```

**Tests**: ✅ 976 passed / 2 skipped / 0 failed
```text
uv run pytest tests/test_mirror.py tests/test_publish.py tests/test_repo_compliance.py -q
266 passed in 2.24s

uv run pytest tests/ -q
976 passed, 2 skipped, 13 warnings in 14.21s

Warnings: 13 DeprecationWarning from tests/test_codebook.py (_infer_type deprecated -> infer_column_type), non-blocking
```

**Coverage**: Not available (no coverage threshold configured)

Subset re-run (`test_mirror`, `test_publish`, `test_repo_compliance`) is included in full suite count; full suite confirms `apply-progress` claim of 266 targeted + 976 total.

### Spec Compliance Matrix

**Compliance summary**: 19/19 scenarios covered (18 COMPLIANT, 1 PARTIAL)

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| PUB-10 | Multi-sheet expands | `tests/test_mirror.py > TestExpandedPlannedRemotes.test_multi_sheet_expands_to_n_remotes` | ✅ COMPLIANT |
| PUB-10 | Single-sheet stays single | `tests/test_mirror.py > TestExpandedPlannedRemotes.test_single_sheet_stays_single` + `tests/test_publish.py > TestSingleSheetRegression.test_single_sheet_no_phantom` | ✅ COMPLIANT |
| PUB-10 | Fallback and invariants | `tests/test_mirror.py > test_fallback_when_staging_none` + `test_fallback_when_staging_not_dir` + `test_recursive_passthrough` + `test_no_openpyxl_import` + `test_convert_to_parquet_false_passthrough` | ✅ COMPLIANT |
| PUB-01 | Diff universal remotes | `tests/test_mirror.py > TestPlannedRemotes.test_nested_csv_remote_preserves_dir` + `tests/test_publish.py > TestRepoDiffSummary.test_empty_repo` (both assert normalized `data/got_ano.parquet`) | ✅ COMPLIANT |
| PUB-01 | Copy stages parquets | `tests/test_publish.py > TestMultiSheetPublish.test_multi_sheet_diff_and_protection_and_copy` (asserts `report__ventas.parquet` staged, expanded==staged) + `TestBatchStaging.test_parquet_placed_in_remote_subdirs` | ✅ COMPLIANT |
| PUB-01 | keep_csv CSV-only | `tests/test_mirror.py > TestExpandedPlannedRemotes.test_keep_csv_csv_only` + `tests/test_publish.py > TestHfPublish.test_keep_csv_stages_csv_alongside_parquet` | ✅ COMPLIANT |
| PUB-01 | Full hf publish | `tests/test_publish.py > TestHfPublish.test_full_publish_upload_folder_called_once` | ✅ COMPLIANT |
| PUB-01 | Quality gate blocks | `tests/test_publish.py > TestQualityGate.test_failed_report_blocks_before_network` | ✅ COMPLIANT |
| PUB-01 | upload failure | `tests/test_publish.py > TestHfPublish.test_upload_folder_failure_returns_1` + `test_upload_failure_accounting_zero_uploaded` | ✅ COMPLIANT |
| PUB-01 | Missing files | `tests/test_publish.py > TestBatchStaging.test_not_found_files_skipped_in_staging` | ✅ COMPLIANT |
| PUB-01 | Multi-sheet diff and per-sheet protection | `tests/test_publish.py > TestMultiSheetPublish.test_multi_sheet_diff_and_protection_and_copy` (diff lists 2, only ventas protected w/o --force) | ✅ COMPLIANT |
| PUB-01 | Split counts expanded | `tests/test_publish.py > TestMultiSheetPublish.test_multi_sheet_diff_and_protection_and_copy` (detect_splits count 2) + `test_multi_sheet_full_publish_stages_n` | ✅ COMPLIANT |
| PUB-09 | Diff and copy agree | `tests/test_mirror.py > TestExpandedPlannedRemotes` (universal eligibility) + `tests/test_publish.py > TestMultiSheetPublish` (both via expanded_planned_remotes, PUB-09 invariant) | ✅ COMPLIANT |
| PUB-09 | Collision error | `tests/test_mirror.py > TestValidateCaseFoldCollisions.test_case_differing_remotes_error_names_both` (case-fold on normalized key) | ✅ COMPLIANT |
| RC-Universal-Card | tsv as parquet | `tests/test_mirror.py > TestPlannedRemotes` (CONVERTIBLE_SUFFIXES includes tsv, eligible -> `normalize_parquet_remote`) + `tests/test_repo_compliance.py > TestExpandedCard` underlying helper (no isolated tsv card unit) | ⚠️ PARTIAL (path tested via csv/xlsx; no dedicated tsv card assertion, but same normalization code path) |
| RC-Universal-Card | xlsx N entries | `tests/test_repo_compliance.py > TestExpandedCard.test_card_with_2_sheet_staging_shows_n` | ✅ COMPLIANT |
| RC-Universal-Card | Structure expanded | `tests/test_repo_compliance.py > TestExpandedCard.test_card_with_2_sheet_staging_shows_n` (Structure lists both, no local path) | ✅ COMPLIANT |
| RC-Universal-Card | Fallback before prepare | `tests/test_repo_compliance.py > TestExpandedCard.test_card_fallback_without_staging_shows_single` | ✅ COMPLIANT |
| RC-Universal-Card | configs==Structure | `tests/test_repo_compliance.py > TestExpandedCard.test_configs_equals_structure` | ✅ COMPLIANT |

**Notes on PARTIAL**: RC `tsv as parquet` is exercised through the same `planned_remotes`/`expanded_planned_remotes` normalization path as csv/xlsx (CONVERTIBLE_SUFFIXES gating + `normalize_parquet_remote`), and `build_dataset_card` uses that helper. Test suite has explicit csv and xlsx card assertions but no dedicated `data/x.tsv -> data/x.parquet` card assertion. Functionally covered; add a parametrized tsv card test to reach full explicit coverage.

### Correctness (Static Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| PUB-10 expanded_planned_remotes via mirror scan | ✅ Implemented | `src/sofer/_mirror.py:180-268` globs `staging_dir/<dir>/<stem>__*.parquet` sorted, fallback to `planned_remotes`, no openpyxl, reuses `normalize_parquet_remote`, handles recursive/`keep_csv`/`convert_to_parquet` |
| PUB-01 hf target uploads via expanded remotes | ✅ Implemented | `src/sofer/publish.py:206-275` _repo_diff_summary staging_dir aware, 615-619 expanded when source.is_dir(), 622-629 dry-run, 477-481 _copy_package expanded, 669-673 publish hf protection/splits share expanded |
| PUB-09 delegation invariant | ✅ Implemented | Single eligibility: `CONVERTIBLE_SUFFIXES` + `convert_to_parquet` + NOT recursive -> `parquet_remote_for` else passthrough, collisions via `_validate_case_fold_collisions`, diff vs staged divergence treated as bug (copy iterates same expanded list) |
| RC-Universal-Card card data_files universal normalized | ✅ Implemented | `src/sofer/repo_compliance.py:1022-1027` and 1169-1172 use `expanded_planned_remotes` when `staging_dir.is_dir()` else fallback, row_counts keyed by verbatim `entry.remote`, no local leak |
| Config usage (no hardcoded delimiters/encodings) | ✅ Implemented | New code uses `cfg.csv_delimiter`/`csv_encoding` via DatasetConfig, no hardcoded `;` in _mirror/publish expansions |
| No duplicated logic | ✅ Implemented | `_parquet_to_hf_dtype` remains in `_parquet_helpers.py` single source, `normalize_parquet_remote`/`sanitize_sheet_name` reused from `_converters` |

### Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| Helper location `_mirror.py` | ✅ Yes | Keeps `parquet_remote_for` co-located, no cycle (`_converters` never imports `_mirror`) |
| Expansion source glob staging vs workbook I/O | ✅ Yes | Glob `__*.parquet` sorted, fallback placeholder; no workbook I/O at plan time |
| XLSX eligibility gated | ✅ Yes | `CONVERTIBLE_SUFFIXES` + `bool(convert_to_parquet)` + NOT recursive; `keep_csv` only for `.csv` |
| Reuse sanitize/normalize | ✅ Yes | Imports `normalize_parquet_remote` for fallback placeholder; glob needs no sanitize — names already sanitized on disk |
| Copy strategy expanded list | ✅ Yes | `_copy_package` iterates expanded remotes via `copy_to_mirror`, dropped inline glob duplication |

**Deviations documented in apply-progress**: Backward-compat fallback for single-underscore sheet files (`report_ventas.parquet` vs `report__ventas.parquet`) when double-underscore glob finds nothing, because current `_converters` normalizes `__` to `_` via `normalize_parquet_remote`. Strict spec glob `__*.parquet` remains primary; fallback keeps existing builds working until normalize collapse is reconciled. Non-breaking, preserves single-sheet invariant.

### Issues Found

**CRITICAL**: None

**WARNING**:
1. **Backward-compat single-underscore fallback in expanded_planned_remotes** — `src/sofer/_mirror.py:244-252` adds `stem_*.parquet` fallback when `__` glob empty. Deviation from spec strict `__*.parquet` is documented and keeps existing `prepare` output working, but should be removed or reconciled once `normalize_parquet_remote` stops collapsing `__` to `_`. Low risk.
2. **RC tsv card scenario lacks explicit tsv unit test** — compliance matrix marks PARTIAL. Underlying code path is identical to csv/xlsx (CONVERTIBLE_SUFFIXES), but no dedicated `data/x.tsv -> data/x.parquet` card assertion exists. Add parametrized test to `test_repo_compliance.py`.
3. **Open-question not yet resolved** — `build_dataset_card` caller in `prepare.py` now passes `staging_dir=output_dir` (verified at `src/sofer/prepare.py:826,836`), but local-target card ground truth vs destination remains open per design.

**SUGGESTION**:
- Add `tests/test_repo_compliance.py` parametrized case for `data/x.tsv` card -> `data/x.parquet`.
- Document single-underscore fallback removal plan in follow-up chore.
- Consider `uv run ruff format --check` in CI (51 files already formatted, not gating).

### Verdict

**PASS WITH WARNINGS**

All 13 tasks complete, 976 tests pass (266 targeted), ruff + mypy green, and 19/19 delta scenarios have covering tests (1 partial). No blockers. Warnings are non-blocking quality gaps (compat fallback, missing tsv card unit, open design question) that do not break archive readiness.

### Next Recommended

**archive** — `openspec/changes/2026-08-29-fix-multisheet-parquet-publish` is ready for `sdd-archive` (hybrid persistence satisfied via this file + Engram mirror). Address WARNING-2 tsv test in follow-up if desired.

### Risks

- Large XLSX not stressed (design open question: `glob` is cheap, but `prepare` handles large workbooks with `read_only,data_only`).
- Accent/space variants now correctly collide; users with legacy remotes differing only by accents will see new error — migration via `convert_to_parquet=false` already documented in earlier change.

### Skill Resolution

- `sdd-verify` executed per `~/.config/opencode/skills/sdd-verify/SKILL.md` + `../_shared/sdd-phase-common.md` Section D envelope.
- Testing mode: Standard verify (strict_tdd: false); no `strict-tdd-verify.md` loaded.
- Persistence: hybrid — file `openspec/changes/2026-08-29-fix-multisheet-parquet-publish/verify-report.md` + Engram `sdd/2026-08-29-fix-multisheet-parquet-publish/verify-report`.

---
*Generated by sdd-verify sub-agent (muse-spark-1.2-contributor) — source inspection + real execution (`pytest` + `ruff` + `mypy`). No HF network.*
