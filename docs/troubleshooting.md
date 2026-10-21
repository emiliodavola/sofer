# Troubleshooting

## Windows

| Topic | What to do | Why / detail |
| --- | --- | --- |
| **CLI CWD** | Always run `sofer init` from the dataset directory (for example `C:\Users\...\test`). The CLI uses live `Path.cwd()`, so `test.toml` and `raw/` are created exactly where you run it. | Running from the parent creates `test.toml` and `raw/` in the wrong place. `cd` into the dataset directory first. |
| **MCP `cwd` argument** | The server root is chosen at startup by `--root PATH` or `SOFER_MCP_ROOT` (the argument wins; with neither, the resolved process cwd). `sofer_init` has an optional `cwd`. When `cwd` is `None`, it uses the live `Path.cwd()` only when that is a strict descendant of the server root; otherwise the call is refused, naming the required `cwd="<dataset dir>"` argument. It does not fall back to the server root. An explicit `cwd="C:/Users/.../Desktop/test"` is a per-call `effective_root` and never mutates the global root. | An explicit `cwd` outside the server root is rejected with `PathOutsideRootError` (no `../` above root, no `C:/evil`, no symlink escape). The `cwd=None` case is contained by a strict `is_relative_to` descendant check. |
| **MCP per-call `root`** | Every path-bearing tool except `sofer_report_failure` accepts `root="<existing directory>"` and runs that one call against it. The envelope echoes `effective_root`, and a bound continuation carries `root` when it differs from the registration root. Omitted or blank keeps the registration root. `SOFER_MCP_ROOT_ALLOWLIST` (read once at server start, `os.pathsep`-separated — `;` on Windows, `:` on POSIX) admits only roots equal to or below an entry; the registration root and omitted-`root` calls are never gated. | Relative `root` values anchor on the registration root, never the cwd. A missing path, a file, or a root outside the allowlist raises `RootUnavailableError`. Resources still read the server root; use the tool with `root` to read another tree. |
| **Placeholder** | The template uses `local = "raw/example.csv"` — valid NTFS, because `:` is reserved for drive letters and alternate data streams. The old `TODO: raw/...` was invalid and made `sofer_validate` fail. After `init`, run `sofer scan` to replace the placeholder with real entries. | `raw/example.csv` is a harmless stub. `scan` overwrites the `[[file]]` list with discovered files via `registration_path`, keyed relative to `raw/`. |
| **Path separators** | Always write `raw/` and `cache/` with forward slashes in TOML (`raw/example.csv`, `cache/file.csv`). Both CLI and MCP normalize to POSIX internally. | Works on Windows and POSIX. `ntpath.splitdrive` would treat `C:/...` as absolute, but `raw/...` stays relative and contained. |
| **Console encoding** | Nothing to do: the CLI never aborts on a character the active console encoding cannot represent. The character is substituted in the emitted text and the command keeps its documented exit code (CLI-R11). Unicode-capable terminals (Windows Terminal, VS Code, macOS, Linux) are unaffected and keep sofer's markers. | Affects streams that are not a Unicode-capable console: output redirected to a file or pipe (`sofer scan --help > out.txt`), an IDE or CI capture, or a legacy code page forced with `PYTHONIOENCODING=cp1252`. Set `PYTHONIOENCODING=utf-8` to keep every marker. |

Reproducible greenfield chain on Windows, run from the correct directory:

```bat
sofer init test --user <hf-user>
sofer scan test.toml              # or: sofer scan --dry-run first
sofer validate test.toml
sofer prepare test.toml
sofer codebook --all-files --config test.toml
sofer publish test.toml --dry-run
sofer publish test.toml           # after human approval
```

If a previous buggy run left `test.toml` or `raw\` in the parent directory,
delete them. Re-running `sofer init` from the correct dataset directory is
idempotent and will not duplicate parent artifacts.

## Hugging Face uploads

`sofer publish --target hf` delivers the whole package with a single
`upload_folder` call. When that call fails, sofer prints the underlying
exception type and message plus the active transfer backend, and retries once.
A total failure reports `Result: 0 uploaded, N failed` and, when the repository
ends up empty, says so explicitly.

The package manifest on disk is the object of record for both the plan and the
enforcement. `prepare` writes `build/manifest.json`; every later build phase
(`codebook_all`, `profile_all`, `render_all`) refreshes it; and `publish` reads
it instead of deriving its own. A manifest that does not declare the delivery
the tree holds — a file it omits, or one it promises and the tree no longer has
— is refused before any network call, and so is a record that cannot be read
(`UNREADABLE_MANIFEST`).

Recovery is the same in both cases: re-run the build chain and retry.

```bash
sofer prepare my-dataset.toml --force --all-files
sofer publish my-dataset.toml
```

`--dry-run` only warns about a manifest mismatch and still prints the plan.

Per-file codebooks are required exactly when the package carries the root
`codebook.md` index: an index with no page under `codebooks/` blocks the
confirm, while a package that never generated codebooks keeps them optional and
ships without a warning.

### `0 uploaded, N failed` with an I/O error

Re-run with the xet transfer backend disabled before assuming the package or the
token is wrong:

```bash
# macOS / Linux
HF_HUB_DISABLE_XET=1 sofer publish my-dataset.toml

