# Tasks: MCP-assisted failure reporting with duplicate search

- **Change**: `2026-09-25-feat-mcp-failure-report`
- **Issue**: GitHub #244 — PR #2 of 2 (stacked on PR #248)
- **Strict TDD**: `false`; implementation ordered before tests, gates re-run after each batch.

## Phase 0 — Baseline

- [x] 0.1 Branch `feat/244-mcp-failure-report` from `feat/244-cli-failure-report` (PR #248).
- [x] 0.2 Confirm the MCP roster/schema/workflow count pins (14) and the registry contract.

## Phase 1 — Shared helpers + config

- [x] 1.1 Add `context_from_parts`, `_error_type_from`, `duplicate_query`, `search_open_issues`
  to `failure_report.py`.
- [x] 1.2 Add `failure_report_duplicate_limit` to `[tool.sofer]` / `config.py` (+ positive-int
  validation).

## Phase 2 — MCP tool

- [x] 2.1 Add `sofer_report_failure` callable with the four outcomes and a docstring carrying
  `When to use` / `Example` / `Requires` / `Next`.
- [x] 2.2 Register it in `_register_tools` with annotations + output_schema; add
  `DUPLICATE_REPORT` / `REPORT_PERSISTED` to `_ERROR_CODES`.
- [x] 2.3 Add the `sofer_report_failure` entry to `workflow._WORKFLOW_METADATA`.

## Phase 3 — Tests

- [x] 3.1 New `tests/test_mcp_failure_report.py`: prepared / duplicate / forced / filed /
  persisted / confidentiality through the real `Client`.
- [x] 3.2 `tests/test_failure_report.py`: `context_from_parts`, `duplicate_query`,
  `search_open_issues` matrix.
- [x] 3.3 Update roster/schema/workflow counts 14 → 15 and the writing-tools partition.

## Phase 4 — Docs & evidence

- [x] 4.1 Update README / README_ES (MCP tool list + counts) and docs.
- [x] 4.2 Run the full suite + ruff + mypy + pyright + coverage; capture real output.
- [x] 4.3 Write `verify-report.md` and archive the change.

## Phase 5 — Delivery (parent-owned)

- [ ] 5.1 Commit on `feat/244-mcp-failure-report`; never `--no-verify`; never push to `dev`. <!-- sdd-owner: parent -->
- [ ] 5.2 Open PR #2 into `dev` via `.github/PULL_REQUEST_TEMPLATE.md` with `Refs #244` and a
  stack note. <!-- sdd-owner: parent -->
- [ ] 5.3 Bounded post-apply review + hand merge authorization to the user. <!-- sdd-owner: parent -->
