# Tasks: fix-quality-encoding-xlsx

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 30–50 (additions + deletions) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR (one commit, small diff) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |
| Review budget (session) | 2000 lines — not exceeded |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Gate all P0 checks to CSV/TSV + fix ran_checks + tests | PR 1 → main | Base: main; includes _formats.py, quality.py, tests; single reviewable slice |

## Phase 1: Foundation — Format Registry

- [x] 1.1 Add `TEXT_SUFFIXES: frozenset[str] = frozenset({".csv", ".tsv"})` to `src/sofer/_formats.py` (distinct from `SUPPORTED_FORMATS`, no hardcode elsewhere)
- [x] 1.2 Implement `is_text_eligible(path: Path) -> bool` in `src/sofer/_formats.py` as `path.suffix.lower() in TEXT_SUFFIXES` with docstring (case-insensitive)
- [x] 1.3 Update `src/sofer/_formats.py` module docstring for `TEXT_SUFFIXES` contract (`.csv.gz→.gz` false, `README→""` false)

## Phase 2: Core Implementation — Gated Dispatch

- [x] 2.1 Import `is_text_eligible` in `src/sofer/quality.py`; update module docstring
- [x] 2.2 In `QualityValidator.run()` add `if not is_text_eligible(resolved): continue` after `exists`/`is_dir`, before probe/`stream_csv`
- [x] 2.3 Guard `_check_encoding_validation(resolved)` early-return if not eligible — no result, no `ran_checks`
- [x] 2.4 Guard `_process_file(resolved)` early-return if not eligible — no accumulators, no `ran_checks`
- [x] 2.5 Ensure `ran_checks` only for eligible files; binary-only yields `[]` + `{}` so `publish` shows `0 failed`

## Phase 3: Testing / Verification

- [x] 3.1 In `tests/test_quality.py` test binary skip: `run()` with `.xlsx`/`.parquet`/`.jsonl` fixtures → `quality_results == []`, `ran_checks == {}` (Binary formats skipped)
- [x] 3.2 Test TSV eligible: `.tsv` short row → `corrupt_records` `fail` (TSV is eligible)
- [x] 3.3 Test case/no-extension: `DATA.XLSX`/`README` skipped, `Report.CSV`/`values.TSV` checked
- [x] 3.4 Test binary-only no cross-file: two identical `.xlsx` → no `duplicates`/`cross_file_types`/`empty_columns`/`corrupt_records`
- [x] 3.5 Test defensive guards: direct `_check_encoding_validation(Path("data.xlsx"))` and `_process_file(Path("data.parquet"))` → no result, no `ran_checks`
- [x] 3.6 Test mixed/ran_checks/encoding: `a.csv`+`b.xlsx`+`c.tsv` only eligible reach probe; `data.csv`+`extra.xlsx` `ran_checks` only `data.csv`; binary-only empty; `latin-1` `José` fails, UTF-8 passes, `.xlsx` skipped, mislabeled `.csv` with `PK` → `ValueError`
- [x] 3.7 Verify: `uv run pytest tests/ -q` (795+ pass), `uv run mypy src/`, `uv run ruff check src/ tests/`

## Phase 4: Documentation / Polish

- [x] 4.1 Update docstrings for `run()`, `_check_encoding_validation`, `_process_file` in `src/sofer/quality.py` (gated dispatch, UTF-8-only `utf-8-sig→utf-8`)
- [x] 4.2 Confirm `src/sofer/_csv_reader.py` unchanged and no new `[tool.sofer]` key in `src/sofer/config.py`
