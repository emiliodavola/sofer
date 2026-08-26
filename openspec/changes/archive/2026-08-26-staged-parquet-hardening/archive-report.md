# Archive Report — staged-parquet-hardening

**Change**: staged-parquet-hardening
**Branch**: fix/staged-parquet-hardening @ e2dc948 (commits 1ff981c, 7816b2b, a137eb7, e2dc948)
**Archived to**: `openspec/changes/archive/2026-08-26-staged-parquet-hardening/`
**Archive date**: 2026-08-26
**Verdict**: ✅ ARCHIVED — **PASS** (0 blockers, 0 critical findings)

## Verification Source

Engram verify-report for this change (topic key
`sdd/staged-parquet-hardening/verify-report`, project sofer) — verdict **PASS**,
no blockers, no critical findings.

### SDD artifact traceability (Engram observation IDs)

| Artifact | Topic key | Observation ID |
|----------|-----------|----------------|
| proposal | `sdd/staged-parquet-hardening/proposal` | recorded in verify-report |
| spec | `sdd/staged-parquet-hardening/spec` | recorded in verify-report |
| design | `sdd/staged-parquet-hardening/design` | recorded in verify-report |
| tasks | `sdd/staged-parquet-hardening/tasks` | recorded in verify-report |
| verify-report | `sdd/staged-parquet-hardening/verify-report` | recorded in verify-report |
| archive-report | `sdd/staged-parquet-hardening/archive-report` | this save |

## Task Completion Gate

`tasks.md`: **11/11 tasks checked** (Phases 1–3). No stale unchecked
implementation tasks; apply-progress and verify-report independently confirm
all phases complete. Gate PASSED — spec sync and archive move proceeded
normally.

## Final Task Status

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | RC-R16 case-fold collision refusal (`_mirror.py`, `model.py`, 3 test files) | ✅ 7/7 |
| 2 | RC-R17 unreadable-staged-Parquet warning (`repo_compliance.py`, tests) | ✅ 7/7 |
| 3 | Documentation & handoff | ✅ 2/2 |

## Spec Sync Summary

Delta applied to the live source of truth
`openspec/specs/repo-compliance/spec.md`:

| Domain | Action | Details |
|--------|--------|---------|
| repo-compliance | Added | **RC-R16 ADDED** as §4.17 — case-fold collision on staged-Parquet remotes is refused, a deterministic hard error during `validate()` before any staging write. Reconciles the binding decisions verbatim: scan eligibility includes `upload_as_csv` and `include_in_schema=false` `.csv` remotes (physically staged via `copy_to_mirror`); equivalence is `parquet_remote_for(entry.remote).lower()` with `str.lower()` (NOT `casefold()` — `"ß"` vs `"ss"` NOT equal). 5 scenarios. |
| repo-compliance | Added | **RC-R17 ADDED** as §4.18 — unreadable staged Parquet emits exactly one `[!]` warning naming the key and failure class (`corrupt/parse` / `io/permission` / `other`), then falls back to CSV without raising; warn-once per key per run; mutually exclusive with RC-R14. 6 scenarios. |

All other requirements in the main spec are preserved untouched. The delta was
applied verbatim with the reconciled wording. Each new section carries a
provenance note (`> Added by change staged-parquet-hardening (archived
2026-08-26).`) matching the repo's established archive convention.

## Archive-time tidies (non-blocking, from verify)

- design.md D2 "Binding decisions override spec S4 ... bullets" and Open
  Questions (a)/(b) reference pre-reconciliation wording. Per instructions,
  these were **left as-is** to keep the change folder historically accurate;
  the LIVE spec (`openspec/specs/repo-compliance/spec.md` §4.17) is the
  source of truth and carries the reconciled wording.

## Archive Contents

- proposal.md ✅
- explore.md ✅
- spec.md ✅ (delta — repo-compliance, 2 ADDED, 11 scenarios)
- design.md ✅
- tasks.md ✅ (11/11 complete)
- archive-report.md ✅ (this file)

## Source of Truth Updated

- `openspec/specs/repo-compliance/spec.md` (§4.17 RC-R16 added; §4.18 RC-R17 added)

## SDD Cycle Complete

The change has been fully planned, implemented, verified, and archived.
Ready for the next change.
