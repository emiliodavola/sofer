# CLI reference

`sofer` is a standalone command-line tool. Run `sofer --help` for the command
list and `sofer <command> --help` for the flags of one command.

Most commands take a dataset TOML path. `scan` and single-file `codebook` /
`profile` / `render` can use `[tool.sofer] default_config_name` when the path is
omitted. See [Tool-wide configuration](configuration.md).

## Commands

| Command | Description |
| --- | --- |
| `init <name>` | Generate a ready-to-edit TOML template and scaffold `raw/`. Requires `--user USER` for `repo_id "USER/<name>"`. A missing `--user` exits 2; a placeholder (`YOUR_USER`) or unsafe identity exits 1 before any write. The success line prints the absolute `config_path`. |
| `scan [config.toml]` | MOVE loose supported files to `raw/<relative>` preserving the tree, then key each file relative to `raw/`, register it in the TOML, and copy it to `cache/`. Flags: `--dry-run`, `--force`, `--ext`. |
| `validate <config.toml>` | Verify config, data integrity, and quality checks. Never contacts Hugging Face. |
| `prepare <config.toml>` | Build the full package locally: CSV/TSV/XLSX/JSONL to Parquet, cross-file schema checks, schema report, Dataset Card (`README.md`), `LICENSE`, and optionally per-file codebooks. Never contacts Hugging Face. |
| `publish <config.toml>` | Deliver the prepared package. Default target `hf`; `--target local` copies it with no network. Auto-prepares when artifacts are missing or stale. |
| `codebook [FILE]` | Generate a markdown codebook for one file, or one codebook per `[[file]]` entry with `--all-files`. |
| `profile [DATASET]` | Introspect a dataset read-only and write `metadata.yaml` with schema, semantic types, and possible PII. With `--all-files`, `DATASET` is the TOML file. |
| `render [PACKAGE]` | Render a status-annotated `README.md` from `metadata.yaml`; `PACKAGE` is the file or its directory. With `--all-files`, `PACKAGE` is the TOML file. |
| `meta check <config.toml>` | Report `[meta]` fields that still carry an `init` placeholder. Read-only and informational: exit code 0 whatever it reports; only an unreadable config exits 1. `--json` emits the stable status object. |
| `meta set <config.toml> --set KEY=VALUE` | Write `[meta]` keys while preserving every other key, comment, and table. `--set` is repeatable. `--dry-run` reports the plan; `--json` emits the stable status object. |
| `mcp add --agent <opencode\|codex\|gemini\|pi\|hermes\|all>` | Register `sofer-mcp` with the selected agent(s). Idempotent, preserves other servers, backs up to `.bak`, and writes atomically. |
| `mcp remove --agent <...\|all>` | Remove `sofer-mcp` from the selected agent(s). Idempotent and atomic. |
| `mcp doctor [--agent <...\|all>] [--json]` | Measure the real cold start by spawning `sofer-mcp` and timing the stdio `initialize` round trip. Informational; reads and writes nothing. |
| `report-failure <file>` | Retry sending a failure report persisted by the assisted failure reporter. |
| `sofer-mcp` | Launch the MCP server over stdio. It exposes 19 tools, 4 resources, and 3 prompts; `fastmcp` is included by default. See [MCP server](mcp.md). |

`sofer upload` was removed in favor of `prepare` + `publish`: generation is
offline and inspectable, delivery is the network step.

## `init`

```bash
sofer init my-dataset --user myuser
sofer init my-dataset --user myuser --move-existing --dry-run
```

| Flag | Meaning |
| --- | --- |
| `--user USER` | Hugging Face username or organization for `repo_id` (required). |
| `--move-existing` | Move depth-1 supported files (`.csv`, `.tsv`, `.parquet`, `.xlsx`, `.jsonl`) from the current directory into `raw/`. Subdirectories are ignored; `cache/`, `build/`, `raw/`, and `EXCLUSIONS` are never moved. |
| `--dry-run` | Preview without writing: no TOML, no `raw/`, no moves. |
| `--force` | Skip the `[y/N]` prompt. The prompt is also skipped when not running on a terminal. |

The template uses `local = "raw/example.csv"` — a Windows-safe placeholder with
no colon.

## `scan`

```bash
sofer scan my-dataset.toml --dry-run
sofer scan my-dataset.toml
sofer scan my-dataset.toml --ext csv --ext jsonl
```

| Flag | Meaning |
| --- | --- |
| `--dry-run` | Preview the move (`-> raw/<rel>`) and the copy. No `raw/` creation, no moves, no cache writes, no TOML update. |
| `--force` | Skip the `[y/N]` prompt and overwrite existing `cache/` files. A collision still aborts before any move. |
| `--ext EXT` | Filter the scan to specific extensions (repeatable). Omitted means all supported formats. |

