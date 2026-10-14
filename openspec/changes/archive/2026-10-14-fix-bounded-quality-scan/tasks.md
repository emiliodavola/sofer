# Tasks: fix-bounded-quality-scan

**Change** `2026-10-14-fix-bounded-quality-scan` (GitHub **#290**) · branch
`fix/290-bounded-quality-scan` from `dev@4ca823e` · store **hybrid** — this file plus the Engram
mirror.

**Inputs read this phase, directly:** `odd/tasks/bounded-quality-scan.md` (specification of record),
`design.md` and `proposal.md` of this change.

**One-line outcome:** per-row memory is bounded independently of dataset size, and the full-scan
decision is an explicit config-owned tri-state instead of a side effect of `fail` severity.

---

## TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`, but this change alters production behaviour, so the
carrier is nevertheless a real red-then-green:

- **RED (measured, before the fix):** the new focused selection ran
  `24 failed, 5 passed in 2.48s` — every bounded-scan test failed on `AttributeError` /
  `TypeError` against the old code (`_needs_full_scan` does not exist; `_col_nonempty` is a set;
  `config.QUALITY_MAX_DUP_TRACKING` does not exist).
- **GREEN (measured, after the fix):** the same focused selection ran `29 passed in 2.60s`; the two
  touched files ran `157 passed`; the full suite ran **2113 passed, 8 skipped** on base `4ca823e`
  (base was `2087 passed, 9 skipped`; the one-test skip delta is host symlink availability, not
  change-related).
- **TRIANGULATE:** `test_accumulator_sizes_do_not_grow_with_dataset_size` proves the memory bound
  structurally — two stream sizes (100 and 3000 rows) produce byte-identical accumulator sizes.
- **REFACTOR:** the two duplicated accumulator-growth sites were extracted to `_capped_append`.

---

## Tasks

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | RED: bounded-accumulator and behaviour tests (cap marks `partial` + names cap; three lists stop growing; `encoding_validation`-only `fail` no longer forces the full scan; `never` keeps `max_sample`; `always` scans everything) | done | `24 failed, 5 passed in 2.48s` |
| T2 | `_col_nonempty` becomes a per-column boolean keyed `file::col` | done | `TestColNonemptyBoolean` 3 passed; `_col_nonempty: dict[str, bool]` |
| T3 | `_dup_hashes` honours `QUALITY_MAX_DUP_TRACKING`; `_check_duplicates` names the cap and sets `partial` | done | `TestDuplicateTrackingCap` 3 passed |
| T4 | `_has_fail_checks()` → `_needs_full_scan()` over `config.QUALITY_ROW_REQUIRING_CHECKS` | done | `TestFullScanPolicy::test_needs_full_scan_*` 2 passed |
| T5 | `QUALITY_FULL_SCAN` (`auto`/`always`/`never`) read from config and honoured against `max_sample`; per-dataset `[quality] full_scan` wins | done | `TestFullScanPolicy` 8 passed; `TestQualityFromToml` policy-table scenarios passed |
| T6 | Cap `_dup_findings`, `_empty_row_numbers`, `_corrupt_findings` at accumulation time via `_capped_append` | done | `TestAccumulatorCaps` 4 passed |
| T7 | `data-quality` spec delta (bounded scan + `partial` contract) | done | `openspec/changes/2026-10-14-fix-bounded-quality-scan/specs/data-quality/spec.md`, merged into the canonical spec, archived in this branch |
| T8 | README + README_ES: bounded strategy, new knobs, `partial` semantics | done | both sections added (rule 13) |
| T9 | Gates: full suite, coverage TOTAL ≥ 90, ruff/format/mypy/pyright, `check_test_mapping.py` | done | see the gate battery below |
| T10 | Commit + push + PR (base `dev`, assignee `emiliodavola`), `Closes #290` | parent-owned | Tool-safety forbids the worker from `git add`/`git commit`; changes are left in the worktree for the parent |

---

## Gate battery (measured on base `4ca823e`)

| Command | Result |
| --- | --- |
| `uv run pytest tests/ -q` | **2113 passed, 8 skipped** (base `2087 passed, 9 skipped`) |
| `uv run coverage run -m pytest` | 2113 passed, 8 skipped |
| `uv run coverage report -m` | **TOTAL 94%** (base 94%); `quality.py` **91%** (base 89%); `cli.py`/`scanner.py`/`prepare.py`/`publish.py` **100%** |
| `uv run ruff check src/ tests/ scripts/` | clean |
| `uv run ruff format --check src/ tests/` | clean |
| `uv run mypy src/ scripts/` | clean |
| `uv run pyright` | clean |
| `uv run python scripts/check_test_mapping.py` | exit 0 (no registry edit) |

The parent re-runs the full battery on the rebased state; these numbers are the pre-rebase run.

---

## Rebase note (parent action, per the parent's heads-up)

The branch is based on `dev@4ca823e`; `origin/dev` has since merged #293, which changed
`_distribute_row` / `_check_duplicates` (the duplicate finding keeps its file and emits pairs
round-robin across files). This change overlaps those exact methods:

- `_reset_accumulators`: `_dup_hashes` / `_dup_findings` typing plus the new `_dup_hashes_capped`.
- `_distribute_row` duplicates block: insertion is wrapped in the cap (new hash stops at the cap;
  an already-tracked hash appends the pair via `_capped_append`).
- `_check_duplicates`: the message is built once and gains the cap note; the pair list keeps whatever
  shape #293 gives it.

Resolution as delivered: keep #293's file-scoped round-robin pair emission **and** #290's bound, by
grouping the pairs per file — `_dup_findings` is a `dict[str, list[tuple[int, int]]]`, each file's
list capped at `REPORT_MAX_ITEMS` through the new `_record_duplicate_pair()`, and `_check_duplicates`
emits the round-robin over those lists while still adding the cap note and the `partial` flag (its
`max(..., default=0)` guard covers the capped-with-no-pairs case). A single global cap applied in
scan order would have re-broken the round-robin: the first `REPORT_MAX_ITEMS` pairs all come from the
noisy file, which is exactly what #293 fixed. The hash insertion cap (`quality_max_dup_tracking`)
stays global, and the two `TestAccumulatorCaps` assertions now measure the per-file lists.

---

## Constraints honoured

- **No `# pragma: no cover` anywhere.** The four rule-14 modules stay at 100.00%.
- **No literal defaults in `quality.py`** — all three knobs are read through `config`.
- **Every touched public/complex method has a docstring** (AGENTS.md rule 2).
- **Removal declared:** `quality_value_preview_len` removal is listed in `design.md` §5.4, the delta
  (`## Config-surface removal recorded by this change`), this file and the archive report.
- **No registry edit:** `data-quality` stays a permanent declared-backlog spec.
