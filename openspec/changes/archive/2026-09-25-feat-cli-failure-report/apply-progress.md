# Apply Progress: 2026-09-25-feat-cli-failure-report

**Status:** success — implementation + tests complete, all gates green.
**Change:** `2026-09-25-feat-cli-failure-report` · **Branch:** `feat/244-cli-failure-report` (base `dev`).
**Scope:** GitHub ISSUE #244, **PR #1 of 2** (CLI + persistence). The MCP path is absent from this diff.
**Mode:** standard (strict TDD off per `openspec/config.yaml`; implementation ordered before tests).

## Phase 0 — Baseline

- Branch created from an up-to-date `dev` (`git checkout dev && git pull --ff-only` → OK).
- Baseline suite not separately re-measured on `dev`; the post-change tally (1964 passed / 2 skipped)
  minus the **45** new tests yields a derived baseline of **1919 passed** (disclosed as derived).
- Gates before edit: `ruff` / `mypy` / `pyright` clean (pyright's pre-existing
  `_toml.py` `tomli` source warning only).

## Phase 1 — Shared module + config

- `src/sofer/failure_report.py` (new, 499 lines): `FailureContext`, `anonymize_paths`,
  `collect_failure_context`, `build_issue_title`, `build_issue_body`, `state_home`, `reports_dir`,
  `persist_report`, `load_report`, `retry_command`, `manual_issue_url`, `gh_available`, `_run_gh`,
  `gh_authenticated`, `create_issue`, `attempt_send`, `_print_recovery`, `send_persisted_report`,
  `report_cli_failure`, `_stdin_is_interactive`, `_ask_yes_no`.
- `config.py`: `_DEFAULTS` gains `failure_report_dir`, `failure_report_repo`,
  `failure_report_traceback_max_chars`, `failure_report_manual_url_max_chars`,
  `failure_report_gh_timeout_seconds`; module constants added; non-empty validation extended to
  `failure_report_dir`/`failure_report_repo` and positive-int validation added for the three bounds.
- `pyproject.toml [tool.sofer]`: the five keys documented with defaults.

## Phase 2 — CLI wiring

- `main()` dispatch wrapped in `try/except Exception` → `failure_report.report_cli_failure(sys.argv[1:], exc)`,
  exit `1`; `SystemExit`/`KeyboardInterrupt` are not intercepted.
- `_cmd_report_failure` + `report-failure` subparser (`help=`/`description=` accurate; 10th subcommand).

## Phase 3 — Tests

- `tests/test_failure_report.py` (new, 387 lines, **40 tests**): anonymization (POSIX/Windows/root),
  allowlist + env-free context, truncation cap (including the tiny-cap boundary), title/body, state-home
  resolution (override/XDG/POSIX fallback/Windows), persistence (one file per failure, never
  overwrite), load validation, retry command, manual URL (prefill + oversized-body omission), gh send
  (missing binary / unauthenticated / success / failure / `_run_gh` OSError / `create_issue`
  unavailable), retry send, and the interactive orchestration (non-tty, decline, review-decline,
  accept+send, accept+offline-persist, long-body paste hint, EOF, broken stdin).
- `tests/test_cli.py` (**3 new tests**): `main()` hook on an uncaught exception, `report-failure`
  parser dispatch, and the PB-02 subprocess boundary with no `gh` on `PATH`.
- `tests/test_config.py` (**2 new tests**): the empty-`failure_report_dir` and non-positive
  `failure_report_gh_timeout_seconds` validations.

## Phase 4 — Gates (real output)

- `uv run pytest tests/ -q` → **1964 passed, 2 skipped** (clean checkout, no `.coverage`; the
  coverage-contract guard skips as designed). Derived baseline 1919 + 45 new = 1964.
- `uv run ruff check src/ tests/ scripts/` → clean; `uv run ruff format --check src/ tests/` →
  "72 files already formatted".
- `uv run mypy src/ scripts/` → "Success: no issues found".
- `uv run pyright` → "0 errors, 1 warning" (pre-existing `_toml.py` `tomli` source warning).
- `uv run coverage run -m pytest` → `coverage report -m`: **TOTAL 94%**;
  `--include=src/sofer/cli.py` → **100%** (610 stmts, 0 miss, 176 branches, 0 partial);
  `--include=src/sofer/failure_report.py` → **100%** (188 stmts, 0 miss, 40 branches, 0 partial).
- `uv run python scripts/check_test_mapping.py` → "OK: test-mapping contract holds".

## Independent verification (subagent)

An independent read-only subagent re-ran the gates and adversarially probed confidentiality,
consent, offline persistence and traceback preservation. Verdict: **PASS, 0 blockers**. Its findings
were acted on before archive:

- **W1 (fixed)** — `_truncate`'s tail slice `text[-tail:]` inverted to the whole traceback when the
  configured cap was smaller than the marker (`tail == 0` → `text[-0:]`); now guarded
  (`(text[-tail:] if tail else "")`) with a boundary test.
- **W2 (fixed)** — the manual `issues/new` URL was unusable at the default cap (≈46 KB). Added
  `failure_report_manual_url_max_chars` (default 6000); above it the URL prefills the title only and
  the recovery output points at the saved file for copy/paste.
- **W3 (docs fixed)** — README/proposal now state that anonymization applies to paths *inside the
  report* (the local terminal path/retry command is intentionally left runnable).
- **W5/W6/W7 (fixed)** — spec-delta `*Tests:*` references corrected to real test names; proposal/design
  key count corrected to five; CONTRIBUTING and AGENTS.md subcommand inventory updated to 10.
- **W4 (inherent, documented)** — exception text can echo dataset-derived strings; the mandatory
  full-body review (byte-identical to what is sent/persisted) is the mitigation.

## Files changed

| File | Nature |
| --- | --- |
| `src/sofer/failure_report.py` | new shared module (499 lines) |
| `src/sofer/cli.py` | `main()` hook + `_cmd_report_failure` + `report-failure` subparser (+55) |
| `src/sofer/config.py` | 5 `_DEFAULTS` keys, 5 constants, validation (+29) |
| `pyproject.toml` | `[tool.sofer]` failure-report keys |
| `tests/test_failure_report.py` | new, 40 tests |
| `tests/test_cli.py` | 3 new tests (+60) |
| `tests/test_config.py` | 2 new validation tests |
| `README.md` / `README_ES.md` | command row + "Assisted failure reporting" section + subcommand count |
| `CONTRIBUTING.md` | reporting-bugs note |
| `docs/configuration.md` | failure-report key table |
| `openspec/changes/2026-09-25-feat-cli-failure-report/**` | proposal / design / tasks / spec delta |

## Deviations from design

1. **No separate `gh auth status` in the failure path when the binary is missing** — `attempt_send`
   short-circuits on `gh_available()` before the auth preflight, avoiding a subprocess spawn for a
   binary that does not exist. The auth preflight still runs (and avoids `gh` opening an interactive
   login) whenever `gh` is present.
2. **Persistence is JSON**, not markdown: the retry subcommand must recover the title/repo
   losslessly. The manual copy/paste layer is the printed `github.com/<repo>/issues/new` URL, whose
   `body` query parameter is the exact reviewed body.
3. **Size**: the new module is 499 lines with mandatory docstrings; the change is larger than the
   400-line review budget for `src/`+`tests/` combined, which is why issue #244 is deliberately split
   into the two chained PRs the issue mandates.

## Remaining tasks (parent-owned)

- Commit, open PR #1 into `dev`, bounded post-apply review + user merge authorization.
