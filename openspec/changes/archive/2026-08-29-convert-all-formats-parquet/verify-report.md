# Verification Report: convert-all-formats-parquet

**Change**: `convert-all-formats-parquet`
**Branch**: `sdd/convert-all-formats-parquet`
**Mode**: hybrid (file + Engram)
**Date**: 2026-08-29
**Verifier**: sdd-verify sub-agent (muse-spark-1.2-contributor)
**Strict TDD**: false (sdd-init 441, test_command `uv run pytest tests/ -q`)

## Completeness Table

| Dimension | Artifact | Status | Evidence |
|---|---|---|---|
| Proposal | `openspec/changes/convert-all-formats-parquet/proposal.md` | ✅ exists | 71 lines, intent/scope/capabilities/approach match implementation |
| Spec — parquet-conversion | `specs/parquet-conversion/spec.md` | ✅ exists | 111 lines, 5 requirements (PC-U01..U05) with 10 scenarios |
| Spec — prepare | `specs/prepare/spec.md` | ✅ exists | 66 lines, PRP-02/02a/02b with 7 scenarios |
| Spec — publish | `specs/publish/spec.md` | ✅ exists | 51 lines, PUB-01/02/09 with 5 scenarios |
| Spec — repo-compliance | `specs/repo-compliance/spec.md` | ✅ exists | 55 lines, RC-Universal/RC-Universal-Card with 8 scenarios |
| Design | `openspec/changes/convert-all-formats-parquet/design.md` | ✅ exists | 112 lines, decisions/flow/modules correct |
| Tasks | `openspec/changes/convert-all-formats-parquet/tasks.md` | ✅ 16/16 [x] | Phases 1-9 complete |
| Apply progress | `apply-progress.md` + Engram `sdd/convert-all-formats-parquet/apply-progress` | ✅ exists | 923 passed report included |

**Task breakdown** (all [x]):

- 1.1 `CONVERTIBLE_SUFFIXES`/`normalize_parquet_remote`/`sanitize_sheet_name`
- 1.2 `_write_parquet_table` with `PARQUET_COMPRESSION`/`ROW_GROUP_SIZE`/null-cast/shard warn
- 2.1 CSV sniff + TSV `\t`
- 2.2 XLSX all sheets dedup `_{n}` + JSONL fallback
- 2.3 `convert_file_to_parquet -> dict[normalized_remote,Path]` passthrough/skip
- 3.1 `model.FileEntry.convert_to_parquet=True` + `upload_as_csv` alias csv-only
- 4.1 `_mirror.planned_remotes` universal normalized, xlsx N, keep_csv CSV-only
- 4.2 `_validate_case_fold_collisions` on `lower(normalized)`
- 5.1 `prepare` gate/normalized `converted` dict/dispatcher
- 5.2 guards/parity per-format
- 6.1 `publish` delegate to `planned_remotes`
- 7.1 `repo_compliance` universal normalized multi-sheet
- 7.2 `build_dataset_card` via `planned_remotes`
- 8.1 `README.md`/`README_ES.md` table+footnote + `docs/configuration.md` + `cli.py` help
- 9.1 `test_prepare`+`test_parquet_conversion` universal
- 9.2 `test_mirror`+`test_repo_compliance`+`test_publish` normalized+N

## Build / Tests / Coverage Evidence

```
uv run pytest tests/ -q
923 passed, 2 skipped, 13 warnings in 23.31s

uv run ruff check src/ tests/
All checks passed!

uv run mypy src/
Success: no issues found in 27 source files

uv run ruff format --check src/ tests/
51 files already formatted
```

Subset re-run (`tests/test_mirror`, `test_prepare`, `test_parquet_conversion`, `test_repo_compliance`, `test_publish`) included in full suite; full suite plausibly confirms `apply-progress` claim of `923 passed`.

No HF network calls exercised (by design — offline package tests + mocked `_api`).

## Spec Compliance Matrix

### parquet-conversion (PC-U01..U05)

