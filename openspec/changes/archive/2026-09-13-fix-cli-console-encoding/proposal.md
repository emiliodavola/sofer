# Proposal: fix-cli-console-encoding

Origin: GitHub issue `emiliodavola/sofer#161`. Exploration: `explore.md` in this
directory. Decisions: `preproposal.md` (RESOLVED 2026-09-13).
Store: openspec · Language: English · Phase: sdd-proposal.

---

## Intent

Make the `sofer` CLI survive a console (or a redirected/piped text stream) whose
encoding cannot represent the characters the CLI emits, instead of aborting with a
raw `UnicodeEncodeError` traceback. And close the spec/test blind spot that let the
defect ship: a canonical requirement already mandates this invariant and its
implementing test passes only because it exercises the one invocation that has no
offending character.

The fix has two halves, and they are not interchangeable:

1. a **boundary encoding guard** on `sys.stdout`/`sys.stderr` at the CLI entry
   point, so an unencodable character is substituted rather than raised — this is
   the only mechanism that covers the data-driven output the CLI does not author;
2. **ASCII substitution** at the five places where the CLI itself authors `U+2192`
   in user-facing text — three argparse strings plus two `scan` prints.

---

## Problem statement

### The reproduction

`PYTHONIOENCODING=cp1252 uv run sofer scan --help` → `rc=1`,
`UnicodeEncodeError: 'charmap' codec can't encode character '\u2192' in position 830`.
`sofer prepare --help` fails identically (position 255). `main()` —
`def main() -> None:` at `src/sofer/cli.py:1556`, its body
(`config.reload(None)` → `_build_parser()` → `parse_args()` →
`sys.exit(args.func(args))`) at `src/sofer/cli.py:1568-1571`, and the
`if __name__ == "__main__":` guard at `src/sofer/cli.py:1574-1575` — wraps nothing
in `try/except`, so the encode error raised inside argparse's `_print_message`
propagates before `parser.exit()` is reached: a traceback, not `exit 0`.

### The surface is far wider than the issue's two help screens

Source inspection (`explore.md` §2-§3) finds **3 argparse `description=`
codepoints** (`cli.py:1072`, `:1073`, `:1429`) **plus 60 `print()` call sites
across 7 modules** carrying **5 distinct non-cp1252 codepoints** (`U+2191`,
`U+2192`, `U+26A0`, `U+2713`, `U+2717`). The issue's enumeration captured a small
fraction of this because most sites spell the glyph as an escaped `\uXXXX`
sequence, invisible to a literal-character scan.

Two numbers circulate for this surface and they are **not** interchangeable, so
each is stated with its metric:

- **Metric A — the glyph is in the emission call site.** A single `print()` call
  whose own source segment contains the character, either as a literal glyph or as
  a `\uXXXX` escape (a call spanning several lines counts once). **60 sites, 7
  modules, 5 codepoints**, split as `prepare.py` 15, `_converters.py` 14,
  `publish.py` 10, `codebook.py` 6, `render.py` 6, `profile.py` 5, `cli.py` 4
  (`cli.py:77`, `:79`, `:549`, `:569`).
- **Metric B — the glyph reaches stdout through a variable or joined string**, so
  the emission call site itself is clean: `verification.py:132` builds
  `status = "\u2713  PASSED" if ... else "\u2717  FAILED"`, printed on the next
  line; `checks.py:131` appends `f"Expected ≥ {n} file entries..."` to
  `report.errors`, rendered by the `print` at `checks.py:55`. At the far end of the
  same class, `cli.py:240` `print(codebook)` emits text whose non-ASCII originates
  in the dataset, not in our source.

Metric A ∪ Metric B is the **62 sites / 9 modules / 6 codepoints** figure recorded
in `explore.md` §3.4 (`U+2265` enters only through Metric B, at `checks.py:131`).
This document reasons with the **Metric A** count; Metric-B sites are treated as
indirect vectors below and are **not** counted again in it.

