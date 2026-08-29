# Tool-wide configuration ([tool.sofer])

Tool-wide defaults live in a `pyproject.toml` under `[tool.sofer]`. Every
value has a sensible default — the whole section is optional.

## Discovery and precedence

sofer resolves the section by walking up the directory tree, in this fixed
order:

1. **Dataset directory** — once a dataset TOML is loaded (e.g.
   `sofer prepare mydata/dataset.toml`), the nearest `pyproject.toml`
   walking up from the TOML's directory wins. This is where per-project
   overrides normally live.
2. **Current working directory** — if no `pyproject.toml` is found above the
   dataset, sofer walks up from the directory the command was invoked in.
   This also covers single-file commands such as `sofer codebook FILE` or
   `sofer profile FILE`, which have no dataset TOML.
3. **Built-in defaults** — if neither walk finds anything, all values fall
   back to the built-in defaults below.

The first `pyproject.toml` found stops the search (matching ruff/pytest
conventions). A found file without a `[tool.sofer]` section contributes no
overrides — the walk does not continue past it.

> **Behavior change for editable installs:** sofer no longer reads its *own*
> repository `pyproject.toml` at runtime. If you maintain sofer and run it
> from an editable install, your user-project overrides now come from the
> project you are working on — not from sofer's repo. Put your `[tool.sofer]`
> section there instead.

## Bootstrap keys (cwd-only)

Two keys are needed *before* any dataset TOML is known:

- `default_config_name` (used to build CLI defaults, e.g. for
  `sofer scan [config]` and `codebook --config`)
- `output_dir` (used by `scan`/`init` before a config is validated)

These honor `[tool.sofer]` overrides only via the **cwd walk-up** at startup.
Once a dataset TOML is loaded, they are re-resolved from the dataset-dir
walk like every other key; the cwd-only limitation applies only to that
pre-config window.

## Seeing which file was used

Set `SOFER_VERBOSE=1` to make sofer print one line on **stderr** describing
where the tool-wide configuration came from:

```text
[tool.sofer] source: /home/me/myproj/pyproject.toml
[tool.sofer] source: built-in defaults
```

Stdout is never modified, so piping/redirecting output stays byte-identical.

## Parquet conversion

| Key | Default | What it does |
|---|---|---|
| `convert_to_parquet` (per `[[file]]`) | `true` | When `true`, `csv/tsv/xlsx/jsonl` are converted to normalized Parquet (`data/GÖT Año.XLSX` → `data/got_ano.parquet`; Excel multi-sheet → `stem__sheet.parquet`). Set `false` to keep the original. `upload_as_csv = true` is a deprecated alias for CSV only. |
| `parquet_compression` | `zstd` | Parquet compression (`[tool.sofer]`). |
| `parquet_row_group_size` | `100000` | Parquet row group size. |
| `parquet_shard_warning_mb` | `500` | Warn when a shard exceeds this MB. |

## Metadata inference tuning

The inference pipeline (used by `profile`) is fully configurable in
`pyproject.toml` — no magic numbers in code:

```toml
[tool.sofer]
# Confidence prior per semantic detector (pattern reliability).
# Higher = the pattern alone is more trustworthy.
semantic_priors = { email = 0.98 }

# Status thresholds (confidence bands).
confirm_threshold = 0.8   # >= this → confirmed
min_threshold = 0.5       # >= this → inferred; below → unknown
detect_threshold = 0.5    # match_rate below this → no detection at all

# Profiling sample size (statistics are computed over a bounded sample, never
# a full in-memory load — and reported as such).
profile_max_sample = 100000

# Confidence is rounded to this many decimal places before it is stored.
confidence_round_digits = 4
```