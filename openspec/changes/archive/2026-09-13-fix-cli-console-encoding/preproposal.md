# Pre-proposal decision record — `2026-09-13-fix-cli-console-encoding`

Status: **RESOLVED** — the grouped question round was answered by the maintainer on
2026-09-13; `sdd-proposal` is unblocked. `status: pending` blocks
`sdd-proposal` until the decisions below are resolved.

Origin: GitHub issue #161. Exploration evidence: `explore.md` in this directory
(verified independently by the orchestrator: the reproduction, the `process-boundary`
PB-02 text, the false-negative test, and the emission census).

## Why the change is not the 2-string fix the issue proposed

| Finding | Evidence |
|---|---|
| `scan --help` / `prepare --help` crash on a cp1252 stdout | `PYTHONIOENCODING=cp1252 uv run sofer scan --help` → rc=1, `UnicodeEncodeError` U+2192 @830 |
| Console-emission surface is ~60 sites across 7 modules, not 2 help strings | AST census: `prepare.py` 15, `_converters.py` 14, `publish.py` 10, `codebook.py` 6, `render.py` 6, `profile.py` 5, `cli.py` 4 (glyphs `⚠` `✗` `✓` `→` `↑`) |
| The issue's "runtime commands are unaffected" does not hold | `cli.py:549,569` print `→` on the `scan` preview and `--dry-run` paths |
| A canonical spec already mandates the invariant, and its test is a false negative | `openspec/specs/process-boundary/spec.md` PB-02 + `tests/test_cli.py::test_help_strict_cp1252`, which runs only `["--help"]` — the one invocation with no offending glyph. **The suite is green over the bug.** |
| Worst failure mode is correctness, not cosmetics | `publish.py:161-208` prints `✓` *after* `upload_file()` returns: a cp1252 crash yields `rc=1` for a complete publish |
| Five indirect vectors cannot be fixed by rewriting literals | non-cp1252 `argv` echoed by argparse, filenames interpolated into prints, third-party `{exc}` text, tracebacks, dataset content printed by `codebook` |

`AGENTS.md` rule 14 constrains the solution: `cli.py` must stay at 100.00% line
coverage with zero `# pragma: no cover`, so any guard line added there needs real
test execution.

## Pending decisions (option tokens are stable)

### D1 — fix shape
- `hybrid` **(recommended)** — boundary guard on stdout/stderr *plus* ASCII in the
  three argparse strings: closes the class for the ~60 runtime sites and all five
  indirect vectors, keeps every glyph on UTF-8 terminals, smallest structural diff.
- `guard-only` — boundary guard, no string edits: fewest lines, but `scan`/`prepare`
  help still contains `→` (degrades to `?` on cp1252 instead of reading `->`).
- `ascii-rewrite` — normalize all ~60 sites to ASCII, no guard: largest diff, largest
  UX change, and still exposed to the indirect vectors.

### D3 — where the fallback error handler lives
- `config-constant` **(recommended)** — module-level constant in `config.py`; satisfies
  rule 1 (no literal in a function body) without new user-facing config surface.
- `toml-option` — expose e.g. `[tool.sofer] console_errors`; configurable, but adds
  config surface + validation + a `tool-config` spec delta.
- `derived-from-stream` — compute from the stream's own codec at runtime; no constant
  and no config, but the behaviour is implicit and harder to test.

### D4 — which capability owns the contract
- `pb02-plus-cli-r11` **(recommended)** — repair PB-02's scenario so it parametrizes
  over every subcommand, and add a `cli` requirement for runtime output safety
  (`cli` currently states nothing about output encoding).
- `pb02-only` — keep the invariant entirely in `process-boundary`; no `cli` delta.
- `cli-r11-only` — put everything in `cli`; leaves PB-02's false-negative scenario
  in place.

### D5 — regression-test scope
- `help-all-subcommands-plus-runtime` **(recommended)** — parametrize `--help` over all
  nine subcommands under cp1252 **and** exercise at least one runtime emission path.
- `help-only` — parametrize the help screens; leaves the runtime paths unlocked.
- `plus-ci-gate` — the above plus a dedicated cp1252 CI step.

## Resolution (maintainer answers, 2026-09-13)

| Decision | Choice | Consequence carried into the proposal |
|---|---|---|
| D1 fix shape | `hybrid` | Boundary guard on `sys.stdout`/`sys.stderr` + ASCII where the CLI owns user-facing text |
| D3 handler home | `config-constant` | `CONSOLE_ERRORS` module constant in `src/sofer/config.py`, consumed by `cli.py`; no new `[tool.sofer]` option |
| D4 spec ownership | `pb02-plus-cli-r11` | **Orchestrator-decided** (the maintainer delegated this one): MODIFY PB-02 to cover every subcommand, ADD `CLI-R11` to the `cli` capability for runtime output safety. Two distinct obligations, each owned where it belongs; either alternative leaves one of them uncovered. |
| D5 test scope | `help-all-subcommands-plus-runtime` | Parametrize `--help` over all nine subcommands under cp1252 **and** exercise a real runtime emission path |

ASCII set for the hybrid (all U+2192, all in text the CLI authors): `cli.py:1072`,
`cli.py:1073`, `cli.py:1429` (argparse strings) plus `cli.py:549`, `cli.py:569` (the
`scan` preview and `--dry-run` prints). The remaining ~58 sites keep their glyphs and
are protected by the guard. `design.md` may argue to keep the two prints and rely on
the guard; if so it must say why.

Non-goals confirmed as stated in the constraints below.

## Constraints carried into the proposal (not open questions)

- Non-goals unless the maintainer says otherwise: normalizing the whole glyph
  vocabulary, forcing UTF-8 mode globally, changing file-output encodings
  (report writers are deliberately utf-8 and must not change), `errors="ignore"`
  (turns a crash into silent output loss).
- The new regression test must assert rc + an ASCII substring, never a glyph, so it
  does not hard-code the chosen strategy.
- `README.md` / `README_ES.md` sync (rule 13) and CLI help-text accuracy (rule 7) in
  the same change; `[tool.sofer]` defaults read via `config.py` (rule 1).
