# SDD Archive Report: prepare-publish-split

**Date**: 2026-08-06
**Status**: Complete
**Verdict**: PASS (blocker resolved — see note below)
**Mode**: Hybrid (openspec + Engram)
**Branch**: `feat/prepare-publish-split-4-remove-upload` (current, HEAD d2648d3)

## Summary

Split the monolithic `upload` command into two top-level commands: `prepare`
(local, offline artifact generation — CSV→Parquet conversion, Dataset Card,
LICENSE, codebooks, checks) and `publish` (delivery — single `upload_folder`
push to the HF Hub or local package write). `uploader.py` (1,075 lines) was
deleted; `upload` was removed from the CLI (exit 2); the `cache/` directory
renamed from `data/`, `build_dir` added to `[dataset]`, and recursive staging
fixed (RC-R04). Delivered as a 4-PR feature-branch chain.

**Verdict note — PUB-05 blocker found in first verify and fixed**: The first
verification run returned **FAIL** — 1 blocker (PUB-05 "Protected file needs
--force" unimplemented; 42/44 scenarios, 16/17 requirements). The gap was
two-layer: `_check_overwrite_protection` never received the data-file list AND
`_copy_package` ignored `protected` for data remotes. Fix in d2648d3
(`planned_files` parameter + staging skip for protected data remotes, 8 new
tests). Re-verify: **PASS** — 562/562 tests, 44/44 scenarios, 17/17
requirements. Only pre-existing non-blocking warnings remain (Windows cp1252
UnicodeEncodeError on config-error path; local-target keep_csv no-op by
construction).

## Spec Sync

| Domain | Action | Details |
|--------|--------|---------|
| prepare | Created | **NEW domain** — `openspec/specs/prepare/spec.md` created from delta verbatim. PRP-01..PRP-08 (8 requirements, 19 scenarios): local-only generation, conversion, card/LICENSE, codebooks, checks, output, verify, force. |
| publish | Created | **NEW domain** — `openspec/specs/publish/spec.md` created from delta verbatim. PUB-01..PUB-05, PUB-07 (6 requirements, 15 scenarios): upload_folder delivery, local target, auto-prepare, dry-run, overwrite protection, keep-csv. |
| repo-compliance | Updated | **RC-R04 ADDED** as § 4.5 (recursive staging — 3 scenarios); **REMOVED** § 4.1 upload orchestration, § 4.2 RC-C01 codebook batch staging, § 4.3 RC-C02 auto-generated overwrite bypass (all with Reason/Migration notes — upload pipeline deleted). RC-R01 (§ 4.4), § 3.3.6 Parquet scenarios (precondition now references `prepare`), § 5–7 preserved. |
| cli | Created | **NEW domain** — `openspec/specs/cli/spec.md` created from delta verbatim. CLI-R01, CLI-R02 (2 requirements, 7 scenarios): upload removed, prepare/publish top-level, help accuracy. |

## Archive Contents

| Artifact | Path | Status |
|----------|------|--------|
| proposal.md | `archive/2026-08-06-prepare-publish-split/proposal.md` | Present |
| exploration.md | `archive/2026-08-06-prepare-publish-split/exploration.md` | Present |
| spec (deltas) | `archive/2026-08-06-prepare-publish-split/specs/{prepare,publish,repo-compliance,cli}/spec.md` | Present |
| design.md | `archive/2026-08-06-prepare-publish-split/design.md` | Present |
| tasks.md | `archive/2026-08-06-prepare-publish-split/tasks.md` | 26/26 tasks complete (reconciled) |

## Stale Checkbox Reconciliation

The persisted `tasks.md` had all 26 checkboxes unchecked at archive time. The
apply-progress observation (`sdd/prepare-publish-split/apply-progress`, #499 —
"PR 1-4 COMPLETE + PUB-05 verify-blocker FIXED", with per-task TDD Cycle
Evidence tables) and the re-verify report (`sdd/prepare-publish-split/
verify-report`, #503 — 562/562 tests, 44/44 scenarios, 17/17 requirements,
ruff/mypy/format clean) prove every task was completed. All checkboxes have
been reconciled to `[x]` backed by this proof (same precedent as
`2026-08-05-feat-schema-warnings-summary`).

## 4-PR Chain Summary

Delivered as a feature-branch chain (only the tracker `feat/prepare-publish-split`
merges to main; each child PR targets the previous PR's branch):

| PR | Branch | Scope | Tests |
|----|--------|-------|-------|
| 1 | `feat/prepare-publish-split-1-config-mirror` | Config foundation: `OUTPUT_DIR` `data/`→`cache/`, `build_dir` in `[dataset]`, codebook Option B, `_mirror.py` — zero behavior change | 511 |
| 2 | `feat/prepare-publish-split-2-prepare` | `prepare.py` + `prepare` subparser + `test_prepare.py`; helpers imported from `uploader.py` (not moved yet); `upload` intact | 536 |
| 3 | `feat/prepare-publish-split-3-publish` | `publish.py` + `publish` subparser + `test_publish.py`; `upload` still alive | 554 |
| 4 | `feat/prepare-publish-split-4-remove-upload` | Move helpers → `prepare.py`, **delete `uploader.py`**, delete `upload` subparser, retarget ~50 call sites, RC-R04 tests, README/`__init__`, full verify | 554 → 562 |

Every PR stayed green independently (intermediate states ran `upload` +
`prepare` + `publish` together). Rollback = revert tracker merge.

## Verification Summary

- **Verdict**: PASS (first verify FAIL on PUB-05 — fixed in d2648d3, re-verified)
- **Tests**: 562 passed, 0 failed (554 baseline + 8 new PUB-05 tests), exit 0
- **Spec scenarios**: 44/44 compliant (prepare 19/19, publish 15/15, repo-compliance 3/3, cli 7/7)
- **Requirements**: 17/17
- **Lint**: ruff clean | **Type check**: mypy clean (18 src files) | **Format**: ruff format clean (31 files)
- **TDD compliance**: RED confirmed 3/3, GREEN confirmed, triangulation (8 distinct PUB-05 cases), safety net 554/554
- **CLI smoke**: `sofer --help` → `{validate,prepare,publish,codebook,init,scan}`; `sofer upload` → exit 2; both `--help` outputs list exact flags
- **CRITICAL**: none | **WARNING**: 2 pre-existing, non-blocking (documented in verify-report #503)

## Engram Observation Trace

| Artifact | Topic Key | Observation ID |
|----------|-----------|----------------|
| proposal | `sdd/prepare-publish-split/proposal` | #495 |
| spec | `sdd/prepare-publish-split/spec` | #496 |
| design | `sdd/prepare-publish-split/design` | #497 |
| tasks | `sdd/prepare-publish-split/tasks` | #498 |
| apply-progress | `sdd/prepare-publish-split/apply-progress` | #499 |
| verify-report | `sdd/prepare-publish-split/verify-report` | #503 |
| archive-report | `sdd/prepare-publish-split/archive-report` | #504 |

## Source of Truth Updated

The following specs now reflect the new behavior:

- `openspec/specs/prepare/spec.md` — NEW domain (8 requirements, 19 scenarios)
- `openspec/specs/publish/spec.md` — NEW domain (6 requirements, 15 scenarios)
- `openspec/specs/cli/spec.md` — NEW domain (2 requirements, 7 scenarios)
- `openspec/specs/repo-compliance/spec.md` — RC-R04 added (§ 4.5); upload orchestration, RC-C01, RC-C02 removed

## SDD Cycle Complete

The change has been fully planned, implemented, verified, and archived.
Ready for the next change.