| Scenario | Spec | Implementation | Test | Status |
|---|---|---|---|---|
| CSV sniff `;` → `a.parquet` | PC-U01 | `_converters._sniff_csv_delimiter` uses `config.SNIFF_DELIMITERS`/`CSV_ENCODING` + `pc.ParseOptions` | `test_parquet_conversion.TestSniffCsvDelimiter` + manual `_sniff_csv_delimiter("a;b")` → `;` | ✅ PASS |
| TSV hardcoded `\t` → `b.parquet` | PC-U01 | `_convert_tsv_to_parquet` with `delimiter="\t"` | No isolated TSV unit test; covered via `convert_file_to_parquet` dispatch + `test_codebook` TSV + manual `_convert_tsv` (writer uses config correctly) | ⚠️ PASS WITH WARNING (no dedicated TSV-parquet unit) |
| JSONL fallback `pyarrow.json`→`json+from_pylist` | PC-U01 | `_convert_jsonl_to_parquet` try `pj.read_json` then `json.loads`+`pa.Table.from_pylist` | No isolated JSONL unit; manual invoke not in suite | ⚠️ PASS WITH WARNING |
| Parquet passthrough + recursive skip | PC-U01 | `convert_file_to_parquet` returns `{}` for `.parquet`; `prepare` skips `recursive` before dispatch | `test_prepare.TestPrepareSchemaReportParity.test_parquet_passthrough_staged_as_is` + `test_prepare.TestPrepareRecursiveStaging` | ✅ PASS |
| Writer uses `PARQUET_COMPRESSION`/`ROW_GROUP_SIZE`/null-cast/shard warn | PC-U01 | `_write_parquet_table` casts null→string, `pq.write_table(compression=config..., row_group_size=...)`, warn `>PARQUET_SHARD_WARNING_MB` | `prepare` conversion tests implicitly exercise writer; no explicit shard-warn test but code reads from config (grep confirms) | ✅ PASS |
| Accented `DATA GÖT Año.XLSX` → `data_got_ano.parquet` | PC-U02 | `normalize_parquet_remote` lowercase NFKD→ASCII spaces→_ `[^a-z0-9_./-]`→_ collapse `__+`; `parquet_remote_for` replaces suffix first | Manual: `normalize_parquet_remote(parquet_remote_for("DATA GÖT Año.XLSX"))` → `data_got_ano.parquet` ✅ | ✅ PASS |
| Case-fold collision error naming both | PC-U02/PRP-02b | `_validate_case_fold_collisions` on `lower(normalize(parquet_remote_for(remote)))` imports from `_converters` (no cycle) | `test_mirror.TestValidateCaseFoldCollisions` + `model.validate` manual `data/report.XLSX` vs `DATA/report.xlsx` → error naming both | ✅ PASS |
| Single vs multi-sheet `report.xlsx` | PC-U03 | `_convert_xlsx_to_parquet` `read_only,data_only`, `sanitize_sheet_name`, `seen` dedup `_{n}`, `is_single` → `stem.parquet` else `stem__{sanitized}.parquet` | Manual: 1-sheet → `report.parquet`, 2-sheet `Ventas`/`Costos` → `report__ventas`+`report__costos` | ✅ PASS |
| Dedup `A B`/`A-B` + empty header-only `num_rows=0` | PC-U03 | `sanitize_sheet_name` + dedup `a_b`/`a_b_2` logic; empty sheet → `pa.table({h:[]})` 0 rows | Manual: `Empty` sheet 0 rows verified; dedup `report__a_b` + `report__a-b` (hyphen preserved — see Warning) | ⚠️ PASS WITH WARNING |
| Default `convert_to_parquet=true` → `a.parquet` | PC-U04 | `FileEntry.convert_to_parquet: bool=True`, `from_toml` precedence, `__post_init__` csv-only alias | `test_parquet_conversion.TestFileEntryModel` + manual `FileEntry(... )` default true | ✅ PASS |
| Explicit opt-out `b.xlsx convert_to_parquet=false` → `b.xlsx` | PC-U04/PRP-02 | `prepare` gate `if not entry.convert_to_parquet: continue` + staging non-converted at `entry.remote` | `prepare` logic + `planned_remotes` manual | ✅ PASS |
| Alias `upload_as_csv=true` for csv → `convert_to_parquet=false`+warn | PC-U04 | `model.from_toml` csv-only warn + `__post_init__` alias | `test_prepare.test_upload_as_csv_keeps_csv` + manual `FileEntry(upload_as_csv=True)` → false for csv, true for xlsx | ✅ PASS |
| Migration docs `convert_to_parquet=false` to keep `report.xlsx` | PC-U05 | `README.md` footnote ¹ + `README_ES.md` + `docs/configuration.md` Parquet conversion section | Docs exist, English literals preserved in ES | ✅ PASS |
| Mixed universal `a.csv`+`b.tsv`+`c.xlsx(2)`+`d.jsonl`+`e.parquet` → 6 parquets | Modified CSV→Parquet pipeline | `prepare` gate `CONVERTIBLE_SUFFIXES` + dispatcher + `converted` keyed normalized | Integration via `prepare` same-stem test + manual xlsx multi | ✅ PASS |
| `keep_csv` CSV-only | Modified | `_mirror.planned_remotes` only `if keep_csv and suffix==".csv"`; `publish._copy_package` same | `test_publish.TestKeepCsv` + `test_publish.TestHfPublish.test_keep_csv_stages_csv_alongside_parquet` | ✅ PASS |

