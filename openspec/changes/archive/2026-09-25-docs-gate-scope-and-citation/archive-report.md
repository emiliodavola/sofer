# Archive Report: Align documented gate-command scope and sync CITATION.cff on `dev` (#212, #191)

**Change**: `docs-gate-scope-and-citation`
**Archived to**: `openspec/changes/archive/2026-09-25-docs-gate-scope-and-citation/`
**Branch**: `docs/gate-scope-and-citation` (base `dev`)

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| — | None | No spec-level behavior changed. CI-06's asserted facts and CI-07's rule-12 latent-issue note are untouched; no delta spec was produced. |

The canonical `openspec/specs/` tree is unchanged by this change; CI-09's checks over
`CONTRIBUTING.md`'s type-checking section and the PR-template Checklist remain satisfied.

## Archive Contents

- `explore.md` — present
- `proposal.md` — present
- `design.md` — present
- `tasks.md` — present, 13/13 tasks complete
- `apply-progress.md` — present
- `verify-report.md` — present
- `specs/` — absent by design (no spec delta)

The change folder was moved with a mechanical `mv` verified by an empty `diff -r` against a
pre-move recursive snapshot.

## Source of Truth Updated

- `AGENTS.md` — rule 5 documents the enforced mypy scope; rule 12 now sets the `CITATION.cff` bump
  on `dev` before the merge, and the branch-flow rule records it.
- `CONTRIBUTING.md`, `.github/PULL_REQUEST_TEMPLATE.md` — documented gate commands now name the
  CI-enforced scope.
- `CITATION.cff` — synced to `0.3.12` / `2026-09-13`.

## SDD Cycle Complete

Implementation: complete (four files). Verification: independent read-only verifier PASS on all six
claims; full suite `1847 passed, 1 skipped`; CFF check exit 0; ruff/mypy/pyright clean.
Unfinished tasks and unresolved findings: none observed. Out of scope (tracked for Ola 2): the
residual narrow-scope strings in `openspec/specs/process-boundary/spec.md` and the
`openspec/config.yaml` / `openspec/project.md` staleness (#184, #236).