Running `scan` twice is safe: already-registered files are skipped, and the
reported count is the number of `[[file]]` entries appended by this run.

## `validate`

```bash
sofer validate my-dataset.toml
```

No flags beyond `--help`. It reads the TOML, checks that files exist, checks
minimum size and expected columns, runs the streaming quality checks, and prints
a report. It never contacts Hugging Face.

## `prepare`

```bash
sofer prepare my-dataset.toml
sofer prepare my-dataset.toml --all-files --verify
```

| Flag | Meaning |
| --- | --- |
| `--output DIR` | Output directory (default: `[dataset] build_dir`, usually `build/`). |
| `--all-files` | Also generate per-file codebooks directly into the output directory. |
| `--no-checks` | Skip the structural and quality validation report (checks run by default and are non-blocking). |
| `--force` | Overwrite existing generated artifacts. |
| `--verify` | Run `datasets.load_dataset()` against the package and print `PASSED`/`FAILED`. Non-blocking. |

With `--force`, stale files that are not in the expanded planned remotes are
pruned, along with `README.md`, `LICENSE`, `codebook.md`, and `codebooks/**`.
Without `--force`, orphans are left in place.

## `publish`

```bash
sofer publish my-dataset.toml --dry-run
sofer publish my-dataset.toml
sofer publish my-dataset.toml --target local --output ./out/
```

| Flag | Meaning |
| --- | --- |
| `--target {hf,local}` | `hf` (default) ensures the repository, gates on quality, and pushes in one `upload_folder` call. `local` copies the package to `--output` with no network. |
| `--output DIR` | `hf`: override the prepare output directory. `local`: destination directory. |
| `--force` | Skip overwrite protection and overwrite remote files. |
| `--keep-csv` | Keep the original CSV alongside the converted Parquet. `hf` target only; CSV-only. |
| `--dry-run` | Show the repo diff and split report without preparing or uploading. |
| `--clean` | Delete the build directory after a successful `hf` publish (`fail == 0`, quality passed, not a dry run). For `local`, delete the resolved destination only. |
| `--clean-cache`, `--all` | With `--clean`, also delete `cache/` (`OUTPUT_DIR`, shared across datasets). Requires explicit opt-in. |

