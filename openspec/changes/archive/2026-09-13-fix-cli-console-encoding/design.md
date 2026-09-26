# Design: CLI console encoding — substitute instead of aborting (GitHub #161)

> **Change:** `2026-09-13-fix-cli-console-encoding` · **Store:** openspec · **Phase:** `sdd-design` ·
> **Language:** English.
> **Inputs (frozen):** `proposal.md` (approved approach, D1 `hybrid` / D3 `config-constant` /
> D4 `pb02-plus-cli-r11` / D5 `help-all-subcommands-plus-runtime`), `preproposal.md`,
> `explore.md`, and the two spec deltas (`process-boundary` PB-02 MODIFIED, `cli` CLI-R11 ADDED).
>
> **Shape:** one boundary encoding guard on `sys.stdout`/`sys.stderr` at the CLI entry point
> (covers every glyph the CLI does not author) + ASCII `->` at the five CLI-authored `U+2192`
> sites + the cp1252 subprocess regression tests + a README note. Exactly the approved scope:
> the remaining ~58 glyph sites, file-output encodings, UTF-8-mode forcing, the MCP path and
> `errors="ignore"` stay out of scope.
>
> **This document settles two unverified assumptions carried by `explore.md`** (§4): Q2 is
> **settled statically with evidence and its expected answer was inverted**; Q1 is settled from
> documented CPython behaviour with a one-line apply-phase probe and has **no impact on the
> strategy**.

---

## Technical Approach

Six changes, all on already-contacted files, in dependency order:

1. **`config.py` — the policy constant.** Module-level `CONSOLE_ERRORS: str = "replace"`,
   inserted in the "Encoding / IO" constant group next to `OUTPUT_ENCODING` and deliberately
   **not** in `_DEFAULTS` (no new `[tool.sofer]` surface; D3).
2. **`cli.py` — the guard helper.** `_configure_console_streams()` defined immediately above
   `main()`, reconfigure-in-place with `errors=config.CONSOLE_ERRORS`, structurally incapable of
   raising and structurally incapable of swapping a stream object.
3. **`cli.py` — the wiring.** The helper is the **first statement of `main()`**, ahead of
   `config.reload(None)` and `_build_parser()`; `main()`'s docstring gains orchestration step 0.
4. **`cli.py` — the five ASCII edits.** `U+2192` → `->` at `548/569` (two `scan` prints) and
   `1072/1073/1429` (three argparse `description=` strings), each normalizing to an ASCII arrow
   that already exists on the same screen or in the same output block.
5. **`tests/test_cli.py` — the regression matrix.** `test_help_strict_cp1252` becomes a
   parametrization over all 12 invocations; four new `TestSubprocessBoundary` runtime tests; a
   new `TestConsoleEncodingGuard` with three direct-helper tests that pin both defensive arms.
   All subprocess tests go through the shared `conftest.run_cli` (PB-09 forbids a second helper).
6. **`README.md` + `README_ES.md` — one mirrored table row** in the existing *Windows notes*
   section (rule 13), documenting behaviour, not a specific substituted rendering.

No other production file is touched. `publish.py`, `prepare.py`, `profile.py`, `render.py`,
`codebook.py`, `_converters.py`, `verification.py`, `checks.py`, `scanner.py` and
`mcp_server.py` keep their glyphs and gain no code.

---

## Architecture Decisions

### Decision 1 — Guard shape: `isinstance(stream, io.TextIOWrapper)` + `try/except (ValueError, OSError)`

| Option | Tradeoff | Decision |
|---|---|---|
| `hasattr(stream, "reconfigure")` gate, no `try` | "Has the attribute" ≠ "can be reconfigured": a *closed* `TextIOWrapper` has `reconfigure` and raises `ValueError`. A closed/detached stream would crash `main()` on its first statement. | Reject |
| `try: stream.reconfigure(...)` + `except AttributeError` | One `except` arm, no `io` import — but `sys.stdout` is typed `TextIO \| MaybeNone`, so this needs `# type: ignore[attr-defined]`; `warn_unused_ignores = true` (pyproject:78) makes a wrong error code a hard mypy failure, and typeshed 3.13 deliberately does **not** put `reconfigure` on `TextIO`. Attribute-sniffing also hides *why* a stream is skipped. | Reject |
| `isinstance(stream, io.TextIOWrapper)` narrowing + `try/except (ValueError, OSError)` | mypy-clean with **zero** suppressions (the `isinstance` narrows `TextIO \| MaybeNone` → `TextIOWrapper`, whose `reconfigure` is typed at `_io.pyi:287`); `None` falls out as "not a text wrapper"; separates "foreign capture object" from "real wrapper that refuses". | **Accept** |
| Swap in `sys.stdout = <wrapper with errors="replace">` | Breaks stream identity → `mcp_server._capture_output` restores by identity and pytest's capture bookkeeping assumes it owns the object; MSP-R01 stdout cleanliness depends on untouched framing. Also replaces the user's own stream object, losing `buffer`/`fileno` behaviour. | Reject |

