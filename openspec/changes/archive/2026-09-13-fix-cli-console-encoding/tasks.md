# Tasks: fix-cli-console-encoding (GitHub #161)

> **Change:** `2026-09-13-fix-cli-console-encoding` · **Store:** openspec · **Phase:** `sdd-tasks` ·
> **Language:** English.
> **Inputs (frozen):** `proposal.md`, `design.md`, `specs/process-boundary/spec.md` (PB-02 MODIFIED),
> `specs/cli/spec.md` (CLI-R11 ADDED).
>
> **Ordering note (why the design's order is adjusted, per its own §"Test matrix"):** the design
> lists config → cli → tests → docs. The task list moves the test-writing phase **before** the
> `src/` edits, because the design itself requires a provable RED (`design.md` §"Test matrix",
> "RED before the fix?") and `proposal.md` §"Regression tests" says the parametrized help test
> "turns the suite RED today". Tests written after the fix cannot demonstrate that. Everything else
> keeps the design's dependency order.

---

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | Implementation: **~155-168** (`config.py` ~7, `cli.py` ~30, `tests/test_cli.py` ~110-125, `README.md` + `README_ES.md` ~6). Frozen SDD artifacts counted separately: **~90** change-dir spec deltas (+ this `tasks.md`). Total incl. frozen artifacts ~245-258. |
| 400-line budget risk | **Low** — implementation subtotal is under half the 400-line threshold; no `src/` file beyond `config.py`/`cli.py`; no new module; no migration; no config-format change. |
| Chained PRs recommended | **No** — two production files, one test file, two mirrored doc rows; the 1500-line session review budget is not approached. |
| Suggested split | Single PR (no chain). Rollback is a plain revert of one unit. |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending (not selected; moot — budget risk is Low, so no delivery decision is required at apply) |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low
```

If the apply diff ever exceeds 400 implementation lines (not expected), stop and ask before
continuing — do not silently chain and do not self-grant `size:exception`.

---

## Non-goals — explicit "do not do" lines (apply-phase guard)

- **Do not** normalize the remaining ~58 Metric-A glyph sites to ASCII. `publish.py`, `prepare.py`,
  `profile.py`, `render.py`, `codebook.py`, `_converters.py`, `verification.py`, `checks.py`,
  `scanner.py`, `mcp_server.py`, `mcp_registration.py` keep their glyphs and gain **zero** code.
- **Do not** force UTF-8 mode globally (`PYTHONUTF8`, `sys.flags.utf8_mode`, re-exec).
- **Do not** change any file-output encoding (`config.OUTPUT_ENCODING`, quality report, codebook
  markdown, Dataset Card stay explicit UTF-8).
- **Do not** use `errors="ignore"` anywhere — substitution must stay visible.
- **Do not** add a `[tool.sofer]` option (no `console_errors` key) and **do not** add
  `CONSOLE_ERRORS` to `config._DEFAULTS`.
- **Do not** mutate the user's environment (`PYTHONIOENCODING`, `PYTHONLEGACYWINDOWSSTDIO`, `chcp`).
- **Do not** touch the MCP capture path (`mcp_server.py` is unmodified) and **do not** add the guard
  to `mcp_server.main()`.
- **Do not** swap/replace `sys.stdout` / `sys.stderr` objects — reconfigure in place only.
- **Do not** edit canonical `openspec/specs/**` (that is `sdd-sync`/archive) and **do not** ASCII-fy
  spec prose (`openspec/specs/cli/spec.md:54` keeps its `→`).
- **Do not** add a second subprocess helper — every subprocess test goes through
  `tests/conftest.py::run_cli` (PB-09).
- **Do not** create a new test module (`test_console.py`) or a new production module — the guard is
  an entry-point concern of `cli.py` and lives in `tests/test_cli.py`.
- **Do not** assert a glyph (`"→" in stdout`) anywhere; assert rc + cp1252-encodability + a stable
  ASCII substring.
- **Do not** add unmandated help text (no console-note sentence in `--help`) — beyond the five ASCII
  edits, `help=`/`description=` strings are unchanged.

---

## Phase 0 — Baseline and fact confirmation

- [x] 0.1 Record the green baseline before any edit: `uv run pytest tests/ -q` completes with the repo's documented 1149 passed / 2 skipped (1151 collected) and no failures; save the tail of the output as the RED/GREEN comparison anchor. <!-- sdd-owner: implementation -->
- [x] 0.2 Confirm the two design-open facts in place, without editing anything: (a) `read tests/test_cli.py` around `class TestSubprocessBoundary` confirms `SUBCOMMANDS` is a class-body tuple of the 9 top-level subcommands (in scope for a class-level `@pytest.mark.parametrize`) and `read tests/conftest.py::run_cli` confirms `env=` + `encoding=` with `errors="strict"`; (b) `grep -n "class EncodedFile\|class CaptureIO" .venv/Lib/site-packages/_pytest/capture.py` both report `io.TextIOWrapper` subclasses (so both pytest capture objects DO expose `reconfigure`, and the defensive arms need their own carriers). Record both outputs as evidence. <!-- sdd-owner: implementation -->
- [x] 0.3 Run the informational Windows encoding probe from `design.md` §Q1 on this host: `uv run python -c "import sys; print(sys.stdout.encoding)"` and the same command redirected (`> out.txt`); record both lines in the apply evidence. Informational only — the guard reconfigures whatever encoding the stream already has, so a non-`utf-8`/`cp1252` result changes no task. <!-- sdd-owner: implementation -->

## Phase 1 — Tests (written first, so RED is demonstrable)

- [x] 1.1 `tests/test_cli.py`: add `import io` to the stdlib import block and extend the `sofer` import
      (`from sofer import cli, mcp_registration` → also `config`); confirm the file still imports by
      running `uv run pytest tests/test_cli.py -q --collect-only`, which must collect without error. <!-- sdd-owner: implementation -->
- [x] 1.2 `tests/test_cli.py::TestSubprocessBoundary::test_help_strict_cp1252`: rework the existing
      single-invocation test into a parametrization over all 12 invocations — `["--help"]`,
      `[command, "--help"]` for each entry of `SUBCOMMANDS`, `["mcp", "add", "--help"]`,
      `["mcp", "remove", "--help"]` — keeping the name, the `env={"PYTHONIOENCODING": "cp1252"}` /
      `encoding="cp1252"` call to `run_cli`, `assert result.returncode == 0`, and
      `result.stdout.encode("cp1252")`; add `assert "UnicodeEncodeError" not in result.stderr`.
      Completion signal: `uv run pytest tests/test_cli.py -q --collect-only -k cp1252` reports 12
      collected cases for this test id (T1). <!-- sdd-owner: implementation -->
- [x] 1.3 `tests/test_cli.py::TestSubprocessBoundary`: add
      `test_runtime_output_strict_cp1252` (T2) — `validate` through `run_cli` against a TOML carrying
      configuration errors under the cp1252 env/encoding; assert `rc == 1`,
      `"Configuration errors" in result.stdout`, `result.stdout.encode("cp1252")`, and
      `"UnicodeEncodeError" not in result.stderr`. (Note in the docstring that `rc == 1` is *not* the
      discriminator — a traceback also exits 1; the substring is.) Achievable with an existing
      fixture/or the same TOML shape used by the current `validate` config-error tests. <!-- sdd-owner: implementation -->
- [x] 1.4 `tests/test_cli.py::TestSubprocessBoundary`: add `test_scan_dry_run_strict_cp1252` (T3) —
      a `raw/a.csv` with no `cache/` counterpart, `scan --dry-run` under the cp1252 env/encoding;
      assert `rc == 0` (the discriminator — today it is 1), `"DRY RUN" in result.stdout`,
      `result.stdout.encode("cp1252")`, and no traceback in stderr. <!-- sdd-owner: implementation -->
- [x] 1.5 `tests/test_cli.py::TestSubprocessBoundary`: add
      `test_interpolated_unencodable_value_strict_cp1252` (T4) — `scan <path containing U+2192>`
      (a nonexistent path is the branch under test, so the ASCII literal `Config file not found` is
      emitted with the data-driven value interpolated); assert `rc == 1`,
      `"Config file not found" in result.stderr`, `result.stderr.encode("cp1252")`, and
      `"UnicodeEncodeError" not in result.stderr` (the discriminator — the traceback also echoes the
      ASCII literal). <!-- sdd-owner: implementation -->
- [x] 1.6 `tests/test_cli.py::TestSubprocessBoundary`: add `test_codebook_warning_strict_cp1252`
      (T5) — a TOML registering an existing unsupported-format file (e.g. `notes.txt`) alongside a
      valid entry, run as `codebook --all-files --config <toml>` under the cp1252 env/encoding;
      assert `rc == 0` (the discriminator), the ASCII warning substring in `result.stderr`,
      `result.stderr.encode("cp1252")`, and no traceback. If the entry does not pass the config
      validation step, switch to the directory variant of the same frozen scenario
      (`"Skipping directory"`) — a one-line test change, not a design change. <!-- sdd-owner: implementation -->
- [x] 1.7 `tests/test_cli.py`: add `class TestConsoleEncodingGuard` with the three direct-helper tests
      that pin the rule-14 arms, each monkeypatching **both** `sys.stdout` and `sys.stderr`:
      `test_console_streams_reconfigured_in_place` (T6 — a real `io.TextIOWrapper(BytesIO(), encoding="ascii", errors="strict")`; assert `stream.errors == "replace"` after `cli._configure_console_streams()`, `sys.stdout is stream`, and that writing `"\u2192"` lands in the buffer as `b"?"`), `test_console_guard_skips_stream_without_reconfigure` (T7 — `io.StringIO()`, the exact object `mcp_server._capture_output` installs; assert no raise and identity preserved), `test_console_guard_survives_unreconfigurable_text_wrapper` (T8 — a closed `io.TextIOWrapper`; assert no raise and identity preserved). All three call the private helper directly by name (`cli._configure_console_streams()`). <!-- sdd-owner: implementation -->
- [x] 1.8 Verify the reworked test keeps the PB-02 assertion shape: no test added or edited in
      Phase 1 asserts a glyph — `grep -n '2192\|"[^"]*→[^"]*" in' tests/test_cli.py` returns no hit in any cp1252 or guard test body. <!-- sdd-owner: implementation -->

## Phase 2 — RED evidence (mandatory; the fix is unproven without it)

- [x] 2.1 Run the new/reworked tests on the **unmodified** `src/` tree:
      `uv run pytest tests/test_cli.py -q -k "cp1252 or ConsoleEncodingGuard"` and confirm the
      discriminating failures: `test_help_strict_cp1252[prepare --help]` and
      `test_help_strict_cp1252[scan --help]` fail with `rc == 1` + a `UnicodeEncodeError` traceback;
      T2 fails on the missing `Configuration errors` substring; T3 fails on `rc == 0`; T4 fails on
      `UnicodeEncodeError` present in stderr; T5 fails on `rc == 0`; T6-T8 fail with
      `AttributeError: module 'sofer.cli' has no attribute '_configure_console_streams'`.
      Save the full pytest output as the RED evidence artifact. <!-- sdd-owner: implementation -->
- [x] 2.2 Confirm the RED run's GREEN remainder — the other 10 help invocations and the preserved
      `test_help_exits_zero_and_lists_every_subcommand` / `test_unknown_command_exits_2` pass in the
      same run, so the failures are attributable to cp1252 encoding and not to a broken test.
      Record the pass/fail counts in the same evidence block. <!-- sdd-owner: implementation -->

## Phase 3 — Implementation (`config.py`, `cli.py`)

- [x] 3.1 `src/sofer/config.py`: insert `CONSOLE_ERRORS: str = "replace"` with the design's 5-line
      rationale comment (CLI-R11 / issue #161; deliberately **not** a `_DEFAULTS` entry) immediately
      after `OUTPUT_ENCODING: str = _DEFAULTS["output_encoding"]` and before `PROBE_CHUNK_BYTES`.
      Verify: `grep -n "CONSOLE_ERRORS" src/sofer/config.py` shows exactly the module-level constant,
      and `grep -n "console_errors" src/sofer/config.py` returns nothing (no `_DEFAULTS` key). <!-- sdd-owner: implementation -->
- [x] 3.2 `src/sofer/cli.py`: add `import io` to the stdlib import block, immediately after
      `import argparse`. Verify with `uv run ruff check src/sofer/cli.py`. <!-- sdd-owner: implementation -->
- [x] 3.3 `src/sofer/cli.py`: define `_configure_console_streams() -> None` immediately above
      `main()` (after the parser builder) with the design's full docstring — the loop over
      `(sys.stdout, sys.stderr)`, the `isinstance(stream, io.TextIOWrapper)` gate feeding `continue`,
      and the `try: stream.reconfigure(errors=config.CONSOLE_ERRORS)` / `except (ValueError, OSError):
      continue`. No `# type: ignore`, no pragma, no stream assignment. Verify:
      `uv run mypy src/` reports no new error and `grep -n "type: ignore\|pragma: no cover" src/sofer/cli.py`
      shows no hit on the new lines. <!-- sdd-owner: implementation -->
- [x] 3.4 `src/sofer/cli.py`: wire the guard as the **first body statement of `main()`**, ahead of
      `config.reload(None)` and `_build_parser()`, and add the orchestration step 0 to `main()`'s
      docstring. Verify: `read src/sofer/cli.py` shows the call as the first statement after the
      signature, and `uv run pytest tests/test_cli.py -q -k "help" ` stays green in-process. <!-- sdd-owner: implementation -->
- [x] 3.5 `src/sofer/cli.py`: apply the five ASCII edits (`U+2192` → `->`) at the two `scan` prints
      (`print(f"     → ...")` in the Phase-2 confirm-preview path and the `--dry-run` copy preview)
      and the three argparse `description=` strings (the two `prepare` strings and the `scan` string
      mentioning `raw/DPTO.csv`). Verify: `grep -c "→" src/sofer/cli.py` drops by exactly 5 from the
      baseline, and the remaining hits are comments/docstrings only (`grep -n "→" src/sofer/cli.py`
      inspected line by line). <!-- sdd-owner: implementation -->
- [x] 3.6 Targeted GREEN: `uv run pytest tests/test_cli.py -q -k "cp1252 or ConsoleEncodingGuard"`
      now passes in full (all Phase-1 tests, including T6-T8). This is the direct RED→GREEN proof
      from Phase 2. <!-- sdd-owner: implementation -->

## Phase 4 — TRIANGULATE: full-suite and boundary verification

- [x] 4.1 `uv run pytest tests/ -q` is green with the count from task 0.1 preserved or higher (no
      test removed, none skipped beyond the documented 2) — covers the R6 risk that an ASCII edit
      breaks an existing assertion and the A3 risk that no site is both printed and file-written. <!-- sdd-owner: implementation -->
- [x] 4.2 MCP boundary untouched (R4): `uv run pytest tests/test_mcp_server.py tests/test_mcp_process.py tests/test_mcp_registration.py -q` is green, proving the helper's in-place-only reconfigure disturbs neither `_capture_output` interleaving nor MSP-R01 stdout cleanliness. <!-- sdd-owner: implementation -->
- [x] 4.3 Dogfood the issue's own reproduction on this host: `PYTHONIOENCODING=cp1252 uv run sofer scan --help`
      and `PYTHONIOENCODING=cp1252 uv run sofer prepare --help` both exit 0 with no traceback, and
      `PYTHONIOENCODING=cp1252 uv run sofer validate` against a config-error TOML still exits 1.
      Record the three exit codes as evidence. <!-- sdd-owner: implementation -->
- [x] 4.4 Exit-code invariants observed, not assumed: the `validate` config-error path still returns
      1, `scan --dry-run` returns 0, and the argparse dispatch error path still exits 2
      (`uv run pytest tests/test_cli.py -q -k "unknown_command or dry_run or config_error"`). <!-- sdd-owner: implementation -->

## Phase 5 — Rule 14 coverage (COV-06, zero pragmas)

- [x] 5.1 Walk the design's coverage table against the implemented code and name every new
      line/branch arm with its single carrier: `import io` (import-time), the helper `def` line
      (import-time), the `for` header (every in-process `main()` test, e.g. `test_main_help_prints`),
      the `isinstance` gate **False arm** (`test_console_streams_reconfigured_in_place` + every
      in-process `main()` test), the gate **True arm** + its `continue`
      (`test_console_guard_skips_stream_without_reconfigure`), the `reconfigure(...)` line
      (`test_console_streams_reconfigured_in_place`, asserting `errors == "replace"` **and** the
      `b"?"` substitution), the `except (ValueError, OSError):` line + its `continue`
      (`test_console_guard_survives_unreconfigurable_text_wrapper`), and the `main()` call site
      (`test_main_help_prints` / `test_cli_main_guard_executed_via_runpy`). Any arm with no carrier
      is a defect to fix in Phase 1, not a pragma. <!-- sdd-owner: implementation -->
- [x] 5.2 Rule 14 evidence, run as the scoped gate (not plain pytest):
      `uv run coverage run -m pytest -q` followed by `bash scripts/check_core_coverage.sh` — all four
      per-file rows report `100.00%` (`cli.py`, `scanner.py`, `prepare.py`, `publish.py`) and the
      script exits 0. Save the script output as evidence. <!-- sdd-owner: implementation -->
- [x] 5.3 Zero-pragma proof: `grep -n "pragma: no cover" src/sofer/cli.py src/sofer/scanner.py src/sofer/prepare.py src/sofer/publish.py`
      returns no match. <!-- sdd-owner: implementation -->

## Phase 6 — Docs (rule 13 mirror + rule 7 accuracy)

- [x] 6.1 `README.md`: append one row to the existing `### Windows notes — CWD, placeholders, and
      separators` table (after the `**Path separators**` row, around `:142`) using the design's exact
      EN wording — topic `**Console encoding**`, behaviour described as "a placeholder (or an escape
      sequence)", never promising the specific `?` rendering (R9). Verify:
      `grep -n "Console encoding" README.md` hits once and no new heading is introduced. <!-- sdd-owner: implementation -->
- [x] 6.2 `README_ES.md`: insert the mirrored row at the same table position (after `**Separadores de
      ruta**`, around `:150`) with the design's ES wording — prose translated, technical content in
      English (`PYTHONIOENCODING`, `UnicodeEncodeError`, the `⚠`/`✓`/`✗`/`→` markers). Verify:
      heading set and section order are identical to `README.md`
      (`grep -n "^### " README.md README_ES.md` diff shows the same count/order) and
      `grep -n "Codificación de consola" README_ES.md` hits once. <!-- sdd-owner: implementation -->
- [x] 6.3 Rule 7 accuracy sweep: no parser flag, flag rename or behaviour change was added, so only
      the five ASCII edits change help text — confirm with
      `grep -n "add_argument\|help=" src/sofer/cli.py` showing no help/description edit outside the
      five literals, and confirm `README.md`'s `scan` command-reference row (documenting `-> raw/<rel>`)
      needs no change while its remaining `→` occurrences are pipeline prose (verified, not a CLI
      output sample). <!-- sdd-owner: implementation -->

## Phase 7 — Final gates and traceability

- [x] 7.1 `uv run pytest tests/ -q` green (full suite, post-docs). <!-- sdd-owner: implementation -->
- [x] 7.2 `uv run ruff check src/ tests/` and `uv run ruff format --check src/ tests/` both clean (pre-commit parity). <!-- sdd-owner: implementation -->
- [x] 7.3 `uv run mypy src/` clean, with no new `# type: ignore` and no `unused-ignore` failure (the
      `isinstance` narrowing must satisfy `warn_unused_ignores = true`). <!-- sdd-owner: implementation -->
- [x] 7.4 `uv run coverage run -m pytest -q && bash scripts/check_core_coverage.sh` exits 0 with four
      `100.00%` rows (re-run after the docs phase so the final tree is what was measured). <!-- sdd-owner: implementation -->
- [x] 7.5 `git diff --check` reports no whitespace/conflict-marker problems in the final diff. <!-- sdd-owner: implementation -->
- [x] 7.6 Scope audit: `git status --porcelain` lists only `src/sofer/config.py`, `src/sofer/cli.py`,
      `tests/test_cli.py`, `README.md`, `README_ES.md` (plus the frozen `openspec/changes/**`
      artifacts) — any other `src/` or canonical-spec path is a scope violation to revert. <!-- sdd-owner: implementation -->
- [x] 7.7 Traceability matrix complete: all 7 frozen scenarios have a named passing test — PB-02
      *Help via subprocess* → `test_help_exits_zero_and_lists_every_subcommand`; PB-02 *cp1252 help on
      the ubuntu matrix* → reworked `test_help_strict_cp1252` (12 cases); PB-02 *cp1252 runtime console
      output* → T2 + T3; PB-02 *Dispatch exit codes* → `test_unknown_command_exits_2`; CLI-R11
      *Runtime output with an unencodable character keeps the command's result* → T2 (shared); CLI-R11
      *ASCII literal with an unencodable interpolated value does not abort* → T4; CLI-R11 *Console
      warning path carrying a glyph degrades instead of aborting* → T5. Record the mapping with the
      final per-test outcomes. <!-- sdd-owner: implementation -->

## Phase 8 — Parent lifecycle gate (post-apply, before archive)

- [x] 8.1 Start or reuse the bounded review over the finalized diff (single PR, no chaining), confirming: guard is the first statement of `main()`, no stream swapping, no `_DEFAULTS` entry, no pragma, no glyph assertion, and the docs row mirrored in both READMEs. <!-- sdd-owner: parent -->
- [x] 8.2 Decide accept vs. rollback as one unit and trigger the archive/sync step so the frozen PB-02 and CLI-R11 deltas land in the canonical specs; do not hand-edit `openspec/specs/**` in this change. <!-- sdd-owner: parent -->