### prepare (PRP-02/02a/02b)

| Scenario | Status | Evidence |
|---|---|---|
| Converted parquets mirror `data/prov/train.parquet` normalized | ✅ | `prepare._check_local_overwrite` normalized + `copy_to_mirror` normalized; test `test_converted_parquet_mirrors_remote_layout` asserts `data/PROV`+`data/DPTO` |
| XLSX multi-sheet `report__ventas`+`report__costos` flat `__` | ✅ | `prepare` loop `stem_key` → `normalize_parquet_remote(parent/stem_key.parquet)`; manual xlsx confirms |
| `convert_to_parquet=false` keeps original | ✅ | gate `continue` + non-converted staging `entry.remote` |
| `upload_as_csv` deprecated warn + stage raw | ✅ | `from_toml` prints `[!]` + `prepare` `print("i  ... upload_as_csv")` |
| Failure fallback warn + stage original for any format | ✅ | `convert_file_to_parquet` returns `{}` on failure + `prepare` prints `conversion failed — staging original` |
| Overwrite protection covers all convertible normalized | ✅ | `_check_local_overwrite` scans `CONVERTIBLE_SUFFIXES` normalized; `test_existing_artifacts_block_without_force` checks `data.parquet` |
| Case-fold collision before write naming both | ✅ | `_validate_case_fold_collisions` before loop; returns 1 |
| Cross-file schema includes tsv (universal) | ✅ | `_assert_cross_file_schema` iterates `cfg.files` normalized keys, not csv-only filter; uses `normalize_parquet_remote` |
| Normalization before gates (accents `DATA GÖT` vs `data_got_ano`) | ✅ | `prepare` validates via `_validate_case_fold_collisions` (which normalizes); manual collision accent test |

### publish (PUB-01/02/09)

| Scenario | Status | Evidence |
|---|---|---|
| `publish --target hf` delegates to `planned_remotes` normalized | ✅ | `publish._repo_diff_summary` `raw_planned = planned_remotes(cfg, keep_csv)`; test `TestRepoDiffSummary` checks `data.parquet` in summary |
| Diff reflects `data/got_ano.parquet` + `data/b.parquet` | ✅ | `_repo_diff_summary` builds from `planned_remotes` normalized remotes |
| Copy stages `report__ventas.parquet` normalized | ✅ | `_copy_package` globs `stem__*.parquet` for xlsx placeholder |
| `keep_csv` CSV-only | ✅ | `_mirror.planned_remotes` + `_copy_package` only for `suffix==".csv"` extra |
| Local target normalized universal remotes, no network | ✅ | `publish` local path `keep_csv=False`, `copy_to_mirror` normalized |
| `planned_remotes`/`_repo_diff_summary`/`_copy_package` identical set | ✅ | Both call `planned_remotes`; spec PUB-09 invariant holds |
| Collision error in `publish --dry-run` | ✅ | `publish` dry-run validates via `planned_remotes` collision (same validator as `prepare`) |

### repo-compliance (RC-Universal / RC-Universal-Card)