These glyphs reach the console on ordinary, documented paths, not just `--help`
(`Metric` column = which census the site belongs to):

| Path | Emission site | Metric |
| --- | --- | --- |
| `validate` / `prepare` / `publish` with configuration errors | `cli.py:77-79` (`✗`) — always taken on a config error | A |
| `validate` reporting a `min_files` violation | `checks.py:131` (`≥`) rendered by `checks.py:55` | B |
| `prepare --verify` | `verification.py:132` (`✓` / `✗`), printed on the following line | B |
| `scan` confirm preview and `scan --dry-run` | `cli.py:549`, `cli.py:569` (`→`) | A |
| `publish --target hf` progress | `publish.py:161-208` (`↑`, `→`, `✓`, `✗`) | A |
| `codebook` / `profile` / `render` warning paths | stderr `⚠` / `✗` in `codebook.py`, `profile.py`, `render.py` | A |
| `codebook` printing dataset-authored markdown | `cli.py:240` `print(codebook)` | B |

### The worst failure mode is correctness, not cosmetics

`src/sofer/publish.py:161-208` prints the success line **after** the network call
returns:

```python
print(f"  \u2191  {label}  \u2192  {remote_path}")   # before
target_api.upload_file(...)                        # the upload
print(f"  \u2713  {label}")                        # after success
```

A `UnicodeEncodeError` on that third line produces a traceback and `rc=1` **for an
upload that actually completed**, and the documented `ok`/`fail` accounting never
prints. The user is told a finished publish failed. This alone makes the fix
exception-shaped (never raise on encoding), not merely literal-shaped.

### Five vectors a literal rewrite cannot close

No amount of editing our own string literals covers these; only a boundary guard
does:

1. non-cp1252 `argv` echoed back by argparse in `invalid choice` / `unrecognized
   arguments` errors;
2. filenames and config values interpolated into our own `print()` calls (a dataset
   directory whose name contains a non-cp1252 character crashes a print whose
   literal text is pure ASCII);
3. third-party exception text (`{exc}` from pyarrow / openpyxl / huggingface_hub);
4. tracebacks — the reporting of a crash crashes, because `main()` has no handler;
5. non-ASCII dataset **content** printed to stdout — `cli.py:240` prints the whole
   generated codebook markdown, which embeds header names and sample values read
   from the data. (This is the Metric-B end of the class: the same guard, not a
   literal rewrite, is what covers it.)

### The spec/test blind spot (the reason a green suite shipped a live crash)

`openspec/specs/process-boundary/spec.md` PB-02 **already mandates** this
invariant: cp1252 help SHALL run on the ubuntu matrix via `PYTHONIOENCODING=cp1252`
with `encoding="cp1252", errors="strict"`, SHALL exit 0, and SHALL produce
strict-decodable stdout. The implementing test exists —
`tests/test_cli.py:1269-1288` `TestSubprocessBoundary::test_help_strict_cp1252` —
and passes, because it runs only `["--help"]`, the one invocation that renders no
subparser `description=`. The bug lives exactly in the blind spot.

Every other help test in the file is in-process with `capsys`, which swaps
`sys.stdout` for an in-memory object that cannot fail to encode. Those tests are
**structurally incapable** of catching this class of defect. Only the subprocess
boundary can observe it.

---

## Scope

### In scope

- **Boundary encoding guard** applied to `sys.stdout` and `sys.stderr` at the CLI
  entry point, before the parser is built (see Approach).
- **`CONSOLE_ERRORS` module constant** in `src/sofer/config.py` (value
  `"replace"`), consumed by `cli.py`.
- **ASCII substitution** at exactly the five CLI-authored `U+2192` occurrences:
  `cli.py:1072`, `cli.py:1073`, `cli.py:1429` (three argparse `description=`
  strings, outside the Metric-A census) and `cli.py:549`, `cli.py:569` (two of
  the 60 Metric-A `print()` sites — the `scan` preview and `--dry-run` prints).
