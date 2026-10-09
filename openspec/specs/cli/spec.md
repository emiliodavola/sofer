# CLI Specification

## Purpose

The `sofer` command-line surface: which commands are top-level, how `prepare`
and `publish` replace `upload`, and the accuracy of `--help` text. This domain
documents the CLI contract only — command behavior lives in the prepare,
publish, and other domain specs.

## Requirements

### Requirement: upload removed; prepare and publish are top-level (CLI-R01)

The `upload` subcommand SHALL be removed from the CLI. `prepare` and `publish`
SHALL be registered as top-level subcommands, each accepting the TOML config
path as their positional argument.

#### Scenario: upload is unrecognized

- GIVEN `sofer upload dataset.toml`
- WHEN the command executes
- THEN argparse SHALL reject it as an unrecognized command
- AND the exit code SHALL be 2

#### Scenario: prepare and publish appear in help

- GIVEN `sofer --help`
- WHEN the help is rendered
- THEN `upload` SHALL NOT appear
- AND `prepare` SHALL appear as a subcommand
- AND `publish` SHALL appear as a subcommand

#### Scenario: prepare dispatches correctly

- GIVEN `sofer prepare dataset.toml --force`
- WHEN the command executes
- THEN the prepare handler SHALL run with `force = True`

#### Scenario: publish dispatches correctly

- GIVEN `sofer publish dataset.toml --target local`
- WHEN the command executes
- THEN the publish handler SHALL run with `target = "local"`

---

### Requirement: Help text accurate for new commands (CLI-R02)

The parser's `help=` and `description=` strings for `prepare` and `publish`
SHALL document their exact flags: `prepare` — `--output`, `--all-files`,
`--no-checks`, `--force`, `--verify`; `publish` — `--target hf|local`,
`--output`, `--force`, `--keep-csv`, `--dry-run`. The parser description and
the `init` template SHALL NOT reference `upload`, and the README SHALL be
updated in the same change. Parser description and `init` template SHALL NOT reference stale `data/` hint; `init` template SHALL state `# Source files → raw/ (scan copies to cache/)` and description SHALL mention `raw/→cache/→build/`.

#### Scenario: prepare help lists all flags

- GIVEN `sofer prepare --help`
- WHEN the help is rendered
- THEN `--output`, `--all-files`, `--no-checks`, `--force`, and `--verify` SHALL be listed

#### Scenario: publish help lists all flags

- GIVEN `sofer publish --help`
- WHEN the help is rendered
- THEN `--target`, `--output`, `--force`, `--keep-csv`, and `--dry-run` SHALL be listed

#### Scenario: No stale upload

- GIVEN the parser description and the `init` template
- WHEN the CLI is built
- THEN neither SHALL mention `upload`
- AND the README SHALL document `prepare` and `publish` instead

#### Scenario: No stale upload and raw/ layout
- GIVEN parser + template
- WHEN built
- THEN neither mentions `upload`, README documents `prepare`/`publish` and `raw/` layout, and `init` template contains `raw/` guidance with no stale `data/` hint

---

### Requirement: profile and render are top-level subcommands (CLI-R03)

The system SHALL register `profile` and `render` as top-level subcommands, alongside `validate`, `prepare`, `publish`, `codebook`, `init`, and `scan`. Each SHALL accept `--output`, `--force`, `--all-files`, and `--config`. Positional is `dataset`/`package` for single-file; when `--all-files` is set the positional MUST be a TOML path containing `[[file]]` and the handler MUST iterate entries (PRF-05/RND-04); without `[[file]]` it MUST fail fast. Single-file without `--force` MUST guard existing dest (PRF-06/RND-05).

(Previously: only `dataset`/`package` + `--output`; no batch, no --force, no TOML contract.)

#### Scenario: profile and render appear in help

- GIVEN `sofer --help`
- WHEN the help is rendered
- THEN `profile` SHALL appear as a subcommand
- AND `render` SHALL appear as a subcommand

#### Scenario: profile dispatches correctly

- GIVEN `sofer profile dataset.csv`
- WHEN the command executes
- THEN the profile handler SHALL run with `dataset.csv` as its argument

#### Scenario: render dispatches correctly

- GIVEN `sofer render ./build/`
- WHEN the command executes
- THEN the render handler SHALL run with `./build/` as its argument

#### Scenario: profile --all-files dispatches batch

