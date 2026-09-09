# Proposal — fix-dataset-config-type-validation

**Issue**: GitHub #118 (child of epic #115) — remaining delta after PR #138
**Date**: 2026-09-09
**Status**: proposed

## Problem

`DatasetConfig.from_toml` assigns TOML values to typed fields **without type
validation**. A malformed dataset TOML such as:

```toml
[meta]
csv_delimiter = 5          # int where a 1-char delimiter is expected
csv_encoding = ["utf-8"]   # list where a codec name is expected
confidential = "yes"       # str where a bool is expected

[[check]]
min_files = "two"          # str where an int is expected
min_total_size_mb = [1.0]  # list where a number is expected
```

reaches comparisons and readers as an arbitrary Python type: `csv_delimiter`
is compared with `== ","` against a list, `min_files` is used in
`len(files) < min_files` against a str, etc. The failure mode is a raw
`TypeError` deep inside a reader or a silent wrong comparison — never a
stable, actionable diagnostic at load time.

The `[tool.sofer]` layer already validates a few keys (`semantic_priors`,
`profile_dir`/`render_dir`, `card_collapse_threshold`) but the merge loop's
`else: merged[key] = val` accepts any type for the remaining keys, and
`DatasetConfig` has no type validation at all.

Issue #118's expected behaviour: invalid configuration **fails before reader
execution** with stable diagnostics; MCP returns `ok:false, exit_code:1`,
stable `error_code`, diagnostics, and truthful recovery; CLI exits non-zero
with the same semantic error and a runnable correction.

## Approach

1. **Add a type-validating pass** over the dataset TOML values in
   `DatasetConfig.from_toml` (fail fast at parse time, before `validate()`):
   - `csv_delimiter` → single-character string (the reader compares equality,
     so a non-string or multi-char value is a config error).
   - `csv_encoding` → non-empty string.
   - `min_files` → non-bool int ≥ 0; `min_total_size_mb` → real number ≥ 0.
   - `confidential`, `private`, `skip_cross_file_schema` → bool.
   - `repo_type` → non-empty string.
   - quality-check numeric fields (`max_null_pct`, `min`, `max`, `min_unique`)
     → numbers when present.
   - Column-check `expected` → list of strings.
   Diagnostics are stable strings naming the offending key, the expected type
   and the received value — surfaced through the existing `validate()` error
   list (CLI `exit 1`, MCP `config_errors` + `CONFIG_ERROR`).
2. **Tighten the `[tool.sofer]` merge loop** so the remaining typed defaults
   (`output_max_bytes`, numeric keys, list keys) reject wrong types instead of
   passing them through.
3. **Determinism**: a profile determinism test asserting repeated identical
   generation yields byte-identical canonical output (closing #118's
   determinism criterion).
4. Spec: new `tool-config` requirement (TC-13) + dataset-config validation
   scenarios; sync to the live base spec.

## Out of scope

- MCP workflow registry/branch routing (#117)
- Artifact manifest (#122)
- Reader behavior changes beyond receiving validated values
- `SOFER_TRACE.md`
