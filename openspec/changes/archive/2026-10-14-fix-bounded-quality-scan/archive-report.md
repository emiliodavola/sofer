# Archive Report: Bound the quality scan and make it explicit

**Change**: `2026-10-14-fix-bounded-quality-scan`
**Archived to**: `openspec/changes/archive/2026-10-14-fix-bounded-quality-scan/`
**Branch**: `fix/290-bounded-quality-scan` (base `dev@4ca823e`)

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `data-quality` | Updated | §1.2 gains the bounded-memory and explicit-full-scan constraints. §2.2 gains `full_scan`. §4.1 gains the `quality_max_dup_tracking` cap clause and scenario. §4.3 gains the per-column boolean clause and scenario. §5.3 gains the `partial` contract. New §4.13 (explicit full-scan policy, 5 scenarios) and §4.14 (bounded per-row accumulators, 2 scenarios) added. §7's duplicate/`max_sample` open question is marked resolved by #290. |

The canonical `openspec/specs/data-quality/spec.md` was amended in place from the delta's
`## MODIFIED Requirements` and `## ADDED Requirements` blocks. Each new or changed clause carries an
inline `**Evidence:**` line with a `test:` node id; `data-quality` remains a permanent
declared-backlog spec, so this change adds **no** `## Test Mapping` table and **no** registry edit.

## Archive Contents

- `proposal.md` — present
- `design.md` — present (D1–D5, the rejected per-check multi-pass alternative, the measured cap
  arithmetic, and the `quality_value_preview_len` config-surface removal)
- `tasks.md` — present, T1–T9 complete; T10 (commit/push/PR) is parent-owned
- `specs/data-quality/spec.md` (delta) — present

No `explore.md`, `apply-progress.md`, `verify-report.md` or `sync-report.md` siblings were produced;
the four files above are the complete set. The verification evidence is in `tasks.md` §"Gate battery"
and below.

## Source of Truth Updated

- `openspec/specs/data-quality/spec.md` — §4.13/§4.14 and the modified clauses are canonical.
- `openspec/test-mapping-registry.md` — **untouched**; `scripts/check_test_mapping.py` exits 0 and
  reports `data-quality: 1 scenario(s), unmapped`. (`data-quality` keeps its existing bold scenario
  style; the merged clauses carry inline `**Evidence:**` lines, and the checker counts only the
  four-hash `#### Scenario:` grammar — unchanged at 1.)
- `src/sofer/quality.py` — bounded accumulators + tri-state full-scan policy.
- `src/sofer/config.py` — three new `[tool.sofer]` keys + `QUALITY_FULL_SCAN_MODES`;
  `quality_value_preview_len` removed.
- `src/sofer/model.py` — optional `[quality]` policy table and `QualityConfig.full_scan`.
- `pyproject.toml` / `docs/configuration.md` — new keys declared and documented; the dead
  `quality_value_preview_len` line removed.
- `README.md` + `README_ES.md` — the bounded strategy, the new knobs and the `partial` semantics
  (rule 13).

## Config-surface change (declared)

`quality_value_preview_len` (`[tool.sofer]`, issue #189) was removed. Its only reader was the
distinct-value set in `_col_nonempty`, replaced here by a per-column boolean. The removal is
declared in `design.md` §5.4, in the delta's `## Config-surface removal recorded by this change`,
in the archived `tasks.md`, and pinned by
`tests/test_config.py::TestQualityScanBoundsConfig::test_quality_value_preview_len_key_removed`.

## Verification (on base `4ca823e`; parent re-runs on the rebased state)

| Gate | Result |
|------|--------|
| `uv run pytest tests/ -q` | 2113 passed, 8 skipped (base 2087 / 9) |
| `uv run coverage run -m pytest` + `uv run coverage report -m` | TOTAL **94%** (base 94%); `quality.py` **91%** (base 89%); rule-14 modules **100.00%** |
| `uv run ruff check src/ tests/ scripts/` | All checks passed |
| `uv run ruff format --check src/ tests/` | 75 files already formatted |
| `uv run mypy src/ scripts/` | Success: no issues found in 37 source files |
| `uv run pyright` | 0 errors, 1 pre-existing warning (`_toml.py` tomli module source) |
| `uv run python scripts/check_test_mapping.py` | exit 0, `OK: test-mapping contract holds` |

RED before GREEN: the focused selection ran `24 failed, 5 passed` before the fix and `29 passed`
after; memory independence is proven structurally by
`TestAccumulatorCaps::test_accumulator_sizes_do_not_grow_with_dataset_size` (100 vs 3000 rows →
identical accumulator sizes). The cap arithmetic was measured with `tracemalloc`
(143 B/entry → 1 M ≈ 137 MB, under the approved ~256 MB boundary), so the default stays `1_000_000`.

## Rebase note

`origin/dev` has since merged #293, which edits `_distribute_row` / `_check_duplicates` (the
duplicate finding keeps its file and emits pairs round-robin). That is the same region this change
touches; the parent resolves it by keeping #293's pair emission and re-applying #290's insertion cap,
`_capped_append` and `partial` flag. Details in the archived `tasks.md` §"Rebase note".

## Delivery

The worker performed **no** `git add`/`git commit`/`git push` — the Tool-safety policy forbids them
and the parent owns terminal git actions. The change is delivered in the working tree for the parent
to commit and rebase. Issue #290 is **not** yet closed by the worker; `Closes #290` belongs in the
parent's commit/PR body.

Unfinished tasks and unresolved findings: none by the worker; T10 is parent-owned.