- GIVEN `sofer profile dataset.toml --all-files`
- WHEN the command executes
- THEN handler SHALL iterate `[[file]]` and write per-entry outputs

#### Scenario: render --all-files dispatches batch

- GIVEN `sofer render dataset.toml --all-files`
- WHEN the command executes
- THEN handler SHALL iterate `[[file]]` and write per-entry READMEs

#### Scenario: TOML without [[file]] errors

- GIVEN TOML with no `[[file]]`
- WHEN `--all-files` executes
- THEN exit code SHALL be non-zero mentioning `[[file]]`

### Requirement: Help text accurate for profile and render (CLI-R04)

The parser's `help=` and `description=` strings for `profile` and `render` SHALL accurately document each command, its flags `--output`, `--all-files`, `--force`, `--config`, the TOML `[[file]]` contract for `--all-files`, and the `use --force to overwrite` guard. The README SHALL be updated in the same change.

(Previously: only described profiling into metadata.yaml / rendering README.md.)

#### Scenario: profile help accurate

- GIVEN `sofer profile --help`
- WHEN the help is rendered
- THEN the help SHALL describe profiling a dataset into `metadata.yaml`
- AND SHALL list `--output`, `--all-files`, `--force`, `--config`

#### Scenario: render help accurate

- GIVEN `sofer render --help`
- WHEN the help is rendered
- THEN the help SHALL describe rendering `README.md` from `metadata.yaml`
- AND SHALL list `--output`, `--all-files`, `--force`, `--config`

---

### Requirement: --version reports the installed release version (CLI-R05)

> Added by change `installable-cli-pypi` (archived 2026-08-26).

`sofer --version` SHALL print `sofer v<version>` where `<version>` is resolved
at runtime from installed distribution metadata — never from a static constant.
The output SHALL be non-empty and PEP 440-valid, and SHALL work from an
installed console script without `uv run`.

#### Scenario: Released install reports the tag version

- GIVEN a non-editable install of a wheel built at tag `v0.3.0`
- WHEN `sofer --version` runs
- THEN stdout SHALL be `sofer v0.3.0` and the exit code SHALL be 0

#### Scenario: Dev install reports a derived version

- GIVEN a dev/editable install with no release tag at HEAD
- WHEN `sofer --version` runs
- THEN the printed version SHALL be non-empty and PEP 440-valid
- AND it SHALL NOT equal any hardcoded literal

#### Scenario: Standalone console script works

- GIVEN an installed (non-editable) console script
- WHEN `sofer --version` runs as a subprocess outside the repository
- THEN the exit code SHALL be 0 and stdout SHALL be non-empty

---

### Requirement: Document stamping uses the shared version resolver (CLI-R06)

> Added by change `installable-cli-pypi` (archived 2026-08-26).

The version stamped into generated documents (`generated.version` in
`metadata.yaml`) SHALL be produced by the SAME shared runtime resolver that
backs `--version`. The static `__version__` constant SHALL be removed; in
dev/editable contexts where installed metadata is unavailable, the resolver
SHALL fall back to a non-empty derived value.

#### Scenario: Stamped version equals the CLI version

- GIVEN a `profile` run in any install context
- WHEN the generated `metadata.yaml` is inspected
- THEN `generated.version` SHALL equal the value printed by `sofer --version`
- AND it SHALL be non-empty

#### Scenario: No static version constant remains

- GIVEN the package source
- WHEN searched for version definitions
- THEN no hardcoded `__version__` string literal SHALL exist
- AND installed-metadata lookup (with dev fallback) SHALL be the version source

---

### Requirement: init creates raw/ and --move-existing (CLI-R07)

> Modified by `fix-sofer-init-cwd-windows-todo` (archived 2026-08-31). Modified by `fix-dataset-identity-context` (archived 2026-09-04).