The chosen narrowing pattern is the one **typeshed itself documents** for this exact problem
(`.venv/.../typeshed/stdlib/sys/__init__.pyi:70-77`: *"To use methods from TextIOWrapper, use an
isinstance check to ensure that the streams have not been overridden: `if isinstance(sys.stdout,
io.TextIOWrapper): sys.stdout.reconfigure(...)`"*).

**Exact code shape** (`src/sofer/cli.py`, immediately above `main()`, i.e. after the parser
builder at `:1554`; `import io` added to the stdlib import block after `import argparse`):

```python
def _configure_console_streams() -> None:
    """Reconfigure the console text streams to substitute unencodable text (CLI-R11).

    Called as the FIRST statement of :func:`main`, ahead of ``config.reload`` and
    ``_build_parser``: argparse resolves ``sys.stdout`` at call time, so a guard placed
    after the parser is built would leave ``--help`` unfixed, and the ``config.reload``
    verbose line (a resolved path interpolated into an f-string) would stay exposed.
    Each stream is reconfigured *in place* with ``errors=config.CONSOLE_ERRORS``; the
    stream objects are never swapped or replaced, so stream identity — and therefore the
    ``io.StringIO`` capture interleaving in :func:`sofer.mcp_server._capture_output` — is
    preserved.

    Defensive by construction (CLI-R11): a stream that cannot be reconfigured in place is
    left untouched and this function SHALL NOT raise. Two cases are skipped explicitly:
    a stream that is not an :class:`io.TextIOWrapper` (an in-memory capture object such as
    :class:`io.StringIO`, a foreign capture stream, or ``None``) and a real wrapper that
    refuses reconfiguration (a closed or detached buffer, or an ``OSError`` from the
    implicit flush when the stream's reader is gone).

    Returns:
        ``None``.  The only observable effect is the error handler of the process's
        ``sys.stdout`` / ``sys.stderr`` objects, which are the same objects on return.
    """
    for stream in (sys.stdout, sys.stderr):
        if not isinstance(stream, io.TextIOWrapper):
            continue
        try:
            stream.reconfigure(errors=config.CONSOLE_ERRORS)
        except (ValueError, OSError):
            continue
```

- **Why the first statement of `main()` and not after `config.reload`.** `CONSOLE_ERRORS` is a
  static constant (Decision 2), so ordering is not a functional dependency; placing the call
  *before* `config.reload(None)` additionally covers the one stderr line `reload()` can emit
  (`config.py:308-310`, `[tool.sofer] source: {shown}` — `shown` is a resolved filesystem path
  and therefore a data-driven vector per CLI-R11). Cost: zero.
- **Why not a class/`with`-block/exit-handler.** A guard on the streams is the only mechanism
  that covers argparse's help/error writes, runtime `print()`, third-party exception text and
  tracebacks with one code path; a `try/except` around `parse_args()+dispatch()` would not cover
  argparse's `--help` write (which happens inside `parse_args`) without also swallowing
  `SystemExit`, and would leave buffered writes to be flushed after the handler exits.
- **Why no second call site.** `sofer-mcp` never runs `cli.main()`; MCP output is captured into
  `io.StringIO` (`mcp_server.py:384-406`) and cannot raise `UnicodeEncodeError`. Adding the guard
  to `mcp_server.main()` would mutate a stream the MCP contract requires to stay untouched
  (MSP-R01) for no benefit — explicit non-goal 6.

### Decision 2 — Exception tuple: `(ValueError, OSError)`, and why nothing else

| Member | Justification | Executed by |
|---|---|---|
| `ValueError` | A `TextIOWrapper` whose buffer has been detached or closed is still an `io.TextIOWrapper`, so the `isinstance` gate passes and CPython rejects it with `ValueError` (`CHECK_ATTACHED` / `CHECK_CLOSED`). `io.UnsupportedOperation` also subclasses `ValueError`. | `test_console_guard_survives_unreconfigurable_text_wrapper` |
| `OSError` | `reconfigure()` performs an implicit flush before setting the new parameters; if stdout's reader is gone (`sofer … \| head -1`) that flush raises `BrokenPipeError`, an `OSError`. Swallowing it here is correct: the guard must not become a new first-statement crash source, and the next real `print()` reproduces the pre-existing broken-pipe behaviour. | same test (arm), plus the `except` line is not duplicated per member |
| `AttributeError` — **not** in the tuple | Unreachable behind the `isinstance` gate: everything that passes it has `reconfigure` on its type. Catching a provably-dead exception would be an untestable line, which rule 14 forbids (no pragmas). | n/a |
| `TypeError` — **not** in the tuple | Only a `None`-callable shape would need it; the `isinstance` gate removes that shape entirely. | n/a |
| Bare `except Exception` / `except BaseException` | Would swallow `KeyboardInterrupt`/`SystemExit`-adjacent surprises and hide real stream bugs; the normative clause is "SHALL NOT raise on a stream that cannot be reconfigured", not "swallow everything". | n/a |

### Decision 3 — `CONSOLE_ERRORS` in `config.py`, **not** in `_DEFAULTS`

```python
# Console error handler for sys.stdout/sys.stderr (CLI-R11, issue #161): an emitted
# character the active console encoding cannot represent is substituted in the stream
# instead of aborting the command. Deliberately NOT a _DEFAULTS entry: this is the
# console guard's implementation policy, not a tool-wide user option. _read_tool_section
# iterates _DEFAULTS, so adding it there would silently make [tool.sofer] console_errors
# settable and drift the behaviour away from the CLI-R11 contract.
CONSOLE_ERRORS: str = "replace"
```

Placement: `src/sofer/config.py`, immediately after `OUTPUT_ENCODING: str = _DEFAULTS["output_encoding"]`
(`:354`) and before `PROBE_CHUNK_BYTES` — inside the "Encoding / IO" constant group, ending the
`_DEFAULTS`-derived run with an explicitly non-derived constant.

| Option | Tradeoff | Decision |
|---|---|---|
| Module constant in `config.py`, not in `_DEFAULTS` | Rule 1 satisfied by location (no magic literal inside a function body); no new TOML key; no `tool-config` delta; not rebindable | **Accept (D3)** |
| `_DEFAULTS["console_errors"] = "replace"` | `_read_tool_section` iterates `_DEFAULTS` (`config.py:174`), so `[tool.sofer] console_errors` would silently become settable — exactly the surface D3 rejected, plus a validation/type arm to test | Reject |
| `[tool.sofer] console_encoding_errors` with validation | Rule-1 "most correct", most expensive: new config surface, `tool-config` spec delta, per-type validation arm | Reject (D3) |
| Literal inside `_configure_console_streams()` | Simplest, but arguably violates rule 1 (a tool-wide default in a function body) and hides the policy from the module that owns IO policy | Reject |

Two verifiable consequences of this placement, both settled from source:

- **`reload()` can never overwrite it.** `config.py:297-303` rebinds only `globals()[key.upper()]
  for key in merged`, and `merged` is `dict(_DEFAULTS)` + TOML values for `_DEFAULTS` keys. With
  no `console_errors` key in `_DEFAULTS`, `CONSOLE_ERRORS` is never touched by the Phase-0
  bootstrap.
- **Unknown-key behaviour is unchanged.** `_read_tool_section` ignores keys it does not know, so
  a hand-written `[tool.sofer] console_errors = "ignore"` is ignored exactly like any other
  unknown key — no new silence, no new failure mode, no `tool-config` obligation.

### Decision 4 — The five ASCII edits: all `U+2192` the CLI authors, all to `->`

| Site | Current text (excerpt) | Resulting text | Rationale |
|---|---|---|---|
| `cli.py:1072` | `"local machine: universal csv/tsv/xlsx/jsonl → normalized Parquet "` | `"...jsonl -> normalized Parquet "` | `prepare --help` is the highest-visibility surface and one of the two crash sites in issue #161; `->` reads identically |
| `cli.py:1073` | `"conversion (Excel → one Parquet per sheet), cross-file schema "` | `"conversion (Excel -> one Parquet per sheet), ..."` | same screen as `:1072` — the two must match |
| `cli.py:1429` | `"(raw/DPTO.csv → cache/DPTO.csv), register new files as "` | `"(raw/DPTO.csv -> cache/DPTO.csv), ..."` | `cli.py:1427` — the line **four lines above on the same help screen** — already reads `Phase 2 — COPY raw/ -> cache/`; the edit removes an intra-screen inconsistency as well as the crash |
| `cli.py:549` | `print(f"     → {config.OUTPUT_DIR}/{flat.as_posix()}")` | `print(f"     -> {config.OUTPUT_DIR}/{flat.as_posix()}")` | The Phase-1 MOVE preview at `:474`/`:482` already prints `f"     -> raw/{rel.as_posix()}"`; the edit makes the Phase-2 COPY preview byte-aligned with its sibling in the same command's output |
| `cli.py:569` | `print(f"     → {dest.relative_to(base_dir).as_posix()}")` | `print(f"     -> {dest.relative_to(base_dir).as_posix()}")` | Same block as the `DRY RUN  Would copy the following files:` line; keeps the `--dry-run` preview consistent with the MOVE preview immediately above it |

**Why not keep `:549`/`:569` as glyphs and rely on the guard** (the option `preproposal.md`
leaves open): (a) the guard renders them as a *substitution* (`?`) on precisely the cp1252
console the fix targets, while the identical relation two lines above renders as `->` — the
degraded console would show two different spellings of one relation; (b) the write target for
both lines already exists verbatim in the same file, so there is no information loss and no new
vocabulary; (c) `README.md:320` documents `scan --dry-run` output as `-> raw/<rel>` — the ASCII
edits move the emitted text *toward* the documented form (rule 7). The remaining ~58 Metric-A
sites keep their glyphs and are covered by the guard, which is what makes this a hybrid rather
than a repo-wide normalization.

Not edited (verified): `cli.py:119`, `:398`, `:415`, `:419`, `:453`, `:519`, `:623-628`,
`:745-748` are comments/module or function docstrings; `cli/spec.md:54` and
`openspec/config.yaml` prose are UTF-8 **documents**, not console streams (non-goal 7);
`cli.py:1354` (`init` description) already reads `->`; the `init` template's
`# Source files → raw/ …` is *file* content written with an explicit encoding (non-goal 3).

### Decision 5 — Test shape: the existing boundary helper, ASCII assertions only

| Option | Tradeoff | Decision |
|---|---|---|
| Extend `TestSubprocessBoundary`, reuse `conftest.run_cli` + the `SUBCOMMANDS` tuple | PB-09 mandates the shared helper; `run_cli` already supports `env=` + `encoding=` + `errors="strict"` | **Accept** |
| Assert `"→" in stdout` | Pre-commits the strategy: it fails under this design (the glyph is substituted on a cp1252 stream) and would fail under a future ASCII normalization too | Reject |
| Assert only `stdout.encode("cp1252")` | Passes today for the crashing cases (the traceback text is ASCII and stdout is empty/partial) — a false negative, i.e. exactly the blind spot that let #161 ship | Reject |
| Assert **exit code + cp1252 encodability + a stable ASCII substring + `"UnicodeEncodeError" not in stderr`** | Each case gets at least one assertion that is RED before the fix and GREEN after, without naming a glyph | **Accept** |
| A second subprocess helper for cp1252 | Duplicates PB-09's contract | Reject |
| A dedicated `test_console.py` | The guard is an entry-point concern of `cli.py`; `tests/test_cli.py` already hosts the entry-point tests (`test_main_help_prints`, `test_cli_main_guard_executed_via_runpy`) | Reject (keeps the affected-files table true) |

### Decision 6 — Docs: one mirrored row in the existing *Windows notes* table

| Option | Tradeoff | Decision |
|---|---|---|
| New `### Console encoding` heading in both READMEs | Rule 13 requires heading + section order parity in the same commit → two heading insertions plus a TOC consideration | Reject (larger diff, same information) |
| New row in the existing `### Windows notes — CWD, placeholders, and separators` table (`README.md:135` / `README_ES.md:143`) | That section already owns platform/console plumbing (CWD, placeholders, separators) and is mirrored 1:1; a row insert keeps headings and section order identical, so rule 13 costs one mirrored line | **Accept** |
| Extend `## Command reference` | Mixes a cross-cutting runtime behaviour into a per-command table | Reject |

Exact EN row (inserted as the last row of the table, after `**Path separators**`, `README.md:142`):

```markdown
| **Console encoding** | Nothing to do: the CLI never aborts on a character the active console
encoding cannot represent — the character is substituted in the emitted text and the command
keeps its documented exit code (CLI-R11). Unicode-capable terminals (Windows Terminal, VS Code,
macOS, Linux) are unaffected and keep sofer's `⚠`/`✓`/`✗`/`→` markers. | Affects streams that are
not a Unicode-capable console: output redirected to a file or pipe (`sofer scan --help >
out.txt`), an IDE/CI capture, or a legacy code page forced with `PYTHONIOENCODING=cp1252`. The
unencodable character is written as a placeholder (or an escape sequence) instead of raising
`UnicodeEncodeError`. To keep every marker, set `PYTHONIOENCODING=utf-8`. |
```

ES row (same position, prose translated, technical content English; `README_ES.md:150`):

```markdown
| **Codificación de consola** | Nada que hacer: la CLI nunca aborta por un carácter que la
codificación activa de la consola no puede representar — el carácter se sustituye en el texto
emitido y el comando conserva su código de salida documentado (CLI-R11). Las terminales con
Unicode (Windows Terminal, VS Code, macOS, Linux) no se ven afectadas y mantienen los marcadores
`⚠`/`✓`/`✗`/`→` de sofer. | Afecta a los flujos que no son una consola con Unicode: salida
redirigida a un archivo o tubería, captura de IDE/CI, o una página de códigos antigua forzada con
`PYTHONIOENCODING=cp1252`. El carácter no representable se escribe como marcador de posición (o
secuencia de escape) en lugar de lanzar `UnicodeEncodeError`. Para conservar todos los
marcadores, define `PYTHONIOENCODING=utf-8`. |
```

The wording deliberately says **"a placeholder (or an escape sequence)"**: the CLI-R11 delta
leaves `?` vs `\u2192` open (both are visible substitutions), so the README must not promise a
specific rendering. The row is the only README change: `README.md:320`'s `scan` row already
documents the ASCII `-> raw/<rel>` for the MOVE phase, and its remaining `→` occurrences are
pipeline prose (`raw/DPTO.csv` → `cache/DPTO.csv`), not CLI output samples — verified, no
sample rewrite (rule 13 does not apply to prose, which is mirrored in both files anyway).

**CLI help accuracy (rule 7):** no new flag, no flag rename and no behaviour change is added to
any parser, so no `help=`/`description=` text needs updating beyond the five ASCII edits
themselves. Adding a console-note sentence to the top-level `--help` would be new,
unmandated text — deliberately not done.

---

## Open-assumption resolutions (the two `explore.md` questions)

### Q2 — "Does pytest's captured stdout expose `reconfigure`?" — **SETTLED; the expected answer was inverted**

Evidence, read from the installed pytest **9.1.1** (`.venv/Lib/site-packages/_pytest/capture.py`):

| Fact | Evidence |
|---|---|
| `capsys` installs `CaptureIO` | `capture.py:1007-1011` (`capsys` fixture) → `CaptureFixture._start` `capture.py:936-942` builds `SysCapture(1)` |
| `SysCapture.__init__` defaults its temp file to `CaptureIO()` | `capture.py:369-374` |
| **`CaptureIO` IS an `io.TextIOWrapper`** | `capture.py:203-209`: `class CaptureIO(io.TextIOWrapper)` |
| Default global capture (`--capture=fd`, no `addopts` override — `pyproject.toml:83-88`) installs `EncodedFile` | `capture.py:712-714` (`_get_multicapture("fd")`) → `capture.py:492-500` |
| **`EncodedFile` IS an `io.TextIOWrapper`** | `capture.py:186-188`: `class EncodedFile(io.TextIOWrapper)`; `SysCapture.start` then does `setattr(sys, "stdout", self.tmpfile)` (`capture.py:402-405`) |

**Consequence, and the design change it forces:** in-process tests do **not** produce a
stream without `reconfigure` — the opposite of `explore.md` §7.3/Q2. So the defensive arm is
**not** free coverage from `test_main_help_prints`, and the design does not claim it is:

- the `isinstance`-False arm is pinned by a **dedicated test** with an `io.StringIO()` (the exact
  object `mcp_server._capture_output` installs, `mcp_server.py:398-401`);
- the `except` arm is pinned by a **dedicated test** with a closed/detached `TextIOWrapper`;
- the success arm is pinned by a **dedicated test** with a real `TextIOWrapper(BytesIO())` whose
  post-call `errors` and substitution behaviour are asserted — so coverage of the success arm
  never depends on how pytest's own capture object behaves under `reconfigure`.

**Residual uncertainty (named, not assumed away):** whether `reconfigure(errors=...)` *succeeds*
on pytest's `EncodedFile`/`CaptureIO` under this Python version. It does not affect correctness:
if it raises, the tuple catches it (`ValueError`/`OSError`) and the test outcome is unchanged.
Cheapest experiment that settles it (apply phase, first 30 seconds):
`uv run pytest tests/test_cli.py -q` — the suite is green either way; the coverage report then
shows whether the `continue` on the `except` line was also hit by the in-process tests.

### Q1 — "What does `sys.stdout.encoding` report when stdout is redirected on Windows?" — **SETTLED as documented behaviour; no impact on the strategy**

Settled from documented CPython/PEP behaviour (not from an execution in this phase):

- **Real Windows console** → PEP 528 makes `sys.stdout` a `_WindowsConsoleIO`-backed text stream
  writing through the console wide-char API with `encoding == "utf-8"`; interactive
  `sofer scan --help` therefore generally does **not** crash on a stock Windows terminal.
- **Not a console** (redirected to a file/pipe, IDE/CI capture, `pythonw`) → CPython's
  `init_sys_streams` builds the standard streams with `io.open(fd, encoding=<PYTHONIOENCODING or
  None>)`; with no `PYTHONIOENCODING` the text wrapper takes the process locale encoding
  (`locale.getencoding()`), i.e. the ANSI code page — cp1252 on es-ES/en-US — which cannot encode
  `U+2192`. `PYTHONIOENCODING=cp1252` forces the same state deterministically, which is why the
  regression tests use it (the PB-02 delta already mandates that boundary).

**Impact on the chosen strategy: none.** The guard reconfigures whatever encoding the stream
already has; on a UTF-8 stream it is a no-op, on a cp1252 stream it substitutes. Q1 only decides
the *user-facing framing* in the README row: "streams that are not a Unicode-capable console —
redirected to a file or pipe, an IDE/CI capture, or a legacy code page forced with
`PYTHONIOENCODING=cp1252`" — which is what Decision 6 writes.

Confirming probe (apply phase, Windows host, informational only):

```bash
uv run python -c "import sys; print(sys.stdout.encoding)"                 # console  -> utf-8
uv run python -c "import sys; print(sys.stdout.encoding)" > out.txt       # redirect -> cp1252
```

---

## Data Flow

```text
sofer <cmd> …            (console script → sofer.cli:main)
python -m sofer.cli …    (tests: conftest.run_cli subprocess boundary)
└─ main()
   ├─ _configure_console_streams()                        [NEW — first statement]
   │   for stream in (sys.stdout, sys.stderr):
   │   ├─ not isinstance(stream, io.TextIOWrapper)  → skip   (StringIO / MCP capture / None / foreign)
   │   ├─ isinstance + reconfigure(errors="replace") → in-place error handler, no swap, no raise
   │   └─ isinstance + ValueError|OSError            → skip   (closed / detached / broken pipe)
   │
   ├─ config.reload(None)      verbose "[tool.sofer] source: …" now console-safe
   ├─ _build_parser()
   ├─ parser.parse_args()      help/usage/"invalid choice" written through the guarded streams
   └─ sys.exit(args.func(args)) runtime print() output degrades per character; exit code unchanged

MCP process (sofer-mcp) — untouched: no cli.main(), output captured into io.StringIO
(mcp_server.py:384-406), restored by identity in `finally`; MSP-R01 framing unaffected.
```

Per-stream effect on a `PYTHONIOENCODING=cp1252` child:

```text
before:  print("  \u2717  Configuration errors …")  → UnicodeEncodeError → traceback, rc=1, partial output
after :  print("  \u2717  Configuration errors …")  → "  ?  Configuration errors …", rc unchanged
```

---

## File Changes

| File | Action | Description |
|---|---|---|
| `src/sofer/config.py` | Modify | Insert `CONSOLE_ERRORS: str = "replace"` + 5-line rationale comment between `OUTPUT_ENCODING` (`:354`) and `PROBE_CHUNK_BYTES` (`:355`). No `_DEFAULTS` entry, no `_read_tool_section` change, no `reload` change. |
| `src/sofer/cli.py` | Modify | (1) `import io` in the stdlib import block (after `import argparse`, `:11`); (2) `_configure_console_streams()` defined immediately above `main()` (between `:1554` and `:1556`); (3) the call as the new first body statement of `main()` (before `config.reload(None)` at `:1568`); (4) `main()` docstring gains orchestration step 0; (5) five literal edits: `:549`, `:569`, `:1072`, `:1073`, `:1429` (`U+2192` → `->`). No `_build_parser` change. |
| `tests/test_cli.py` | Modify | (1) imports: add `import io`, extend `from sofer import cli, mcp_registration` with `config`; (2) rework `test_help_strict_cp1252` (`:1269-1288`) into a parametrization over 12 invocations; (3) add `test_runtime_output_strict_cp1252`, `test_scan_dry_run_strict_cp1252`, `test_interpolated_unencodable_value_strict_cp1252`, `test_codebook_warning_strict_cp1252` to `TestSubprocessBoundary`; (4) add `TestConsoleEncodingGuard` with `test_console_streams_reconfigured_in_place`, `test_console_guard_skips_stream_without_reconfigure`, `test_console_guard_survives_unreconfigurable_text_wrapper`. |
| `tests/conftest.py` | Unchanged | `run_cli` already takes `env=` + `encoding=` with `errors="strict"` (`:180-216`); PB-09 forbids a second helper. |
| `README.md` | Modify | One row appended to the *Windows notes* table (`:142`). |
| `README_ES.md` | Modify | Mirrored row in the same section position (`:150`), prose translated. |
| `src/sofer/publish.py`, `prepare.py`, `profile.py`, `render.py`, `codebook.py`, `_converters.py`, `verification.py`, `checks.py`, `scanner.py`, `mcp_server.py`, `mcp_registration.py` | Unchanged | Glyphs preserved and now protected by the guard; MCP capture path untouched. |
| `openspec/specs/process-boundary/spec.md`, `openspec/specs/cli/spec.md` | Unchanged in apply | Canonical specs are synced from the frozen change-dir deltas at archive time. |

No file is deleted, no file is created.

---

## Interfaces / Contracts

| Contract | Shape | Guarantees |
|---|---|---|
| `sofer.config.CONSOLE_ERRORS` | `str == "replace"` | Module-scope constant; **not** read from `[tool.sofer]`, **not** rebound by `reload()` (not a `_DEFAULTS` key). |
| `sofer.cli._configure_console_streams()` | `() -> None`, private | Idempotent; never raises (CLI-R11); never assigns to `sys.stdout`/`sys.stderr`; for every `io.TextIOWrapper` stream, `stream.errors == "replace"` on return; leaves `encoding`, `newline`, `line_buffering` and `write_through` unchanged. |
| Stream identity | invariant | Before and after `main()` starts, `sys.stdout`/`sys.stderr` are the **same objects** (`is`), so `mcp_server._capture_output`'s save/restore-by-identity and pytest's capture bookkeeping are unaffected. |
| Exit codes | invariant | The guard changes no command's documented exit code; `validate` with configuration errors still returns 1, `scan --dry-run` still returns 0, argparse dispatch errors still exit 2. |
| Emitted text | contract | Help and runtime output remain strict-decodable as cp1252 on a cp1252 stream, with the surrounding ASCII substrings (`Configuration errors`, `DRY RUN`, `Config file not found`, `Unsupported format`) intact. |
| Coverage | contract | `cli.py` (and `scanner.py`, `prepare.py`, `publish.py`) stay at 100.00 % line coverage with **zero** `# pragma: no cover` (rule 14 / COV-06). |

---

## Coverage plan for rule 14 (`cli.py` must stay at 100.00 %, zero pragmas)

New/changed executable lines and the single test that proves each. Docstring lines carry no
bytecode and are not measured; `try:` produces no separate line entry.

| Line | Statement | Arm | Executed by | How we know |
|---|---|---|---|---|
| `cli.py` `import io` | module import | — | collection of any test importing `sofer.cli` | import-time, unconditionally |
| helper `def _configure_console_streams() -> None:` | definition | — | import-time | import-time |
| `for stream in (sys.stdout, sys.stderr):` | loop header | — | every test that reaches `main()` (e.g. `test_main_help_prints`, `test_cli_main_guard_executed_via_runpy`) or calls the helper directly | existing tests call `main()` today |
| `if not isinstance(stream, io.TextIOWrapper):` | gate | **False** (real text wrapper) | same as above (pytest fd-capture installs `EncodedFile`, a `TextIOWrapper` — settled, §Q2) + `test_console_streams_reconfigured_in_place` | static: `capture.py:186`; behavioural: the substitution assertion in the new test |
| same | gate | **True** (non-text stream) | `test_console_guard_skips_stream_without_reconfigure` (`io.StringIO`) | `isinstance(io.StringIO(), io.TextIOWrapper) is False` (stdlib type hierarchy) |
| `continue` (inside the gate) | skip arm | — | same test | the test asserts the buffer is untouched and no exception escaped |
| `stream.reconfigure(errors=config.CONSOLE_ERRORS)` | success arm | — | `test_console_streams_reconfigured_in_place` (deterministic) + every in-process `main()` test (incidental) | the test asserts `stream.errors == "replace"` **and** writes `"\u2192"` to an `ascii`-encoded wrapper whose buffer then holds `b"?"` — a direct proof that the guard substitutes instead of raising |
| `except (ValueError, OSError):` | handler entry | — | `test_console_guard_survives_unreconfigurable_text_wrapper` (closed/detached wrapper raises `ValueError`) | the test drives the handler and asserts it does not raise and does not swap the stream |
| `continue` (inside `except`) | skip arm | — | same test | same assertion |
| `_configure_console_streams()` call in `main()` | — | — | every test that reaches `main()`: `test_main_help_prints` (`:208`), `test_cli_main_guard_executed_via_runpy` (`:1454`), plus the new tests | these tests call `cli.main()`/`runpy` today |

Edited literal lines (`:549`, `:569`, `:1072`, `:1073`, `:1429`) change only a string constant —
statement structure, branch structure and bytecode shape are unaffected, so their existing
coverage carriers are unchanged (the `scan` confirm-prompt path for `:549`, the `scan` dry-run
path for `:569`, the help tests for the three `argparse` strings). The full-suite run of
`bash scripts/check_core_coverage.sh` is the enforcement, and the apply phase runs it **before**
declaring the change done.

Gate command sequence (the scoped script needs a `.coverage` database):

```bash
uv run coverage run -m pytest -q
bash scripts/check_core_coverage.sh     # per-file --fail-under=100 for cli scanner prepare publish
```

---

## Test matrix (with the RED-before-GREEN expectation)

Spec-scenario mapping (rule 6; the frozen deltas' informational tables are honoured — the three
names they pin are used verbatim):

| # | Test (`tests/test_cli.py`) | Spec scenario | RED before the fix? | Why |
|---|---|---|---|---|
| T1 | `TestSubprocessBoundary::test_help_strict_cp1252[argv]` — 12 cases: `["--help"]`, `<cmd> --help` for the `SUBCOMMANDS` tuple, `["mcp", "add", "--help"]`, `["mcp", "remove", "--help"]`; `env={"PYTHONIOENCODING": "cp1252"}`, `encoding="cp1252"` | PB-02 *cp1252 help on the ubuntu matrix* | **YES** for `prepare --help` and `scan --help` (`rc == 1`); the other 10 cases are green today (ASCII/em-dash only) | `cli.py:1072/1073/1429` — the crash the issue reports |
| T2 | `test_runtime_output_strict_cp1252` — `validate` on a TOML with configuration-errors → `rc == 1`, `"Configuration errors" in stdout`, `stdout.encode("cp1252")`, `"UnicodeEncodeError" not in stderr` | PB-02 *cp1252 runtime console output* + CLI-R11 *Runtime output with an unencodable character keeps the command's result* | **YES** on the substring assertions — note `rc == 1` alone is *not* a discriminator (a traceback also exits 1); today the first `✗` write raises before `Configuration errors` reaches stdout | `cli.py:77-79` |
| T3 | `test_scan_dry_run_strict_cp1252` — `raw/a.csv` with no `cache/` counterpart, `scan --dry-run` → `rc == 0`, `"DRY RUN" in stdout`, `stdout.encode("cp1252")`, no traceback | PB-02 *cp1252 runtime console output* (the `scan --dry-run` half of the scenario's "and/or") | **YES** on `rc == 0` — today `rc == 1`; `"DRY RUN"` alone would already pass (the preceding line is printed before the crash), which is why `rc` is the discriminator here | `cli.py:569` |
| T4 | `test_interpolated_unencodable_value_strict_cp1252` — `scan <path containing U+2192>` (nonexistent path is the branch under test) → `rc == 1`, `"Config file not found" in stderr`, `stderr.encode("cp1252")`, no traceback | CLI-R11 *ASCII literal with an unencodable interpolated value does not abort* | **YES** on `"UnicodeEncodeError" not in stderr` (today's traceback contains it, and it also echoes the ASCII literal, so only the traceback assertion discriminates) | `cli.py:602-604` — ASCII literal + data-driven `config_path` |
| T5 | `test_codebook_warning_strict_cp1252` — TOML registering an existing unsupported-format file (`notes.txt`), `codebook --all-files --config …` → `rc == 0`, `"Unsupported format" in stderr`, `stderr.encode("cp1252")`, no traceback | CLI-R11 *Console warning path carrying a glyph degrades instead of aborting* | **YES** on `rc == 0` (today the `⚠` write on stderr aborts with 1) | `codebook.py:552` (stderr, `⚠`) |
| T6 | `TestConsoleEncodingGuard::test_console_streams_reconfigured_in_place` — real `TextIOWrapper(BytesIO(), encoding="ascii", errors="strict")` patched onto both streams; assert `errors == "replace"`, `sys.stdout is stream`, and a written `"\u2192"` lands as `b"?"` | CLI-R11 normative clause + rule 14 success arm | n/a (new-behaviour test; it fails only if the guard is missing/rewritten) | determinism independent of pytest internals |
| T7 | `test_console_guard_skips_stream_without_reconfigure` — `io.StringIO()` on both streams; assert the helper does not raise and both streams are the same objects | CLI-R11 *"a stream that cannot be reconfigured in place … SHALL be left untouched rather than raising"* (the object `mcp_server._capture_output` installs) | n/a (rule 14 skip arm) | `isinstance` gate arm |
| T8 | `test_console_guard_survives_unreconfigurable_text_wrapper` — closed `TextIOWrapper` on both streams; assert no raise, identity preserved | same clause (closed/detached case) | n/a (rule 14 `except` arm) | `try/except` arm |

Preserved, unchanged: `test_help_exits_zero_and_lists_every_subcommand` (PB-02 *Help via
subprocess*), `test_unknown_command_exits_2` (PB-02 *Dispatch exit codes*), and every in-process
`capsys` help test. The interacton with the existing `test_help_strict_cp1252` is a **rework, not
an addition**: it keeps its name, its cp1252 env/encoding and its `stdout.encode("cp1252")`
assertion, and gains `rc`-per-case (already asserted), the `UnicodeEncodeError`-free stderr
assertion, and the 11 extra invocations.

Test-shape sketch (design prose, not an edit):

```python
    @pytest.mark.parametrize(
        "argv",
        [
            ["--help"],
            *([command, "--help"] for command in SUBCOMMANDS),
            ["mcp", "add", "--help"],
            ["mcp", "remove", "--help"],
        ],
    )
    def test_help_strict_cp1252(self, argv: list[str], tmp_path) -> None:
        """Every help screen under cp1252 exits 0 with no UnicodeEncodeError (PB-02)."""
        result = run_cli(
            argv, cwd=tmp_path, env={"PYTHONIOENCODING": "cp1252"}, encoding="cp1252"
        )
        assert result.returncode == 0, result.stderr
        assert "UnicodeEncodeError" not in result.stderr
        result.stdout.encode("cp1252")
```

`run_cli` is called with `env=`/`encoding=` exactly as today (PB-09: no new helper, no
re-implementation). `SUBCOMMANDS` is declared earlier in the class body, so it is in scope for
the decorator. T5's unsupported-format entry is assumed to pass `DatasetConfig.validate()`
(asserted by the spec delta); if the apply run shows otherwise, the directory variant named in
the same scenario (`⚠  Skipping directory`, `codebook.py:543`) is the fallback, and that is a
one-line test change, not a design change.

---

## Risks and assumptions

| # | Risk / assumption | Likelihood | What proves it |
|---|---|---|---|
| R1 | Guard placed too late (after `_build_parser()`), leaving `--help` broken | Low (Decision 1 fixes the position) | T1 `prepare --help` / `scan --help` under cp1252 |
| R2 | `reconfigure(errors=…)` *fails* on pytest's `EncodedFile`/`CaptureIO`, so the success arm would rely only on T6 | Low | T6 is independent of pytest internals; `bash scripts/check_core_coverage.sh` after `uv run coverage run -m pytest` (a missed line fails the gate loudly) |
| R3 | The `except` arm raises something outside `(ValueError, OSError)` for a closed/detached wrapper | Low | T8 (apply-phase run; if it surfaces another exception type the tuple gains that type and T8 stays the carrier — a one-token change) |
| R4 | Guard disturbs `mcp_server._capture_output` interleaving or MSP-R01 stdout cleanliness | Very low | The helper performs no assignment to `sys.stdout`/`sys.stderr` (T6-T8 assert identity); `uv run pytest tests/test_mcp_server.py tests/test_mcp_process.py -q` |
| R5 | `cli.py` coverage drops below 100.00 % | Very low (every line/arm mapped above) | `bash scripts/check_core_coverage.sh` |
| R6 | A five-literal ASCII edit breaks an existing assertion | Very low — verified no test in `tests/` asserts `U+2192` or the description substrings (`grep '2192\|raw/→\|normalized Parquet'` → no hits) | `uv run pytest tests/ -q` |
| R7 | `PYTHONIOENCODING=cp1252` makes the cp1252 help cases *pass for the wrong reason* after the fix (substitution hides a real glyph regression) | Accepted by design | The tests assert rc + encodability + ASCII substring only (**never** a glyph), per the CLI-R11 delta; the glyph-preserving contract on UTF-8 terminals is the existing default-env tests |
| R8 | A user who set `PYTHONIOENCODING` to force a hard failure loses that behaviour | Accepted (proposal) | Documented in the README row ("the command keeps its documented exit code") |
| R9 | The README promises a specific substituted rendering | Low | Decision 6 wording: "a placeholder (or an escape sequence)"; the spec leaves `?` vs escape open |
| R10 | Chosen exception handler renders `?`, which loses information on a legacy console | Accepted (proposal) | Visible, non-fatal, and `errors="ignore"` (silent loss) is an explicit non-goal |
| A1 | Q1 (redirected-stream encoding on Windows) | Settled from documented CPython/PEP 528 behaviour; empirical probe listed in §Q1 | `uv run python -c "import sys; print(sys.stdout.encoding)" > out.txt` in apply; **no impact** on the strategy either way |
| A2 | T5's unsupported-format entry passes `DatasetConfig.validate()` | Assumed from the frozen CLI-R11 delta ("both pass config validation, which only checks that the path exists") | T5's own `rc == 0` + a rerun with the directory variant if it fails |
| A3 | No site is both printed and written to a file (so the guard cannot change file output) | Confirmed by `explore.md` §4.1 greps and re-checked by the full suite | `uv run pytest tests/ -q` (codebook/card/report byte assertions) |

Out of scope, restated so reviewers do not re-litigate: the ~58 remaining Metric-A glyph sites,
`publish.py`'s post-success print (covered by the guard, no source change), UTF-8-mode forcing,
file-output encodings, `errors="ignore"`, environment mutation, the MCP capture path, spec-prose
ASCII-fication (`cli/spec.md:54` keeps its `→`), and a `[tool.sofer] console_errors` option.

---

## Verification and rollback

**Verify (apply phase, in this order):**

```bash
# 1. RED proof before touching src/ (expect failures on the two arrow help screens only)
uv run pytest tests/test_cli.py -q -k "cp1252"

# 2. Full suite
uv run pytest tests/ -q

# 3. Lint / types / format (pre-commit parity)
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/

# 4. Rule 14 coverage gate (needs a fresh database)
uv run coverage run -m pytest -q
bash scripts/check_core_coverage.sh

# 5. Dogfood the issue's own reproduction
PYTHONIOENCODING=cp1252 uv run sofer scan --help    # rc 0, no traceback
PYTHONIOENCODING=cp1252 uv run sofer prepare --help # rc 0, no traceback
```

**Rollback:** revert the change as a single unit (one PR, no chaining). There is **no persisted
state, no data migration, no config-format change and no new user-facing option**: removing
`CONSOLE_ERRORS`, the helper, its call and the five ASCII literals restores today's behaviour
exactly (cp1252 consoles crash again with `UnicodeEncodeError`). README.md and README_ES.md
revert together (rule 13); the tests revert with `cli.py`. No `.bak`, cache or build artifact is
involved. If only the docs are wrong, the row can be reverted alone — it carries no behaviour.

---

## Review workload

| Area | Est. changed lines |
|---|---|
| `src/sofer/config.py` (constant + rationale comment) | ~7 |
| `src/sofer/cli.py` (`import io`, helper + docstring, call, `main()` docstring step 0, 5 literal edits) | ~30 |
| `tests/test_cli.py` (parametrized help rework + T2-T5 + T6-T8 + imports) | ~110-125 |
| `README.md` + `README_ES.md` (one mirrored table row each) | ~6 |
| **Implementation subtotal** | **~155-168** |
| Change-dir spec deltas (written in the spec phase, frozen) | ~90 |
| **Total incl. frozen deltas** | **~245-258** |

The test-side estimate is higher than `proposal.md`'s ~40 lines because this design adds the
three guard tests T6-T8 (rule 14 arms) and splits the runtime evidence across T2-T5 (one test
per CLI-R11 scenario). That is a refinement of the same scope, not an expansion: still well under
the 400-line review threshold, no `src/` file other than `config.py`/`cli.py` touched, no
cross-cutting refactor, so a **single PR** remains appropriate — no chaining and no
`size:exception` acceptance is required.

---

## Open questions

None blocking. Two items are recorded for the reviewer rather than decided here:

- **T5 variant choice** (unsupported-format file vs directory entry) — both are named in the
  frozen CLI-R11 scenario; the design prefers the file variant because an existing in-process
  test (`tests/test_codebook.py:601-611`) already pins that exact warning string.
- **Mixed glyph vocabulary** — `⚠`/`✓`/`✗`/`↑`/`→` vs `[!]`/`X`/`OK`/`->` stays mixed (proposal
  non-goal 1). Adding a new non-cp1252 glyph is now safe by construction but still visually
  inconsistent; normalizing the vocabulary is a separate UX change with its own spec delta.
