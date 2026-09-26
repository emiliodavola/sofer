# Proposal: Assisted CLI failure reporting with a local fallback

- **Change**: `2026-09-25-feat-cli-failure-report`
- **Issue**: GitHub **#244** (assisted failure reporting from CLI/MCP via `gh`)
- **PR**: **PR #1 of 2** (slice = CLI + persistence; sibling `2026-09-25-feat-mcp-failure-report`
  adds the MCP tool + duplicate search)
- **Domain**: `cli`
- **Status**: proposed

## Intent

Today an unexpected CLI crash prints a bare traceback and the user loses the exact command,
arguments, error, and environment that a maintainer needs to reproduce it. This change makes
the CLI offer, after an unhandled runtime failure, to file a GitHub issue pre-filled with that
execution context — **only with explicit consent**, and **never** with user data.

The report is confidential by construction and never lossy: when `gh` is unavailable,
unauthenticated, or offline, the report is persisted to disk and the user is given three
independent recovery layers (saved file, retry command, manual issue URL).

## Scope

### In scope

- A single shared module `src/sofer/failure_report.py` that collects the execution context,
  anonymizes it, builds the issue body, persists it, and sends it through `gh`.
- A CLI hook in `main()` that, on an **uncaught** exception, prints the original traceback and
  (interactive only) offers to report it: prompt → review the full body → confirm → send.
- A new `sofer report-failure <file>` subcommand that retries a persisted report.
- Five new `[tool.sofer]` defaults (`failure_report_dir`, `failure_report_repo`,
  `failure_report_traceback_max_chars`, `failure_report_manual_url_max_chars`,
  `failure_report_gh_timeout_seconds`) with `config.py` constants.
- README / README_ES / CONTRIBUTING documentation of the flow.

### Out of scope

- The MCP path (tool, duplicate search, agent consent) — sibling change
  `2026-09-25-feat-mcp-failure-report`.
- Any automatic issue creation: **nothing** is created without explicit consent.
- Any dataset content, sample value, secret value, or environment value in the report.
- Non-`gh` issue backends (GitLab, Jira, ...).

## Approach

1. `failure_report.py` owns every step; `cli.py` only wires the hook and the retry subcommand
   (keeps `cli.py` thin and its 100% coverage mandate cheap to satisfy).
2. Context is a strict allowlist: command, argv, exception type/message, traceback, sofer
   version, Python version, platform. No environment dump, no dataset reads.
3. `anonymize_paths()` replaces the user's home directory with `~` in every emitted string.
4. Consent is two-step: "report?" then a full-body review before "send?".
5. Send path: `gh auth status` → `gh issue create`. On any failure (missing binary, auth,
   network) persist one JSON file per failure under the state directory and print the triple
   safety net (`path`, `sofer report-failure <path>`, manual
   `https://github.com/<repo>/issues/new`, and `gh auth login`).

## Affected specs

- `openspec/specs/cli/spec.md` → ADDED `CLI-R13` (assisted failure reporting) and
  `CLI-R14` (persisted-report retry + offline fallback).

## Risks

- Interactive prompting must never hang CI: prompts are gated on `sys.stdin.isatty()`.
- The report must never leak data: enforced by allowlist + anonymizer + a review step, each
  covered by tests.
- `cli.py` is under a 100% line-coverage mandate; the hook and subcommand are deliberately
  thin and fully exercised in-process and through the subprocess boundary.