- **Spec deltas**: MODIFY PB-02 (prose + the cp1252 scenario covers every
  subcommand) and ADD `CLI-R11` to the `cli` capability (runtime console output
  SHALL NOT raise `UnicodeEncodeError`).
- **Regression tests** under `PYTHONIOENCODING=cp1252` through the existing
  `tests/conftest.py::run_cli` subprocess boundary: `--help` parametrized over all
  nine subcommands (plus `mcp add`/`mcp remove`) **and** at least one real runtime
  emission path.
- **README/CLI accuracy**: a short "Console encoding" note in `README.md` and
  `README_ES.md`, plus any `help=`/`description=` text accuracy updates, in the
  same change (AGENTS.md rules 7 and 13).

### Out of scope (non-goals)

1. **Normalizing the remaining 58 Metric-A `print()` sites to ASCII**
   (60 − the 2 in-scope `scan` prints). They keep their glyphs
   and are protected by the guard, so UTF-8 terminals (macOS, Linux, Windows
   Terminal, VS Code) lose nothing. The mixed marker vocabulary noted in
   `explore.md` §2.5 stays mixed; resolving it is a separate UX change.
2. **Forcing UTF-8 mode globally** (`PYTHONUTF8`, `sys.flags.utf8_mode`, re-exec).
   Process-wide semantics change that also alters `locale.getpreferredencoding`
   for dataset reads the `data-quality` capability pins.
3. **Changing file-output encodings.** The quality report, codebook markdown and
   Dataset Card are deliberately written with an explicit `utf-8`
   (`config.OUTPUT_ENCODING`, `pyproject.toml [tool.sofer]`). Untouched.
4. **`errors="ignore"`.** It converts a crash into silent output loss.
5. **Mutating the user's environment** (`PYTHONIOENCODING`,
   `PYTHONLEGACYWINDOWSSTDIO`, `chcp` / `SetConsoleOutputCP`). Outside a CLI's
   remit.
6. **The MCP capture path.** `mcp_server._capture_output` swaps in `io.StringIO`,
   which cannot raise `UnicodeEncodeError`; there is no defect there, and MSP-R01
   stdout cleanliness must not be disturbed.
7. **ASCII-ifying spec prose.** Spec files are UTF-8 documents, not console
   streams. Only *emitted* text is held to the console-safe rule. (Note for
   `design`: `openspec/specs/cli/spec.md:54`, inside CLI-R02 — whose requirement
   heading is at `:47` — itself contains `U+2192` in prose
   (`raw/→cache/→build/`), deliberately left alone.)
8. **A new `[tool.sofer]` option** (e.g. `console_errors`) and the
   `tool-config` spec delta it would require. Decision D3 chose a module constant.
9. **Translating or reflowing help text**, changing report widths, or making the
   exit code depend on an encoding failure (the opposite of the fix).

---

## Approach

### 1. Guard placement (`src/sofer/cli.py`)

A small module-level helper (e.g. `_configure_console_streams()`) is called as the
**first statement of `main()`**, before `_build_parser()` / `parse_args()`.

Placement is load-bearing, not stylistic: argparse resolves `_sys.stdout` at call
time and writes rendered help through it, so a guard placed after
`_build_parser()` would leave the issue's own `--help` symptom unfixed. Placed
first, one mechanism covers help output, runtime `print()` output, and tracebacks.

The helper reconfigures each of `sys.stdout` / `sys.stderr` with
`errors=config.CONSOLE_ERRORS`, and is defensive by construction: a stream that
lacks `reconfigure` (pytest capture, an `io.StringIO` swap, a closed or detached
stream) is skipped and must never raise. It never swaps or replaces the stream
objects, so MCP `_capture_output` interleaving is unaffected.

