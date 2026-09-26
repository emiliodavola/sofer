# Archive Report: 2026-09-25-feat-mcp-failure-report

**Change**: `2026-09-25-feat-mcp-failure-report`
**Issue**: GitHub **#244 ONLY** — **PR #2 of 2**, stacked on `feat/244-cli-failure-report` (PR #248)
**Date**: 2026-09-26
**Artifact store**: `openspec` (repo-local)
**Status**: **archived** (mechanics complete; delivery commit/PR is parent-owned)
**Verify verdict**: `pass` — `blockers: 0`, `critical_findings: 0`, `requirements: 2/2`, `scenarios: 6/6`
**Branch**: `feat/244-mcp-failure-report` (stacked on PR #248; base `dev`)
**Archived path**: `openspec/changes/archive/2026-09-25-feat-mcp-failure-report/`

## Summary

Adds the MCP half of issue #244: the 15th tool `sofer_report_failure` prepares a confidential
failure report from agent-supplied `error`/`command`/`trace`, searches the repository's open
issues for duplicates, and files through `gh` only on explicit `confirm=true` (with `force` to
override a duplicate match). A send failure persists one timestamped file locally and returns the
triple recovery layers. The tool reuses `failure_report.py` from PR #248, so no confidentiality
logic is duplicated.

Two independent-verification rounds: round 1 returned FAIL with a confidentiality blocker (the
duplicate search sent raw agent text to GitHub) and a canonical-spec contradiction (MSP-R03 still
pinned 14 callables); both were fixed — the query is now built from the anonymized command + error
TYPE only, and MSP-R03/PB-01 were modified to 15 — and round 2 returned **PASS**.

## Spec Sync

**DONE at archive** — canonical merge applied.

| Field | Value |
| --- | --- |
| Domain synced | `mcp-server` (1) + `process-boundary` (roster count) |
| ADDED requirements | `MSP-R19` (assisted failure reporting tool with duplicate search) |
| MODIFIED requirements | `MSP-R03` (14 → 15 callables, + `sofer_report_failure`); PB-01 callable count 14 → 15 |
| REMOVED / RENAMED | none |
| Canonical files | `openspec/specs/mcp-server/spec.md`, `openspec/specs/process-boundary/spec.md` |
| Provenance | `> Added by change \`2026-09-25-feat-mcp-failure-report\` (issue #244).` on MSP-R19; MSP-R03 provenance extended with the modification |
| Destructive merge | Not applicable — MSP-R03 modification is additive to the roster |

## Verification Evidence

See `verify-report.md`. Headline: `uv run pytest tests/ -q` → **1982 passed, 2 skipped**;
`coverage report` → **TOTAL 94%**, `cli.py` **100%**, `failure_report.py` **100%** (215 stmts);
`ruff` / `mypy` / `pyright` clean (one pre-existing warning); `check_test_mapping.py` OK. Roster is
15/15 at runtime and in the workflow registry.

## Task Completion Gate

All implementation rows (Phases 0–4) are complete; the three Phase-5 rows are parent-owned
(commit → PR #2 → bounded review/merge authorization) and remain open by design.

## Delivery

| Field | Value |
| --- | --- |
| Branch | `feat/244-mcp-failure-report`, stacked on `feat/244-cli-failure-report` (PR #248) |
| Commits | none yet (parent-owned); the change is the working-tree diff |
| PR | **#2 NOT yet opened** — parent-owned; target `dev`, `Refs #244`, stack note "merge #248 first" |
| Release / tag | none |
| PR boundary | MCP + shared helpers + registry + MCP tests + docs; the CLI wiring is untouched |

## Rollback Notes

`git checkout -- src/sofer/mcp_server.py src/sofer/workflow.py src/sofer/config.py
src/sofer/failure_report.py pyproject.toml tests/test_mcp_server.py tests/test_mcp_schema.py
tests/test_mcp_process.py tests/test_workflow.py tests/test_failure_report.py README.md
README_ES.md docs/configuration.md` and delete `tests/test_mcp_failure_report.py` restores the
PR-#248 state; the canonical `MSP-R19` / MSP-R03 modification and the PB-01 count would then need
manual reversal.
