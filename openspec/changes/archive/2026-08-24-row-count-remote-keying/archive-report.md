# Archive Report — row-count-remote-keying

**Change**: row-count-remote-keying
**Branch**: fix/row-count-remote-keying @ commits bc06500, bc89e74, ccd9719, 72c1bea
**Archived to**: `openspec/changes/archive/2026-08-24-row-count-remote-keying/`
**Archive date**: 2026-08-24
**Verdict**: ✅ ARCHIVED — **PASS** (0 blockers, 0 critical findings)

## Verification Source

Engram observation #556 — verify-report for this change (verdict `pass`,
blockers 0, critical 0). Filesystem copy: `verify-report.md` in this folder.

### SDD artifact traceability (Engram observation IDs)

| Artifact | Topic key | Observation ID |
|----------|-----------|----------------|
| exploration | `sdd/row-count-remote-keying/explore` | #548 |
| proposal | `sdd/row-count-remote-keying/proposal` | #549 |
| spec | `sdd/row-count-remote-keying/spec` | #550 |
| design | `sdd/row-count-remote-keying/design` | #551 |
| tasks | `sdd/row-count-remote-keying/tasks` | #553 |
| apply-progress | (saved as "Apply row-count-remote-keying: complete") | #554 |
| verify-report | `sdd/row-count-remote-keying/verify-report` | #556 |
| archive-report | `sdd/row-count-remote-keying/archive-report` | this save |

## Task Completion Gate

`tasks.md`: **17/17 tasks checked** (Phases 1–3). No stale unchecked
implementation tasks; apply-progress (#554) and verify-report (#556)
independently confirm all phases complete. Gate PASSED — spec sync and
archive move proceeded normally. No archive-time reconciliation needed.

## Final Task Status

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Producer re-keying (`setdefault(entry.remote, ...)` at both sites), `_warn_duplicate_remotes`, docstring contracts | ✅ 5/5 |
| 2 | Tests mapping RC-R07/R11/R12 scenarios + gate-review ordering assertion | ✅ 11/11 |
| 3 | Full regression: pytest + ruff check/format + mypy (3.13) | ✅ 1/1 |

Final regression at verification time: **757 passed / 0 failed / 0 skipped**,
`ruff check .` clean, `ruff format --check .` clean, `mypy src/` clean under
Python 3.13. Note: tasks.md's quoted "422-test baseline" was stale (suite was
already ~744 pre-change) — cosmetic only; the gate is "no skips added,
baseline green", which held.

## Spec Sync Summary

Delta applied to the live source of truth
`openspec/specs/repo-compliance/spec.md`:

| Domain | Action | Details |
|--------|--------|---------|
| repo-compliance | Updated | **RC-R07 MODIFIED** — §4.8 rewritten: exact per-file row counts keyed by verbatim `entry.remote` (POSIX) instead of mixed origin basenames; first-declared entry wins via `setdefault`; sole consumer sums values only. Requirement text replaced and scenario set expanded from 2 to 5 scenarios (added: same-stem distinct keys, Parquet+CSV dual-path keying, single-remote unchanged). |
| repo-compliance | Added | **RC-R11 ADDED** as §4.12 — duplicate declared remote emits exactly one `[!]` warning naming the remote; build completes deterministically (first-declared-wins); warning must not abort. 2 scenarios. |
| repo-compliance | Added | **RC-R12 ADDED** as §4.13 — non-schema entries (recursive trees, non-`.csv` remotes, `include_in_schema=false`) contribute no exact counts; when NO file yields an exact count, `num_examples` falls back to `CARD_FALLBACK_ROWS_PER_FILE × len(cfg.files)` read from tool config at call time. 2 scenarios. |

All other requirements in the main spec are preserved untouched. The delta
was applied verbatim — no archive-time corrections were needed.

## Residuals Carried by Design (documented, NOT fixed — intentional)

1. **Partial-counts silent undercount for mixed datasets**: when a dataset
   mixes schema-included files (exact counts) with non-schema files
   (recursive/non-CSV/excluded), `num_examples` sums ONLY the partial exact
   counts — silently undercounting. RC-R12's fallback applies only when NO
   file yields a count. Specced as unchanged behavior (non-goal of this
   change); fixing it would require full-file I/O or directory walks for
   non-schema files. Candidate for a future change if users report it.
2. **Staged-parquet flat-stem lookup bug** (`repo_compliance.py`, staging
   lookup resolves `<remote stem>.parquet` flatly): subdirectory remotes miss
   their staged parquet and fall back to CSV; same-stem remotes share one
   candidate path. Explicitly out of scope of this change (proposal Out-of-
   Scope; design Migration section) — **needs its own follow-up issue** so
   verification confusion around it is tracked separately.

## PR Description Pointers

The PR description should include:

1. **Root cause**: exact row counts were keyed by mixed origin basenames
   (Parquet remote stems vs CSV local filenames); same-basename files across
   subdirectories silently overwrote each other, undercounting
   `num_examples` in the Dataset Card frontmatter (fixes GitHub #57).
2. **Fix**: both producers now key by verbatim `entry.remote` (unique per
   well-formed dataset) using `setdefault` for first-declared-wins;
   duplicate declared remotes emit one deterministic `[!]` warning.
   `ColumnSchema.origin` stays basename-based (display-only, never joined
   against keys).
3. **Behavior note**: `build_schema_report_with_rows()`'s dict keys change
   from basenames to POSIX remote paths — sole production consumer is
   values-only, but external callers reading keys would be affected.
4. Residuals above (partial-counts undercount; staged-parquet lookup bug →
   follow-up issue to be filed from this PR).
5. Verification evidence: 757 passed, ruff clean, mypy clean (Python 3.13);
   verdict `pass`, 9/9 spec scenarios mapped to passing tests (+1
   beyond-spec ordering test).

## Archive Contents

- proposal.md ✅
- exploration.md ✅
- specs/repo-compliance/spec.md ✅ (delta)
- design.md ✅
- tasks.md ✅ (17/17 complete)
- verify-report.md ✅
- archive-report.md ✅ (this file)

## Source of Truth Updated

- `openspec/specs/repo-compliance/spec.md` (§4.8 modified; §4.12, §4.13 added)

## SDD Cycle Complete

The change has been fully planned, implemented, verified, and archived.
Ready for the next change.
