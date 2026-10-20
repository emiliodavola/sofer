# MCP server

sofer ships a Model Context Protocol (MCP) server that exposes the same
deterministic pipeline to AI agents over stdio. No LLM is called, and the only
network access is the Hugging Face upload inside `sofer_publish_confirm`.

The server exposes **19 tools**, **4 resources**, and **3 prompts**:

```bash
sofer-mcp          # stdio MCP server (JSON-RPC 2.0 over stdin/stdout)
```

`fastmcp` is included in the default dependencies. `sofer[mcp]` is an alias for
the same wheel, not a separate installation requirement:

```bash
pip install "sofer @ git+https://github.com/emiliodavola/sofer.git@vX.Y.Z"
pip install "sofer[mcp] @ git+https://github.com/emiliodavola/sofer.git@vX.Y.Z"   # alias
uv tool install "sofer @ git+https://github.com/emiliodavola/sofer.git@vX.Y.Z" --force
uvx --from git+https://github.com/emiliodavola/sofer.git@vX.Y.Z --with "sofer[mcp]" sofer-mcp --help
```

For registration, environment forwarding, and timeouts, see
[Agent setup](agent-setup.md). For containment and publish authorization, see
[Security](security.md).

## Canonical build chain

`tools/list` is self-sufficient. The phased order is:

```text
Phase 0 Bootstrap [conditional: REQUIRED if greenfield — no TOML or empty [[file]]]
  sofer_init -> sofer_scan_dry_run / sofer_scan_apply -> sofer_meta_set
  Metadata step between bootstrap and Phase 1:
  sofer_meta_check reports placeholders; sofer_meta_set writes description,
  license, source, tags, and any other card key.

Phase 1 Build:
  sofer_validate -> sofer_prepare -> sofer_codebook_all
  -> sofer_profile_all -> sofer_render_all

Phase 2 Publish:
  sofer_publish(dry_run=True) -> STOP (human approval)
  -> sofer_publish_confirm
```

- **Phase 0** `init` → `scan` is required for greenfield datasets (no `.toml`
  or empty `[[file]]`) and optional otherwise. Build assumes `[[file]]` entries
  exist.
- Each tool lists `Requires:` and `Next:`, so `tools/list` alone teaches the
  order. Server `instructions` is the single source for the phased diagram and
  the untrusted-content disclaimer.
- `sofer_auth_status` is the preflight. It checks `token`, `confidential`, and
  `approval_phrase` without network access, and reports the configured
  visibility. `check_remote=true` adds the repository's current visibility with
  one read-only call.
- `sofer_repo_settings` reads the same posture and can set the target
  visibility. A write needs the approval phrase and the exact state
  (`private=true|false`). A publish whose configured visibility differs from the
  repository's is refused.

## Tools

| Step | Tool | Key arguments | When to use |
| --- | --- | --- | --- |
| 0 | `sofer_init` | `name`, `user`, `cwd`, `move_existing`, `dry_run`, `force` | Greenfield bootstrap; creates the TOML and `raw/`. `cwd` must stay under the server root; `raw/example.csv` is Windows-safe. |
| 0 | `sofer_scan_dry_run` / `sofer_scan_apply` | `config`, `force`, `extensions` | Phase 0 preview/apply after `init`. Both MOVE loose files into `raw/` unconditionally; the preview does not mutate. |
| M | `sofer_meta_check` | `config` | Read the metadata state without running the validator. Reports the same warning `sofer_validate` prints. |
| M | `sofer_meta_set` | `config`, `values`, `dry_run` | Write `[meta]` before Phase 1. Preserves every other key and comment. `build_stale` names a build tree that predates the write. With no `values` it writes nothing and returns a continuation asking for them. |
| M | `sofer_file_set` | `config`, `entries`, `dry_run` | Replace the `[[file]]` array. The only MCP way to declare a recursive folder entry, `column_types`, `convert_to_parquet` / `upload_as_csv`, or `include_in_schema`. Every local path must exist under the server root. A folder remote that would double-register a file entry is refused; an empty list is refused while entries exist. |
| 1 | `sofer_validate` | `config` | Quick check; always first for existing datasets. |
| 2 | `sofer_prepare` | `config`, `output_dir`, `run_checks`, `force`, `verify` | After validate; writes Parquet, `README.md`, and `LICENSE`. |
| 3 | `sofer_codebook_all` | `config`, `output_dir`, `delimiter`, `encoding` | After prepare; batch codebooks. |
| 4a | `sofer_profile` | `dataset`, `output_dir`, `force`, `delimiter`, `encoding` | Single-file triage (`assess_dataset`). |
| 4b | `sofer_profile_all` | `config`, `output_dir`, `delimiter`, `encoding` | Phase 1 batch profile under `cache/profiles/`. |
| 5a | `sofer_render` | `package`, `output_dir`, `force` | Single-file render after `sofer_profile`. |
| 5b | `sofer_render_all` | `config`, `output_dir` | Phase 1 batch render under `cache/renders/`; requires `profile_all`. |
| 6 | `sofer_publish` | `config`, `target="local"`, `output_dir`, `force`, `dry_run` | `dry_run=True` preview; stop before confirm. |
| 7 | `sofer_publish_confirm` | `config`, `target="hf"`, `output_dir`, `acknowledge_risk`, `acknowledge_confidential`, `acknowledge_public`, `approval_phrase`, `force` | Only after human approval. A public target (`[dataset] private = false`) needs its own `acknowledge_public`; `acknowledge_risk` covers the irreversible upload, not the exposure. The envelope records the posture. |
| * | `sofer_auth_status` | `config`, `check_remote` | Preflight without publish; reports the configured visibility and, with `check_remote=true`, the repository's current one. |
| * | `sofer_repo_settings` | `config`, `private`, `approval_phrase`, `dry_run` | Read the target repository's visibility and posture. `private` plus `approval_phrase` sets the visibility and needs a token. |
| * | `sofer_codebook` | `path`, `output_file`, `max_sample`, `delimiter`, `encoding` | Single-file codebook. |
| * | `sofer_report_failure` | `error`, `command`, `trace`, `confirm`, `force` | Prepare a confidential failure report and, only with `confirm=true`, file it via `gh` after searching open issues for duplicates. |

