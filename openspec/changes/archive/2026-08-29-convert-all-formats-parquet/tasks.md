# Tasks: convert-all-formats-parquet

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 600-800 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR (within 2000 budget) |
| Delivery strategy | auto |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | _converters + model + mirror | PR 1 | Base=main |
| 2 | prepare/publish/repo-compliance | PR 1 | Depends 1 |
| 3 | Docs + test migration | PR 1 | README_ES sync |

## Phase 1: _converters Foundation

- [x] 1.1 `src/sofer/_converters.py`: `CONVERTIBLE_SUFFIXES`, `normalize_parquet_remote`, `sanitize_sheet_name` | Spec: PC-U02 | Done: `pytest test_converters` + `mypy` | Dep: none
- [x] 1.2 `_write_parquet_table`: `PARQUET_COMPRESSION`/`ROW_GROUP_SIZE`, null→string, shard warn `PARQUET_SHARD_WARNING_MB` | Spec: PC-U01 | Done: opts+warn test, `ruff` | Dep: 1.1

## Phase 2: Per-Format Converters

- [x] 2.1 CSV sniff (`SNIFF_DELIMITERS`/`CSV_ENCODING`) + TSV `\t` | Spec: PC-U01 sniff/TSV | Done: round-trip tests | Dep: 1.2
- [x] 2.2 XLSX (`read_only,data_only`, all sheets→`pa.Table`, dedup `_{n}`, 0-row) + JSONL (pyarrow.json+fallback) | Spec: PC-U01/PC-U03 | Done: xlsx N+empty+fallback | Dep: 2.1
- [x] 2.3 `convert_file_to_parquet -> dict[normalized_remote,Path]`, passthrough+`recursive` skip, tmp idx, failure→warn | Spec: PC-U01/PRP-02 | Done: `mypy` | Dep: 2.2

## Phase 3: Model Flag

- [x] 3.1 `src/sofer/model.py`: `convert_to_parquet=True`, `upload_as_csv` alias csv-only warn, precedence | Spec: PC-U04 | Done: `test_model` alias tests | Dep: 1.1

## Phase 4: Mirror

- [x] 4.1 `src/sofer/_mirror.py` `planned_remotes` universal normalized, xlsx N, `keep_csv` CSV-only | Spec: PUB-01/09 | Done: `test_mirror` N+keep_csv | Dep: 2.3,3.1
- [x] 4.2 `_validate_case_fold_collisions` on `lower(normalized)`, import from `_converters` no cycle | Spec: PC-U02/PRP-02b | Done: names both remotes | Dep: 4.1

## Phase 5: Prepare

- [x] 5.1 `src/sofer/prepare.py` gate→convertible set, `converted` keyed normalized, dispatcher, tmp idx | Spec: PRP-02/02b | Done: mixed-format integration | Dep: 4.2
- [x] 5.2 Guards/parity: `_check_local_overwrite`+`_validate_case_fold_collisions` normalized, `_assert_cross_file_schema`+`_check_large_values` per-format | Spec: PRP-02/02a | Done: `test_prepare`+`mypy`/`ruff` | Dep: 5.1

## Phase 6: Publish

- [x] 6.1 `src/sofer/publish.py` `_repo_diff_summary`/`_copy_package` delegate to `planned_remotes`, CSV-only `keep_csv` | Spec: PUB-01/02/09 | Done: `test_publish` diff==copy | Dep: 4.1,5.2

## Phase 7: Repo Compliance

- [x] 7.1 `src/sofer/repo_compliance.py` `_build_schema_report_impl` convertible set, normalized staged key, multi-sheet origins, warn+fallback | Spec: RC-Universal | Done: `test_repo_compliance` | Dep: 5.1
- [x] 7.2 `build_dataset_card` `configs.data_files` via `planned_remotes` (xlsx N) | Spec: RC-Universal-Card | Done: card lists `.parquet` | Dep: 7.1

## Phase 8: Docs

- [x] 8.1 `README.md`/`README_ES.md` table+footnote, `docs/configuration.md`, `cli.py` help | Spec: PC-U05 | Done: ES sync, `ruff` | Dep: 3.1

## Phase 9: Test Migration

- [x] 9.1 `tests/test_prepare.py`+`test_parquet_conversion.py` universal expectations, opt-out+passthrough | Spec: PRP-02 | Done: `pytest -q` 795+ | Dep: 5.2
- [x] 9.2 `tests/test_mirror.py`+`test_repo_compliance.py`+`test_publish.py` normalized+N | Spec: PUB/RC | Done: `pytest -q`+`mypy green` | Dep: 4.2,6.1,7.1