**AGENTS.md rule 14 applies here.** `cli.py` must measure 100.00% line coverage
with zero `# pragma: no cover`, so every new line and both arms of the defensive
branch must be executed by the suite:

- `tests/test_cli.py::test_main_guard_via_runpy` (real `sys.stdout` via
  `runpy`) exercises the reconfigure arm;
- in-process tests (`test_main_help_prints` and the `capsys`-based help tests)
  exercise the stream-without-`reconfigure` arm.

The coverage plan must be verified by execution during `apply`, not assumed.

### 2. The constant (`src/sofer/config.py`)

```python
CONSOLE_ERRORS: str = "replace"
```

Module-level, adjacent to `OUTPUT_ENCODING` (`config.py:354`). It is deliberately
**not** added to `_DEFAULTS`: `_read_tool_section` iterates `_DEFAULTS`, so adding
it there would silently make `[tool.sofer] console_errors` settable — exactly the
config surface D3 rejected. Keeping the literal at module scope in `config.py`
(rather than inside a function body in `cli.py`) satisfies AGENTS.md rule 1 by
location: no literal magic value in a function body, no new user-facing option, no
`tool-config` spec delta.

### 3. The ASCII edits (five CLI-authored `U+2192` occurrences → `->`: three argparse strings plus two of the 60 Metric-A `print()` sites)

| Site | Text | Why it is safe and useful |
| --- | --- | --- |
| `cli.py:1072` | `prepare` description | help screen — highest-visibility surface for a new user on any platform |
| `cli.py:1073` | `prepare` description | same |
| `cli.py:1429` | `scan` description | same; `cli.py:1427` on the *same screen* already reads `->`, so this also removes an intra-screen inconsistency |
| `cli.py:549` | `scan` Phase-2 confirm preview | CLI-authored, and the surrounding MOVE preview vocabulary is already ASCII `-> raw/<rel>` |
| `cli.py:569` | `scan --dry-run` copy preview | same |

Everything else keeps its glyph and relies on the guard. (`design.md` may argue to
keep the two `scan` prints and rely on the guard; if so it must say why.)

### 4. Spec deltas

- **MODIFY PB-02** (`process-boundary`): the requirement prose SHALL state that
  every subcommand's help — `sofer <cmd> --help` for all nine subcommands plus the
  nested `mcp add`/`mcp remove` — and the CLI's runtime console paths are
  cp1252-safe; the existing "cp1252 help on the ubuntu matrix" scenario SHALL be
  repaired so `--help` is exercised for every subcommand, and a scenario SHALL be
  added for a runtime emission. PB-02 keeps its identity as the *test-boundary*
  requirement.
- **ADD `CLI-R11`** (`cli`): runtime console output SHALL NOT raise
  `UnicodeEncodeError`; a character the active console encoding cannot represent
  SHALL be substituted rather than abort the command. The `cli` capability
  currently says nothing about output encoding, and `process-boundary`'s own
  purpose statement says it specifies no production behavior — so the behavioral
  contract belongs in `cli` and the boundary proof belongs in PB-02.

Scenario wording follows `openspec/config.yaml` (`Given/When/Then`, RFC 2119
keywords); every scenario added SHALL get a corresponding test (AGENTS.md rule 6).

### 5. Regression tests (`tests/test_cli.py`)

Extend `TestSubprocessBoundary`, reusing the shared `run_cli` helper (PB-09
forbids re-implementing it) and the existing `SUBCOMMANDS` tuple — no new helper:

- **Exhaustive help**: parametrize `["--help"]` plus `[command, "--help"]` for
  each of the nine subcommands, plus `["mcp", "add", "--help"]` and
  `["mcp", "remove", "--help"]`, all under `env={"PYTHONIOENCODING": "cp1252"}` and
  `encoding="cp1252"`. Assert `rc == 0` and re-encode the captured stdout as
  cp1252. This turns the suite RED today on at least `prepare --help` and
  `scan --help`.
