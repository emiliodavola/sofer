# Tasks: Key exact row counts by remote path (row-count-remote-keying)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~110–130 (≈25 src incl. warning, ≈90 tests) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR on `fix/row-count-remote-keying` |
| Delivery strategy | single-pr |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Re-key producers, duplicate warning, docstrings | PR 1 | `src/sofer/repo_compliance.py` |
| 2 | Spec-mapped tests RC-R07/R11/R12 | PR 1 (same) | `tests/test_repo_compliance.py` |
| 3 | Full regression + quality gates | PR 1 (same) | pytest + ruff + mypy |

Per-task verification (Phases 1–2): `uv run pytest tests/test_repo_compliance.py -q && uv run ruff check <touched files> && uv run ruff format --check <touched files>`.

## Phase 1: Core Implementation

- [ ] 1.1 In `src/sofer/repo_compliance.py`, add `_warn_duplicate_remotes(cfg: DatasetConfig) -> None` above `_build_schema_report_impl`: iterate `cfg.files` in declaration order; for each remote declared by 2+ entries print one `  [!] Duplicate remote '<remote>' declared by multiple [[file]] entries; keeping the first entry's row count.` (style of existing `[!]` prints, :571/:579). Docstring states determinism (declaration-order emission) and never-raises. ~10 lines.
- [ ] 1.2 Call `_warn_duplicate_remotes(cfg)` at top of `_build_schema_report_impl` (both public wrappers route through impl — D5).
- [ ] 1.3 Re-key parquet producer (:453): `row_counts[origin_name] = pf.metadata.num_rows` → `row_counts.setdefault(entry.remote, pf.metadata.num_rows)` (verbatim remote, first-wins — D1/D4). Loop's lowered `remote` (:417) stays CSV-gate-only.
- [ ] 1.4 Re-key CSV producer (:514): `row_counts[local.name] = len(rows)` → `row_counts.setdefault(entry.remote, len(rows))`.
- [ ] 1.5 Update docstring contracts (AGENTS.md #2): `_build_schema_report_impl` Returns block (:400–405), `build_schema_report_with_rows` Returns (:649–654), `build_dataset_card` `row_counts` arg (:703) — keys are verbatim POSIX `entry.remote`, unique per well-formed dataset, duplicates keep FIRST count + `[!]`, sole consumer sums values. Include gate-review note: if the first-declared entry's file is unreadable it contributes no entry, so a later same-remote entry stores its count. Add partial-counts-undercount comment at splits computation (:789–793).

## Phase 2: Tests (map every spec scenario)

- [ ] 2.1 RC-R07 "num_examples equals actual rows" — existing assertion `{"d.csv": 5}` (:1944) stays valid; append comment: keys are verbatim remotes.
- [ ] 2.2 RC-R07 "Multi-file splits sum" — assertion `{"a.csv": 30, "b.csv": 40}` (:1964) stays valid; append remote-keys comment.
- [ ] 2.3 RC-R07 same-stem regression (new test): fixture `tmp_path/a/data.csv` (30 rows) + `tmp_path/b/data.csv` (40 rows), remotes `a/data.csv` / `b/data.csv`; assert `row_counts == {"a/data.csv": 30, "b/data.csv": 40}` and `num_examples == 70`.
- [ ] 2.4 RC-R07 dual-path keying (new test): one staged-parquet entry + one `upload_as_csv` entry, distinct remotes; assert both counts keyed by their respective `entry.remote`.
- [ ] 2.5 RC-R07 "Single-remote unchanged" — update :1985 `{"p.parquet": 5}` → `{"p.csv": 5}` (remote now the key); adjust test name/comment accordingly.
- [ ] 2.6 RC-R11 duplicate warns (new test): two `[[file]]` entries sharing a remote; capsys asserts exactly one `[!]` naming that remote, build completes, first entry's count kept in dict.
- [ ] 2.7 RC-R11 silence (new test): all-unique remotes → no duplicate-remote warning in captured output.
- [ ] 2.8 Gate-review warning-ordering assertion: config duplicating two distinct remotes → warnings appear in first-declaration order (extend 2.6 or sibling test).
- [ ] 2.9 RC-R12 recursive-only fallback (new test): only recursive entries, `row_counts=None` → `num_examples == config.CARD_FALLBACK_ROWS_PER_FILE × len(cfg.files)`.
- [ ] 2.10 RC-R12 excluded-files fallback (new test): all `include_in_schema=false`, `row_counts={}` → same fallback product.
- [ ] 2.11 Append clarifying comments at :1944, :1964, :2020 (`{"w.csv": 3}` wrapper test) noting keys are verbatim remotes.

## Phase 3: Final Regression

- [ ] 3.1 Full gates: `uv run pytest tests/ -q` (baseline green, no skips added), `uv run ruff check .`, `uv run ruff format --check .`, mypy under Python 3.13 (`uv run mypy src/`). Confirm diff ≈110–130 lines; commit as reviewable work units (Unit 1 → Unit 2 → Unit 3).
