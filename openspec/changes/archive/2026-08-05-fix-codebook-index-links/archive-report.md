# SDD Archive Report: fix-codebook-index-links

**Date**: 2026-08-05
**Status**: Complete
**Verdict**: PASS WITH WARNINGS
**Mode**: Hybrid (openspec + Engram)

## Summary

Two codebook bugs fixed: (1) root index links pointed to `data/codebooks/` but the
uploader stages under `codebooks/` — fixed one line in `generate_all()` — and
(2) `YOUR_USER`-style placeholder repo_ids passed validation silently — added
placeholder detection in `validate()` and hooked it into `_cmd_codebook()`.

10/10 tasks complete, 475/475 tests passing, 8/8 spec scenarios compliant, ruff
and mypy clean. The only warning is a branch naming deviation (implemented on
`dev` instead of `fix/codebook-index-links`).

## Spec Sync

| Domain | Action | Details |
|--------|--------|---------|
| codebook | MODIFIED | **CB-R04** — Root index link paths changed from `data/codebooks/` to `codebooks/`. Added 2 new scenarios: nested subdirectory preservation and relative-path assertion. |
| repo-compliance | ADDED | **RC-R01** — New section 4.4 "Placeholder Rejection in Validation". Rejects `YOUR_USER`, `YOUR_ORG`, `your-username`, `YOUR_ORGANIZATION` placeholder patterns. `_cmd_codebook()` calls `validate()` before generation. 5 scenarios. |

## Archive Contents

| Artifact | Path | Status |
|----------|------|--------|
| proposal.md | `archive/2026-08-05-fix-codebook-index-links/proposal.md` | Present |
| spec (delta) | `archive/2026-08-05-fix-codebook-index-links/specs/codebook/spec.md` | Present — CB-R04 MODIFIED |
| spec (delta) | `archive/2026-08-05-fix-codebook-index-links/specs/repo-compliance/spec.md` | Present — RC-R01 ADDED |
| design.md | `archive/2026-08-05-fix-codebook-index-links/design.md` | Present |
| tasks.md | `archive/2026-08-05-fix-codebook-index-links/tasks.md` | 10/10 tasks complete |

## Verification Summary

- **Tests**: 475 passed, 0 failed
- **Lint**: ruff clean
- **Type check**: mypy clean
- **Spec compliance**: 8/8 scenarios — CB-R04 (3 scenarios, COMPLIANT), RC-R01 (5 scenarios, COMPLIANT)
- **TDD compliance**: 6/6 checks — 4 RED tasks confirmed, GREEN confirmed, triangulation adequate, safety net verified
- **Assertion quality**: All assertions verify real behavior — no tautologies or smoke-test-only assertions

### Warnings (Non-Blocking)

- **Branch mismatch**: Implementation was on `dev` instead of `fix/codebook-index-links`. Code is correct, but SDD branch naming convention was not followed.

## Stale Checkbox Reconciliation

The persisted `tasks.md` had all 10 checkboxes unchecked at archive time. The verify-report (`sdd/fix-codebook-index-links/verify-report`, observation #483) proves every task was completed: 475/475 tests passing, ruff clean, mypy clean, 8/8 spec scenarios compliant. All checkboxes have been reconciled to `[x]` backed by this proof.

## Key Implementation Details

- **Link fix**: `codebook.py:496` — `out_path.relative_to(data_dir).as_posix()` (was `relative_to(base_dir)`)
- **Placeholder set**: `frozenset({"your_user", "your_org", "your-username", "your_organization"})` — case-insensitive check in `validate()`
- **Validation gate**: `cli.py:125` — `_cmd_codebook()` calls `cfg.validate()` before `generate_all_codebooks()`, exits 1 on errors
- **Test impact**: 1 assertion fix in `test_codebook.py`, ~7 new test methods across `test_model.py` and `test_cli.py`

## Engram Observation Trace

| Artifact | Topic Key | Observation ID |
|----------|-----------|----------------|
| proposal | `sdd/fix-codebook-index-links/proposal` | (Engram) |
| spec | `sdd/fix-codebook-index-links/spec` | (Engram) |
| design | `sdd/fix-codebook-index-links/design` | (Engram) |
| tasks | `sdd/fix-codebook-index-links/tasks` | (Engram) |
| verify-report | `sdd/fix-codebook-index-links/verify-report` | #483 |
| archive-report | `sdd/fix-codebook-index-links/archive-report` | (this artifact) |

## Source of Truth Updated

The following specs now reflect the new behavior:

- `openspec/specs/codebook/spec.md` — CB-R04 updated with `codebooks/` prefix and 2 new scenarios
- `openspec/specs/repo-compliance/spec.md` — RC-R01 added as section 4.4 with 5 scenarios

## SDD Cycle Complete

The change has been fully planned, implemented, verified, and archived. Ready for the next change.