# Windows (PowerShell)
$env:HF_HUB_DISABLE_XET = "1"; sofer publish my-dataset.toml
```

`HF_HUB_DISABLE_XET` is read once, when `huggingface_hub` is imported, so it
must be set in the environment of the `sofer` process; setting it after the
process starts has no effect.

The retry count, probed environment-variable names, and error-message cap are
`[tool.sofer]` defaults: `hf_upload_retry_count`, `hf_backend_disable_env`,
`hf_backend_prefix_env`, and `hf_upload_error_max_chars`. See
[Tool-wide configuration](configuration.md).

## MCP connection failures

`sofer-mcp` imports pandas, pyarrow, datasets, and fastmcp before it can answer
`initialize`. A first launch after an install or upgrade is slower than a warm
one, and a host may report `Connection failed … timed out` even though the
registration is correct.

Measure the real cold start and compare it with the configured budget:

```bash
sofer mcp doctor
sofer mcp doctor --agent opencode --json
```

`doctor` spawns the server (or the module entry point when the console script is
not on `PATH`) and times the stdio `initialize` round trip. The budget is
`[tool.sofer] mcp_connect_timeout_seconds`; exceeding it is informational and
never changes the exit code. Raise the written deadline with
`sofer mcp add --connect-timeout SECONDS`, or omit the timeout keys with
`--no-timeout`.

Long tool calls reset their own deadline through progress notifications. Their
`tools/list` descriptions say so and name the expected duration. See
[Agent setup](agent-setup.md#host-timeouts).

## Init gate refusals

Every MCP session must call `sofer_init` before any other tool; a host that
skips it (or opens a new session) receives a structured refusal rather than a
tool error:

| `error_code` | Fix |
| --- | --- |
| `INITIALIZATION_REQUIRED` | Call `sofer_init` first. Attach an existing dataset with `config="<dataset.toml>"`, or create one with `name`, `user`, and `cwd`. Follow the envelope's `next` for the exact arguments. |
| `INITIALIZATION_IN_PROGRESS` | An init is still running in this session. Wait for its result, then retry the original call; do not send a second init. |
| `INITIALIZATION_CONTEXT_BUSY` | Another admitted request is still executing. Retry the init after it finishes; the active dataset stays valid. |
| `INITIALIZATION_CONTEXT_MISMATCH` | The call targets a different `root` or `config` than the active one. Run `sofer_init` for that target; there is no silent switch. |
| `INITIALIZATION_SESSION_UNAVAILABLE` | The transport exposes no live session. Use the shipped stdio transport. |

A `dry_run=true` init never unlocks the session: its continuation points back
to the same init with `dry_run=false`. A failed attach also leaves the session
uninitialized, and a supplied `config` never falls back to creating a dataset.

## Assisted failure reporting

When a CLI command fails with an uncaught error, sofer prints the traceback and,
on an interactive terminal only, offers to file a GitHub issue in the repository
configured by `failure_report_repo`. Nothing is filed without explicit consent,
and you review the complete body before it is sent.

The report contains only the command and its arguments, the error and traceback,
and the `sofer` / Python / platform versions. It never contains dataset contents
or environment-variable or secret values, and it replaces your home directory
with `~` in every path inside the report.

```bash
# interactive: answer "y" at the prompt to review and send the report
sofer validate my-dataset.toml
```

If `gh` is missing, unauthenticated, or the network is down, the report is
written to one timestamped JSON file per failure under the sofer state directory
(`~/.local/state/sofer/failure-reports/`; `%LOCALAPPDATA%\sofer\failure-reports`
on Windows). sofer prints the saved path, the retry command, the manual
`github.com/<repo>/issues/new` URL, and the permanent fix `gh auth login`.

```bash
# retry a persisted report once gh is authenticated / online
sofer report-failure ~/.local/state/sofer/failure-reports/failure-20260925T101112000000Z-12345.json
```

The state location can be overridden with `SOFER_STATE_HOME`. The target
repository and report bounds are `[tool.sofer]` keys; see
[Tool-wide configuration](configuration.md#assisted-failure-reporting).

## Related

- [Getting started](getting-started.md) for the canonical chain.
- [CLI reference](cli.md) for flags.
- [Configuration](configuration.md) for `[tool.sofer]`.
