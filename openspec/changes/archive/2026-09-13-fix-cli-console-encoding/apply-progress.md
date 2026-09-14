# Apply progress: fix-cli-console-encoding (GitHub #161)

> **Change:** `2026-09-13-fix-cli-console-encoding` · **Store:** openspec · **Phase:** `sdd-apply` ·
> **Language:** English.
> **Inputs read:** `tasks.md`, `design.md`, `specs/process-boundary/spec.md`, `specs/cli/spec.md`,
> `proposal.md`, `openspec/config.yaml`, `AGENTS.md` rules 1/2/6/7/13/14.
> **Strict TDD:** not active (`openspec/config.yaml` `strict_tdd: false`); the tasks artifact's own
> ordering (tests first, so RED is demonstrable) was followed.

---

## Checkbox status (persisted artifact)

| Phase | Rows | State |
|---|---|---|
| 0 — Baseline and fact confirmation | 0.1–0.3 | `- [x]` (3/3) |
| 1 — Tests written first | 1.1–1.8 | `- [x]` (8/8) |
| 2 — RED evidence | 2.1–2.2 | `- [x]` (2/2), with a recorded deviation on the T4/T5 expectations |
| 3 — Implementation | 3.1–3.6 | `- [x]` (6/6) |
| 4 — TRIANGULATE | 4.1–4.4 | `- [x]` (4/4), with a recorded pre-existing MCP-selection failure |
| 5 — Rule 14 coverage | 5.1–5.3 | `- [x]` (3/3) |
| 6 — Docs | 6.1–6.3 | `- [x]` (3/3) |
| 7 — Final gates | 7.1–7.7 | `- [x]` (7/7) |
| 8 — Parent lifecycle | 8.1–8.2 | `- [ ]` (0/2) — parent-owned, untouched byte-for-byte |

`openspec/changes/2026-09-13-fix-cli-console-encoding/tasks.md` now shows **36 `- [x]` implementation
rows and 2 `- [ ]` parent rows** (verified by re-reading the persisted file). No parent-owned row was
modified; no second subprocess helper was added (`tests/conftest.py` untouched, PB-09).

---

## Phase 0 — Baseline and fact confirmation

### 0.1 Green baseline (before any edit)

```text
$ uv run pytest tests/ -q
1747 passed, 6 skipped, 14 warnings in 46.81s
```

**Deviation (documented, not silent):** `tasks.md` 0.1 and `AGENTS.md` document the baseline as
"1149 passed / 2 skipped (1151 collected)". The actual baseline on this tree is **1747 passed /
6 skipped (1753 collected)**. The tasks artifact's real invariant — "no failures, and the count is
preserved or higher afterwards" — was applied; the stale documented count is a doc-drift finding,
not a regression caused by this change (the pre-edit run above was taken before any file was
touched).

### 0.2 Design-open facts confirmed in place

- (a) `tests/test_cli.py::TestSubprocessBoundary` declares `SUBCOMMANDS = ("init", "scan",
  "validate", "prepare", "publish", "codebook", "profile", "render", "mcp")` as a **class-body**
  tuple, so it is in scope for a class-level `@_pytest.mark.parametrize`. `tests/conftest.py::run_cli`
  takes `env: dict[str, str] | None`, `encoding: str = "utf-8"` and calls `subprocess.run(...,
  text=True, encoding=encoding, errors="strict", ...)` — the cp1252 boundary is already expressible,
  no helper change needed.
- (b) `grep -n "class EncodedFile\|class CaptureIO" .venv/Lib/site-packages/_pytest/capture.py`:

  ```text
  186:class EncodedFile(io.TextIOWrapper):
  203:class CaptureIO(io.TextIOWrapper):
  ```

  Both pytest capture objects **do** expose `reconfigure`, so — as the design concluded — the
  defensive no-`reconfigure` arm and the refusing-wrapper arm are **not** free coverage and were
  carried by dedicated `io.StringIO` / closed-`TextIOWrapper` tests (T7/T8).

### 0.3 Informational Windows encoding probe (design §Q1)

```text
$ uv run python -c "import sys; print(sys.stdout.encoding)"              # console  -> cp1252
$ uv run python -c "import sys; print(sys.stdout.encoding)" > out.txt    # redirect -> cp1252
```

Both report `cp1252` on this host (the harness pipes stdout, so the "console" case is also a
redirect here). Informational only: the guard reconfigures whatever encoding the stream already
carries; no task changed. Additionally confirmed the stream error handlers under the regression
env:

