# Design: MCP-assisted failure reporting with duplicate search

- **Change**: `2026-09-25-feat-mcp-failure-report`
- **Issue**: GitHub #244 — PR #2 of 2 (stacked on PR #248)
- **Domain**: `mcp-server`

## 1. Module layout

```
src/sofer/
├── failure_report.py   # PR #248 — extended with context_from_parts, duplicate_query,
│                       #           search_open_issues
├── mcp_server.py       # NEW sofer_report_failure tool + registration
└── workflow.py         # registry entry for the new tool
```

No confidentiality logic is duplicated: the MCP adapter calls the same
`anonymize_paths` / `build_issue_body` / `attempt_send` / `persist_report` helpers as the CLI.

## 2. Shared additions (failure_report.py)

- `context_from_parts(command, error, trace, *, home=None)` builds a `FailureContext` when
  there is no live exception. It sets `argv=(command,)` so the body shows `sofer <command>`,
  derives the error type from the first `*Error`/`*Exception` token (`_error_type_from`,
  defaulting to `Failure`), and applies the same anonymization/truncation.
- `duplicate_query(command, error_type)` keeps the first
  `failure_report_duplicate_query_tokens` identifier tokens of the **anonymized command plus the
  error TYPE only**. The message text, paths and dataset-derived strings are never tokenized, so
  the query sent to GitHub cannot carry user data. Callers pass `ctx.command` / `ctx.error_type`
  from the anonymized context.
- `search_open_issues(repo, query)` runs
  `gh issue list --repo <repo> --state open --search <query> --json number,title,url
  --limit <failure_report_duplicate_limit>` and returns `(matches, reason)`. It reuses the
  `gh_available` / `gh_authenticated` / `_run_gh` preflight so an unavailable or offline
  `gh` degrades to `([], reason)` instead of raising.

## 3. Tool contract (D1)

```
sofer_report_failure(error, command="", trace="", confirm=false, force=false)
```

| Input | Meaning |
| --- | --- |
| `error` (required) | The error message/summary the agent observed. |
| `command` | The failed sofer command / MCP tool. |
| `trace` | Optional traceback text. |
| `confirm` | `false` (default) prepares only; `true` files. |
| `force` | With `confirm=true`, file even when open issues match. |

Outcomes (all return the standard `ok`/`exit_code`/`output` envelope):

1. **Prepared** (`confirm=false`): `ok:true, created:false`, plus `title`, `body`,
   `duplicates`, `manual_url`, and `hints.action = "confirm_report_failure"`. Nothing is
   created and `attempt_send` is never called.
2. **Duplicate** (`confirm=true`, matches, not `force`): `error_code = "DUPLICATE_REPORT"`,
   `duplicates` listed, nothing created.
3. **Filed** (`confirm=true`, no matches or `force`): `ok:true, created:true, issue_url`.
4. **Persisted** (filing failed): `error_code = "REPORT_PERSISTED"`, plus `persisted_path`,
   `retry_command`, `manual_url`, and `hints.action = "gh_auth_login"`.

Consent is the `confirm` flag: the tool cannot file without it, mirroring the CLI's
two-step prompt. The agent relays the human decision.

## 4. Registry and roster (D2)

- `workflow._WORKFLOW_METADATA` gains `sofer_report_failure` (phase `triage`, requires
  `("failure context",)`, no continuation). It is deliberately **not** added to
  `WORKFLOW_BRANCHES`, which is a curated chain.
- `mcp_server._ERROR_CODES` gains `DUPLICATE_REPORT` and `REPORT_PERSISTED`.
- The tool's `output_schema` declares `created`, `duplicates`, `title`, `body`,
  `manual_url`, `issue_url`, `persisted_path`, `retry_command` plus the shared error-envelope
  fields, so FastMCP does not drop them at the boundary.
- Annotations: `readOnlyHint:false`, `destructiveHint:false`, `idempotentHint:false`,
  `openWorldHint:true` (the only tool that reaches the network to file).

## 5. Test strategy

- `tests/test_mcp_failure_report.py` (new): the four outcomes above through the real
  in-memory `Client`, plus a confidentiality test (env value absent, home anonymized).
- `tests/test_failure_report.py`: `context_from_parts`, `duplicate_query`, and
  `search_open_issues` (missing gh / unauthenticated / success / bad JSON / non-list JSON).
- Roster/schema/workflow counts updated 14 → 15 (`test_mcp_server.py`, `test_mcp_schema.py`,
  `test_workflow.py`), and `sofer_report_failure` added to the writing-tools partition.

## 6. PR boundary

Stacked on `feat/244-cli-failure-report` (PR #248). This PR touches `failure_report.py`
(additive helpers only), `mcp_server.py`, `workflow.py`, the MCP tests, docs and the
mcp-server spec delta. It does not re-touch the CLI wiring or the cli spec.
