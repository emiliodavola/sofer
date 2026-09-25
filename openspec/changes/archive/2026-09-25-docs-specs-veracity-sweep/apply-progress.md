# Apply Progress: Specs/docs veracity sweep — uploader.py, inventories, project.md (#188, #236, #187, #184)

**Change**: `docs-specs-veracity-sweep`
**Mode**: ODD work-unit commits (Strict TDD disabled; SDD subagent delegation was blocked by the runtime preflight gate, so the orchestrator applied and verified directly)

## Completed Tasks

- [x] 1.1–1.2 parquet-conversion §4/§5 superseded, §4.1/§4.2 retargeted
- [x] 1.3 parquet-conversion §10.3 defers; §11 checklist corrected
- [x] 1.4 repo-compliance §6.3 defers; checklist corrected; cli.py row fixed
- [x] 1.5 codebook CB-R04 names the `publish` staging layout
- [x] 1.6 mcp-server + process-boundary examples de-identified
- [x] 2.1–2.4 AGENTS.md, CONTRIBUTING.md, docs/configuration.md, openspec/project.md corrected
- [x] 3.1–3.4 checker, suite, gates, independent verification, verify-report
- [x] 4.1 Archive the change folder

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `openspec/specs/parquet-conversion/spec.md` | Modified | Superseded banner; owners retargeted; coverage defers; checklist fixed |
| `openspec/specs/repo-compliance/spec.md` | Modified | Coverage defers; owners retargeted; `uploader.upload()` claim removed |
| `openspec/specs/codebook/spec.md` | Modified | CB-R04 names the `publish` staging layout |
| `openspec/specs/mcp-server/spec.md` | Modified | Example → `<hf-user>` |
| `openspec/specs/process-boundary/spec.md` | Modified | Two examples → `<hf-user>` |
| `AGENTS.md` | Modified | Rule 4 example; rule 10 inventory + source-of-truth line |
| `CONTRIBUTING.md` | Modified | Tree + ruff config location |
| `docs/configuration.md` | Modified | Conversion example `raw/` → `build/` |
| `openspec/project.md` | Modified | Coverage, counts, inventory, version claim, layout, gate scopes |
| `openspec/changes/archive/2026-09-25-docs-specs-veracity-sweep/` | New | This change's artifacts |

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Work-unit commits | `bd91eee` specs (#188); `8e51139` spec examples (#180); `4e67352` root docs (#236/#187/#184); `ffa55b5` residual reference fixes |
| Focused test command and result | `uv run pytest tests/test_ci_workflows.py -q` — `39 passed`; `uv run python scripts/check_test_mapping.py` — `OK: test-mapping contract holds` |
| Runtime harness command/scenario and result | N/A — documentation/spec prose; no runtime boundary. Full `uv run pytest tests/ -q` on HEAD (`ffa55b5`) — `1849 passed, 2 skipped, 1 warning in 284.92s` |
| Lint/type gates | `ruff check src/ tests/ scripts/` — All checks passed; `ruff format --check src/ tests/` — 70 files already formatted; `mypy src/ scripts/` — no issues in 35 files; `pyright` — 0 errors, 1 pre-existing `_toml.py` warning |
| Rollback boundary | `git revert ffa55b5 4e67352 8e51139 bd91eee` (or reset the branch to `60cb540`); no source/CI/workflow dependency |

## Deviations from Design

The independent verifier flagged two residual stale `uploader` references outside the literal
`uploader.py` pattern: `repo-compliance/spec.md` §7.3 ("upload command already calls
`uploader.upload()`") and `codebook/spec.md` CB-R04 ("matching uploader's HF staging"). Both
were closed in the follow-up work-unit commit `ffa55b5`; `codebook/spec.md` is a third spec
file beyond #188's two, added as a same-class correction.

## Issues Found

None remaining. The two residual references above were found by the independent verifier and
fixed before archive.

## Remaining Tasks

None.

## Workload / PR Boundary

- Mode: single PR
- Current work unit: canonical-spec retirement + inventories/baselines
- Boundary: 9 docs/spec files (+ archived change artifacts)
- Estimated review budget impact: ~58 authored lines (Low)

## Status

18/18 tasks complete. Ready for archive.