`sofer init <name> --user <user>` SHALL require an explicit `--user` (missing → argparse usage error, exit 2, no write). Identity SHALL be validated pre-write via the shared contract (INIT-05): missing/blank/placeholder (`YOUR_USER` or any `_PLACEHOLDERS` value)/unsafe/injection-shaped name or user SHALL be rejected with exit 1 BEFORE any write — no `<name>.toml`, no `raw/`; the generated TOML SHALL NEVER contain `YOUR_USER`. The success line SHALL print the canonical ABSOLUTE `config_path`. `init` MUST create `raw/` (`RAW_DIR`) via `mkdir -p` idempotently alongside `<name>.toml`. `--dry-run` SHALL perform NO writes in EITHER branch (plain init and `--move-existing` alike): no `<name>.toml`, no `raw/`, no moves — it SHALL print `DRY RUN  Would create <name>.toml` / `DRY RUN  Would scaffold <RAW_DIR>` (plus move preview lines under `--move-existing`) and exit 0, matching the MCP `sofer_init(dry_run=True)` no-mutation semantics. Template SHALL state `# Source files → raw/ (scan copies to cache/)` and `[[file]] local` MUST be Windows-safe `raw/example.csv` (no `:`, `ntpath.splitdrive` → `""`, valid NTFS). `--move-existing` SHALL move depth-1 supported files (`SUPPORTED_FORMATS`, direct children of cwd, excluding `cache`/`build`/`raw`/EXCLUSIONS) into `raw/` with: `check_flatten_collisions` before any move; collision with existing `raw/` content → fail naming sources; `--force` or non-interactive skip prompt, else prompt `[y/N]` and abort on `N`. Without flag, loose files stay.

(Previously: `--user` optional defaulting to the `YOUR_USER` placeholder; no identity validation; a relative filename was printed.)

#### Scenario: init creates raw/

- GIVEN no `raw/`
- WHEN `sofer init my-ds --user myuser`
- THEN `raw/` exists and `my-ds.toml` contains `raw/` comment

#### Scenario: Idempotent

- GIVEN `raw/` exists with files
- WHEN `sofer init other --user myuser`
- THEN succeeds, `raw/` unchanged

#### Scenario: Depth-1 only supported

- GIVEN `a.csv`, `subdir/b.csv`, `notes.txt`, `cache/c.csv`
- WHEN `sofer init my-ds --user myuser --move-existing --force`
- THEN only `a.csv` → `raw/a.csv`

#### Scenario: Collision guard

- GIVEN `raw/a.csv` exists and loose `a.csv` exists
- WHEN `--move-existing --force`
- THEN fail naming both, no move

#### Scenario: Dry-run preview

- GIVEN loose `a.csv`, `b.xlsx`
- WHEN `--move-existing --dry-run`
- THEN lists `a.csv → raw/a.csv`, no move, no TOML written, `raw/` not created if absent, exit 0

#### Scenario: Dry-run plain init no mutation

- GIVEN `sofer init my-ds --user myuser --dry-run` (no `--move-existing`)
- THEN exit 0 with `DRY RUN  Would create my-ds.toml` and `DRY RUN  Would scaffold raw` preview lines, and neither `my-ds.toml` nor `raw/` SHALL be created

#### Scenario: Non-interactive guard

- GIVEN loose `a.csv`, `not isatty`, no `--force`
- WHEN `--move-existing`
- THEN skip move, `raw/` still created, message hints `--force`

#### Scenario: Prompt N aborts

- GIVEN loose `a.csv`, tty
- WHEN `--move-existing` user `N`
- THEN no move, exit 0

#### Scenario: Template mentions raw/

- GIVEN `sofer init my-ds --user myuser` done
- WHEN `my-ds.toml` inspected
- THEN contains `raw/` guidance, no stale `data/` hint

#### Scenario: Windows-safe placeholder

- GIVEN `sofer init my-ds --user myuser`
- WHEN `my-ds.toml` inspected
- THEN `local="raw/example.csv"`, no `":"`

#### Scenario: ntpath drive

- GIVEN `raw/example.csv`
- WHEN `ntpath.splitdrive` win32
- THEN `("", "raw/example.csv")`

#### Scenario: scan xlsx after init

- GIVEN `my-ds.toml` + `DATA_GOT_ALL.xlsx`
- WHEN `sofer scan` then `validate`
- THEN `cache/DATA_GOT_ALL.xlsx` registered, validate pass

#### Scenario: --user required

- GIVEN `sofer init my-ds` with no `--user`
- WHEN the command executes
- THEN argparse SHALL exit 2 naming the missing `--user` and NO file SHALL be written

#### Scenario: Placeholder user rejected pre-write

- GIVEN `sofer init my-ds --user YOUR_USER`
- WHEN the command executes
- THEN exit 1 SHALL name the placeholder and neither `my-ds.toml` nor `raw/` SHALL be created

#### Scenario: Unsafe identity rejected pre-write

