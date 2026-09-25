# Apply Progress: Align documented gate-command scope and sync CITATION.cff on `dev` (#212, #191)

**Change**: `docs-gate-scope-and-citation`
**Mode**: Standard (Strict TDD disabled per `openspec/config.yaml`)

## Completed Tasks

- [x] 1.1 `AGENTS.md` rule 5 mypy scope → `src/ scripts/`
- [x] 1.2 `CONTRIBUTING.md` Development commands mypy scope → `src/ scripts/`
- [x] 1.3 `CONTRIBUTING.md` Development commands ruff check scope → `src/ tests/ scripts/`
- [x] 1.4 PR template Verification block scopes widened
- [x] 1.5 PR template Checklist scopes widened
- [x] 2.1 `AGENTS.md` rule 12: CFF sync moved to step 1 on `dev`; the merge carries it
- [x] 2.2 `AGENTS.md` branch-flow bullet records the `dev`-commit bump
- [x] 2.3 `CITATION.cff` synced to `0.3.12` / `2026-09-13` via `scripts/update_citation.py`
- [x] 3.1 `scripts/update_citation.py --check --version 0.3.12` exits 0
- [x] 3.2 Full suite and lint/type gates green
- [x] 3.3 No residual narrower gate command in the three docs
- [x] 3.4 Verify-phase evidence recorded in `verify-report.md`
- [x] 4.1 Archive the change folder (`diff -r` readback)

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `AGENTS.md` | Modified | Rule 5 mypy scope; rule 12 CFF step order; branch-flow sentence |
| `CONTRIBUTING.md` | Modified | Development commands: mypy + ruff check scopes |
| `.github/PULL_REQUEST_TEMPLATE.md` | Modified | Verification block + Checklist scopes |
| `CITATION.cff` | Modified | `version: 0.3.12`, `date-released: 2026-09-13` |

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and result | `uv run pytest tests/test_ci_workflows.py -q` — 36 passed |
| Runtime harness command/scenario and result | `uv run python scripts/update_citation.py --check --version 0.3.12` — exit 0; full `uv run pytest tests/ -q` — 1847 passed, 1 skipped |
| Rollback boundary | revert the four files; no code, workflow, or spec has a dependency on the change |

## Deviations from Design

None. The transform of `date-released` used the actual `v0.3.12` release date (`2026-09-13`) rather
than today's date, so `dev`'s CFF is byte-identical to `main`'s for the two synced fields.

## Issues Found

None.

## Remaining Tasks

None.

## Workload / PR Boundary

- Mode: single PR
- Current work unit: documented gate scope + CFF sync
- Boundary: `AGENTS.md` + `CONTRIBUTING.md` + PR template + `CITATION.cff`
- Estimated review budget impact: ~25 authored lines (Low)

## Status

13/13 tasks complete. Ready for archive.
