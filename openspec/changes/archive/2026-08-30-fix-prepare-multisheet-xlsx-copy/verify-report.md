```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:0156ea46526219a81e1aa6819f53af150f925529a03758d9e6191a29a0f1a914
verdict: pass
blockers: 0
critical_findings: 0
requirements: 1/1
scenarios: 13/13
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:0c87919c13b7831e25792f5f6f3c21dc6b92d00ac155a33499ee3de349aa53ea
build_command: uv run mypy src/
build_exit_code: 0
build_output_hash: sha256:e7c982786727c1ea6b0e5e0346e1e60ba39748267137c4655285186d19e1c5e8
```

## Verification Report

**Change**: fix-prepare-multisheet-xlsx-copy
**Version**: N/A (PRP-02 delta 2026-08-30)
**Mode**: Standard (strict_tdd false)

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 12 |
| Tasks complete | 12 |
| Tasks incomplete | 0 |

All Phase 1 (1.1, 1.2), Phase 2 (2.1-2.3), Phase 3 (3.1-3.4), Phase 4 (4.1-4.3) checked. Implementation tasks (2.1-2.3 + 3.1-3.3) were marked complete in apply-progress; remaining verification tasks (3.4 gate, 4.1 manual clean-build, 4.2 spec delta, 4.3 deferral note) confirmed in this verify run.

### Build & Tests Execution

**Build**: ✅ Passed
```text
$ uv run mypy src/
Success: no issues found in 27 source files
exit: 0  hash: sha256:e7c982786727c1ea6b0e5e0346e1e60ba39748267137c4655285186d19e1c5e8
```

**Tests (focus)**: ✅ Passed
```text
$ uv run pytest tests/test_prepare.py -q
42 passed in 1.18s
exit: 0
```

**Tests (full)**: ✅ Passed
```text
$ uv run pytest tests/ -q
1029 passed, 2 skipped, 13 warnings in 15.92s
exit: 0  hash: sha256:0c87919c13b7831e25792f5f6f3c21dc6b92d00ac155a33499ee3de349aa53ea
warnings: 13 DeprecationWarning from _infer_type (pre-existing, not this change)
```

**Manual leak check**: ✅ Passed
```text
$ uv run python -c "create temp openpyxl DATA_GOT_ALL.xlsx (aristas/nodos) -> prepare into temp build"
tmp C:\Users\elaze\AppData\Local\Temp\tmp0i3a5mmz\build
[~] DATA_GOT_ALL.xlsx -> data_got_all_aristas.parquet
[~] DATA_GOT_ALL.xlsx -> data_got_all_nodos.parquet
build/* = [data_got_all_aristas.parquet, data_got_all_nodos.parquet, LICENSE, README.md]
glob *.xlsx == []  (no source leak)
MANUAL CHECK PASS

Additional manual: raw.xlsx convert_to_parquet=false -> staged as raw.xlsx, no parquet (PASS)
Additional manual: bad.tsv conversion failure -> staged as bad.tsv with warning (PASS)
```

**Coverage**: ➖ Not available (no coverage threshold configured; not required per tasks)

### Spec Compliance Matrix

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| PRP-02 | Converted parquets mirror normalized remote layout | `tests/test_prepare.py > TestPrepareConversion::test_converted_parquet_mirrors_remote_layout` | ✅ COMPLIANT |
| PRP-02 | XLSX multi-sheet expanded (normalized) | `tests/test_prepare.py > TestMultisheetLeakRegression::test_multisheet_stages_only_parquet_no_source_leak` + `TestOverwriteFallbackSingleUnderscore::test_fallback_detects_without_force` (report_ventas/costos) | ✅ COMPLIANT |
| PRP-02 | Multisheet stages only parquet — no source leak | `tests/test_prepare.py > TestMultisheetLeakRegression::test_multisheet_stages_only_parquet_no_source_leak` + manual temp-build glob check | ✅ COMPLIANT |
| PRP-02 | Single-sheet XLSX unchanged | `tests/test_prepare.py > TestSingleSheetPreserved::test_single_sheet_one_parquet` | ✅ COMPLIANT |
| PRP-02 | convert_to_parquet=false keeps original suffix | Manual verification: `raw.xlsx` with `convert_to_parquet=False` -> `build/raw.xlsx` exists, no `raw.parquet` (code path `prepare.py:745` + staging guard `871`); analog CSV path covered by existing suite | ✅ COMPLIANT |
| PRP-02 | upload_as_csv alias still honored for csv | `tests/test_prepare.py > TestPrepareSchemaReportParity::test_upload_as_csv_keeps_csv` | ✅ COMPLIANT |
| PRP-02 | Conversion failure falls back to original for any format | `tests/test_prepare.py > TestPrepareSchemaReportParity::test_conversion_failure_falls_back_to_csv` + manual `bad.tsv` fallback verification | ✅ COMPLIANT |
| PRP-02 | Overwrite protection covers all suffixes normalized (XLSX fallback) | `tests/test_prepare.py > TestOverwriteFallbackSingleUnderscore::test_fallback_detects_without_force` + `::test_check_local_overwrite_fallback_direct` + `tests/test_prepare.py > TestPrepareForce::test_existing_artifacts_block_without_force` + manual force=True overwrite | ✅ COMPLIANT |
| PRP-02 | Case-fold collision on normalized remotes refused before write | `tests/test_mirror.py > TestValidateCaseFoldCollisions::*` (4 tests, all passed in full suite) via `_validate_case_fold_collisions` called at `prepare.py:731` | ✅ COMPLIANT |
| PRP-02 | Cross-file schema grouping handles both underscore forms | `tests/test_prepare.py > TestSchemaGroupingSingleUnderscore::test_grouping_with_single_underscore_keys` + `::test_single_sheet_no_extra_grouping` | ✅ COMPLIANT |
| PRP-02 | Legacy CSV scenarios preserved | `tests/test_prepare.py > TestPrepareConversion::test_converted_parquet_mirrors_remote_layout` (normalized lowercase) | ✅ COMPLIANT |
| PRP-02 | upload_as_csv entries keep their CSV (legacy) | `tests/test_prepare.py > TestPrepareSchemaReportParity::test_upload_as_csv_keeps_csv` (duplicate legacy scenario) | ✅ COMPLIANT |
| PRP-02 | Conversion failure falls back to CSV (legacy) | `tests/test_prepare.py > TestPrepareSchemaReportParity::test_conversion_failure_falls_back_to_csv` | ✅ COMPLIANT |

