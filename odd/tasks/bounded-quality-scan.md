# Feature: bounded-quality-scan — issue #290

**Branch:** `fix/290-bounded-quality-scan` from `dev@4ca823e`. **Issue:** `emiliodavola/sofer#290`
**Delivery PR:** (this PR) → `dev`. **SDD change:** `openspec/changes/<date>-fix-bounded-quality-scan/`
(archived inside this PR, AGENTS.md rule 15). **Risk:** high — it changes what a `fail`-severity
quality gate sees on a real dataset; unbounded memory is the reported defect.

## Goal

`sofer_validate` / `sofer_prepare` cannot run on a 3.2 GB / 66.2 M-row corpus: a `fail`-severity check
forces a full unsampled pass and two per-row accumulators grow without bound (16.1 GB RSS, killed).
Reproduce with `quality.py`'s own mechanism, then bound every accumulator and make the full-scan
decision explicit and config-owned instead of a side effect of severity. Evidence map: `_has_fail_checks`
(`src/sofer/quality.py:202`), `_process_file` sampling override (`:223-227`), `_distribute_row`
accumulators (`:270-346`), `_col_nonempty` (`:188`), `_dup_hashes`/`_dup_findings` (`:180-181`),
`_check_duplicates` (`:357`), `_check_empty_columns` (`:382`), `_check_encoding_validation` (`:534`).

## Specs

S1 (issue §"Expected behaviour" 1, verbatim): "Make the `empty_columns` bookkeeping a per-column
boolean (\"seen non-empty\") instead of a value set, which removes the largest accumulator for free."
S2 (2, verbatim): "Cap `_dup_hashes` (or switch to a sampled/counting-hash structure) so `duplicates`
memory is independent of dataset size."
S3 (3, verbatim): "Force the full scan only for the checks that actually need it, rather than for the
whole validator, and do not let a cheap 8 KB probe (`encoding_validation`) trigger it."
S4 (4, verbatim): "Expose an explicit full-scan / `max_sample` control that is honoured when set,
instead of being overridden by check severity."
S5 (issue §Summary, verbatim): "a `fail`-severity quality check forces a full **unsampled** pass over
every row, and two per-row accumulators grow without bound."
S6 (issue §"Expected behaviour", verbatim): "A bounded, documented strategy for large datasets."
S7 (derived from S6 + issue §Mechanism: the per-row accumulator list is not limited to the two named
ones): "`_dup_findings`, `_empty_row_numbers` and `_corrupt_findings` are truncated only at report
time (`REPORT_MAX_ITEMS`, `REPORT_MAX_CORRUPT_RECORDS`), so a corpus that is entirely duplicated,
empty or corrupt still grows them to O(rows). Memory SHALL be independent of dataset size for every
per-row accumulator."

## Decisions not in the issue

| # | Decision | Rationale / evidence |
| --- | --- | --- |
| D1 | New knobs are `[tool.sofer]` defaults read through `config.py` (`QUALITY_MAX_DUP_TRACKING`, `QUALITY_FULL_SCAN`), never literals in `quality.py`. | AGENTS.md rule 1; `config.py:406` is the existing quality-default home (`QUALITY_VALUE_PREVIEW_LEN`). |
| D2 | Hitting the duplication cap **stops inserting new hashes and marks the `duplicates` finding partial with the cap named** — no eviction. | Evicting would drop the first-seen row number the `Row a = Row b` message needs and would silently hide later duplicates; a named partial is honest. |
| D3 | S3 is implemented as a **narrower predicate**, not as per-check multi-pass scanning: the scan is full only when an active **`fail`-severity** check is one that needs every row (`corrupt_records`), and `encoding_validation` (8 KB probe) never triggers it. The set of full-scan-requiring checks is config-declared. | The validator is deliberately single-pass (`openspec/project.md`); a per-check multi-pass scan would triple I/O on multi-GB files — out of scope, recorded as a non-goal. |
| D4 | S4's control is tri-state: `auto` (default, today's behaviour), `always`, `never`. `never` honours `[quality] max_sample` even with `fail` checks, and the affected findings are marked `partial`. | "Honoured when set" needs a value that means "I know what I am giving up"; a pure boolean cannot express today's heuristic as the default. |
| D5 | Default `QUALITY_MAX_DUP_TRACKING` is a bounded value that keeps a 66 M-row corpus far below 1 GB, and the cap's existence plus the partial marking are documented in README/README_ES. | S6; a cap nobody knows about is a silent coverage change. |

## Tasks

| # | Task | Spec | State | Evidence |
| --- | --- | --- | --- | --- |
| T1 | RED: bounded-accumulator and behaviour tests — duplicate cap marks `partial` and names the cap; the three finding lists stop growing at their report limits; `encoding_validation`-only `fail` no longer forces the full scan; `quality_full_scan = never` keeps `max_sample` with a `fail` check active; `always` scans everything | S1 S2 S3 S4 S7 | done | RED `24 failed, 5 passed in 2.48s`; GREEN `29 passed`; `tests/test_quality.py` |
| T2 | `_col_nonempty` becomes a per-column "seen non-empty" boolean map (keyed `file::col` as today) | S1 | done | `TestColNonemptyBoolean` 3 passed; `_col_nonempty: dict[str, bool]` |
| T3 | `_dup_hashes` honours `QUALITY_MAX_DUP_TRACKING`; `_check_duplicates` reports the cap and sets `partial` | S2 D2 D5 | done | `TestDuplicateTrackingCap` 2 passed |
| T4 | `_has_fail_checks()` → a full-scan predicate over the config-declared row-requiring check names | S3 D3 | done | `TestFullScanPolicy::test_needs_full_scan_*` 2 passed |
| T5 | `QUALITY_FULL_SCAN` (`auto`/`always`/`never`) read from config and honoured against `max_sample`; per-dataset `[quality] full_scan` wins | S4 D1 D4 | done | `TestFullScanPolicy` 8 passed; `TestQualityFromToml` policy-table scenarios |
| T6 | Cap the three finding lists at accumulation time | S7 | done | `TestAccumulatorCaps` 4 passed |
| T7 | `data-quality` spec delta (the sampling/full-scan clause and the `partial` contract) | S3 S4 S6 | done | delta merged into the canonical spec and archived in this branch |
| T8 | README + README_ES: the bounded strategy, the new knobs, what `partial` means | S6 D5 | done | both sections added (rule 13) |
| T9 | Gates: full suite, `coverage report -m` TOTAL ≥ 90, ruff/format/mypy/pyright, `check_test_mapping.py` | — | done | 2113 passed / 8 skipped; TOTAL 94%; all lint/type gates clean; checker exit 0 |
| T10 | Commit + push + PR (base `dev`, assignee `emiliodavola`), `Closes #290` | — | parent-owned | Tool-safety forbids the worker from `git add`/`git commit`/`git push`; changes left in the worktree |

## Log

L1 (2026-10-13, user, verbatim): "revisá los issues tipo bug e implementalos, 1 rama y PR (asignado a
mi) por issue"
L2: the delegated explore stalled, so the parent mapped the sites directly (`quality.py:180-346`,
`:534-550`) — ditto for the collision with #293 (`_distribute_row`, `_dup_hashes`).
