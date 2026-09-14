# Delta for process-boundary

> **Change:** `2026-09-13-fix-cli-console-encoding` (GitHub #161) — `sofer <cmd> --help` and
> other console emissions crash with `UnicodeEncodeError` on a cp1252 stream.
>
> Boundary delta. PB-02 already mandated cp1252 help safety, but its implementing test
> (`tests/test_cli.py::TestSubprocessBoundary::test_help_strict_cp1252`) exercised only
> `["--help"]` — the one invocation that renders no subparser `description=` — so a green suite
> covered a live crash. This delta repairs PB-02: the cp1252 boundary SHALL span every
> subcommand's help **and** the CLI's runtime console paths. The behavioural contract for
> runtime output lives in the `cli` capability (CLI-R11, added by this same change); PB-02 keeps
> its identity as the *test-boundary* requirement that proves it.
>
> Block format follows the repo's archived change specs: a full-block
> `## MODIFIED Requirements` replacement of PB-02 (every pre-existing scenario copied intact)
> so archive-time replacement loses nothing.

## MODIFIED Requirements

### Requirement: CLI user-visible output via executable subprocess (PB-02)

Tests in `tests/test_cli.py` SHALL invoke `[sys.executable, "-m", "sofer.cli", ...]` (or the installed script) whenever the requirement concerns user-visible output; parser-level tests SHALL remain for dispatch semantics. Tests SHALL reuse the shared `tests/conftest.py::run_cli` subprocess helper (PB-09) and SHALL NOT re-implement it. The cp1252 boundary SHALL cover BOTH the help output of EVERY subcommand the CLI exposes — the nine top-level subcommands (`init`, `scan`, `validate`, `prepare`, `publish`, `codebook`, `profile`, `render`, `mcp`) plus the nested `mcp add` and `mcp remove` — AND the CLI's runtime console paths, which SHALL be exercised by at least one real command run, not only `--help`. These invocations SHALL run on the ubuntu CI matrix via `PYTHONIOENCODING=cp1252` with `encoding="cp1252", errors="strict"`, SHALL exit with their documented exit code, SHALL produce strict-decodable stdout (and strict-decodable stderr where the exercised path emits there), and SHALL NOT surface a `UnicodeEncodeError`. A cp1252 boundary assertion SHALL be shaped as exit code + cp1252-encodability + a stable ASCII substring of the surrounding message, and SHALL NOT assert a glyph, so the boundary test does not pre-commit how the CLI makes its text encodable. Windows-only behavior SHALL skip without privileges rather than fail.

(Previously: the cp1252 clause was a single `--help` invocation, which renders no subparser `description=` and therefore passed while `prepare --help` / `scan --help` crashed; runtime console paths were not covered at all.)

#### Scenario: Help via subprocess

- GIVEN the CLI subprocess helper
- WHEN `python -m sofer.cli --help` runs
- THEN exit code SHALL be 0 and stdout SHALL list every subcommand

#### Scenario: cp1252 help on the ubuntu matrix

- GIVEN `PYTHONIOENCODING=cp1252` in the subprocess env
- WHEN `--help` runs for every subcommand the CLI exposes — `--help` alone, plus `<cmd> --help` for `init`, `scan`, `validate`, `prepare`, `publish`, `codebook`, `profile`, `render`, `mcp`, plus `mcp add --help` and `mcp remove --help`
- THEN every invocation SHALL exit with code 0 and stdout SHALL strict-decode as cp1252
- AND no invocation SHALL surface a `UnicodeEncodeError`

#### Scenario: cp1252 runtime console output

- GIVEN `PYTHONIOENCODING=cp1252` in the subprocess env and a real command whose ordinary console output carries a character outside the cp1252 repertoire (a `validate` run that reports configuration errors, and a `scan --dry-run` run that previews a copy)
- WHEN each command runs through the executable subprocess boundary
- THEN each SHALL exit with its documented exit code (`1` for the configuration-error report, `0` for the dry run) and stdout SHALL strict-decode as cp1252
- AND the surrounding ASCII substring SHALL still be present (`Configuration errors`, `DRY RUN`)
- AND no `UnicodeEncodeError` traceback SHALL appear on stderr

#### Scenario: Dispatch exit codes

- GIVEN `python -m sofer.cli <unknown-command>`
- WHEN it runs
- THEN argparse SHALL exit 2

---

<!-- Informational only: maps each scenario to its apply-phase test (AGENTS.md #6 /
openspec/config.yaml — every spec scenario MUST have a corresponding test).
Not part of the archived requirement blocks. -->

| Scenario | Test (`tests/test_cli.py`, `TestSubprocessBoundary`) |
| --- | --- |
| Help via subprocess | existing `test_help_exits_zero_and_lists_every_subcommand` (preserved, unchanged) |
| cp1252 help on the ubuntu matrix | rework of `test_help_strict_cp1252` into a parametrized test over `["--help"]`, `[cmd, "--help"]` for the `SUBCOMMANDS` tuple, and `["mcp", "add", "--help"]` / `["mcp", "remove", "--help"]` — `env={"PYTHONIOENCODING": "cp1252"}`, `encoding="cp1252"`, assert `rc == 0` and re-encode stdout as cp1252 |
| cp1252 runtime console output | new `test_runtime_output_strict_cp1252` — `validate` against a TOML with configuration errors (`rc == 1`, `"Configuration errors"` in stdout) and/or `scan --dry-run` (`rc == 0`, `"DRY RUN"` in stdout), both under the same cp1252 env/encoding, plus stdout/stderr re-encoded as cp1252 |
| Dispatch exit codes | existing `test_unknown_command_exits_2` (preserved, unchanged) |