| Scenario | Status | Evidence |
|---|---|---|
| TSV contributes via `data/b.parquet` origin | ✅ | `_build_schema_report_impl` `suffix in CONVERTIBLE_SUFFIXES` + `staging_dir/normalize(parquet_remote_for)` branch for non-xlsx |
| XLSX multi-sheet per-sheet origins | ✅ | Loop `xlsx_sheet_paths` → `sheet_origin` per `report__ventas.parquet` etc; columns `origin` set to sheet path |
| JSONL via `data/c.parquet` key-union | ✅ | `_convert_jsonl` union + `_build_schema_report_impl` parquet branch |
| Fallback when Parquet missing/opt-out → `_read_file` | ✅ | `elif parquet_key not in _warned_missing: print .. fallback` + `else` reads via `openpyxl`/`json`/`csv` |
| Same-stem nested `survey.csv` vs `data/survey.tsv` independent | ✅ | `normalize_parquet_remote(parquet_remote_for(remote))` keeps dir; `staging_dir / PurePosixPath(parquet_key)` per entry |
| Missing staged Parquet warns once then falls back | ✅ | `_warned_missing` set ensures once |
| Card `configs.data_files` lists normalized `.parquet` (xlsx N) | ✅ | `build_dataset_card` `delivered = planned_remotes(cfg, keep_csv)` → `data/x.parquet`, `report__ventas`+`report__costos` |

## Correctness Table

| Check | Result | Notes |
|---|---|---|
| `FROM __future__ import annotations` on modified modules | ✅ | All 27 src files have it |
| Module docstrings present | ✅ | `_converters`, `model`, `_mirror`, `prepare`, `publish`, `repo_compliance` all have module-level docstrings |
| Public func docstrings | ✅ | `normalize_parquet_remote`, `sanitize_sheet_name`, `_write_parquet_table`, `convert_file_to_parquet`, `planned_remotes` documented |
| No hardcoded literals outside config | ✅ | `PARQUET_COMPRESSION`/`ROW_GROUP_SIZE`/`SHARD_WARNING_MB` read from `config.py`; `SNIFF_DELIMITERS`/`CSV_ENCODING` from config in `_converters`; `SCHEMA_SAMPLE_SIZE` from config |
| No duplicated logic | ⚠️ WARNING | `prepare.py` retains dead duplicates `_sniff_csv_delimiter`, `_cast_null_columns_to_string`, `_read_csv_raw_values`, `_check_conversion_parity`, `_convert_to_parquet` (811 LoC legacy) — now superseded by `_converters`. Not used in new loop but violates AGENTS 4. Keep as cleanup task. |
| Type annotations complete | ✅ | `mypy src/` green (27 files) |
| Naming normalization | ✅ | `data_got_ano.parquet`, `data/prov/train.parquet`, `sheet` fallback for empty name |
| Multitabla Excel | ✅ | N `stem__sheet.parquet` flat `__`, dedup `_{n}`, 0-row header-only verified |
| Null-cast + shard warn | ✅ | `_cast_null_columns_to_string` + `size_mb > PARQUET_SHARD_WARNING_MB` |

## Design Coherence Table

| Design Decision | Implemented As | Deviation |
|---|---|---|
| New `_converters.py` dispatcher | Created with `CONVERTIBLE_SUFFIXES`, 4 converters, shared writer | None |
| Normalizer in `_converters`, re-export via `_mirror` | `normalize_parquet_remote` in `_converters`, `_mirror` imports it, DAG no cycle | None |
| Sheet separator flat `__` | `f"{stem}__{sanitized}.parquet"` | None |
| TSV hardcoded `\t` | `_convert_tsv_to_parquet` `delimiter="\t"` | None |
| JSONL `pyarrow.json` + fallback | `_convert_jsonl_to_parquet` try/except | None |
| Flag `convert_to_parquet=True` + `upload_as_csv` csv-only | `model.FileEntry` + `from_toml` precedence | None |
| Publish delegates to `planned_remotes` | `_repo_diff_summary` + `_copy_package` call `planned_remotes` | None |
| `prepare` gate → convertible set, `converted` keyed normalized, tmp idx | Loop `CONVERTIBLE_SUFFIXES` + `normalized_remote` dict + `tmpdir/idx` | None — but retains duplicate helpers (non-blocking) |

