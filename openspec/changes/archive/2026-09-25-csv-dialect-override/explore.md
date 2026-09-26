# Explore: 2026-09-25-csv-dialect-override

## Question

Issue #204 asks for an **optional explicit CSV dialect override** — `--delimiter` /
`--encoding` on the CLI and optional `delimiter` / `encoding` parameters on the MCP
tools — that **wins over config** for a single invocation, while leaving today's
behaviour byte-identical when the caller supplies neither. Which surfaces actually
read CSV/TSV bytes, and what precedence do they currently use?

## Findings

### Surfaces that parse CSV/TSV content

| Surface | Reader | Dialect today | Wrong dialect visible? |
|---------|--------|---------------|------------------------|
| CLI `sofer codebook FILE` | `codebook.generate` → `_csv_reader.stream_csv` | `config.CSV_DELIMITER` / `config.CSV_ENCODING` at call time (CB-R11) | yes — header collapses to one column |
| CLI `sofer codebook --all-files` | `codebook.generate_all` | `cfg.csv_delimiter` / `cfg.csv_encoding` (`[meta]`, authoritative) → `None` override already supported | yes |
| CLI `sofer profile DATASET` | `profile.profile` → `stream_csv` | `config.CSV_DELIMITER` / `config.CSV_ENCODING` | yes — schema/columns wrong |
| CLI `sofer profile --all-files` | `profile.generate_all_profiles` → `_read_dataset_for_profile` | `config.CSV_DELIMITER` / `config.CSV_ENCODING` | yes |
| MCP `sofer_codebook` | `codebook.generate` | post-reload `sofer_config.CSV_*` (MSP-R10) | yes |
| MCP `sofer_codebook_all` | `codebook.generate_all` | `cfg.csv_*` (MSP-R10) | yes |
| MCP `sofer_profile` | `profile.profile` → `stream_csv` | post-reload `config.CSV_*` | yes |
| MCP `sofer_profile_all` | `profile.generate_all_profiles` | `config.CSV_*` | yes |

### Surfaces named by the issue that do NOT read CSV content

`sofer scan` (CLI `_cmd_scan`) and the MCP `sofer_scan_dry_run` / `sofer_scan_apply`
tools only **discover, move, and copy** files and `merge_entries` into the TOML —
they never open a CSV byte stream, never call `stream_csv`, and never sniff a
delimiter. A `delimiter`/`encoding` parameter on those tools would be inert
(dead API surface). The issue explicitly delegates the choice of commands to the
design phase ("Decide in the design phase whether to add them to every CSV-reading
command or only the ones where a wrong dialect is silently damaging"), so the
"scan tools" mention cannot be honoured literally without adding a no-op.

### Existing override plumbing already in the domain layer

- `codebook.generate_all(cfg, output_dir, delimiter=None, encoding=None, max_sample=None)`
  already resolves `None` → `cfg.csv_*`, so an explicit value already wins there.
- `codebook.generate(csv_path, output_path, delimiter=";", encoding="utf-8-sig", max_sample)`
  takes the reader dialect as parameters; the CLI/MCP adapters already pass the
  resolved config values into it (CB-R11 / MSP-R10).
- `profile.profile` / `profile.generate_all_profiles` compute the dialect from
  `config.CSV_*` internally and take no override.

### Reader semantics that constrain the override

- `_csv_reader.stream_csv` honours a supplied encoding first, then falls back
  `utf-8-sig → utf-8` (never `latin-1`/`cp1252`); an unknown codec raises
  `LookupError`, exhausted fallbacks raise `ValueError`.
- `.tsv` is **tab-delimited by format** — `codebook._read_tsv` and
  `profile._stream_columns` force `\t`; a supplied delimiter does not apply to
  `.tsv` today. The override therefore affects `.csv` for the delimiter and
  `.csv`/`.tsv` for the encoding.

## Conclusion

The meaningful home for the override is the **codebook and profile** families —
the "content-reading" peers of the `scan` tools, both single-file and batch. The
batch domain functions already accept dialect overrides (`generate_all`), so the
change is mostly threading CLI arguments and MCP parameters into existing
resolution points, plus one new optional parameter pair in `profile.py`.
`scan`, `validate`, and `prepare` stay untouched (see proposal non-goals).
