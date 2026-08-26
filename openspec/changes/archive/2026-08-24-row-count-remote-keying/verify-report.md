```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:857bd15c76442e77171f9a4371e546a78e1306bc54a15ce418818d87977e5eb4
verdict: pass
blockers: 0
critical_findings: 0
requirements: 3/3
scenarios: 9/9
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:aee06016faf97c3ae5cf37ba019772bec352ef780c967b73233ae7b7730e16e0
build_command: uv run mypy src/
build_exit_code: 0
build_output_hash: sha256:653c24af21ad3bc4a8cf9a6ba237261490a6dc0b9703ef71eef912330b8ca539
```

## Verification Report

**Change**: row-count-remote-keying
**Version**: repo-compliance delta (RC-R07 modified; RC-R11, RC-R12 added)
**Mode**: Standard (no Strict TDD)
**Branch**: `fix/row-count-remote-keying` — commits bc06500, bc89e74, ccd9719, 72c1bea

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 17 |
| Tasks complete | 17 |
| Tasks incomplete | 0 |

All tasks verified checked in `openspec/changes/row-count-remote-keying/tasks.md` with corresponding code/test evidence on disk.

### Build & Tests Execution
**Build**: ✅ Passed
```text
$ uv run mypy src/
Success: no issues found in 24 source files   (exit 0)
$ uv run ruff check src/ tests/
All checks passed!                            (exit 0)
$ uv run ruff format --check src/ tests/
45 files already formatted                    (exit 0)
```

**Tests**: ✅ 757 passed / ❌ 0 failed / ⚠️ 0 skipped (13 pre-existing DeprecationWarnings in test_codebook.py, unrelated to this change)
```text
$ uv run pytest tests/ -q
757 passed, 13 warnings in ~4s                (exit 0)
Targeted subset:
$ uv run pytest tests/test_repo_compliance.py -k "TestNumExamplesFromRowCounts or
  TestDuplicateRemoteWarning or TestNonSchemaRowCountFallback or
  TestBuildSchemaReportWithRowsWrapper" -v
13 passed, 141 deselected                     (exit 0)
```

**Coverage**: ➖ Not available (no coverage tool configured)

### Spec Compliance Matrix
| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| RC-R07 | num_examples equals actual rows | `tests/test_repo_compliance.py > TestNumExamplesFromRowCounts::test_num_examples_equals_actual_rows_csv` | ✅ COMPLIANT |
| RC-R07 | Multi-file splits sum per-file row counts | `tests/test_repo_compliance.py > TestNumExamplesFromRowCounts::test_multi_file_sums_row_counts` | ✅ COMPLIANT |
| RC-R07 | Same-stem subdirectory remotes keep distinct counts | `tests/test_repo_compliance.py > TestNumExamplesFromRowCounts::test_same_stem_subdirectory_remotes_keep_distinct_counts` | ✅ COMPLIANT |
| RC-R07 | Parquet and CSV paths both key by remote | `tests/test_repo_compliance.py > TestNumExamplesFromRowCounts::test_parquet_and_csv_paths_both_key_by_remote` | ✅ COMPLIANT |
| RC-R07 | Single-remote behavior unchanged | `tests/test_repo_compliance.py > TestNumExamplesFromRowCounts::test_num_examples_equals_actual_rows_csv` (+ `test_parquet_row_count_not_capped_by_sample` asserting `{"p.csv": 5}`) | ✅ COMPLIANT |
| RC-R11 | Hand-edited TOML with duplicate remotes warns | `tests/test_repo_compliance.py > TestDuplicateRemoteWarning::test_duplicate_remote_warns_once_and_keeps_first` | ✅ COMPLIANT |
| RC-R11 | Distinct remotes stay silent | `tests/test_repo_compliance.py > TestDuplicateRemoteWarning::test_unique_remotes_stay_silent` | ✅ COMPLIANT |
| RC-R12 | Recursive-only dataset uses fallback | `tests/test_repo_compliance.py > TestNonSchemaRowCountFallback::test_recursive_only_dataset_uses_fallback` | ✅ COMPLIANT |
| RC-R12 | Excluded-from-schema files contribute no exact counts | `tests/test_repo_compliance.py > TestNonSchemaRowCountFallback::test_excluded_files_fallback` | ✅ COMPLIANT |

