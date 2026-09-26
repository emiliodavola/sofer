# Proposal: MCP-assisted failure reporting with duplicate search

- **Change**: `2026-09-25-feat-mcp-failure-report`
- **Issue**: GitHub **#244** (assisted failure reporting from CLI/MCP via `gh`)
- **PR**: **PR #2 of 2** — stacked on `feat/244-cli-failure-report` (PR #248)
- **Domain**: `mcp-server`
- **Status**: proposed

## Intent

The CLI half of issue #244 (PR #248) lets a human file a failure report after an
interactive crash. An MCP agent has no such prompt: it drives sofer through tools and
must be able to (a) prepare a confidential report from a failure it observed, (b) search
the repository's open issues for a duplicate, and (c) file only on explicit confirmation.

This change adds the 15th MCP tool, `sofer_report_failure`, and the duplicate search it
needs. It reuses `failure_report.py` from PR #248, so the confidentiality rules are shared
verbatim.

## Scope

### In scope

- `failure_report.context_from_parts` — build a `FailureContext` from agent-supplied
  `command` / `error` / `trace` strings (no live exception), with the same anonymization
  and truncation as the CLI path.
- `failure_report.duplicate_query` + `failure_report.search_open_issues` — a
  `gh issue list --search` duplicate probe returning `(matches, reason)`; an empty search
  never blocks filing.
- `sofer_report_failure(error, command, trace, confirm, force)` MCP tool:
  - `confirm=false` (default): prepare and return the body, title, manual URL and
    duplicates; **create nothing**.
  - `confirm=true` + duplicates + not `force`: surface the matching issues, do not file.
  - `confirm=true` + (no duplicates or `force`): file via `gh`; on auth/network failure
    persist one report file and return the recovery layers.
- One new `[tool.sofer]` key `failure_report_duplicate_limit` (default 5).
- Workflow registry entry, tool roster/schema test updates (14 → 15), docs.

### Out of scope

- The CLI path (already shipped in PR #248).
- Auto-commenting on a duplicate (the tool surfaces matches; it does not write to them).
- Any dataset content, secret value, or un-anonymized home path in the report.

## Approach

1. Reuse `failure_report.py` (shared module) — no confidentiality logic is duplicated.
2. The tool is a thin adapter: build context → build body → search → gate → send/persist.
3. The MCP surface never files without `confirm=true`; the agent must relay the human's
   consent, mirroring the CLI's two-step prompt.
4. Duplicate matches are returned in the envelope so the agent can point the reporter at an
   existing issue instead of filing a redundant one.

## Affected specs

- `openspec/specs/mcp-server/spec.md` → ADDED `MSP-R19` (assisted failure reporting tool
  with duplicate search).

## Risks

- Adding a tool changes the roster count (14 → 15); the roster/schema/workflow tests are
  updated in the same change.
- Duplicate search depends on `gh`; when unavailable the search returns an empty list plus a
  reason and filing proceeds (degraded, never blocking).
- `sofer_report_failure` is the only tool with `openWorldHint: true`; its annotations and
  docs make the network side effect explicit.
