# Design: Assisted CLI failure reporting

- **Change**: `2026-09-25-feat-cli-failure-report`
- **Issue**: GitHub #244 — PR #1 of 2
- **Domain**: `cli`

## 1. Module layout

```
src/sofer/
├── failure_report.py   # NEW — context collection, anonymization, body, persistence, gh send
└── cli.py              # thin wiring: main() hook + _cmd_report_failure
```

`failure_report.py` is the single home (AGENTS.md rule 4) for the whole flow. Both the CLI
adapter (this change) and the MCP adapter (sibling change) consume it, so the confidentiality
rules cannot drift between surfaces.

## 2. Failure detection (D1)

Only **uncaught** exceptions are reportable. The existing `_cmd_*` handlers deliberately catch
their expected failures and return a friendly exit code; those have no traceback and are not
"runtime failures". `main()` therefore wraps dispatch:

```python
try:
    exit_code = args.func(args)
except Exception as exc:              # SystemExit / KeyboardInterrupt pass through
    failure_report.report_cli_failure(sys.argv[1:], exc)
    exit_code = 1
sys.exit(exit_code)
```

`report_cli_failure()` always prints the original traceback first (behavior preservation), then
offers the report only when `sys.stdin.isatty()`. Non-interactive runs create nothing.

Rejected alternatives:
- Wrapping every `_cmd_*` catch: large, unverifiable, and there is no traceback to report.
- Reporting on non-zero exit codes: conflates expected validation failures with crashes and
  would create noise.

## 3. Confidentiality by construction (D2)

The context is a **strict allowlist**:

| Field | Source | Sanitization |
| --- | --- | --- |
| `command` | argv[0] basename if it looks like `sofer`, else `"sofer"` | none needed |
| `argv` | `sys.argv[1:]` | `anonymize_paths` |
| `error_type` | `type(exc).__name__` | none |
| `error_message` | `str(exc)` | `anonymize_paths` |
| `traceback` | `traceback.format_exception` | `anonymize_paths`, truncated |
| `sofer_version` | `_version.get_version()` | none |
| `python_version` | `platform.python_version()` | none |
| `platform` | `platform.platform()` | `anonymize_paths` (hostname/user can appear) |

`anonymize_paths(text)` replaces the resolved home directory with `~` in both POSIX and Windows
forms (`str(home)`, `home.as_posix()`, the backslash form and the doubled-backslash form that a
rendered Windows source literal can produce). **No** environment variable value is ever read into
the report; the only
environment-derived fact is the configured repo name (a public constant).

No dataset file is opened. No sample, row, column value, or cell is reachable from the context.

## 4. Consent and review (D3)

```
runtime failure
  └─ traceback to stderr
     └─ if stdin is a tty:
          "Report this failure to <repo>? [y/N]"  ── N ──▶ nothing created
            └─ y
               print full body (review)
               "Send this report? [y/N]"           ── N ──▶ nothing sent
                 └─ y ──▶ gh auth status ── ok ──▶ gh issue create
                              │
                              └─ failed/offline ──▶ persist + triple safety net
```

The review step prints the **complete, final** body (post-anonymization) so what the user
approves is byte-identical to what is sent. The body is built once and reused by the review,
the send, and the persisted file.

## 5. Persistence (D4)

- Location: `_state_home() / config.FAILURE_REPORT_DIR`, where `_state_home()` honors
  `SOFER_STATE_HOME` (tests), then `XDG_STATE_HOME` (POSIX), then `LOCALAPPDATA` (Windows),
  then `~/.local/state`. The `sofer` app segment is a module constant.
- One **JSON** file per failure: `failure-<UTC yyyymmddTHHMMSSffffffZ>-<pid>.json` holding
  `{repo, title, body, created_at}`. Timestamp + pid guarantee a fresh file; the writer never
  overwrites an existing path.
- `retry_command(path)` returns `sofer report-failure "<path>"`.

## 6. GitHub send (D5)

`subprocess.run(["gh", ...])` with `capture_output=True`; `shutil.which("gh")` first. Order:

1. missing binary → persist;
2. `gh auth status` non-zero → persist;
3. `gh issue create --repo <repo> --title <t> --body-file <tmp>` non-zero (network, perms) →
   persist;
4. success → print the issue URL.

`--body-file` is used (not `--body`) so the body is passed verbatim and shell-safe. The temp
file is deleted in a `finally`.

## 7. Configuration (D6)

Three keys, defaults in `pyproject.toml [tool.sofer]` + `config.py` `_DEFAULTS`:

| key | default | purpose |
| --- | --- | --- |
| `failure_report_dir` | `"failure-reports"` | subdirectory under the state home |
| `failure_report_repo` | `"emiliodavola/sofer"` | `owner/repo` target for issues |
| `failure_report_traceback_max_chars` | `20000` | traceback truncation cap |
| `failure_report_manual_url_max_chars` | `6000` | body length above which the manual URL prefills the title only (the body stays in the saved file) |
| `failure_report_gh_timeout_seconds` | `30` | per-`gh`-call subprocess timeout |

No literal is inlined in a function body (AGENTS.md rule 1).

## 8. `sofer report-failure` subcommand (D7)

`_cmd_report_failure(args) -> int` reads the persisted JSON, re-runs the same send path, prints
the issue URL on success or the triple safety net on failure. It is the executable form of the
"retry command" layer and the 10th top-level subcommand; its `help=` / `description=` text and
the README are updated in the same change.

## 9. Test strategy

- Unit matrix for `failure_report.py`: anonymization (POSIX + Windows + doubled-backslash home),
  allowlist (no env leak), body/title content, persistence (one file, timestamped, no
  overwrite), gh send success/auth-failure/missing-binary, retry command, manual URL.
- `cli.py`: hook covered in-process (monkeypatched `report_cli_failure` and a raising command)
  and the subcommand covered in-process; `main()` branch where `args.func` returns 0 stays
  covered by existing tests.
- Subprocess boundary: a real `sofer report-failure` invocation against a persisted file with a
  stubbed `gh` on `PATH` (offline, deterministic).

## 10. PR boundary

This PR ships only the shared module + CLI + persistence + docs. It adds no MCP tool and does
not touch `mcp_server.py`, the MCP tool roster, `workflow.py`, or the mcp-server spec.