- **At least one real runtime path**: `validate` against a TOML with configuration
  errors (exercises `cli.py:77-79`) asserting `rc == 1` and the ASCII substring
  `"Configuration errors"`; and/or `scan --dry-run` (exercises `cli.py:569`)
  asserting `rc == 0` and `"DRY RUN"`. `prepare --verify` may be added behind an
  `importorskip` for the optional `datasets` extra.
- **Assertion shape**: rc + cp1252-encodability + a stable **ASCII** substring —
  never a glyph. Asserting `"→" in stdout` would fail under the chosen strategy and
  would hard-code it; the test must survive the strategy.

### 6. Docs

A short "Console encoding" note in `README.md` **and** its mirrored section in
`README_ES.md` in the same change (rule 13); technical content stays English in
both. `README.md:320` (the `scan` row of the Command reference) already documents
the ASCII `-> raw/<rel>` for the MOVE phase; the `→` that the same row also
contains is pipeline prose (`raw/DPTO.csv` → `cache/DPTO.csv`), not a CLI output
sample, so no sample rewrite is expected — confirm during `apply`.

---

## Affected canonical specs

| Spec | Change | Requirement |
| --- | --- | --- |
| `openspec/specs/process-boundary/spec.md` | Modified | **PB-02** — prose covers every subcommand; cp1252 scenario parametrized; runtime scenario added |
| `openspec/specs/cli/spec.md` | Added | **CLI-R11** — runtime console output never raises `UnicodeEncodeError` |

## Affected files

| Area | Impact | Description |
| --- | --- | --- |
| `src/sofer/config.py` | Modified | `CONSOLE_ERRORS` module constant (not in `_DEFAULTS`) |
| `src/sofer/cli.py` | Modified | console-stream helper + call as first statement of `main()`; 5 `U+2192` → `->` edits |
| `tests/test_cli.py` | Modified | cp1252 help parametrized over all subcommands + runtime-path scenarios |
| `tests/conftest.py` | Unchanged | `run_cli` already supports `env` + `encoding` (PB-09) |
| `openspec/specs/process-boundary/spec.md` | Modified | PB-02 |
| `openspec/specs/cli/spec.md` | Added | CLI-R11 |
| `README.md`, `README_ES.md` | Modified | "Console encoding" note, both files (rule 13) |
| `src/sofer/publish.py`, `prepare.py`, `profile.py`, `render.py`, `codebook.py`, `_converters.py`, `verification.py`, `checks.py` | Unchanged | glyphs preserved; protected by the guard |

---

## Risks

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| Guard placed after `_build_parser()` leaves `--help` unfixed | Med | Guard is the first statement of `main()`; the parametrized cp1252 help test fails if this regresses |
| Guard breaks on a stream without `reconfigure` (pytest capture, `StringIO`, closed) | Med | Capability check + never raise; both arms executed so rule 14's 100.00% holds without pragmas |
| MCP `_capture_output` interleaving disturbed | Low | Guard reconfigures only and never swaps streams; MSP-R01 stdout cleanliness and the existing MCP boundary tests guard it |
| `cli.py` coverage drops below 100.00% (COV-06) | Med | Every new line/branch executed: `runpy` main-guard test hits the real-stdout arm, in-process tests hit the no-`reconfigure` arm; verified by running the scoped coverage gate |
| The 5 ASCII edits change text asserted by existing tests | Low | Update affected assertions in the same change; run the full suite |
| `"replace"` renders an unencodable glyph as `?` on a legacy console | Accepted | Explicit, visible, and non-fatal; `errors="ignore"` rejected as silent loss |
| A user who set `PYTHONIOENCODING` deliberately to force a hard failure loses that | Low | Accepted tradeoff — fixing the crash class is the point; noted in the README note |
| Test hard-codes the chosen strategy by asserting a glyph | Med | Assert rc + cp1252-encodability + an ASCII substring only |