```text
$ PYTHONIOENCODING=cp1252 uv run python -c "import sys; print('stdout', sys.stdout.encoding, sys.stdout.errors); print('stderr', sys.stderr.encoding, sys.stderr.errors)"
stdout cp1252 strict
stderr cp1252 backslashreplace
```

This fact is the root cause of the Phase-2 deviation recorded below.

---

## Phase 1 — Tests written before the `src/` edits

Files: `tests/test_cli.py` only.

- **1.1** `import io` added to the stdlib block; `from sofer import cli, mcp_registration` extended to
  `from sofer import cli, config, mcp_registration`. Collection check: `uv run pytest
  tests/test_cli.py -q --collect-only` collected **165** tests with no import error.
- **1.2** `test_help_strict_cp1252` reworked into a class-level parametrization over the 12 PB-02
  invocations (kept its name, its `env={"PYTHONIOENCODING": "cp1252"}` / `encoding="cp1252"` call,
  `rc == 0`, and `result.stdout.encode("cp1252")`, and gained
  `assert "UnicodeEncodeError" not in result.stderr`). Completion signal verified:

  ```text
  $ uv run pytest tests/test_cli.py -q --collect-only -k cp1252
  tests/test_cli.py::TestSubprocessBoundary::test_help_strict_cp1252[argv0]   ... [argv11]
  tests/test_cli.py::TestSubprocessBoundary::test_runtime_output_strict_cp1252
  tests/test_cli.py::TestSubprocessBoundary::test_scan_dry_run_strict_cp1252
  tests/test_cli.py::TestSubprocessBoundary::test_interpolated_unencodable_value_strict_cp1252
  tests/test_cli.py::TestSubprocessBoundary::test_codebook_warning_strict_cp1252
  16/165 tests collected (149 deselected)
  ```

  12 of the 16 are the T1 parametrization.
- **1.3** T2 `test_runtime_output_strict_cp1252` — `validate` against a `YOUR_USER` placeholder TOML
  (`rc == 1`, `"Configuration errors" in result.stdout`, `stdout.encode("cp1252")`, no traceback).
  Docstring records that `rc == 1` is **not** the discriminator.
- **1.4** T3 `test_scan_dry_run_strict_cp1252` — `raw/a.csv` with no `cache/` counterpart, `rc == 0`,
  `"DRY RUN" in result.stdout`, `stdout.encode("cp1252")`, no traceback.
- **1.5** T4 `test_interpolated_unencodable_value_strict_cp1252` — `scan <path containing U+2192>`
  (nonexistent path), `rc == 1`, `"Config file not found" in result.stderr`,
  `stderr.encode("cp1252")`, no traceback.
- **1.6** T5 `test_codebook_warning_strict_cp1252` — TOML registering an existing unsupported-format
  file (`notes.txt`) beside a valid `data.csv`; `codebook --all-files --config dataset.toml`,
  `rc == 0`, `"Unsupported format" in result.stderr`, `stderr.encode("cp1252")`, no traceback. The
  file variant passed `DatasetConfig.validate()` as the design assumed (assumption A2 confirmed);
  the `Skipping directory` fallback was **not** needed.
- **1.7** `class TestConsoleEncodingGuard` (module-level, 3 tests) —
  `test_console_streams_reconfigured_in_place` (T6: real `io.TextIOWrapper(BytesIO(),
  encoding="ascii", errors="strict")` patched on both streams; asserts `config.CONSOLE_ERRORS ==
  "replace"`, `stream.errors == "replace"`, stream identity, and that writing `"\u2192"` lands in the
  buffer as `b"?"`), `test_console_guard_skips_stream_without_reconfigure` (T7: `io.StringIO`, the
  exact `mcp_server._capture_output` object), and
  `test_console_guard_survives_unreconfigurable_text_wrapper` (T8: closed `TextIOWrapper`). All three
  call the private helper by name.
- **1.8** No glyph assertion was introduced. `grep -n '2192\|"[^"]*→[^"]*" in' tests/test_cli.py`
  returns four hits, all non-assertion: three docstring prose lines (`:1340`, `:1367`, `:1562`) and
  the T4 fixture path literal (`:1373`, `tmp_path / "missing\u2192dataset.toml"`) which the frozen
  CLI-R11 scenario requires. `grep -n '→' tests/test_cli.py` finds only three pre-existing
  docstrings (`:769`, `:804`, `:894`); the guard test writes the arrow as the ASCII source escape
  `"\u2192"`.

---

## Phase 2 — RED evidence (recorded before any `src/` edit)

Command on the **unmodified** `src/` tree:

```text
$ uv run pytest tests/test_cli.py -q -k "cp1252 or ConsoleEncodingGuard" -p no:randomly
7 failed, 12 passed, 146 deselected in 11.52s
```

Discriminating failures (exact pytest output):

```text
FAILED tests/test_cli.py::TestSubprocessBoundary::test_help_strict_cp1252[argv2]   # scan --help
FAILED tests/test_cli.py::TestSubprocessBoundary::test_help_strict_cp1252[argv4]   # prepare --help
FAILED tests/test_cli.py::TestSubprocessBoundary::test_runtime_output_strict_cp1252
FAILED tests/test_cli.py::TestSubprocessBoundary::test_scan_dry_run_strict_cp1252
FAILED tests/test_cli.py::TestConsoleEncodingGuard::test_console_streams_reconfigured_in_place
FAILED tests/test_cli.py::TestConsoleEncodingGuard::test_console_guard_skips_stream_without_reconfigure
FAILED tests/test_cli.py::TestConsoleEncodingGuard::test_console_guard_survives_unreconfigurable_text_wrapper
```

Per-test reason (captured with HEAD's `src/sofer/cli.py` restored read-only via `git show`, then
restored again — no git write command was run):

- T1 `argv2` / `argv4` (`scan --help`, `prepare --help`): `rc == 1` with a `UnicodeEncodeError`
  traceback (`cli.py:1072/1073/1429` subparser `description=` strings).
