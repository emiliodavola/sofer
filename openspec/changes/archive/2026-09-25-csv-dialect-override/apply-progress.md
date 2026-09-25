# Apply progress: 2026-09-25-csv-dialect-override

**Branch:** `feat/204-csv-dialect-override` (base `dev@e9d5101`, PR-only)
**Issue:** #204 (`type:feature`, `status:approved`)

## What changed

### `src/sofer/profile.py`

- `profile(...)` gained keyword-only `delimiter: str | None = None` /
  `encoding: str | None = None`. For streamed formats the explicit value wins
  over `config.CSV_*`; `.tsv` stays `\t`; non-streamed formats keep `""`.
  `FileMetadata.encoding`/`delimiter` record the values actually used.
- `_read_dataset_for_profile(...)` + `generate_all_profiles(...)` thread the same
  pair through the batch path.
- `_stream_columns(...)` accepts an optional initial encoding.

### `src/sofer/cli.py`

- `_add_dialect_args(parser)` adds `--delimiter` / `--encoding` (default `None`)
  to the `codebook` and `profile` subparsers.
- `_echo_explicit_dialect(args)` prints the supplied override(s) to stderr, naming
  only the supplied keys.
- `_cmd_codebook` / `_cmd_profile` resolve explicit → config on both tiers and
  forward the pair (`generate_all` already resolves `None` → `cfg.csv_*`).
- Help/description strings document the flags and precedence.

### `src/sofer/mcp_server.py`

- `sofer_codebook`, `sofer_codebook_all`, `sofer_profile`, `sofer_profile_all`
  gained optional `delimiter` / `encoding` (default `None`) with fallback-stating
  descriptions.
- `_dialect_envelope(...)` returns `{"dialect": None}` when neither is supplied,
  else `{"dialect": {"delimiter": ..., "encoding": ...}}`.
- `dialect` is declared in the four tools' `output_schema`
  (`_DIALECT_ENVELOPE_SCHEMA_FIELD`) — FastMCP materializes declared fields, so an
  undeclared key would be dropped at the boundary.
- `sofer_codebook_all` now passes `delimiter=delimiter` (previously
  `cfg.csv_delimiter`) — `generate_all` resolves `None` identically, so the
  omitted path is unchanged.

### Tests

- `tests/test_cli.py::TestExplicitCsvDialectOverride` (10)
- `tests/test_mcp_server.py::TestExplicitCsvDialectOverrideMcp` (6)
- `tests/test_mcp_schema.py::TestExplicitDialectParams` (3)
- `tests/test_profile.py::TestProfileExplicitDialectPrf07` (5)
- `tests/test_parity.py`: the two new CLI flags declared in the `codebook` and
  `profile` `flag_map`.

### Docs & specs

- README.md + README_ES.md (flags, precedence, `.tsv` carve-out, MCP `dialect`).
- Delta specs CB-R12 / PRF-07 / CLI-R12 / MSP-R18 + canonical sync.

## Decisions taken in apply

- **`dialect` is always present on the MCP success envelope** (`null` when neither
  parameter was supplied), because FastMCP's `output_schema` validation
  materializes every declared non-required field. The CLI omitted path is
  genuinely unchanged (no echo, same resolution expression).
- **`.tsv` keeps its format-enforced tab delimiter**; only `.csv` consumes the
  explicit delimiter (matches the pre-existing `_read_tsv` / `_stream_columns`
  behaviour).
- **`scan` is intentionally left without a dialect parameter** — it never reads
  CSV bytes; `profile` is the second content-reading surface the issue's "scan
  tools" wording maps to.