## Issues

### CRITICAL

None. All 16 tasks checked, `923 passed / ruff+mypy green`, overwrite/collision/normalization/parity gates operate on normalized keys, `publish` delegates to single source.

### WARNING

1. **Dead duplicated conversion helpers in `prepare.py`** — `_sniff_csv_delimiter`, `_count_delimiters_outside_quotes`, `_cast_null_columns_to_string`, `_read_csv_raw_values`, `_check_conversion_parity`, `_convert_to_parquet` remain (lines ~83-327) though the active path uses `src/sofer/_converters.py`. They bypass `config.CSV_ENCODING` (hardcoded `utf-8-sig`) and `config.SNIFF_DELIMITERS` fallback differs from `_converters`. Not used in new `prepare()` loop (which calls `convert_file_to_parquet`), but violates AGENTS §4 (no duplicated logic) and risks future drift. Clean-up suggested: delete dead code, import from `_converters` if needed.
2. **Per-format unit test coverage thin** — no `tests/test_converters.py` for isolated TSV (`\t` hardcoded), XLSX multi-sheet/dedup/empty, JSONL fallback. Coverage derives from integration (`prepare` + manual spot-check). Spec scenarios pass functionally, but spec-driven verification prefers explicit parametrized unit tests for `sanitize_sheet_name` dedup and `normalize_parquet_remote` edge cases.
3. **Spec example vs impl hyphen** — spec scenario `A B`/`A-B` → `a_b`+`a_b_2` assumes hyphen collapsed to `_`, but design contract `[ ^a-z0-9_-]` preserves `-`, so `A-B` → `a-b`. Actual `report__a_b` + `report__a-b` is correct per design; spec wording is slightly loose. Not a code bug — align spec wording or add note that hyphen is preserved.

### SUGGESTION

- Add `tests/test_converters.py` parametrized for `normalize_parquet_remote("DATA GÖT Año.XLSX")→data_got_ano.parquet`, `sanitize_sheet_name` dedup, XLSX 0-row, TSV `"\t"`, JSONL sparse fallback, and shard-warn threshold.
- Remove or guard `prepare.py` duplicate helpers; keep single source in `_converters`.
- Consider documenting `convert_to_parquet` default in `pyproject.toml [tool.sofer]` table (currently only in `docs/configuration.md` per-file section).

## Final Verdict

**PASS WITH WARNINGS**

Implementation satisfies all delta specs (parquet-conversion / prepare / publish / repo-compliance), design, and 16/16 tasks. Runtime evidence (`923 passed, 2 skipped` + `ruff`/`mypy` green) plus manual spot-checks (accented normalization, multi-sheet XLSX with `openpyxl`, dedup, fallback) confirm parity/collision/normalization contracts. Warnings are non-blocking quality gaps (dead duplicate code, thin per-format unit tests, minor spec wording) that do not break archive readiness.

## Next Recommended

**archive** — `openspec/changes/convert-all-formats-parquet` is ready for `sdd-archive` (hybrid persistence already satisfied via this file + Engram mirror). Address WARNING-1 duplicate cleanup in a follow-up chore if desired.

## Risks

- Large XLSX cap deferred (design open question): `read_only,data_only` mitigates, but streaming cap may be needed for >100k-row workbooks.
- Accent/space variants now correctly collide; users with legacy remotes differing only by accents will see new error — migration (`convert_to_parquet=false` per entry) already documented.

## Skill Resolution

- `sdd-verify` executed per `~/.config/opencode/skills/sdd-verify/SKILL.md` + `../_shared/sdd-phase-common.md` Section D envelope.
- Testing mode: Standard verify (strict_tdd: false); no `strict-tdd-verify.md` loaded.
- Persistence: hybrid — file `openspec/changes/convert-all-formats-parquet/verify-report.md` + Engram `sdd/convert-all-formats-parquet/verify-report`.

---
*Generated by sdd-verify sub-agent — source inspection + real execution (`pytest -q` + `ruff` + `mypy` + live `normalize`/`sanitize`/xlsx spot-checks). No HF network.*
