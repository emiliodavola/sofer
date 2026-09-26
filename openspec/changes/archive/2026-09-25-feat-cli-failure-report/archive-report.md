# Archive Report: 2026-09-25-feat-cli-failure-report

**Change**: `2026-09-25-feat-cli-failure-report`
**Issue**: GitHub **#244 ONLY** — **PR #1 of 2** (sibling: `2026-09-25-feat-mcp-failure-report`)
**Date**: 2026-09-26
**Artifact store**: `openspec` (repo-local)
**Status**: **archived** (mechanics complete; delivery commit/PR is parent-owned)
**Verify verdict**: `pass` — `blockers: 0`, `critical_findings: 0`, `requirements: 2/2`, `scenarios: 7/7`
**Branch**: `feat/244-cli-failure-report` (base `dev`)
**Archived path**: `openspec/changes/archive/2026-09-25-feat-cli-failure-report/`

## Summary

Implements issue #244's CLI half: on an uncaught CLI exception, sofer prints the traceback and —
on an interactive terminal only — offers to file a confidential GitHub issue. The report context is
a strict allowlist (command/args, error + traceback, `sofer`/Python/platform), home paths are
anonymized to `~`, no env-var value or dataset content is read, and nothing is filed without
two-step explicit consent plus a full-body review. When `gh` is missing, unauthenticated, or
offline, one timestamped JSON report per failure is persisted under the sofer state directory and
the user gets the triple safety net (saved path, `sofer report-failure` retry command, manual
`github.com/<repo>/issues/new` URL) plus the permanent fix `gh auth login`.

A new `src/sofer/failure_report.py` is the single home for the whole flow; `cli.py` only wires the
`main()` hook and the new `report-failure` subcommand. The MCP path is absent from this change.

## Spec Sync

**DONE at archive** — canonical merge applied.

| Field | Value |
| --- | --- |
| Domain synced | `cli` (1 of 1) |
| ADDED requirements | `CLI-R13` (assisted failure reporting) + `CLI-R14` (persisted-report retry / offline fallback) |
| MODIFIED / REMOVED / RENAMED | none |
| Canonical file | `openspec/specs/cli/spec.md` (appended after `CLI-R12`) |
| Provenance | `> Added by change \`2026-09-25-feat-cli-failure-report\` (issue #244).` on both requirements |
| Declared transforms | delta's `*Introduced by change …*` italic line → canonical provenance blockquote; delta's `*Tests:*` pointer runs dropped (canonical format carries no test pointers); zero edits to existing canonical content |
| Destructive merge | Not applicable — ADD-only |

## Verification Evidence

See `verify-report.md`. Headline: `uv run pytest tests/ -q` → **1964 passed, 2 skipped**;
`coverage report` → **TOTAL 94%**, `cli.py` **100%**, `failure_report.py` **100%**; `ruff` / `mypy` /
`pyright` clean (one pre-existing `_toml.py` warning); `check_test_mapping.py` OK. An independent
read-only subagent returned **PASS, 0 blockers**; its reachable truncation bug (W1) and the
oversized manual URL (W2) were fixed before archive.

## Task Completion Gate

All implementation rows (Phases 0–4) are complete; the three Phase-5 rows are parent-owned
(commit → PR #1 → bounded review/merge authorization) and remain open by design.

## Delivery

| Field | Value |
| --- | --- |
| Branch | `feat/244-cli-failure-report`, base `dev` |
| Commits | none yet (parent-owned); the change is the working-tree diff |
| PR | **#1 NOT yet opened** — parent-owned; target `dev`, `Refs #244` |
| Release / tag | none (hatch-vcs derives from tags) |
| PR boundary | CLI + persistence + docs only; no `mcp_server.py` / `workflow.py` / mcp spec touch |

## Rollback Notes

`git checkout -- src/sofer/cli.py src/sofer/config.py pyproject.toml tests/test_cli.py
tests/test_config.py README.md README_ES.md CONTRIBUTING.md docs/configuration.md` and delete
`src/sofer/failure_report.py` + `tests/test_failure_report.py` restores the pre-change state; the
canonical `CLI-R13`/`CLI-R14` blocks would then need manual removal.
