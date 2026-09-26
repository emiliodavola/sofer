# Tasks: Assisted CLI failure reporting

- **Change**: `2026-09-25-feat-cli-failure-report`
- **Issue**: GitHub #244 — PR #1 of 2
- **Strict TDD**: `false` (per `openspec/config.yaml`); implementation ordered before tests, all
  gates re-run after each batch.

## Phase 0 — Baseline

- [x] 0.1 Record branch (`feat/244-cli-failure-report`, base `dev`), baseline suite tally, and
  `ruff` / `mypy` / `pyright` state before any edit.
- [x] 0.2 Confirm anchors: `main()` dispatch at `cli.py:1740`, `_build_parser` subparser block,
  `config.py` `_DEFAULTS`, `pyproject.toml [tool.sofer]`.

## Phase 1 — Shared module + config

- [x] 1.1 Add `failure_report_dir`, `failure_report_repo`,
  `failure_report_traceback_max_chars`, `failure_report_manual_url_max_chars`,
  `failure_report_gh_timeout_seconds` to `pyproject.toml [tool.sofer]` and `config.py`
  `_DEFAULTS` + module constants.
- [x] 1.2 Create `src/sofer/failure_report.py`: module docstring, `FailureContext`,
  `anonymize_paths`, `collect_failure_context`, `build_issue_title`, `build_issue_body`.
- [x] 1.3 Add persistence: `state_home`, `reports_dir`, `persist_report`, `load_report`,
  `retry_command`, `manual_issue_url`.
- [x] 1.4 Add `gh` integration: `_run_gh`, `gh_available`, `gh_authenticated`, `create_issue`,
  `send_persisted_report`, `report_cli_failure` (prompt + review + send/persist).

## Phase 2 — CLI wiring

- [x] 2.1 Wrap `main()` dispatch in `try/except Exception` calling
  `failure_report.report_cli_failure`, preserving `SystemExit` / `KeyboardInterrupt`.
- [x] 2.2 Add `_cmd_report_failure` and register the `report-failure` subparser with accurate
  `help=` / `description=` and `func` dispatch.

## Phase 3 — Tests

- [x] 3.1 `tests/test_failure_report.py`: anonymization, allowlist/no-leak, body/title,
  persistence (one timestamped file, no overwrite), gh success/auth/offline, retry, manual URL.
- [x] 3.2 CLI tests: `main()` hook (decline, accept+send, accept+offline persist, non-tty no
  prompt), `report-failure` dispatch, subprocess boundary with a stubbed `gh`.

## Phase 4 — Docs & evidence

- [x] 4.1 Update README / README_ES (runbook section) and CONTRIBUTING.
- [x] 4.2 Run the full suite + `ruff` + `mypy` + `pyright` + `coverage` (cli.py must stay
  100.00%); capture real output into `apply-progress.md`.
- [x] 4.3 Write `verify-report.md` (SDD verify) and archive the change.

## Phase 5 — Delivery (parent-owned)

- [ ] 5.1 Commit the work in reviewable work units on `feat/244-cli-failure-report`; pre-commit
  hooks run ruff + mypy; never `--no-verify`; never push to `dev`. <!-- sdd-owner: parent -->
- [ ] 5.2 Open PR #1 into `dev` via `.github/PULL_REQUEST_TEMPLATE.md` with `Refs #244` and real
  command output. <!-- sdd-owner: parent -->
- [ ] 5.3 Bounded post-apply review + hand merge authorization to the user. <!-- sdd-owner: parent -->