The package manifest on disk is the object of record for the plan and the
enforcement. See [Troubleshooting](troubleshooting.md#hugging-face-uploads) for
the recovery when the manifest and the tree disagree.

## `codebook`

```bash
sofer codebook raw/persons.csv -o codebook.md
sofer codebook --all-files --config my-dataset.toml
sofer codebook raw/persons.csv --delimiter ";" --encoding utf-8-sig
```

| Flag | Meaning |
| --- | --- |
| `-o, --output FILE` | Output file. Default: print to stdout. |
| `--max-sample N` | Maximum rows sampled for analysis (default: `codebook_max_sample`). |
| `--all-files` | Generate codebooks for every `[[file]]` entry. |
| `--config CONFIG` | TOML config for `--all-files` (default: `default_config_name`). |
| `--delimiter D` | Explicit CSV delimiter; wins over the configured `csv_delimiter`. Applies to `.csv` only; `.tsv` stays tab-delimited. |
| `--encoding E` | Explicit CSV encoding; wins over the configured `csv_encoding`. Applies to `.csv` and `.tsv`. |

## `profile`

```bash
sofer profile raw/contacts.csv
sofer profile dataset.toml --all-files
sofer profile raw/contacts.csv --output ./out --force
```

| Flag | Meaning |
| --- | --- |
| `--output DIR` | Output directory. Default: next to the dataset. With `--all-files`, relative paths anchor to the TOML directory. |
| `--all-files` | Profile every `[[file]]` entry in the TOML config. |
| `--force` | Overwrite an existing `metadata.yaml`. |
| `--config CONFIG` | TOML config for `--all-files`. |
| `--delimiter D` / `--encoding E` | Explicit CSV dialect for this invocation, as in `codebook`. |

Without `--force`, an existing destination raises `FileExistsError` with the
hint `use --force to overwrite <path>`.

## `render`

```bash
sofer render raw/
sofer render raw/metadata.yaml
sofer render dataset.toml --all-files
```

| Flag | Meaning |
| --- | --- |
| `--output DIR` | Output directory. Default: the `metadata.yaml` directory. With `--all-files`, relative paths anchor to the TOML directory. |
| `--all-files` | Render every `[[file]]` entry from its profile. Missing `metadata.yaml` entries are skipped. |
| `--force` | Overwrite an existing `README.md`. |
| `--config CONFIG` | TOML config for `--all-files`. |

## `meta`

```bash
sofer meta check my-dataset.toml
sofer meta set my-dataset.toml --set license=MIT --set tags=census,tabular
sofer meta set my-dataset.toml --set description="..." --dry-run --json
```

`meta check` flags `[meta]` fields that are empty or still start with `TODO`,
`YOUR_`, or `example` (the `meta_placeholder_prefixes` values).

`meta set` reads a value by the key's kind: text verbatim, a list as
comma-separated items (`--set tags=a,b`, empty for `[]`), and a flag as
`true`/`false`. The write is atomic, a refusal writes nothing, and re-running
with the same values writes nothing. A `build/` tree older than the edit is
named on stderr; rerun `prepare` to refresh its card and LICENSE.

The settable surface has 39 keys; see
[Dataset configuration](dataset-config.md#meta).

## `mcp`

```bash
sofer mcp add --agent all
sofer mcp add --agent opencode --scope project --cwd ./my-proj
sofer mcp add --agent gemini --scope user --dry-run
sofer mcp remove --agent all
sofer mcp doctor --json
```

| Flag | Commands | Meaning |
| --- | --- | --- |
| `--agent` | `add`, `remove`, `doctor` | `opencode`, `codex`, `gemini`, `pi`, `hermes`, or `all`. |
| `--scope` | `add`, `remove` | `user` (home directory) or `project` (current directory). |
| `--cwd PATH` | `add` | Absolute working directory for the server; must be an existing directory. A tree outside the home and the process cwd is accepted with a warning naming it. |
| `--user-config PATH` | `add`, `remove` | Explicit user-scope config file. Wins over the adapter's env override and the home default. Rejected with `--agent all`. |
| `--timeout SECONDS` | `add` | Per-request tool-call deadline. Default: `[tool.sofer] mcp_request_timeout_seconds`. A non-positive value exits 2. |
| `--connect-timeout SECONDS` | `add` | Initial-connection / cold-start deadline. Default: `[tool.sofer] mcp_connect_timeout_seconds`. |
| `--no-timeout` | `add` | Omit the timeout keys, restoring the pre-#287/#296 entry shape and native codex/gemini delegation. |
| `--dry-run` | `add`, `remove` | Preview without writing; no file or `.bak` is created. |
| `--json` | `doctor` | Emit the stable machine-readable status object. |

See [Agent setup](agent-setup.md) for the per-agent locations, shapes, and
timeout units.

## `report-failure`

```bash
sofer report-failure ~/.local/state/sofer/failure-reports/failure-20260925T101112000000Z-12345.json
```

Sends a report persisted by the assisted failure reporter. On success it prints
the created issue URL. If `gh` is still missing, unauthenticated, or offline, it
prints the saved path, this retry command, the manual
`github.com/<repo>/issues/new` URL, and `gh auth login`.

## Flags at a glance

| Flag | Commands | What it does |
| --- | --- | --- |
| `--keep-csv` | `publish` (HF only) | Upload the original CSV alongside the Parquet. |
| `--no-checks` | `prepare` | Skip the validation report and build anyway. |
| `--force` | `init`, `prepare`, `publish`, `profile`, `render`, `scan` | Overwrite artifacts or destination files and skip the interactive confirmation. |
| `--dry-run` | `init`, `publish`, `scan`, `mcp add`, `mcp remove`, `meta set` | Preview without side effects. |
| `--clean` | `publish` | Delete the build after a successful Hub publish; for `local`, delete the resolved destination. |
| `--clean-cache` / `--all` | `publish` (with `--clean`) | Also delete the shared `cache/`. |
| `--all-files` | `codebook`, `prepare`, `profile`, `render` | Generate one artifact per `[[file]]` entry. Requires entries; collisions raise `ValueError`. |
| `--config` | `codebook`, `profile`, `render` | TOML path for `--all-files`. |
| `--delimiter` / `--encoding` | `codebook`, `profile` | Explicit CSV dialect for this invocation. Resolution: explicit → configured → reader fallback. A supplied value is echoed on stderr. |
| `--ext EXT` | `scan` | Filter by extension (repeatable). |
| `--user USER` | `init` | Hugging Face username or organization. Required. |
| `--output DIR/FILE` | `codebook`, `prepare`, `publish`, `profile`, `render` | Output location; for `codebook`, `-o/--output` is a file path. |
| `--json` | `meta check`, `meta set`, `mcp doctor` | Emit the stable machine-readable status object. |