- T2 (T2's own RED, re-run against HEAD src):

  ```text
  >       assert "Configuration errors" in result.stdout
  E       AssertionError: assert 'Configuration errors' in ''
  E       ...codeEncodeError: 'charmap' codec can't encode character '\u2717' in position 4
  ```

  i.e. stdout empty, `rc == 1`, the `✗` write aborts before the report.
- T3:

  ```text
  E       AssertionError: Traceback (most recent call last):
  E           File ".../src/sofer/cli.py", line 569, in _cmd_scan
  E             print(f"     \u2192 {dest.relative_to(base_dir).as_posix()}")
  E         UnicodeEncodeError: 'charmap' codec can't encode character '\u2192' in position 5
  E       assert 1 == 0
  ```

  i.e. `rc == 1` today (the discriminator), the `DRY RUN` line already printed.
- T6–T8: `AttributeError: module 'sofer.cli' has no attribute '_configure_console_streams'`.

### 2.1 / 2.2 deviation — T4 and T5 are **not** RED, and why

`test_interpolated_unencodable_value_strict_cp1252` (T4) and `test_codebook_warning_strict_cp1252`
(T5) **passed pre-fix** (they are 2 of the 12 passes above). Root cause, evidence-captured in 0.3:
CPython gives `sys.stderr` the default error handler **`backslashreplace`**, so with
`PYTHONIOENCODING=cp1252` the child's stderr already substitutes `→` / `⚠` as `\u2192` / `\u26a0`
instead of raising. Both tests therefore exercise a path that was already safe on this Python, and
the design's "RED before the fix?" column for T4/T5 is **falsified by the interpreter, not by the
test**.

Minimal, honest resolution: the two tests were **kept exactly as the frozen scenarios prescribe**
(they are required by CLI-R11's scenarios 2 and 3 and by PB-02's requirement to cover runtime
console paths), and no assertion of a specific substitution rendering was added — the spec leaves
`?` vs an escape sequence open, and asserting either would over-constrain the contract. Their value
is regression protection for the stderr half of the guard (a stream that *is* strict — e.g. a
caller-set `PYTHONIOENCODING=cp1252:strict`, or any future code that prints to a strict stream) plus
the rc/encodability/ASCII-substring contract. The RED discriminators for this change are T1, T2,
T3 and T6–T8, all of which failed as the design predicted.

### GREEN remainder in the RED run

The 12 passes were the 10 other help invocations (`--help`, `init`, `validate`, `publish`,
`codebook`, `profile`, `render`, `mcp`, `mcp add`, `mcp remove`), T4 and T5 — so the failures are
attributable to cp1252 encoding, not to a broken test. `test_help_exits_zero_and_lists_every_subcommand`
and `test_unknown_command_exits_2` were not in the `-k` selection; both were confirmed PASSED in the
Phase-7 traceability run and in the full suite.

---

## Phase 3 — Implementation

| File | Change | Rationale |
|---|---|---|
| `src/sofer/config.py` (+7) | `CONSOLE_ERRORS: str = "replace"` + the design's 5-line rationale comment, inserted between `OUTPUT_ENCODING` (line 354) and `PROBE_CHUNK_BYTES`, **outside `_DEFAULTS`** | AGENTS.md rule 1 (no literal in a function body) by location, no new `[tool.sofer]` surface (D3). `_read_tool_section` iterates `_DEFAULTS`, so `reload()` can never rebind it. |
| `src/sofer/cli.py` (+44/−5) | (1) `import io` after `import argparse`; (2) `_configure_console_streams() -> None` immediately above `main()` with the design's docstring — `isinstance(stream, io.TextIOWrapper)` gate feeding `continue`, `stream.reconfigure(errors=config.CONSOLE_ERRORS)` inside `try/except (ValueError, OSError): continue`, no assignment to `sys.stdout`/`sys.stderr`, no `# type: ignore`, no pragma; (3) the call as the **first body statement of `main()`**, ahead of `config.reload(None)`; (4) `main()` docstring orchestration step 0; (5) the five `U+2192` → `->` edits at `:549`, `:569` (the two `scan` prints) and the three `prepare`/`scan` argparse `description=` strings | Fixes the crash class for authored *and* interpolated text; guard placement covers argparse's help write and tracebacks; in-place reconfigure preserves stream identity (MSP-R01). |
| `tests/test_cli.py` (+200/−5) | Phase-1 matrix (T1 rework + T2–T5 + `TestConsoleEncodingGuard` T6–T8), `import io`, `config` import | Every frozen scenario gets a test (rule 6); rule-14 arms get deterministic carriers independent of pytest's capture internals. |

Task-3 verifications:

```text
$ grep -n "CONSOLE_ERRORS" src/sofer/config.py
361:CONSOLE_ERRORS: str = "replace"

$ grep -n '"console_errors"' src/sofer/config.py        # no _DEFAULTS key
(no match — the phrase appears only inside the rationale comment)

$ git show HEAD:src/sofer/cli.py | grep -c '→'   -> 20
$ grep -c '→' src/sofer/cli.py                   -> 15   (exactly -5)
```

The 15 remaining `→` lines are comments/module & function docstrings only (`:120`, `:399`, `:416`,
`:420`, `:454`, `:520`, `:624`–`:629`, `:746`–`:749`) — none is emitted text.

### 3.6 Targeted GREEN (RED → GREEN proof)

```text
$ uv run pytest tests/test_cli.py -q -k "cp1252 or ConsoleEncodingGuard" -p no:randomly
19 passed, 146 deselected in 8.89s
```

(7 failed + 12 passed before → 19 passed after.)

---

## Phase 4 — TRIANGULATE

- **4.1** Full suite, post-implementation and again post-docs on the final tree:

  ```text
  $ uv run pytest tests/ -q
  1765 passed, 6 skipped, 14 warnings  (1771 collected)
  ```

  Baseline was 1747 passed / 6 skipped (1753 collected); the delta is **+18**, exactly the 11 extra
  T1 parametrizations + T2–T5 (4) + T6–T8 (3). No test was removed and no new skip was introduced.
- **4.2 MCP boundary** — **deviation (pre-existing, not caused by this change).** The three-file
  selection is **not** fully green:

  ```text
  $ uv run pytest tests/test_mcp_server.py tests/test_mcp_process.py tests/test_mcp_registration.py -q
  1 failed, 323 passed, 3 skipped
  FAILED tests/test_mcp_registration.py::TestMerge::test_codex_normalize_string_vs_array
  ```

  The same test passes in isolation (`1 passed`), fails only in that selection (order-dependent),
  and the **same failure reproduces with HEAD's `src/sofer/cli.py` and `src/sofer/config.py`
  restored** (`1 failed, 323 passed, 3 skipped`) — proven pre-existing and independent of this
  change. The full suite (`tests/ -q`), which also runs this test, is green. The change adds no
  assignment to `sys.stdout`/`sys.stderr` (T6–T8 assert identity), so `_capture_output` interleaving
  and MSP-R01 framing are untouched.
- **4.3 Dogfood (issue reproduction) on this host:**

  ```text
  $ PYTHONIOENCODING=cp1252 uv run sofer scan --help      -> rc 0, no UnicodeEncodeError
  $ PYTHONIOENCODING=cp1252 uv run sofer prepare --help   -> rc 0, no UnicodeEncodeError
  $ PYTHONIOENCODING=cp1252 uv run sofer validate <config-error TOML> -> rc 1
  ```

  The `validate` run printed `Configuration errors` in stdout, no `UnicodeEncodeError` in stderr,
  and rendered the substitution on this cp1252 host as a placeholder (`?  Configuration errors ? fix
  before checking:`) — the spec's deliberately-open rendering; no test asserts it.
- **4.4 Exit-code invariants:**

  ```text
  $ uv run pytest tests/test_cli.py -q -k "unknown_command or dry_run or config_error"
  14 passed, 151 deselected in 2.01s
  ```

---

## Phase 5 — Rule 14 coverage (COV-06, zero pragmas)

### 5.1 Coverage-table walk (every new/changed line and arm with its carrier)

| Line / arm | Carrier |
|---|---|
| `config.py` `CONSOLE_ERRORS` | executed at import of `sofer.config` by any test |
| `cli.py` `import io`, helper `def` line | import-time |
| `for stream in (sys.stdout, sys.stderr):` | every in-process `main()` test (`test_main_help_prints`, `test_cli_main_guard_executed_via_runpy`) and every guard test |
| `isinstance` gate **False** arm | `test_console_streams_reconfigured_in_place` + all in-process `main()` tests (pytest fd capture installs `EncodedFile`, a `TextIOWrapper`) |
| `isinstance` gate **True** arm + its `continue` | `test_console_guard_skips_stream_without_reconfigure` (`io.StringIO`) |
| `stream.reconfigure(errors=config.CONSOLE_ERRORS)` | `test_console_streams_reconfigured_in_place` (asserts `errors == "replace"` **and** the `b"?"` substitution) |
| `except (ValueError, OSError):` + its `continue` | `test_console_guard_survives_unreconfigurable_text_wrapper` (closed wrapper → `ValueError`) |
| `_configure_console_streams()` call in `main()` | `test_main_help_prints`, `test_cli_main_guard_executed_via_runpy`, plus the new subprocess tests |
| five edited literals | existing carriers unchanged (string constants only) |

No arm lacked a carrier, so no pragma was needed.

### 5.2 / 7.4 Scoped gate (final tree)

```text
$ uv run coverage run -m pytest -q
1765 passed, 6 skipped, 14 warnings in 69.15s

$ bash scripts/check_core_coverage.sh
Name                   Stmts   Miss Branch BrPart  Cover   Missing
src\sofer\cli.py         574      0    166      0   100%
src\sofer\scanner.py     159      0     76      0   100%
src\sofer\prepare.py     432      0    226      0   100%
src\sofer\publish.py     326      0    138      0   100%
gate rc=0
```

All four gated rows are **100.00%**, and `BrPart 0` on `cli.py` proves both arms of the `isinstance`
gate and both `continue` arms executed.

### 5.3 Zero-pragma proof

```text
$ grep -n "pragma: no cover" src/sofer/cli.py src/sofer/scanner.py src/sofer/prepare.py src/sofer/publish.py
(no match; grep rc=1)
```

---

## Phase 6 — Docs (rule 13 mirror + rule 7 accuracy)

| File | Change | Rationale |
|---|---|---|
| `README.md` (+1) | one row appended to the existing `### Windows notes — CWD, placeholders, and separators` table (line 143, directly after `**Path separators**`) — topic `**Console encoding**`, behaviour stated as "written as a placeholder (or an escape sequence)" | The section already owns platform/console plumbing and is mirrored 1:1; no new heading, no TOC change. Wording deliberately does not promise the specific `?` rendering (R9). |
| `README_ES.md` (+1) | the mirrored row at the same table position (line 151, after `**Separadores de ruta**`), prose translated, technical content English (`PYTHONIOENCODING`, `UnicodeEncodeError`, the `⚠`/`✓`/`✗`/`→` markers) | Rule 13. |

Verification:

```text
$ grep -c '^### ' README.md README_ES.md          -> 17 / 17   (same count, same order)
$ grep -c "Console encoding" README.md            -> 1
$ grep -c "Codificación de consola" README_ES.md  -> 1
```

Note on the task's wording: the `grep -n "^### " README.md README_ES.md` diff cannot be *textually*
identical because the headings are translated — parity was verified as heading **count and order**
(17/17, same positions), which is what rule 13 requires; my change introduced no heading.

**6.3 Rule 7 accuracy sweep.** No parser flag, rename or behaviour change was added, so the only
help-text edits are the five ASCII literals — proven by `git diff src/sofer/cli.py`, whose only
`description=`/`help=` hunks are those five lines. `README.md`'s `scan` command-reference row
(line 321) already documents `--dry-run` printing `-> raw/<rel>` (the MOVE phase) and needs no
change; its remaining `→` occurrences are pipeline prose (`raw/DPTO.csv` → `cache/DPTO.csv`,
lines 243/291/320/…), not CLI output samples. The five edits move emitted text *toward* the
documented ASCII form.

---

## Phase 7 — Final gates (final tree)

| Gate | Command | Result |
|---|---|---|
| 7.1 | `uv run pytest tests/ -q` | `1765 passed, 6 skipped` (1771 collected) |
| 7.2 | `uv run ruff check src/ tests/` | `All checks passed!` |
| 7.2 | `uv run ruff format --check src/sofer/cli.py src/sofer/config.py tests/test_cli.py` | `3 files already formatted` — **deviation below** on the repo-wide check |
| 7.3 | `uv run mypy src/` | `Success: no issues found in 32 source files` (no new `# type: ignore`; `warn_unused_ignores` satisfied by the `isinstance` narrowing) |
| 7.4 | `uv run coverage run -m pytest -q` + `bash scripts/check_core_coverage.sh` | four `100%` rows, `gate rc=0` |
| 7.5 | `git diff --check` | `rc=0` — no whitespace errors, no conflict markers |
| 7.6 | `git status --porcelain` | only `README.md`, `README_ES.md`, `src/sofer/cli.py`, `src/sofer/config.py`, `tests/test_cli.py` modified + the untracked change dir |

**7.2 deviation (pre-existing):** the repo-wide `uv run ruff format --check src/ tests/` reports
`6 files would be reformatted, 61 files already formatted`. The six are
`tests/test_ci_workflows.py`, `tests/test_coverage_contract.py`, `tests/test_mcp_registration.py`,
`tests/test_profile.py`, `tests/test_publish.py`, `tests/test_splits.py` — **none touched by this
change** (the three files this change edited are all "already formatted"), so this is pre-existing
drift under ruff 0.16.0, not a regression. Per the task's own scope rule, unrelated files were not
reformatted.

**7.6 scope audit:** `git diff --numstat` = `README.md 1/0`, `README_ES.md 1/0`,
`src/sofer/cli.py 44/5`, `src/sofer/config.py 7/0`, `tests/test_cli.py 200/5` → **263 changed lines**
(253 insertions, 10 deletions). No `src/sofer/` file outside `config.py`/`cli.py`, no other change
directory, no `tests/conftest.py`, no canonical `openspec/specs/**`.

**Workload / PR boundary:** 263 implementation lines, comfortably under the 400-line threshold and
the 1500-line session budget → the tasks' `400-line budget risk: Low`, `Chained PRs recommended: No`,
`Decision needed before apply: No` forecast is **confirmed**; single PR, no chain, no
`size:exception`.

### 7.7 Traceability matrix (final per-test outcomes)

```text
$ uv run pytest tests/test_cli.py -v -p no:randomly -k "help_exits_zero and not cp1252 or cp1252 or ConsoleEncodingGuard or unknown_command"
21 passed, 144 deselected in 10.54s
```

| Frozen scenario | Test | Outcome |
|---|---|---|
| PB-02 *Help via subprocess* | `test_help_exits_zero_and_lists_every_subcommand` | PASSED |
| PB-02 *cp1252 help on the ubuntu matrix* (all 12 invocations) | `test_help_strict_cp1252[argv0..argv11]` | 12 × PASSED |
| PB-02 *cp1252 runtime console output* (validate half) | `test_runtime_output_strict_cp1252` | PASSED |
| PB-02 *cp1252 runtime console output* (scan --dry-run half) | `test_scan_dry_run_strict_cp1252` | PASSED |
| PB-02 *Dispatch exit codes* | `test_unknown_command_exits_2` | PASSED |
| CLI-R11 *Runtime output with an unencodable character keeps the command's result* | `test_runtime_output_strict_cp1252` (shared) | PASSED |
| CLI-R11 *ASCII literal with an unencodable interpolated value does not abort* | `test_interpolated_unencodable_value_strict_cp1252` | PASSED |
| CLI-R11 *Console warning path carrying a glyph degrades instead of aborting* | `test_codebook_warning_strict_cp1252` | PASSED |
| CLI-R11 normative clause, rule-14 arms | `TestConsoleEncodingGuard::test_console_streams_reconfigured_in_place` / `…skips_stream_without_reconfigure` / `…survives_unreconfigurable_text_wrapper` | 3 × PASSED |

All 7 frozen scenarios have a named, passing test (AGENTS.md rule 6).

---

## Deviations and surprises (summary)

1. **Baseline count drift (task 0.1).** Documented 1149 / 2 skipped; actual 1747 / 6 skipped. The
   "count preserved or higher" invariant was applied.
2. **T4 and T5 are not RED (tasks 2.1, 2.2, 1.5, 1.6).** `PYTHONIOENCODING=cp1252` makes *stderr*
   `backslashreplace` in CPython, so those two paths were already non-crashing. Tests kept verbatim
   per the frozen scenarios; no rendering assertion added (R9 preserved). Evidence recorded in 0.3
   and in the RED section.
3. **MCP three-file selection has one pre-existing, order-dependent failure (task 4.2).**
   `test_codex_normalize_string_vs_array` fails in that selection and passes alone; the identical
   failure reproduces against HEAD's `src/`, so it is not caused by this change. The full suite is
   green.
4. **Repo-wide `ruff format --check` is red on six untouched files (task 7.2).** Pre-existing; the
   three files this change edited are formatted.
5. **T5 used the file variant, not the directory fallback** — assumption A2 held
   (`DatasetConfig.validate()` only checks existence), so no test change was needed.
6. **Two pi-lens advisories on pre-existing lines** were surfaced while editing: `import tomli as
   _tomli` (the `tomllib` fallback, `config.py`/`cli.py`) and `shutil.move` / `merged[key] = float(val)`
   (defensive calls). All verified identical at `HEAD` and untouched by this diff — no action taken
   (out of scope, and rule 14 forbids new pragmas/suppressions).

## Remaining work

- **Parent-owned (deferred):** 8.1 bounded review of the finalized diff, 8.2 accept-vs-rollback and
  the archive/sync step (frozen PB-02 + CLI-R11 deltas must land in `openspec/specs/**` there, never
  hand-edited here).
- No implementation task remains unchecked.

---

## V-01 closure

> **Follow-up only.** The parent rejected the `sdd-verify` finding `V-01` as a follow-up and closed
> it now, test-only. **Allowed surfaces:** `tests/test_cli.py` + this file. `src/**`, `README*`,
> `openspec/specs/**`, `tasks.md`, `verify-report.md`, `tests/conftest.py` and the frozen deltas were
> **not** touched. No git write command was run.

### Clause covered

`CLI-R11` scenario 2 (*ASCII literal with an unencodable interpolated value does not abort*), **stdout
clause**: *“AND stdout SHALL strict-decode as cp1252 with the ASCII literal substring present”*. The
pre-existing `test_interpolated_unencodable_value_strict_cp1252` asserts the **stderr** half on the
`scan <missing path>` **argv** vector; it does not exercise an interpolated value on **stdout**.

### Vector chosen (and why it matches the frozen wording)

**One new test:** `tests/test_cli.py::TestSubprocessBoundary::test_interpolated_stdout_value_strict_cp1252`.

A dataset TOML declares `[[file]] local = "data→.csv"` (the `U+2192` written as the ASCII source
escape `"\u2192"`, never a glyph literal), the file `data→.csv` is present loose in the dataset dir,
and `scan dataset.toml --dry-run` previews the MOVE phase:

```text
  DRY RUN  Would move the following files:
     -> raw/data?.csv
```

The line is an **ASCII literal** (`DRY RUN` header + `-> raw/`) plus an **interpolated value** —
`rel.as_posix()` = the declared local path — that cp1252 cannot represent. This matches scenario 2's
own example *“a declared local path, whose name contains such a character”*, is the **TOML-driven**
vector the delta's information table names (not the argv vector verify flagged), rides the forbidden
`run_cli(..., env={"PYTHONIOENCODING": "cp1252"}, encoding="cp1252")` boundary (PB-09, `errors="strict"`),
and asserts **rc 0 + the ASCII substring + `stdout.encode("cp1252")` + no traceback** — no glyph and
no substitution rendering (R9 preserved). It is deliberately **not** a rerun of the authored-glyph
case: HEAD's MOVE-preview literal was already ASCII `->` (only `cli.py:549`/`:569` carried the `→`
authored glyph), so the only unencodable character on this stdout path is the **interpolated** value.

