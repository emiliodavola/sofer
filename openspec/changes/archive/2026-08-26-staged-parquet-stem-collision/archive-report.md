# Archive Report — staged-parquet-stem-collision

**Change**: staged-parquet-stem-collision
**Branch**: fix/staged-parquet-stem-collision @ ac45f86 (commits ab3bb2b, 1bcd6d0, 6f072f3, e5debbd, ac45f86)
**Archived to**: `openspec/changes/archive/2026-08-26-staged-parquet-stem-collision/`
**Archive date**: 2026-08-26
**Verdict**: ✅ ARCHIVED — **PASS WITH WARNINGS** (single warning reconciled before archive; 0 blockers, 0 critical findings)

## Verification Source

Engram observation #569 — verify-report for this change (verdict
`pass_with_warnings`, blockers 0, critical 0). The single WARNING (stale
unchecked Phase 3 task boxes in `tasks.md`) was reconciled by commit `ac45f86`
before this archive — all 18 tasks are now `[x]`.

### SDD artifact traceability (Engram observation IDs)

| Artifact | Topic key | Observation ID |
|----------|-----------|----------------|
| exploration | `sdd/staged-parquet-stem-collision/explore` | #560 |
| proposal | `sdd/staged-parquet-stem-collision/proposal` | #561 |
| spec | `sdd/staged-parquet-stem-collision/spec` | #562 |
| design | `sdd/staged-parquet-stem-collision/design` | #563 |
| gate-review | `Gate review staged-parquet-stem-collision design` | #565 |
| tasks | `sdd/staged-parquet-stem-collision/tasks` | #566 |
| apply-progress | `Apply staged-parquet-stem-collision` | #567 |
| verify-report | `sdd/staged-parquet-stem-collision/verify-report` | #569 |
| archive-report | `sdd/staged-parquet-stem-collision/archive-report` | this save |

## Task Completion Gate

`tasks.md`: **18/18 tasks checked** (Phases 1–4). No stale unchecked
implementation tasks; apply-progress (#567) and verify-report (#569)
independently confirm all phases complete. The verify-report WARNING was the
only open item — Phase 3 checkboxes 3.1–3.4 were unchecked despite
runtime-proven completion — and it was reconciled in commit `ac45f86` before
archive. Gate PASSED — spec sync and archive move proceeded normally.

## Final Task Status

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Helper extraction `parquet_remote_for()` + 7-site adoption + unit tests | ✅ 6/6 |
| 2 | Consumer flip — lookup, origins, warn-once | ✅ 5/5 |
| 3 | Scenario tests S1–S10 (spec ↔ test map) | ✅ 4/4 |
| 4 | Reconciliation, gates, follow-up advisories | ✅ 4/4 |

Final regression at verification time: **771 passed** in 4.22s, `ruff check`
clean, `ruff format --check` clean (45 files), `mypy src/` clean (24 source
files) under Python 3.13. Scenario coverage 10/10 at runtime (S1–S10 mapped
to `test_repo_compliance.py`, `test_prepare.py`, `test_mirror.py`).

## Spec Sync Summary

Delta applied to the live source of truth
`openspec/specs/repo-compliance/spec.md`:

| Domain | Action | Details |
|--------|--------|---------|
| repo-compliance | Modified | **RC-R05 MODIFIED** (§4.6) — `ColumnSchema.origin` now holds the source file's **remote-relative POSIX path** (`.parquet` key on the Parquet path, `entry.remote` on the CSV path) instead of the basename. Full block replaced; scenario set expanded from 2 to 3 (added: nested Parquet origins distinguish same-stem files). Provenance note records `staged-parquet-stem-collision` modification. |
| repo-compliance | Modified | **RC-R07 supersession clause reconciled** (§4.8) — the stale clause "`ColumnSchema.origin` remains basename-based display provenance" was corrected to "display provenance only — holding the remote-relative POSIX path per RC-R05", and the provenance note now records the `staged-parquet-stem-collision` modification. This is the RC-R05 "supersedes RC-R07's clause calling origin 'basename-based'" cross-reference handled per the spec's `(Previously: …)` convention. |
| repo-compliance | Added | **RC-R13 ADDED** as §4.14 — staged-Parquet resolution keys by remote-relative POSIX path via `parquet_remote_for(entry.remote)`; lookup MUST NOT use a bare stem; writer and reader share one definition. 3 scenarios. |
| repo-compliance | Added | **RC-R14 ADDED** as §4.15 — missing staged Parquet emits exactly one deterministic `[!]` warning naming the `.parquet` key, then CSV fallback (no raise). **"Eligible entry" definition pinned verbatim** from tasks.md archive-note advisory 3 (CSV remote + not `recursive` + not `upload_as_csv` + `include_in_schema` respected). 2 scenarios. |
| repo-compliance | Added | **RC-R15 ADDED** as §4.16 — backslash normalization on both handshake sides, idempotent. 2 scenarios. |

All other requirements in the main spec are preserved untouched. The delta was
applied verbatim; the only adaptation was replacing the delta's positional
"below" cross-reference in RC-R13's `(Previously: …)` note with a section
reference (`§ 4.6`), because in the merged spec RC-R05 precedes RC-R13.

## Residuals Carried (documented, NOT fixed — intentional)

1. **Case-insensitive filesystem collision** (tasks.md advisory 4): remotes
   differing only by case (`A.csv` vs `a.csv`) derive distinct keys from
   `parquet_remote_for` (case-preserving) but resolve to the SAME file on
   case-insensitive filesystems. Recorded as a follow-up issue after #60
   ships — do NOT implement in this change.
2. **Corrupt-but-present Parquet stays silent-fallback** (design Open
   Questions): RC-R14 scopes the `[!]` warning to absence only; a
   present-but-corrupt Parquet still falls back to CSV silently. Deliberate
   non-goal.

## PR Description Pointers

The PR description should include:

1. **Root cause**: the schema-report consumer looked up staged Parquets as a
   flat `{stem}.parquet` under `staging_dir`, silently missing nested remotes'
   Parquets and cross-contaminating same-stem root/nested entries (fixes
   GitHub #60's remaining defect).
2. **Fix**: extracted `_mirror.parquet_remote_for()` (single definition
   adopted at all 7 derivation sites) and flipped the lookup to the
   remote-relative POSIX key; `origin` is now the remote-relative path; a
   deterministic `[!]` warning fires once per missing key with CSV fallback.
3. **Behavior note**: `ColumnSchema.origin` changes from basename to
   remote-relative POSIX path — any external consumer reading `origin` sees
   the new value.
4. Residual above (case-insensitive collision → follow-up issue).
5. Verification evidence: 771 passed, ruff clean, mypy clean (Python 3.13);
   verdict `pass_with_warnings` (single stale-checkbox warning, reconciled).

## Archive Contents

- proposal.md ✅
- explore.md ✅
- spec.md ✅ (delta — repo-compliance, 3 ADDED + 1 MODIFIED, 10 scenarios)
- design.md ✅
- tasks.md ✅ (18/18 complete)
- archive-report.md ✅ (this file)

## Source of Truth Updated

- `openspec/specs/repo-compliance/spec.md` (§4.6 modified; §4.8 clause
  reconciled; §4.14, §4.15, §4.16 added)

## SDD Cycle Complete

The change has been fully planned, implemented, verified, and archived.
Ready for the next change.
