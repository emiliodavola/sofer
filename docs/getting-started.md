# Getting started

sofer turns a raw dataset into a documented, profiled, and quality-assessed
package that can be published to Hugging Face Hub or copied to a local
directory.

## Requirements

- Python 3.10 or newer.
- A Hugging Face username or organization only when you publish to the Hub.
- `HF_TOKEN` only for a Hub publish. Local builds never need credentials.

## Install

sofer is a standalone CLI. Install it from the git tag of the release you want;
replace `X.Y.Z` with that tag.

```bash
# with uv (isolated tool install):
uv tool install "sofer @ git+https://github.com/emiliodavola/sofer.git@vX.Y.Z" --force

# or with pip:
pip install "sofer @ git+https://github.com/emiliodavola/sofer.git@vX.Y.Z"

# alias — same wheel, explicit extra:
pip install "sofer[mcp] @ git+https://github.com/emiliodavola/sofer.git@vX.Y.Z"

# transient run without installing:
uvx --from git+https://github.com/emiliodavola/sofer.git@vX.Y.Z --with "sofer[mcp]" sofer-mcp --help
```

`fastmcp` is included by default; `sofer[mcp]` is an alias for the same wheel.
Verify the install with:

```bash
sofer --help
sofer --version
```

`sofer --version` matches the release tag (`v0.6.2` installs as
`sofer v0.6.2`).

## Quick start

```bash
# 1. Generate a configuration template and scaffold raw/
sofer init my-dataset --user myuser

# 2. Scan for data files.
#    Phase 1 MOVEs loose supported files into raw/; Phase 2 copies raw/ -> cache/.
sofer scan my-dataset.toml

# 3. Fill the human metadata step in my-dataset.toml.
#    The agent can infer description and tags; a human supplies license and source.
sofer meta check my-dataset.toml
sofer meta set my-dataset.toml \
  --set description="What the dataset contains" \
  --set license=MIT \
  --set source="Some organisation" \
  --set tags=census,tabular

# 4. Build the package locally — no network calls.
sofer prepare my-dataset.toml

# 5. Inspect the package in build/:
#    Parquet files, README.md (Dataset Card), LICENSE, schema report.
#    Building locally is NOT publishing.

# 6. Publish as a separate, explicit step.
sofer publish my-dataset.toml --dry-run   # review the plan
sofer publish my-dataset.toml             # Hugging Face Hub (needs HF_TOKEN)
# or copy the package to a local directory, with no network:
sofer publish my-dataset.toml --target local --output ./out/
```

Repositories are private by default. Publishing to a public target is a
separate decision and requires an explicit authorization; see
[Security](security.md).

## Full walkthrough

Run `sofer init` from the dataset directory. The CLI uses the live working
directory, so `my-dataset.toml` and `raw/` are created exactly where you run
it.

```bash
# 1. Create a template (--user sets repo_id to "myuser/my-dataset").
#    The placeholder [[file]] local = "raw/example.csv" is Windows-safe:
#    it has no colon and is a valid NTFS path.
sofer init my-dataset --user myuser

# 2. Discover and register files.
#    scan auto-registers CSV, TSV, Parquet, Excel, and JSONL files.
sofer scan my-dataset.toml              # preview first with --dry-run

# 3. Fill [meta]. See "Human metadata step" below.
sofer meta check my-dataset.toml

# 4. Build the package locally. Zero network calls:
#    Parquet conversion, Dataset Card (README.md), LICENSE, schema report.
sofer prepare my-dataset.toml

#    Optionally include per-file codebooks in the package.
sofer prepare my-dataset.toml --all-files

# 5. Validate locally. Never contacts Hugging Face.
sofer validate my-dataset.toml

# 6. Publish. This auto-prepares when artifacts are missing or stale.
sofer publish my-dataset.toml                  # default target: hf
sofer publish my-dataset.toml --dry-run        # show the diff and split report
sofer publish my-dataset.toml --target local --output ./out/   # no network
```