### RED evidence (HEAD's `src/`, empirically reproduced the way `sdd-verify` did)

Scratch package outside the repo (no git write): copy the working `src/sofer` tree, then overwrite
`cli.py` and `config.py` with `git show HEAD:…`.

```text
$ mkdir -p /tmp/v01-head && cp -r src/sofer /tmp/v01-head/sofer
$ git show HEAD:src/sofer/cli.py    > /tmp/v01-head/sofer/cli.py      # CONSOLE_ERRORS count 0
$ git show HEAD:src/sofer/config.py > /tmp/v01-head/sofer/config.py   # _configure_console_streams count 0
$ grep -n 'print(f"     -> raw/' /tmp/v01-head/sofer/cli.py
474:                print(f"     -> raw/{rel.as_posix()}")          # ASCII literal in HEAD

$ PYTHONPATH=/tmp/v01-head uv run pytest \
      "tests/test_cli.py::TestSubprocessBoundary::test_interpolated_stdout_value_strict_cp1252" \
      -q -p no:randomly --tb=long
FAILED tests/test_cli.py::TestSubprocessBoundary::test_interpolated_stdout_value_strict_cp1252
1 failed in 1.35s

E       AssertionError: Traceback (most recent call last):
E         File ".../v01-head/sofer/cli.py", line 1575, in <module>
E           main()
E         File ".../v01-head/sofer/cli.py", line 474, in _cmd_scan
E           print(f"     -> raw/{rel.as_posix()}")
E         File ".../cp1252.py", line 19, in encode
E           return codecs.charmap_encode(input,self.errors,encoding_table)[0]
E       UnicodeEncodeError: 'charmap' codec can't encode character '\u2192' in position 16: character maps to <undefined>
E       assert 1 == 0
```

