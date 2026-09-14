# Delta for cli

> **Change:** `2026-09-13-fix-cli-console-encoding` (GitHub #161) — a cp1252 console stream
> makes the CLI abort with a raw `UnicodeEncodeError` instead of printing a degraded character.
>
> Additive delta. The `cli` capability stated nothing about output text or encoding, while
> `process-boundary`'s own purpose statement says it specifies no production behavior.
> `CLI-R11` is therefore the next free requirement ID in this capability (CLI-R01..CLI-R10 are
> taken) and owns the behavioural contract; the boundary proof that the contract holds through a
> real subprocess lives in PB-02 (`process-boundary`), which this same change repairs.
>
> Out of scope by design: generated/documented *file* output keeps its explicit UTF-8 encoding
> (quality report, codebook markdown, Dataset Card), and the MCP capture path (an in-memory
> buffer that cannot fail to encode) is untouched.

## ADDED Requirements

### Requirement: Console output survives an unencodable character (CLI-R11)

> Added by change `2026-09-13-fix-cli-console-encoding` (GitHub #161).

The CLI SHALL NOT abort a command because a character it emits cannot be represented in the active console output encoding. When `sys.stdout` / `sys.stderr` are encoded with a codec that cannot represent an emitted character — cp1252 cannot represent, for example, U+2192, U+2191, U+26A0, U+2713, U+2717, or U+2265 — that character SHALL be substituted in the emitted stream rather than raising `UnicodeEncodeError`, and the command SHALL keep its documented exit code and its remaining output. Substitution SHALL be visible (a placeholder or an escape sequence); silent character loss (an `ignore` error handler) SHALL NOT be used.

The invariant SHALL hold both for characters the CLI authors in its own literals and for characters that reach the console through interpolation: values read from the dataset TOML, resolved dataset/file paths, text from third-party exceptions, dataset-derived content echoed to the console, and argv that argparse echoes back in an error message. Help output (`--help` for every subcommand, including the nested `mcp add` / `mcp remove`) SHALL satisfy the same invariant, because argparse renders its help through the same streams. A stream that cannot be reconfigured in place (an in-memory capture object such as pytest's captured stdout or the MCP capture buffer) SHALL be left untouched rather than raising.

This requirement constrains *emitted* console text only. Text written to files by sofer's own writers (quality report, codebook markdown, Dataset Card) and the CLI's own help/documentation sources SHALL retain their explicit UTF-8 encoding and SHALL NOT be re-encoded by this contract.

#### Scenario: Runtime output with an unencodable character keeps the command's result

- GIVEN a command run with `PYTHONIOENCODING=cp1252` whose ordinary stdout carries a character outside cp1252 (e.g. `validate` reporting configuration errors, or `scan --dry-run` previewing a copy)
- WHEN the command completes
- THEN it SHALL keep its documented exit code and stdout SHALL strict-decode as cp1252
- AND the ASCII substring of the surrounding message SHALL still be present (`Configuration errors`, `DRY RUN`)
- AND no `UnicodeEncodeError` traceback SHALL appear on stderr

#### Scenario: ASCII literal with an unencodable interpolated value does not abort

- GIVEN a command whose own literal text is ASCII and whose interpolated value carries a character outside cp1252 (e.g. a `repo_id`, or a declared local path, whose name contains such a character), and `PYTHONIOENCODING=cp1252` in the environment
- WHEN the command reports that value
- THEN the command SHALL NOT raise `UnicodeEncodeError` and SHALL keep its documented exit code
- AND stdout SHALL strict-decode as cp1252 with the ASCII literal substring present

#### Scenario: Console warning path carrying a glyph degrades instead of aborting

- GIVEN `sofer codebook --all-files --config <toml>` whose TOML registers a file entry the codebook pass skips (an unsupported format, or a directory — both pass config validation, which only checks that the path exists), and `PYTHONIOENCODING=cp1252` in the environment
- WHEN the command runs
- THEN stderr SHALL strict-decode as cp1252 and the ASCII warning substring SHALL be present (`Unsupported format, skipping` or `Skipping directory`)
- AND the command SHALL exit 0, with the skipped entry's warning neither dropped nor aborted

---

<!-- Informational only: maps each scenario to its apply-phase test (AGENTS.md #6 /
openspec/config.yaml — every spec scenario MUST have a corresponding test).
Not part of the archived requirement blocks. -->

| Scenario | Test |
| --- | --- |
| Runtime output with an unencodable character keeps the command's result | new `tests/test_cli.py::TestSubprocessBoundary::test_runtime_output_strict_cp1252` (shared with the PB-02 runtime scenario) — `run_cli(..., env={"PYTHONIOENCODING": "cp1252"}, encoding="cp1252")`, assert rc, ASCII substring, and `stdout.encode("cp1252")` |
| ASCII literal with an unencodable interpolated value does not abort | new `tests/test_cli.py::TestSubprocessBoundary::test_interpolated_unencodable_value_strict_cp1252` — a TOML whose interpolated value carries a cp1252-unrepresentable character, run through `run_cli` under cp1252 |
| Console warning path carrying a glyph degrades instead of aborting | new `tests/test_cli.py::TestSubprocessBoundary::test_codebook_warning_strict_cp1252` — `codebook --all-files` against a TOML registering an existing unsupported-format (or directory) entry alongside a valid one, asserting rc 0, the ASCII warning substring in stderr, and `stderr.encode("cp1252")` |