`sofer_report_failure` never includes dataset contents or environment-variable
values and anonymizes home paths to `~`. With the default `confirm=false` it
returns the prepared body, title, manual URL, and any matching open issues
without creating anything. With `confirm=true` it files the issue, or persists
it locally when `gh` is missing, unauthenticated, or offline. See
[Troubleshooting](troubleshooting.md#assisted-failure-reporting).

## Resources

Resource URIs resolve relative to the server root. For example,
`sofer://dataset/dataset.toml` reads `<root>/dataset.toml`. Absolute POSIX paths
are also accepted through the rest-pattern templates: `sofer://dataset//tmp/...`
arrives with a leading `/` and must still resolve inside the root.

| Resource | Meaning |
| --- | --- |
| `sofer://dataset/{config_path*}` | Dataset TOML. |
| `sofer://codebook/{data_file*}` | Codebook for a data file. |
| `sofer://metadata/{data_file*}` | Profile metadata for a data file. |
| `sofer://status` | Static server posture snapshot: `approval_configured`, `phrase_source`, `root`, `version`, `started_at`, `tool_count`. Never reads a dataset file. |

`sofer_auth_status` reports the same root as `server_root`, so an agent can
preflight reachability before a write attempt. A containment refusal keeps the
`<what> resolves outside the server root` prefix and appends the resolved root
plus the remedy (`set SOFER_MCP_ROOT or --root at server start, then restart the
host`).

Resources always read the server root. To read another dataset tree, pass the
tool's per-call `root` argument instead of changing the resource root.

## Prompts

| Prompt | Chain |
| --- | --- |
| `prepare_dataset` | Full bootstrap/build/publish chain with per-step arguments and copy-paste examples. |
| `assess_dataset` | `sofer_validate` → `sofer_profile(dataset)` → `sofer_render(package)` for single-file triage. |
| `finalize_and_publish` | Review, dry-run, approval, and confirm. |

## Response contracts

Successful calls return an envelope with:

- `ok` (boolean);
- `exit_code` (integer);
- `output` (string);
- tool-specific fields such as `confidential`, `config_errors`, `placeholders`,
  `files`, or `posture`.

Expected failures return a structured envelope instead of throwing:

```text
{ok: false, error_code: ..., message: ..., next: ..., config_errors: [...]}
```

`next` is the continuation hint. For a long call it may carry `root` when the
per-call root differs from the registration root.

Arguments follow the CLI semantics:

- `config` is the TOML path and must stay under the server root.
- `dataset` / `package` name a single file or the `metadata.yaml` directory.
- `output_dir` / `output_file` override the destination, or are `None` for the
  default.
- `run_checks` replaces the old `no_checks` flag.
- `force` is the overwrite guard.
- `cwd` on `sofer_init` is a per-call `effective_root` under the server root,
  never a mutation of the global root.
- Batch calls use the `*_all(config)` tools; there is no `all_files` flag.

Optional `delimiter` / `encoding` on the CSV-reading tools
(`sofer_codebook`, `sofer_codebook_all`, `sofer_profile`,
`sofer_profile_all`) state the CSV dialect for that call. The explicit value
wins over the configured one (dataset `[meta]` for the `_all` tools,
`[tool.sofer]` otherwise). Omitting both keeps the current behavior. The
response echoes the supplied values in `dialect` (`null` when neither is
supplied). `.tsv` stays tab-delimited; the explicit delimiter applies to
`.csv`.

## Compatibility

These changes are pre-1.0 (v0.4) and are kept here because they still matter to
users upgrading older MCP integrations:

- `output` → `output_file` (`sofer_codebook`) / `output_dir` (all others).
- `no_checks` → `run_checks=True`.
- `sofer_profile` / `sofer_render` split into `sofer_profile` +
  `sofer_profile_all` and `sofer_render` + `sofer_render_all`; `all_files` was
  removed.
- `target` is now `Literal["local"]` / `Literal["hf"]` (single-value const).
- Expected failures return the structured envelope instead of throwing.

## Copy-paste chain

```python
sofer_validate(config="dataset.toml")
sofer_prepare(config="dataset.toml", output_dir=None, run_checks=True)
sofer_codebook_all(config="dataset.toml", output_dir=None)
sofer_profile_all(config="dataset.toml", output_dir=None)
sofer_render_all(config="dataset.toml", output_dir=None)
sofer_publish(
    config="dataset.toml", dry_run=True
)  # STOP — get approval before sofer_publish_confirm
sofer_auth_status(config="dataset.toml")  # preflight
# after approval:
sofer_publish_confirm(config="dataset.toml", acknowledge_risk=True)
```

Path-bearing tools accept `root="<existing directory>"` for a single call; see
[Security](security.md#path-containment) for the containment rules.