`publish` re-runs `prepare` automatically whenever the package is missing or
stale: the TOML, or any declared source file, is newer than the newest Parquet.

## Human metadata step

`sofer init` writes `[meta]` placeholders. Filling them is a required step
between bootstrap and the build. On an MCP-driven run the agent completes what
the data can determine (description, tags) and the human supplies what it
cannot (license, source).

`sofer meta check` reports the same warning `sofer validate` prints:
a field is a placeholder when it is empty or still starts with `TODO`,
`YOUR_`, or `example`. The check is informational and exits 0 whatever it
reports.

`sofer meta set` writes keys into `[meta]` while preserving every other key,
comment, and table. Text values are verbatim, list values are comma-separated,
and flags are `true` or `false`:

```bash
sofer meta set my-dataset.toml \
  --set description="Census microdata, 2020" \
  --set license=CC-BY-4.0 \
  --set source="National statistics office" \
  --set tags=census,population \
  --set confidential=true
```

The settable surface has 39 keys — every `[meta]` key the pipeline reads. See
[Dataset configuration](dataset-config.md#meta) for the full list.

## The package tree

```text
raw/     tracked source root — loose data files are moved here, then copied to cache/
cache/   sofer artifact cache (gitignored) — scan destination and profile/render batch output
build/   prepare output and publish input (per-dataset [dataset] build_dir, default "build")
```

Pipeline: `raw/` (tracked) → `cache/` (gitignored) → `build/` (gitignored).

```text
raw/DPTO.csv                -> cache/DPTO.csv                -> build/*.parquet
raw/Labels/etiquetas_a.csv  -> cache/Labels/etiquetas_a.csv  -> build/*.parquet
```

`scan` is MOVE-then-copy. The move is mandatory: it keeps the registered
sources in `raw/`, not only in the disposable `cache/`. See
[Dataset configuration](dataset-config.md#source-layout) for the full rules.

## MCP walkthrough

The MCP server exposes the same pipeline. **Every MCP session must call
`sofer_init` first**; it is the only tool admitted while the session is
uninitialized. Attach an existing dataset with `config`, or create a greenfield
one with `name`/`user`/`cwd`. The canonical order for a greenfield dataset is:

```python
sofer_init(name="test", user="<hf-user>", cwd="C:/Users/.../Desktop/test")
sofer_scan_dry_run(config="test.toml")  # preview — no writes
sofer_scan_apply(config="test.toml")  # register files and copy to cache/
sofer_meta_check(config="test.toml")
sofer_meta_set(config="test.toml", values={"description": "...", "license": "MIT"})
sofer_validate(config="test.toml")
sofer_prepare(config="test.toml")
sofer_codebook_all(config="test.toml")
sofer_profile_all(config="test.toml")
sofer_render_all(config="test.toml")
sofer_publish(config="test.toml", dry_run=True)  # STOP — human reviews build/
sofer_auth_status(config="test.toml")  # preflight
# after approval:
sofer_publish_confirm(config="test.toml", acknowledge_risk=True)
```

For an existing dataset, the session gate is the read-only attach:

```python
sofer_init(config="test.toml")  # no files written
sofer_validate(config="test.toml")
# ... Phase 1 Build and Phase 2 Publish as above
```

See [MCP server](mcp.md) for the full tool surface and
[Agent setup](agent-setup.md) for registration and timeouts.

## Windows

Always run `sofer init` from the dataset directory, use forward slashes in TOML
(`raw/example.csv`), and let `scan` replace the placeholder with real entries.
The full notes, including `cwd`, per-call `root`, and console encoding, live in
[Troubleshooting](troubleshooting.md#windows).

## Next steps

- [CLI reference](cli.md) for every command and flag.
- [Data package](data-package.md) for formats, quality checks, codebooks,
  profiling, and rendering.
- [Tool-wide configuration](configuration.md) for `[tool.sofer]`.
