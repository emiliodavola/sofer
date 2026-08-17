# SDD Archive Report: sofer-v2-metadata-core

**Date**: 2026-08-06
**Status**: Complete
**Verdict**: PASS WITH WARNINGS (the single warning was closed after verify — see note)
**Mode**: Hybrid (openspec + Engram)
**Branch**: `feat/sofer-v2-metadata-core-6-render` (current, HEAD 42bb4fa)

## Summary

Repivot sofer from HF-uploader to a Dataset Documentation & Quality CLI — Fase A
of the metadata core. Additive vertical slice: a new `metadata.yaml` schema
becomes the dataset-documentation source of truth; a read-only `profile` command
generates it from a dataset file; a `render` command produces a
status-annotated `README.md` from it. Inference is never presented as fact:
every column carries `confirmed` / `inferred` / `unknown` plus a deterministic
confidence (`match_rate × prior`, rounded to `confidence_round_digits`). Five
new modules (`_patterns.py`, `semantic.py`, `pii.py`, `metadata.py`,
`profile.py`, `render.py`) plus additive edits to `model.py`, `config.py`,
`cli.py`, and `pyproject.toml`. Delivered as a 6-PR feature-branch chain.

**Verdict note — warning closed post-verify**: The verification report
(`sdd/sofer-v2-metadata-core/verify-report`, #515) returned **PASS WITH
WARNINGS** with one WARNING — CLI-R04 "profile help accurate" had no dedicated
pytest (verified via `sofer profile --help` smoke only) — and three
SUGGESTIONs. The warning was closed by commit `42bb4fa
test(profile): add profile --help accuracy assertion (CLI-R04)`, which added
`test_profile_help_accurate` to `tests/test_profile.py`. Final count: **688
tests** (687 + 1). No CRITICAL issues ever existed.

## Spec Sync

| Domain | Action | Details |
|--------|--------|---------|
| semantic-type-inference | Created | **NEW domain** — `openspec/specs/semantic-type-inference/spec.md` created from delta verbatim. STI-01..05 (5 requirements, 10 scenarios): detector contract, Detection shape, confidence = match_rate × prior, config-driven status thresholds, EmailDetector. |
| pii-detection | Created | **NEW domain** — `openspec/specs/pii-detection/spec.md` created from delta verbatim. PII-01..04 (4 requirements, 6 scenarios): detector contract, finding shape, note always `possible_pii`, EmailPiiDetector. |
| metadata | Created | **NEW domain** — `openspec/specs/metadata/spec.md` created from delta verbatim. MTA-01..06 (6 requirements, 6 scenarios): schema skeleton, `METADATA_VERSION`, deterministic serialization, InferenceStatus machine, read-only, per-column contract. |
| profile | Created | **NEW domain** — `openspec/specs/profile/spec.md` created from delta verbatim. PRF-01..04 (4 requirements, 7 scenarios): command surface, orchestration, read-only, unsupported-format error. |
| render | Created | **NEW domain** — `openspec/specs/render/spec.md` created from delta verbatim. RND-01..03 (3 requirements, 5 scenarios): command surface, README from metadata, distinct inference states. |
| cli | Updated | **CLI-R03** and **CLI-R04** ADDED to existing `openspec/specs/cli/spec.md` (2 requirements, 5 scenarios): profile/render top-level, help accuracy. CLI-R01/R02 preserved untouched. |

## Archive Contents

| Artifact | Path | Status |
|----------|------|--------|
| proposal.md | `archive/2026-08-06-sofer-v2-metadata-core/proposal.md` | Present |
| exploration.md | `archive/2026-08-06-sofer-v2-metadata-core/exploration.md` | Present |
| spec (deltas) | `archive/2026-08-06-sofer-v2-metadata-core/specs/{semantic-type-inference,pii-detection,metadata,profile,render,cli}/spec.md` | Present |
| design.md | `archive/2026-08-06-sofer-v2-metadata-core/design.md` | Present |
| tasks.md | `archive/2026-08-06-sofer-v2-metadata-core/tasks.md` | 27/27 tasks complete (reconciled) |

## Stale Checkbox Reconciliation

The persisted `tasks.md` had all 27 implementation checkboxes unchecked at
archive time (planning artifacts only, never re-saved after apply). The
apply-progress observation (`sdd/sofer-v2-metadata-core/apply-progress`, #513 —
WU1–WU5 complete with per-task TDD Cycle Evidence, cumulative 663 tests) and the
verify-report (`sdd/sofer-v2-metadata-core/verify-report`, #515 — 27/27 tasks
across 6 phases, 687/687 tests, 39/39 scenarios, ruff/mypy/format clean) prove
every task was completed, including WU6 (render), which the apply-progress
artifact predates. All checkboxes have been reconciled to `[x]` backed by this
proof (same precedent as `2026-08-06-prepare-publish-split`).

## 6-WU Chain Summary

Delivered as a feature-branch chain (only the tracker `feat/sofer-v2-metadata-core`
merges to main; each child PR targets the previous PR's branch):

| PR | Branch | Scope | Tests |
|----|--------|-------|-------|
| 1 | `feat/sofer-v2-metadata-core-1-foundation` | `InferenceStatus` enum (model.py), config keys + validation (config.py), `EMAIL_PATTERN` (_patterns.py), pyproject mirror | 562 → 584 |
| 2 | `feat/sofer-v2-metadata-core-2-semantic` | `semantic.py` (`Detection`, `SemanticDetector`, `EmailDetector`, `infer_semantic_types`, `infer_status`) + `test_semantic.py` | 609 |
| 3 | `feat/sofer-v2-metadata-core-3-pii` | `pii.py` (`PiiDetection`, `PiiDetector`, `EmailPiiDetector`, `infer_pii_types`) + `test_pii.py` | 630 |
| 4 | `feat/sofer-v2-metadata-core-4-metadata` | `metadata.py` (`METADATA_VERSION`, schema dataclasses, `serialize`/`load`, `missing_fields`) + `test_metadata.py` | 648 |
| 5 | `feat/sofer-v2-metadata-core-5-profile` | `profile.py` orchestrator + `_cmd_profile` + CLI subparser + `test_profile.py` | 663 |
| 6 | `feat/sofer-v2-metadata-core-6-render` | `render.py` + `_cmd_render` + render subparser + `test_render.py` (24 tests) + README | 687 → 688 |

Every PR stayed green independently. Rollback = revert tracker merge (additive
only; no data migration; 562 baseline tests untouched).

## Verification Summary

- **Verdict**: PASS WITH WARNINGS (warning closed by 42bb4fa — profile help test added)
- **Tests**: 688 passed, 0 failed (687 at verify + 1 profile-help assertion), exit 0
- **Spec scenarios**: 39/39 compliant (semantic-type-inference 10, pii-detection 6, metadata 6, profile 7, render 5, cli 5) — 38 via pytest + 1 originally via CLI smoke, now fully covered by pytest after the warning closure
- **Requirements**: 24/24 (STI 5, PII 4, MTA 6, PRF 4, RND 3, CLI-R03/R04 2)
- **Lint**: ruff clean | **Type check**: mypy clean (24 source files) | **Format**: ruff format clean (44 files)
- **TDD compliance**: Strict TDD, RED→GREEN per phase, confidence `round(0.8×0.9, 4) == 0.72` asserted via `pytest.approx`
- **CLI smoke**: `sofer --help` → `{validate,prepare,publish,codebook,profile,render,init,scan}`; `profile --help` and `render --help` accurate
- **Read-only invariant**: profile/render never mutate source; `test_source_bytes_unchanged` asserts byte-identity
- **CRITICAL**: none | **WARNING**: 1 (closed) | **SUGGESTION**: 3 (non-blocking)

## Engram Observation Trace

| Artifact | Topic Key | Observation ID |
|----------|-----------|----------------|
| proposal | `sdd/sofer-v2-metadata-core/proposal` | #508 |
| spec | `sdd/sofer-v2-metadata-core/spec` | #509 |
| design | `sdd/sofer-v2-metadata-core/design` | #510 |
| design-review-fixes | `sdd/sofer-v2-metadata-core/design-review-fixes` | #511 |
| tasks | `sdd/sofer-v2-metadata-core/tasks` | #512 |
| apply-progress | `sdd/sofer-v2-metadata-core/apply-progress` | #513 |
| verify-report | `sdd/sofer-v2-metadata-core/verify-report` | #515 |
| archive-report | `sdd/sofer-v2-metadata-core/archive-report` | (this report) |

## Source of Truth Updated

The following specs now reflect the new behavior:

- `openspec/specs/semantic-type-inference/spec.md` — NEW domain (5 requirements, 10 scenarios)
- `openspec/specs/pii-detection/spec.md` — NEW domain (4 requirements, 6 scenarios)
- `openspec/specs/metadata/spec.md` — NEW domain (6 requirements, 6 scenarios)
- `openspec/specs/profile/spec.md` — NEW domain (4 requirements, 7 scenarios)
- `openspec/specs/render/spec.md` — NEW domain (3 requirements, 5 scenarios)
- `openspec/specs/cli/spec.md` — CLI-R03/R04 added (2 requirements, 5 scenarios)

## SDD Cycle Complete

The change has been fully planned, implemented, verified, and archived.
Ready for the next change.
