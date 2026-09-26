# Apply Progress: 2026-09-25-feat-mcp-failure-report

**Status:** success — implementation + tests complete, all gates green.
**Change:** `2026-09-25-feat-mcp-failure-report` · **Branch:** `feat/244-mcp-failure-report`
(stacked on `feat/244-cli-failure-report`, PR #248; base `dev`).
**Scope:** GitHub ISSUE #244, **PR #2 of 2** (MCP tool + duplicate search).
**Mode:** standard (strict TDD off; implementation ordered before tests).

## Phase 0 — Baseline

- Branch created from `feat/244-cli-failure-report` (PR #248) so the shared module is present.
- Roster/schema/workflow pins at 14 confirmed before editing.

## Phase 1 — Shared helpers + config

- `failure_report.py` (+100): `context_from_parts`, `_error_type_from`, `duplicate_query`,
  `search_open_issues` (gh available/auth preflight, `--json number,title,url`, JSON-parse
  degradation to `([], reason)`).
- `config.py` + `pyproject.toml`: `failure_report_duplicate_limit` (default 5) with the
  positive-int validation loop.

## Phase 2 — MCP tool

- `sofer_report_failure(error, command="", trace="", confirm=false, force=false)` added to
  `mcp_server.py` with the four outcomes (prepared / duplicate / filed / persisted).
- Registered with `readOnlyHint:false, destructiveHint:false, idempotentHint:false,
  openWorldHint:true` and an output_schema declaring every report field.
- `_ERROR_CODES` gains `DUPLICATE_REPORT` / `REPORT_PERSISTED`; the "15 callables" comments and
  `_register_tools` docstring updated.
- `workflow.py`: `sofer_report_failure` registry entry (phase `triage`, no continuation).

## Phase 3 — Tests

- New `tests/test_mcp_failure_report.py` (134 lines, **6 tests**): prepared-without-send,
  duplicates block, force overrides, filed, persisted, confidentiality.
- `tests/test_failure_report.py` (+9 tests): `context_from_parts` (2) and `search_open_issues`
  matrix (7: query, missing gh, unauthenticated, success, gh failure, bad JSON, non-list JSON).
- Roster/schema/workflow counts updated 14 → 15 across `test_mcp_server.py`,
  `test_mcp_schema.py`, `test_mcp_process.py`, `test_workflow.py`; the writing-tools partition
  gains `sofer_report_failure`.

## Phase 4 — Gates (real output)

- `uv run pytest tests/ -q` → **1982 passed, 2 skipped** (PR #248's 1964 + **18** new tests).
- `uv run ruff check src/ tests/ scripts/` → clean; `ruff format --check src/ tests/` →
  "73 files already formatted".
- `uv run mypy src/ scripts/` → "Success: no issues found".
- `uv run pyright` → "0 errors, 1 warning" (pre-existing `_toml.py` `tomli` source warning).
- `uv run coverage run -m pytest` → `coverage report -m`: **TOTAL 94%**;
  `--include=src/sofer/cli.py` → **100%**; `--include=src/sofer/failure_report.py` → **100%**
  (215 stmts, 0 miss, 48 branches, 0 partial); `mcp_server.py` 91% (no per-file floor; the
  pre-existing gaps are unchanged).
- `uv run python scripts/check_test_mapping.py` → OK.

## Files changed

| File | Nature |
| --- | --- |
| `src/sofer/failure_report.py` | +100: MCP-path helpers |
| `src/sofer/mcp_server.py` | +166: `sofer_report_failure` + registration + error codes |
| `src/sofer/workflow.py` | +6: registry entry |
| `src/sofer/config.py` / `pyproject.toml` | `failure_report_duplicate_limit` |
| `tests/test_mcp_failure_report.py` | new, 6 tests |
| `tests/test_failure_report.py` | +9 tests |
| `tests/test_mcp_server.py` / `test_mcp_schema.py` / `test_mcp_process.py` / `test_workflow.py` | roster 14 → 15 |
| `README.md` / `README_ES.md` / `docs/configuration.md` | MCP tool list + counts + key |
| `openspec/specs/mcp-server/spec.md` | canonical sync: MSP-R03 14 → 15, MSP-R19 added |
| `openspec/specs/process-boundary/spec.md` | PB-01 callable count 14 → 15 |

## Deviations from design

1. **`force` was added as an explicit parameter** (design listed it): without it the tool could
   never file when the search returned a loose match, so the override is necessary.
2. **`search_reason` is surfaced in the prepared envelope's `output`** rather than dropped, so a
   degraded search (gh offline) is visible to the agent instead of silently reading as "no
   duplicates".

## Remaining tasks (parent-owned)

- Commit, open PR #2 into `dev` (stacked note), bounded post-apply review + merge authorization.
