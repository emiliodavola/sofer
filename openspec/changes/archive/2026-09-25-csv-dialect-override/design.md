# Design: 2026-09-25-csv-dialect-override

## Context

Both surfaces resolve the CSV dialect from config today and pass it into a shared
reader:

- `codebook.generate(csv_path, output_path, delimiter, encoding, max_sample)` —
  the CLI (`_cmd_codebook`) and MCP (`sofer_codebook`) already pass the resolved
  tool-wide values in; `generate_all` additionally accepts `delimiter`/`encoding`
  overrides that win over `cfg.csv_*`.
- `profile.profile` / `profile.generate_all_profiles` — compute the dialect from
  `config.CSV_*` internally and expose no override.

The change threads one optional pair from the adapters into those resolution points
so an explicit value sits **above** whatever config tier the command uses.

## Decisions

### D1 — The only "not supplied" sentinel is `None`

argparse defaults `--delimiter`/`--encoding` to `None`; the MCP parameters default
to `None`. Every adapter resolves:

```python
delimiter = explicit_delimiter if explicit_delimiter is not None else configured_delimiter
encoding = explicit_encoding if explicit_encoding is not None else configured_encoding
```

No truthiness test (`""` would be a user error, not "unset"), and no frozen literal.
This makes the omitted path reuse the exact expression it uses today.

### D2 — The configured tier is the command's existing tier, not a new one

- Single-file `codebook` / `profile` (CLI and MCP): tool-wide post-reload
  `config.CSV_DELIMITER` / `config.CSV_ENCODING`.
- Batch (`--all-files`, `sofer_codebook_all`, `sofer_profile_all`): the dataset
  `[meta]` `cfg.csv_delimiter` / `cfg.csv_encoding`, which is the authoritative
  source already (MSP-R10). `codebook.generate_all` already resolves `None` this way;
  `profile.generate_all_profiles` gains the same two parameters and resolves them
  identically.

No config tier is added, removed, or reordered (issue non-goal: "Not changing the
config tiers … anchored in TC-02/TC-04"). The explicit value is an **additional**
tier above the existing ones.

### D3 — `.tsv` keeps tab; the delimiter override targets `.csv`

`codebook._read_tsv` and `profile._stream_columns` force `\t` for `.tsv` by format.
The design preserves that: only `.csv` consumes the explicit delimiter; `.csv` and
`.tsv` both consume the explicit encoding. This is stated in the help text and in
PRF-07 / CB-R12.

### D4 — Batch override is an explicit opt-in above the dataset `[meta]` tier

For `codebook --all-files`, `sofer_codebook_all`, and `sofer_profile_all`, a
supplied value overrides `cfg.csv_*` for every file. This is deliberate: the
dataset `[meta]` remains the default (authoritative, per-file-independent), and a
caller who states one dialect for a mixed batch accepts that statement. No new
"per-file dialect map" is introduced.

### D5 — The override is echoed for traceability

The issue requires both surfaces to echo which dialect was used when an explicit
value was supplied:

- **CLI** — a single informational line on **stderr**, so `sofer codebook FILE`
  keeps stdout as pure markdown:

  ```text
    i  Explicit dialect: delimiter=',' encoding='utf-8'
  ```

  Only the supplied keys are listed (delimiter-only, encoding-only, or both). A
  helper `_echo_explicit_dialect(args)` owns this and is exercised for all three
  shapes.

- **MCP** — an optional `"dialect"` key added to the return envelope when at
  least one parameter was supplied:

  ```python
  {"delimiter": delimiter, "encoding": encoding}
  ```

  The key is declared in each tool's `output_schema` (FastMCP materializes every
  declared non-required field, so an undeclared key would be dropped at the
  boundary) and is `null` when neither parameter is supplied. The dialect
  resolution itself is unchanged in the omitted path.

### D6 — Parameter descriptions state the fallback

Every MCP parameter is declared, so the schema test
`test_every_param_has_description` requires a description. The descriptions are:

```python
delimiter: "Explicit CSV field delimiter for this call; when omitted, the configured value applies."
encoding:  "Explicit CSV file encoding for this call; when omitted, the configured value applies."
```

### D7 — `profile.py` gains exactly one optional pair, resolved in one place

```python
def profile(dataset_path, output_dir=None, *, force=False, delimiter=None, encoding=None) -> int
def generate_all_profiles(cfg, output_dir=None, delimiter=None, encoding=None) -> list[str]
def _read_dataset_for_profile(path, suffix, delimiter=None, encoding=None) -> tuple[...]
```

`profile` and `_read_dataset_for_profile` share the resolution:

```python
if suffix in _STREAMED_FORMATS:
    delim = "\t" if suffix == ".tsv" else (delimiter if delimiter is not None else config.CSV_DELIMITER)
    enc = encoding if encoding is not None else config.CSV_ENCODING
```

The `FileMetadata.encoding`/`delimiter` fields record the values actually used, so a
profile produced under an explicit override is self-describing.

### D8 — `codebook.py` is untouched

`generate` already accepts `delimiter`/`encoding`; `generate_all` already resolves
`None`. The adapters simply pass the explicit value where they currently pass the
configured one. No domain change, no new default.

## Contract / invariants

- Resolution is exactly `explicit → configured → existing reader fallback` on both
  surfaces and both tiers.
- `None` (never a truthiness test) is the sentinel; the omitted path is
  byte-identical to today, pinned by an omitted-case test per surface.
- `.tsv` stays tab-delimited; `.csv` consumes the explicit delimiter; both consume
  the explicit encoding.
- The explicit value never mutates config state and never leaks to another
  invocation (per-call parameters only).
- Every new MCP parameter is optional and described; no `required` list changes.
- `cli.py` keeps 100.00% line coverage with no `# pragma: no cover` (rule 14).

## Test strategy

- `tests/test_cli.py` — `codebook`/`profile`, explicit delimiter wins over a
  disagreeing `[tool.sofer]`; explicit encoding wins; omitted output equals the
  pre-change output for the same fixture; stderr echo for delimiter-only,
  encoding-only, both; `--all-files` override wins over `[meta]`; help lists the
  flags. Every new `cli.py` branch exercised.
- `tests/test_mcp_server.py` — the four tools: explicit wins, omitted unchanged,
  `"dialect"` present only when supplied, descriptions present.
- `tests/test_mcp_schema.py` — the new parameters exist and are described, never
  required.
- `tests/test_profile.py` — `profile(...)` / `generate_all_profiles(...)` explicit
  override; `.tsv` stays tab; `FileMetadata` records the used dialect.

## Consequences

- A caller who knows the dialect no longer has to write `pyproject.toml` or rely on
  a correct `[meta]`; the tool's default config-optional posture is preserved.
- `scan` intentionally has no dialect parameter (it reads no CSV bytes); the issue's
  "scan tools" mention is realized by `profile`, the second content-reading surface.
- A batch override is a single dialect for every file — correct when stated, and
  never the default.