- GIVEN `sofer init "a/../b" --user myuser` (or a name/user with quotes, newline, drive, or separator)
- WHEN the command executes
- THEN exit 1 SHALL name the invalid component and NO file SHALL be written

#### Scenario: canonical config_path printed

- GIVEN `sofer init my-ds --user myuser` run from `<abs>/proj`
- WHEN the command succeeds
- THEN stdout SHALL print the absolute `config_path` `<abs>/proj/my-ds.toml`

### Requirement: Help for init --move-existing (CLI-R08)

`sofer init --help` SHALL document `raw/` creation and `--move-existing`/`--dry-run`/`--force` (depth 1, `SUPPORTED_FORMATS`, collision, non-interactive). Description SHALL mention `raw/→cache/→build/`.

#### Scenario: Help lists flags
- GIVEN `sofer init --help`
- WHEN rendered
- THEN `--move-existing`, `--dry-run`, `--force` SHALL appear

---

### Requirement: mcp add/remove help (CLI-R09)

> Added by change `feat-mcp-registration-automation` (archived 2026-09-09).
> Extended by change `2026-09-12-fix-mcp-opencode-env` (additive env-forwarding scenario).
> Extended by change `2026-09-25-feat-pi-mcp-agent` (#142) — `pi` added to the agent set.
> Extended by change `2026-09-25-fix-mcp-native-delegation` (#167/#232) — native
> delegation fidelity sentence.
> Extended by change `2026-10-09-feat-mcp-hermes-adapter` (#272) — `hermes` added to the agent set,
> with the YAML preservation and single-scope sentences.

`sofer` MUST expose `mcp` with `add`/`remove`. `add` MUST accept `--agent <opencode|codex|gemini|pi|hermes|all> [--scope user|project] [--cwd PATH] [--user-config PATH] [--dry-run]`; `remove` MUST accept `--agent <opencode|codex|gemini|pi|hermes|all> [--scope user|project] [--user-config PATH] [--dry-run]`. Help for `sofer --help` and `sofer mcp*` MUST list these.

`add` and `remove` MUST also accept `--user-config PATH`: the explicit user-scope config **file**,
which wins over the adapter's env override and the home default, and which MUST be rejected with
`--agent all` because one path cannot name four different agent config files.

The `sofer mcp add` help text SHALL additionally document env-forwarding behavior: codex, gemini, pi and hermes receive env forwarding with names only (gemini as `$KEY` references, pi and hermes as `${KEY}` references), and opencode entries carry no environment, so a warning is emitted when `HF_TOKEN`/`SOFER_MCP_APPROVAL_PHRASE` are set and `--agent opencode` (or `all`) is chosen. The help text SHALL also document that a YAML config edit preserves the rest of the document while a TOML edit may strip comments, and that `hermes` reads a single user-scope config, so `--scope project` resolves to that same file and the substitution is named on stderr.

The `sofer mcp add` / `sofer mcp remove` help text SHALL also document native
delegation fidelity: native `codex`/`gemini` delegation is used only when the
native CLI can faithfully forward the same env NAMES and scope as the file edit,
and when it cannot the config file is edited instead with a warning on stderr.

(Previously: CLI-R09 documented only the flag surface and the env-forwarding
behavior; native delegation fidelity was not part of the help contract. #167/#232
add the fidelity sentence.)

#### Scenario: mcp in top help

- GIVEN `sofer --help` rendered
- WHEN inspected
- THEN `mcp` SHALL appear

#### Scenario: mcp lists children

- GIVEN `sofer mcp --help` rendered
- WHEN inspected
- THEN `add` and `remove` SHALL appear

#### Scenario: add help

- GIVEN `sofer mcp add --help`
- WHEN rendered
- THEN `--agent`, `--scope`, `--cwd`, `--user-config`, `--dry-run` SHALL be listed
- AND the `--agent` choices SHALL include `opencode`, `codex`, `gemini`, `pi`, `hermes` and `all`

#### Scenario: remove help

- GIVEN `sofer mcp remove --help`
- WHEN rendered
- THEN `--agent`, `--scope`, `--user-config`, `--dry-run` SHALL be listed
- AND the `--agent` choices SHALL include `opencode`, `codex`, `gemini`, `pi`, `hermes` and `all`

#### Scenario: add help documents env forwarding

- GIVEN `sofer mcp add --help`
- WHEN rendered
- THEN the description SHALL state that codex, gemini, pi and hermes receive env forwarding (names only)
- AND the description SHALL state that opencode entries carry no environment and that a warning is emitted when `HF_TOKEN`/`SOFER_MCP_APPROVAL_PHRASE` are set with `--agent opencode` (or `all`)

#### Scenario: add help documents the YAML preservation and the single-scope note

- GIVEN `sofer mcp add --help`
- WHEN rendered
- THEN the description SHALL distinguish the YAML edit (preserves the rest of the document) from the TOML edit (may strip comments)
- AND the description SHALL state that `hermes` reads a single user-scope config and that `--scope project` resolves to it with a warning on stderr

#### Scenario: help documents native delegation fidelity

- GIVEN `sofer mcp add --help` (and `sofer mcp remove --help`)
- WHEN rendered
- THEN the description SHALL state that native delegation is used only when it can forward the same env NAMES and scope as the file edit
- AND the description SHALL state that when it cannot, the config file is edited with a warning on stderr

### Requirement: Machine-readable status as stable JSON (CLI-R10)

CLI status output that is machine-readable SHALL be stable JSON, not a Python dictionary `repr`. Where a command already emits a status/result line for tools or agents to consume, that line SHALL serialize to JSON with the same stable keys as the MCP envelope contract (`ok`, `exit_code`, `phase`, `requires`, `next`, `config_path`, `dataset_root`, `error_code`, `message`, `config_errors`) or a documented subset, keeping parity between CLI and MCP status.

(Previously: CLI status was human prose; machine-readable status, where present, was not contractually JSON.)

#### Scenario: CLI status line is parseable JSON

- GIVEN a CLI command that emits a machine-readable status line
- WHEN the line is parsed
- THEN it SHALL decode as JSON with the documented stable keys

#### Scenario: CLI status does not leak Python syntax

- GIVEN a command that emits status
- THEN `repr`-style Python literals (e.g. `{'ok': True}`) SHALL NOT appear; only JSON appears

### Requirement: Console output survives an unencodable character (CLI-R11)

> Added by change `2026-09-13-fix-cli-console-encoding` (archived 2026-09-13).

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

### Requirement: Optional explicit CSV dialect flags (CLI-R12)

> Added by change `2026-09-25-csv-dialect-override` (GitHub #204).

`sofer codebook` and `sofer profile` SHALL accept optional `--delimiter` /
`--encoding` arguments on both their single-file and `--all-files` forms, defaulting
to `None` ("not supplied"). When supplied, the explicit value SHALL win over the
applicable configured value (single-file: the post-reload tool-wide
`config.CSV_DELIMITER` / `config.CSV_ENCODING`; `codebook --all-files`: the dataset
`[meta]`). When omitted, behaviour SHALL be byte-identical to the pre-change
command — no new line, no changed output.

When at least one explicit value is supplied, the command SHALL echo the supplied
override on **stderr** in a single informational line naming only the supplied
keys (e.g. `  i  Explicit dialect: delimiter=',' encoding='utf-8'`), so the
single-file codebook's stdout stays pure markdown. The `.tsv` format SHALL remain
tab-delimited; the explicit delimiter SHALL apply to `.csv` only.

The `codebook` and `profile` `help=` / `description=` strings SHALL document the new
flags and their "explicit wins over config" precedence.

#### Scenario: flags are listed in help

- GIVEN `sofer codebook --help`
- WHEN rendered
- THEN `--delimiter` and `--encoding` SHALL be listed
- AND the `profile` help SHALL likewise list both flags

#### Scenario: explicit value wins over config

- GIVEN `[tool.sofer] csv_delimiter = ";"` and a `.csv` using `,`
- WHEN `sofer codebook FILE --delimiter ,` runs
- THEN the codebook SHALL reflect the explicit `,`

#### Scenario: omitted flags preserve behaviour

- GIVEN the same invocation without `--delimiter` / `--encoding`
- WHEN it runs
- THEN the output SHALL be byte-identical to the pre-change command
- AND stderr SHALL carry no explicit-dialect line

#### Scenario: explicit dialect echoed on stderr

- GIVEN an explicit `--delimiter` and/or `--encoding` is supplied
- WHEN the command runs
- THEN stderr SHALL carry one line naming the supplied key(s)
- AND stdout SHALL NOT carry the echo

#### Scenario: both commands accept the flags

- GIVEN `sofer profile DATASET --delimiter , --encoding utf-8`
- WHEN it runs
- THEN both explicit values SHALL be applied to the CSV/TSV read

### Requirement: Assisted CLI failure reporting with consent and confidentiality (CLI-R13)

> Added by change `2026-09-25-feat-cli-failure-report` (issue #244).

When an uncaught exception escapes a CLI command, the CLI MUST print the original traceback
(preserving today's failure output) and, **only when `sys.stdin` is a TTY**, offer to open a
GitHub issue in the configured repository. Nothing SHALL be created without explicit consent:
the user MUST first confirm the offer, then review the complete issue body, then confirm the
send. Declining either prompt MUST create nothing and MUST NOT change the exit code (`1`).

The report context SHALL be a strict allowlist — the command and its arguments, the exception
type and message, the traceback, the `sofer` version, the Python version, and the platform. The
report MUST NEVER include dataset contents (no row, sample, cell value, or excerpt), MUST NEVER
include the value of any environment variable (at most a variable NAME when it has diagnostic
value, and this change includes none), and MUST anonymize local paths by replacing the user's
home directory with `~` in POSIX and Windows forms. The body printed for review MUST be
byte-identical to the body that is sent or persisted.

#### Scenario: Non-interactive failure never prompts and never creates

- GIVEN a command that raises an uncaught exception and `sys.stdin` is not a TTY
- WHEN the CLI runs
- THEN it SHALL print the traceback and exit `1`
- AND it SHALL NOT create a GitHub issue, persist a report file, or prompt

#### Scenario: Declining creates nothing

- GIVEN an interactive failure and the user answers `N` to the "report?" prompt
- WHEN the CLI runs
- THEN no issue SHALL be created and no report file SHALL be written
- AND the exit code SHALL remain `1`

#### Scenario: Accepting reviews the exact body before sending

- GIVEN an interactive failure and the user answers `y` to the "report?" prompt
- WHEN the review prompt is shown
- THEN the complete anonymized body SHALL be printed
- AND the issue SHALL be created (or persisted on failure) only after the user answers `y` to the second prompt
- AND the reviewed body SHALL equal the body sent/persisted

#### Scenario: Report excludes data, secrets, and identifying paths

- GIVEN a failure whose traceback and arguments embed a home-directory path and an environment variable value
- WHEN the report body is built
- THEN the home directory SHALL appear as `~` and the absolute home path SHALL be absent
- AND no environment-variable value SHALL appear (only the documented allowlisted facts)
- AND no dataset content SHALL appear

### Requirement: Persisted-report retry and offline fallback (CLI-R14)

> Added by change `2026-09-25-feat-cli-failure-report` (issue #244).

Filing a report depends on `gh` being present, authenticated, and the network being reachable.
When any of these fails, the flow MUST NOT lose the report. It SHALL persist **one** file per
failure under sofer's state directory (`_state_home() / failure_report_dir`), named with a UTC
timestamp and the process id, and MUST NOT overwrite an existing file. The persisted document
SHALL carry the repository, title, body, and creation timestamp.

When persisting, the CLI SHALL print the path, the retry command
`sofer report-failure "<path>"`, the manual fallback URL
`https://github.com/<repo>/issues/new` with the body pre-loadable for copy/paste, and the
permanent fix `gh auth login`.

The `sofer report-failure <file>` subcommand SHALL load a persisted report and re-run the send
path through `gh`; on success it SHALL print the created issue URL, and on failure it SHALL
re-emit the same recovery layers without losing the file.

#### Scenario: Missing auth or network persists and prints the triple safety net

- GIVEN an accepted report and `gh` missing, unauthenticated, or offline
- WHEN the CLI attempts to send
- THEN exactly one report file SHALL be written under the configured state directory with a timestamped name
- AND the output SHALL name the file path, the `sofer report-failure` retry command, the manual `github.com/<repo>/issues/new` URL, and `gh auth login`

#### Scenario: One file per failure, never overwritten

- GIVEN two failures in the same second
- WHEN both reports are persisted
- THEN two distinct files SHALL exist and neither SHALL be overwritten

#### Scenario: Retry sends a persisted report

- GIVEN a persisted report file and a working authenticated `gh`
- WHEN `sofer report-failure <file>` runs
- THEN the issue SHALL be created and its URL printed
- AND the command SHALL exit `0`