**Compliance summary**: 13/13 scenarios compliant (11 via automated covering tests in `test_prepare.py`, 1 via `test_mirror.py`, 2 via manual verification plus analog automated coverage; no FAILING or UNTESTED)

### Correctness (Static Evidence)

| Requirement | Status | Notes |
|-------------|--------|-------|
| PRP-02 conversion preserved + guards `__`+`_` | ✅ Implemented | `src/sofer/prepare.py:864-869` is_converted XLSX-only dual predicate `k==norm_key or k.startswith(stem+"__") or (k.startswith(stem+"_") and k!=norm_key)`; non-XLSX keeps equality. Aligns with `src/sofer/_mirror.py:239-252` PUB-10. |
| Overwrite guard XLSX fallback | ✅ Implemented | `src/sofer/prepare.py:610-622` glob `__*.parquet` primary + fallback `_*.parquet` filtered `c.stem != stem` + single-sheet candidate. Mirrors `_mirror.py`. |
| Schema grouping both forms | ✅ Implemented | `src/sofer/prepare.py:371-379` adds `k.startswith(norm_stem+"_") and k!=norm_key` and `k.startswith(legacy_key+"_") and k!=legacy_key` alongside `__` forms. |
| normalize `__+`->`_` unchanged + single-sheet short-circuit | ✅ Implemented | `src/sofer/_converters.py:70` `re.sub(r"__+", "_", s)` unchanged; `prepare.py:871` `k!=norm_key` guard prevents false positive on `dataset.parquet`. |
| No hardcoded literals | ✅ Implemented | `prepare.py` and `_converters.py` use `config.PARQUET_COMPRESSION`/`PARQUET_ROW_GROUP_SIZE`/`PARQUET_SHARD_WARNING_MB`; grep shows no hardcoded literals in changed lines. |
| Build succeeds | ✅ Implemented | `uv run mypy src/` Success, 27 files. `win32 sys.stdout.reconfigure` false positive not present (guard `hasattr` remains at `690`). |

### Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| Guard predicate dual `__`+`_` (B) | ✅ Yes | Implemented exactly as `design.md` Option 1: `k==norm_key \|\| k.startswith(s+"__") \|\| (k.startswith(s+"_") && k!=norm_key)` at 3 sites. |
| Overwrite detection FS glob vs dict | ✅ Yes | Site 2 uses FS glob (ground truth for prior-run PRP-07); Site 1 uses `converted` dict — matches design table. |
| Fallback scope XLSX-only | ✅ Yes | All `_` fallback branches guarded `if suffix == ".xlsx"`; CSV/TSV/JSONL unchanged. |
| Normalize fix guard now, `__` preservation deferred | ✅ Yes | `_converters.py` unchanged; future migration noted in tasks 4.3, no code now. |
| Single commit, ~90 lines | ✅ Yes | 3 sites + 7 tests in one work unit; actual diff ~90 lines, no extra docs/config. |

### Issues Found

**CRITICAL**: None

**WARNING**:
- W1: Stale `build/DATA_GOT_ALL.xlsx` from prior leaky runs is not auto-cleaned by `prepare`. Manual clean-build check used temp dir; any existing `C:/Users/elaze/Desktop/test/build` stale artifact must be deleted manually (noted in apply-progress Risks, not a code defect).
- W2: `convert_to_parquet=false` for XLSX has no dedicated automated test in `test_prepare.py` (only manual verification here + analog CSV coverage). Non-blocking; code path is shared (`prepare.py:745`), but adding a regression test `raw.xlsx` with `convert_to_parquet=False` would harden the matrix.

**SUGGESTION**:
- S1: Consider adding an explicit `test_raw_xlsx_convert_false` to `test_prepare.py` to make the manual verification auditable in CI (low effort, mirrors `test_upload_as_csv_keeps_csv`).
- S2: `tests/test_codebook.py` emits 13 DeprecationWarnings for `_infer_type` — pre-existing, unrelated; follow-up to migrate to `infer_column_type`.

### Verdict

**PASS**

All 13 PRP-02 scenarios have covering evidence and passed at runtime (1029/1029, 42/42 in prepare), mypy is clean, 3 design sites align with `_mirror.py` PUB-10, no source leak in clean `build/`, overwrite fallback and schema grouping handle single-underscore normalized keys, and single-sheet remains unaffected.