**Discriminator is genuine and isolates the *interpolation* clause:** the crash site is the ASCII
literal `-> raw/` with the interpolated `rel` path carrying `U+2192` at position 16 — not a
program-authored glyph. Pre-fix the command exits `rc 1`; the `DRY RUN` header is written before the
offending write, so the ASCII-substring assertion alone would pass pre-fix and `rc == 0` is the real
discriminator. Re-run after `ruff format`: same failure (1 failed in 0.99s).

### GREEN evidence

```text
$ uv run pytest "tests/test_cli.py::TestSubprocessBoundary::test_interpolated_stdout_value_strict_cp1252" -q -p no:randomly
1 passed in 1.68s

$ uv run pytest tests/test_cli.py -q -k cp1252 -p no:randomly
17 passed, 149 deselected in 9.35s          # was 16 before this test (12 help params + T2–T5)

$ uv run pytest tests/test_cli.py --collect-only -q
166 tests collected in 0.26s                # was 165

$ uv run pytest tests/ -q
1766 passed, 6 skipped, 14 warnings in 54.87s   # was 1765 passed / 6 skipped — exactly +1
```

### Rule 14 coverage (must not move — proven)

```text
$ uv run coverage run -m pytest -q
1766 passed, 6 skipped, 14 warnings in 70.04s (0:01:10)

$ bash scripts/check_core_coverage.sh        # gate rc=0
src\sofer\cli.py         574      0    166      0   100%
src\sofer\scanner.py     159      0     76      0   100%
src\sofer\prepare.py     432      0    226      0   100%
src\sofer\publish.py     326      0    138      0   100%

$ grep -n "pragma: no cover" src/sofer/{cli,scanner,prepare,publish}.py   # (no match)
```

