# Tasks: Specs/docs veracity sweep — uploader.py, inventories, project.md (#188, #236, #187, #184)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~58 authored (specs ~35, root docs ~23); SDD artifacts excluded |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | single PR |
| Delivery strategy | single-pr |
| Chain strategy | size-exception |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Canonical specs name the current owners | PR 2 | `uv run pytest tests/test_ci_workflows.py -q` | `uv run python scripts/check_test_mapping.py` | revert the spec commits |
| 2 | Inventories + project.md match the tree | PR 2 | `uv run pytest tests/ -q` | N/A (docs) | revert the root-doc commit |

## Phase 1: Canonical specs (#188, #180 spec scope)

- [x] 1.1 parquet-conversion §4 heading + Superseded banner; §4.1/§4.2 retargeted.
- [x] 1.2 parquet-conversion §5 superseded (subcommand only).
- [x] 1.3 parquet-conversion §10.3 defers to `coverage`; §11 checklist rows corrected.
- [x] 1.4 repo-compliance §6.3 defers to `coverage`; checklist rows corrected; cli.py row fixed.
- [x] 1.5 codebook CB-R04 names the `publish` staging layout.
- [x] 1.6 mcp-server + process-boundary examples → `<hf-user>`.

## Phase 2: Inventories and baselines (#236, #187, #184)

- [x] 2.1 AGENTS.md rule 4 example names `prepare.py`; rule 10 lists newer modules + source-of-truth line.
- [x] 2.2 CONTRIBUTING.md tree adds `_toml.py`/`execution_context.py`/`manifest.py`/`workflow.py`; ruff config location.
- [x] 2.3 docs/configuration.md conversion example uses `raw/` → `build/`.
- [x] 2.4 project.md: coverage installed; counts dropped; inventory fixed; version claim fixed; `data/` → `raw/`; gate scopes widened.

## Phase 3: Verification

- [x] 3.1 `scripts/check_test_mapping.py` OK.
- [x] 3.2 Full suite green; ruff/mypy/pyright clean.
- [x] 3.3 Independent read-only verification PASS; residual references flagged and closed.
- [x] 3.4 Record verify-phase evidence in `verify-report.md`.

## Phase 4: Archive

- [x] 4.1 Move the change folder to `openspec/changes/archive/2026-09-25-docs-specs-veracity-sweep/` (mechanical move, `diff -r` readback).
