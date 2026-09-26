# Verify Report: 2026-09-25-feat-cli-failure-report

```yaml
verdict: pass
blockers: 0
critical_findings: 0
requirements: 2/2
scenarios: 7/7
test_exit_code: 0
build_exit_code: 0
```

**Change:** `2026-09-25-feat-cli-failure-report` · **Issue:** GitHub #244 · **PR #1 of 2**
**Branch:** `feat/244-cli-failure-report` (base `dev`)
**Verification:** self-run gates + one independent read-only subagent (no state modified).

## Requirement coverage

| Requirement | Scenarios | Evidence |
| --- | --- | --- |
| CLI-R13 — Assisted failure reporting with consent and confidentiality | 4/4 | `tests/test_failure_report.py::TestCliIntegration` (non-tty, decline, accept+review+send), `TestContext`/`TestBody`/`TestAnonymize` (allowlist, no env leak, home anonymization); `tests/test_cli.py::test_main_offers_report_on_uncaught_exception` |
| CLI-R14 — Persisted-report retry and offline fallback | 3/3 | `TestPersistence::test_one_file_per_failure_never_overwrites`, `TestSend::test_offline_persists_and_prints_safety_net` / `test_missing_gh_never_calls_create`, `TestPersistence::test_retry_command_shape`; `tests/test_cli.py::test_report_failure_subprocess_offline_prints_safety_net` |

## Gate evidence

| Gate | Command | Result |
| --- | --- | --- |
| Full suite | `uv run pytest tests/ -q` | **1964 passed, 2 skipped** (clean checkout; coverage-contract guard skips by design) |
| Coverage (TOTAL) | `uv run coverage run -m pytest` + `coverage report -m` | **94%** (floor 90) |
| Coverage (cli.py, COV-06) | `coverage report --include=src/sofer/cli.py` | **100%** — 610 stmts, 0 miss, 176 branches, 0 partial |
| Coverage (failure_report.py) | `coverage report --include=src/sofer/failure_report.py` | **100%** — 188 stmts, 0 miss, 40 branches, 0 partial |
| Lint | `uv run ruff check src/ tests/ scripts/` | clean |
| Format | `uv run ruff format --check src/ tests/` | 72 files already formatted |
| Types | `uv run mypy src/ scripts/` | Success: no issues found |
| Types | `uv run pyright` | 0 errors, 1 pre-existing warning (`_toml.py` `tomli` source) |
| Spec↔test | `uv run python scripts/check_test_mapping.py` | OK: test-mapping contract holds |
| No-pragma guard | `tests/test_coverage_contract.py` | core modules carry no `pragma: no cover` |

## Independent verification (subagent, read-only)

Verdict **PASS, 0 blockers**. It independently re-ran the gates and adversarially probed the
mandatory issue sections:

- **Confidentiality** — source-inspected that `collect_failure_context` / `anonymize_paths` /
  `build_issue_body` never read `os.environ`; an env var set to `hunter2-TOPSECRET` did not appear
  in the body; `/home/alice` became `~`; consent is two-step and non-tty creates nothing.
- **Offline fallback** — one timestamped JSON file per failure (timestamp + pid + collision
  counter), retry command, manual URL and `gh auth login` all emitted.
- **No regression** — `main()` wraps only dispatch; `SystemExit`/`KeyboardInterrupt` pass through;
  a non-tty crash still prints the traceback and exits `1`.

Findings raised and disposition:

| # | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| W1 | bug (reachable) | `_truncate` returned the **whole** traceback when the configured cap was smaller than the truncation marker (`tail == 0` → `text[-0:]`) | **Fixed** — guarded tail slice + boundary test (`TestContext::test_tiny_cap_never_returns_the_full_traceback`) |
| W2 | warning | Manual `issues/new` URL was ~46 KB at the default cap (unusable as a recovery layer) | **Fixed** — `failure_report_manual_url_max_chars` (6000); above it the URL prefills the title and the output points at the saved file |
| W3 | docs | README/proposal claimed anonymization of "every path", including the local terminal output | **Fixed** — wording scoped to paths inside the report |
| W5 | traceability | Spec-delta `*Tests:*` pointers named non-existent tests | **Fixed** — corrected to real test names |
| W6 | docs | proposal/design declared 3 config keys; 4 shipped | **Fixed** — declared five (incl. the manual-URL cap) |
| W7 | docs | CONTRIBUTING/AGENTS still said "9 subcommands" | **Fixed** — updated to 10 |
| W4 | inherent | Exception text can echo dataset-derived strings (the issue requires the error + traceback) | **Accepted & documented** — the mandatory full-body review (byte-identical to what is sent/persisted) is the mitigation |

No blockers remain. The change is ready for archive.