## Residual risk (stated honestly)

The guard protects **console/`sys.stdout`/`sys.stderr` streams only**. It does not
make sofer's *file* output encoding-safe. Any path where sofer opens a file and
chooses an encoding remains governed by `config.OUTPUT_ENCODING` and the per-dataset
TOML — if a user sets that to a codec that cannot represent the text being written,
they still get an encoding failure, by design and out of scope. Redirecting the
process's stdout to a file is covered (that stream *is* reconfigured); writing a
file sofer opens itself is not.

The mixed glyph vocabulary (`⚠`/`✓`/`✗`/`↑`/`→` vs `[!]`/`X`/`OK`/`->`) also
remains. Adding a new non-cp1252 glyph tomorrow is now safe by construction, but it
is still visually inconsistent.

## Rollback

Revert the change as a single unit. There is no persisted state, no data migration,
and no new config surface, so rollback is a plain revert; after it, cp1252 consoles
crash exactly as they do today. The only user-visible artifacts are the five ASCII
edits and the README note, both trivially revertible.

## Success criteria

- [ ] `PYTHONIOENCODING=cp1252` + `sofer <cmd> --help` for all nine subcommands
      and `mcp add`/`mcp remove` → `rc == 0` and stdout strict-decodes as cp1252.
- [ ] At least one runtime path (`validate` config-error and/or `scan --dry-run`)
      under cp1252 → documented rc, strict-decodable stdout, expected ASCII substring.
- [ ] PB-02 scenario parametrized over every subcommand; `CLI-R11` present with its
      scenarios; every scenario has a corresponding test (rule 6).
- [ ] `cli.py`, `scanner.py`, `prepare.py`, `publish.py` remain at 100.00% line
      coverage with zero `# pragma: no cover` (rule 14 / COV-06).
- [ ] `uv run pytest tests/ -q`, `uv run ruff check src/ tests/`, `uv run mypy src/`
      all green.
- [ ] `README.md` and `README_ES.md` synced (rule 13); help text accurate (rule 7).

## Review workload

Estimated changed lines:

| Area | Est. lines |
| --- | --- |
| `src/sofer/config.py` | ~3 |
| `src/sofer/cli.py` (helper + docstring + call + 5 literal edits) | ~25 |
| `tests/test_cli.py` (parametrized help test + runtime scenarios) | ~40 |
| Spec deltas (PB-02 modification, CLI-R11 addition, change-dir spec files) | ~50-60 |
| `README.md` + `README_ES.md` | ~12 |
| **Total** | **~130-140** |

Well under the 400-line review threshold, with no `src/` file other than
`config.py`/`cli.py` touched and no cross-cutting refactor. A **single PR** is
appropriate; neither PR chaining nor a `size:exception` acceptance is required.

## Question round

The proposal-shaping question round was already conducted and **closed** on
2026-09-13 (`preproposal.md` is the decision record): D1 = `hybrid`, D3 =
`config-constant`, D4 = `pb02-plus-cli-r11`, D5 =
`help-all-subcommands-plus-runtime`. No product/business question remains open, so
no further round is proposed. The assumptions carried forward, for the record:

- the pain is a real crash class, not a cosmetic glyph preference, and its most
  common real-world trigger is **redirection/piping or a wrapper-set
  `PYTHONIOENCODING`**, not plain interactive typing (PEP 528 means a real Windows
  console reports utf-8);
- keeping the glyph vocabulary matters enough that the majority of users should not
  lose it to serve cp1252 consoles — hence a guard rather than a repo-wide ASCII
  rewrite;
- an unencodable character on a cp1252 console should degrade visibly (`?`) rather
  than fail, and `errors="ignore"` is explicitly unacceptable;
- the five ASCII sites are the complete set of CLI-authored `U+2192` output; and
- the regression test asserts rc + encodability + an ASCII substring, never a
  glyph, so it does not pre-commit the implementation strategy.