**Compliance summary**: 9/9 scenarios compliant (plus gate-review ordering test `test_duplicate_remote_warnings_in_declaration_order`, beyond spec minimum)

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| RC-R07 | ✅ Implemented | Both producer sites re-keyed: parquet `row_counts.setdefault(entry.remote, pf.metadata.num_rows)` (repo_compliance.py:487), CSV `row_counts.setdefault(entry.remote, len(rows))` (:550). Keys are verbatim `entry.remote`; loop's lowered `remote` (:449) remains CSV-gate-only. Sole production consumer (`prepare.py:714`) passes dict through to `build_dataset_card`, which sums `.values()` only (:840). No key-reading consumers found. |
| RC-R11 | ✅ Implemented | `_warn_duplicate_remotes` (:383–405) iterates `cfg.files` in declaration order, emits one `[!]` per duplicated remote, never raises (`FileEntry.remote: str` is required — model.py:68), called at top of `_build_schema_report_impl` (:438) so both public wrappers route through it (D5). First-wins enforced by `setdefault` (D4). |
| RC-R12 | ✅ Implemented | Recursive/non-.csv/excluded entries skip both producers (:449–450 gate); fallback `CARD_FALLBACK_ROWS_PER_FILE × len(cfg.files)` read via `config.X` at call time (:831–843 region), not hardcoded. |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| D1 verbatim remote key (no normalization) | ✅ Yes | Keys use raw `entry.remote`; case-sensitivity documented in design Open Questions |
| D2 ColumnSchema.origin stays basename-based | ✅ Yes | `origin_name` still derived from `local.name`/stem.parquet (:464–471), used only for ColumnSchema.origin (:535); no join against keys |
| D3 Return type unchanged | ✅ Yes | Still `tuple[list[ColumnSchema], dict[str, int]]` |
| D4 setdefault first-declared-wins at BOTH sites | ✅ Yes | Verified at :487 and :550 in diff |
| D5 Warning at impl top, both wrappers covered | ✅ Yes | `_warn_duplicate_remotes(cfg)` first statement of impl |

Docstring contracts updated accurately for `_build_schema_report_impl`, `build_schema_report_with_rows`, and `build_dataset_card`'s `row_counts` arg, including the gate-review note about unreadable first entries. Partial-counts undercount comment added at splits computation.

### Adversarial Diff Review (git diff dev...HEAD)
- setdefault first-wins implemented at BOTH producer sites — confirmed.
- Warning deterministic (dict insertion order = declaration order) and cannot raise (required str field; pure dict/print ops).
- No missed consumer: grep across src/ shows only `prepare.py:714/:748/:757` (pass-through) and the value-summing consumer. `verification.py`'s `split_row_counts` is an unrelated per-split structure from loaded datasets.
- Same-stem fixture asserts `row_counts == {"a/data.csv": 30, "b/data.csv": 40}` AND `num_examples == 70` — confirmed.
- Diff size ~182 test lines + ~55 src lines vs ~110–130 forecast — single-PR scale, budget respected (apply deviation, documented).
- Out-of-scope items untouched: staged-parquet flat-stem lookup bug left as designed (follow-up issue).

### Issues Found
**CRITICAL**: None
**WARNING**: None
**SUGGESTION**: None blocking. Residual documented behavior (mixed schema/non-schema partial counts silently undercount) is specced as unchanged in RC-R12 non-goals — no action this change.

### Verdict
PASS — all gates green (757 tests, ruff check/format, mypy clean); all 9 spec scenarios mapped to passing runtime tests; implementation matches design decisions D1–D5 exactly.