A test-only change moved none of the four gated rows: all remain **100.00%**, `Miss 0`, `BrPart 0`,
**zero** pragmas.

### Other gates

| Gate | Command | Result |
|---|---|---|
| Lint | `uv run ruff check src/ tests/` | `All checks passed!` |
| Format (touched file) | `uv run ruff format --check tests/test_cli.py` | `1 file already formatted` |
| Types | `uv run mypy src/` | `Success: no issues found in 32 source files` |
| Whitespace | `git diff --check` | `rc=0` |
| Scope | `git status --porcelain` / `git diff --numstat` | only `tests/test_cli.py` changed by this follow-up (`237/5`; was `200/5`) — `+37` lines, no `src/`, no `README*`, no `tests/conftest.py` |

### Persisted tasks artifact (no row changed)

`tasks.md` is outside this work unit's allowed edit surfaces and remains byte-for-byte untouched:
**36/36 implementation rows `- [x]`**, the two `sdd-owner: parent` rows (8.1, 8.2) still `- [ ]`. The
follow-up added **no new task row**, so there is no checkbox to flip; the native status already reads
`36/36` complete.

### Deviations

1. **`ruff format` applied to the new block** (`tests/test_cli.py` only). The first paste used an
   8-space continuation indent; formatting is whitespace-only and confined to the added method, so the
   file stays “already formatted” (it was before this edit). RED/GREEN were re-run after formatting.
2. **pi-lens surfaced 5 STOP advisories** (`from conftest import run_cli` at `test_cli.py:16`, and
   `import tomli as _tomli` at `:119/:142/:163/:176`). All are **pre-existing, untouched** lines already
   recorded in apply-progress D6; per scope rule they were not modified.
3. No other deviation. The test asserts no glyph and no substituted rendering, matching the assertion
   shape used by T1–T5.
