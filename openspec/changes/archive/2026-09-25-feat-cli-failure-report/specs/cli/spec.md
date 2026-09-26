# Delta for cli

Change `2026-09-25-feat-cli-failure-report` — **issue #244, PR #1 of 2** (CLI + persistence).

- **ADDED** — `### Requirement: Assisted CLI failure reporting with consent and confidentiality (CLI-R13)`.
- **ADDED** — `### Requirement: Persisted-report retry and offline fallback (CLI-R14)`.
- No **MODIFIED** requirements, no **REMOVED** requirements. The MCP path (tool + duplicate
  search) is a separate change, `2026-09-25-feat-mcp-failure-report`; it is absent from this delta.

## ADDED Requirements

### Requirement: Assisted CLI failure reporting with consent and confidentiality (CLI-R13)

*Introduced by change `2026-09-25-feat-cli-failure-report` (issue #244).*

When an uncaught exception escapes a CLI command, the CLI MUST print the original traceback
(preserving today's failure output) and, **only when `sys.stdin` is a TTY**, offer to open a
GitHub issue in the configured repository. Nothing SHALL be created without explicit consent:
the user MUST first confirm the offer, then review the complete issue body, then confirm the
send. Declining either prompt MUST create nothing and MUST NOT change the exit code (`1`).

The report context SHALL be a strict allowlist — the command and its arguments, the exception
type and message, the traceback, the `sofer` version, the Python version, and the platform. The
report MUST NEVER include dataset contents (no row, sample, cell value, or excerpt), MUST NEVER
include the value of any environment variable (at most a variable NAME when it has diagnostic
value, and this change includes none), and MUST anonymize local paths by replacing the user's
home directory with `~` in POSIX and Windows forms. The body printed for review MUST be
byte-identical to the body that is sent or persisted.

#### Scenario: Non-interactive failure never prompts and never creates

- GIVEN a command that raises an uncaught exception and `sys.stdin` is not a TTY
- WHEN the CLI runs
- THEN it SHALL print the traceback and exit `1`
- AND it SHALL NOT create a GitHub issue, persist a report file, or prompt

#### Scenario: Declining creates nothing

- GIVEN an interactive failure and the user answers `N` to the "report?" prompt
- WHEN the CLI runs
- THEN no issue SHALL be created and no report file SHALL be written
- AND the exit code SHALL remain `1`

#### Scenario: Accepting reviews the exact body before sending

- GIVEN an interactive failure and the user answers `y` to the "report?" prompt
- WHEN the review prompt is shown
- THEN the complete anonymized body SHALL be printed
- AND the issue SHALL be created (or persisted on failure) only after the user answers `y` to the second prompt
- AND the reviewed body SHALL equal the body sent/persisted

#### Scenario: Report excludes data, secrets, and identifying paths

- GIVEN a failure whose traceback and arguments embed a home-directory path and an environment variable value
- WHEN the report body is built
- THEN the home directory SHALL appear as `~` and the absolute home path SHALL be absent
- AND no environment-variable value SHALL appear (only the documented allowlisted facts)
- AND no dataset content SHALL appear

*Tests:* `tests/test_failure_report.py::TestAnonymize::test_home_replaced_posix` ·
`tests/test_failure_report.py::TestAnonymize::test_home_replaced_windows_backslash_form` ·
`tests/test_failure_report.py::TestContext::test_context_is_allowlisted_and_env_free` ·
`tests/test_failure_report.py::TestBody::test_body_carries_no_dataset_data` ·
`tests/test_failure_report.py::TestCliIntegration::test_non_tty_creates_nothing` ·
`tests/test_failure_report.py::TestCliIntegration::test_decline_creates_nothing` ·
`tests/test_failure_report.py::TestCliIntegration::test_accept_reviews_body_then_sends`

### Requirement: Persisted-report retry and offline fallback (CLI-R14)

*Introduced by change `2026-09-25-feat-cli-failure-report` (issue #244).*

Filing a report depends on `gh` being present, authenticated, and the network being reachable.
When any of these fails, the flow MUST NOT lose the report. It SHALL persist **one** file per
failure under sofer's state directory (`_state_home() / failure_report_dir`), named with a UTC
timestamp and the process id, and MUST NOT overwrite an existing file. The persisted document
SHALL carry the repository, title, body, and creation timestamp.

When persisting, the CLI SHALL print the path, the retry command
`sofer report-failure "<path>"`, the manual fallback URL
`https://github.com/<repo>/issues/new` with the body pre-loadable for copy/paste, and the
permanent fix `gh auth login`.

The `sofer report-failure <file>` subcommand SHALL load a persisted report and re-run the send
path through `gh`; on success it SHALL print the created issue URL, and on failure it SHALL
re-emit the same recovery layers without losing the file.

#### Scenario: Missing auth or network persists and prints the triple safety net

- GIVEN an accepted report and `gh` missing, unauthenticated, or offline
- WHEN the CLI attempts to send
- THEN exactly one report file SHALL be written under the configured state directory with a timestamped name
- AND the output SHALL name the file path, the `sofer report-failure` retry command, the manual `github.com/<repo>/issues/new` URL, and `gh auth login`

#### Scenario: One file per failure, never overwritten

- GIVEN two failures in the same second
- WHEN both reports are persisted
- THEN two distinct files SHALL exist and neither SHALL be overwritten

#### Scenario: Retry sends a persisted report

- GIVEN a persisted report file and a working authenticated `gh`
- WHEN `sofer report-failure <file>` runs
- THEN the issue SHALL be created and its URL printed
- AND the command SHALL exit `0`

*Tests:* `tests/test_failure_report.py::TestPersistence::test_one_file_per_failure_never_overwrites` ·
`tests/test_failure_report.py::TestSend::test_offline_persists_and_prints_safety_net` ·
`tests/test_failure_report.py::TestSend::test_missing_gh_never_calls_create` ·
`tests/test_failure_report.py::TestPersistence::test_retry_command_shape` ·
`tests/test_cli.py::test_report_failure_subprocess_offline_prints_safety_net`
