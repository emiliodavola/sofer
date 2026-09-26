# Delta for mcp-server

Change `2026-09-25-feat-mcp-failure-report` — **issue #244, PR #2 of 2** (MCP + dedupe).

- **ADDED** — `### Requirement: Assisted failure reporting tool with duplicate search (MSP-R19)`.
- **MODIFIED** — `### Requirement: Tool roster and schema contract (MSP-R03)`: 14 → 15 callables,
  adding `sofer_report_failure` to the roster and the count scenario.
- No **REMOVED** requirements. The tool roster grows from 14 to 15 callables; the CLI half of
  issue #244 is the sibling change `2026-09-25-feat-cli-failure-report` and is absent from this
  delta.

## MODIFIED Requirements

### Requirement: Tool roster and schema contract (MSP-R03)

*Modified by change `2026-09-25-feat-mcp-failure-report` (issue #244) — 15 callables
(+ `sofer_report_failure`).*

Server SHALL expose 15 callables: `sofer_validate, sofer_prepare, sofer_publish,
sofer_publish_confirm, sofer_codebook, sofer_codebook_all, sofer_profile, sofer_profile_all,
sofer_render, sofer_render_all, sofer_scan_dry_run, sofer_scan_apply, sofer_init,
sofer_auth_status, sofer_report_failure`. Every param SHALL be `Annotated[Field(description)]`
non-empty (10.1); `target` SHALL be `Literal["local"]`/`Literal["hf"]` single-value (const or
enum) (10.5); `output` SHALL split to `output_file` vs `output_dir` (10.7); `all_files` removed —
batch via `*_all` (10.6); `no_checks` → `run_checks:bool=true` (10.9); every tool SHALL have
`annotations` and typed `output_schema`. `sofer_init` additionally exposes `cwd: str | None = None`
per INIT-02 and its `output_schema` SHALL declare `config_path`/`dataset_root` (absolute strings)
per INIT-03.

#### Scenario: Constrained schemas

- GIVEN `tools/list`
- WHEN inspected
- THEN count SHALL be 15, `target` SHALL have `const` or `enum` single value, no tool SHALL expose `all_files`/`no_checks`/`output` (only `output_file`/`output_dir`/`run_checks`), and every `properties[*].description` SHALL be non-empty

## ADDED Requirements

### Requirement: Assisted failure reporting tool with duplicate search (MSP-R19)

*Introduced by change `2026-09-25-feat-mcp-failure-report` (issue #244).*

The server MUST expose a 15th tool, `sofer_report_failure(error, command="", trace="", confirm=false,
force=false)`, that prepares a confidential failure report and files it through `gh` only when
`confirm=true`. With the default `confirm=false` it MUST return the prepared `title`, `body`,
`manual_url` and any `duplicates` while creating nothing and never calling the send path. The report
MUST reuse the shared reporter contract: no dataset contents, no environment-variable values, and
home paths replaced by `~`.

Before filing, the tool MUST search the repository's **open** issues for duplicates (via
`gh issue list --search`) and, when matches exist and `force` is not set, MUST surface them in the
envelope with `error_code = "DUPLICATE_REPORT"` instead of filing a redundant report. With
`force=true` (and `confirm=true`) the tool MUST file despite matches.

When `confirm=true` and filing succeeds, the envelope MUST report `created=true` and the created
`issue_url`. When `gh` is missing, unauthenticated, or offline, the tool MUST NOT lose the report:
it MUST persist exactly one timestamped file under the configured state directory and return the
`persisted_path`, the `retry_command`, the manual `github.com/<repo>/issues/new` URL, and a
`gh auth login` hint (`error_code = "REPORT_PERSISTED"`).

#### Scenario: Prepared report creates nothing without confirmation

- GIVEN an agent calls `sofer_report_failure(error=..., command=...)` with the default `confirm=false`
- WHEN the tool returns
- THEN `created` SHALL be `false` and no issue SHALL be filed
- AND the envelope SHALL carry the prepared `title`, `body`, `manual_url` and `duplicates`
- AND `hints.action` SHALL be `confirm_report_failure`

#### Scenario: Matching open issues are surfaced instead of a redundant report

- GIVEN `confirm=true`, no `force`, and the duplicate search returns at least one open issue
- WHEN the tool runs
- THEN it SHALL NOT file a new issue
- AND the envelope SHALL return `error_code = DUPLICATE_REPORT` with the matching issues in `duplicates`

#### Scenario: Confirmed filing creates the issue

- GIVEN `confirm=true` and a working authenticated `gh` with no blocking duplicates (or `force=true`)
- WHEN the tool runs
- THEN `created` SHALL be `true` and `issue_url` SHALL name the created issue

#### Scenario: Filing failure persists with the recovery layers

- GIVEN `confirm=true` and `gh` missing, unauthenticated, or offline
- WHEN the tool runs
- THEN `error_code` SHALL be `REPORT_PERSISTED`
- AND the envelope SHALL name the persisted `persisted_path`, the `retry_command`, the manual issue URL, and a `gh_auth_login` hint

#### Scenario: Report excludes secrets and anonymizes home paths

- GIVEN an error message containing a home-directory path and an environment variable value present in the process
- WHEN the report is prepared
- THEN the home directory SHALL appear as `~` and the absolute home path SHALL be absent
- AND the environment-variable value SHALL NOT appear anywhere in the envelope
- AND no dataset content SHALL appear

*Tests:* `tests/test_mcp_failure_report.py::TestReportFailureTool::test_not_confirmed_prepares_without_sending` ·
`tests/test_mcp_failure_report.py::TestReportFailureTool::test_duplicates_block_creation` ·
`tests/test_mcp_failure_report.py::TestReportFailureTool::test_force_overrides_duplicates` ·
`tests/test_mcp_failure_report.py::TestReportFailureTool::test_confirmed_send_creates_issue` ·
`tests/test_mcp_failure_report.py::TestReportFailureTool::test_send_failure_persists_locally` ·
`tests/test_mcp_failure_report.py::TestReportFailureTool::test_duplicate_query_carries_no_message_data` ·
`tests/test_mcp_failure_report.py::TestReportFailureTool::test_confidentiality_anonymizes_and_never_leaks_env`
