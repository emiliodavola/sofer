# Exploration: convert-all-formats-parquet

## Problem Statement

`sofer prepare` currently converts only CSV files to Parquet by default. All other declared data formats (TSV, XLSX, JSONL, Parquet) are staged verbatim via `copy_to_mirror`. The request is to make Parquet conversion universal: every data file (csv, tsv, xlsx, jsonl) MUST be converted to `.parquet` by default, with Parquet passthrough unchanged.

Original (Spanish) request: "Todos los archivos de data (csv, tsv, xlsx, jsonl) tienen que ser convertidos a .parquet por default. Currently only csv (and parquet passthrough) is converted in prepare.py _convert_to_parquet + conversion loop (line 672: remote_lower.endswith(".csv") or ".parquet"). Other formats (.tsv, .xlsx, .jsonl, .parquet) are staged as-is via copy_to_mirror. User wants universal conversion to Parquet by default."

## Current State

### Conversion pipeline today

* **Entry gate — `src/sofer/prepare.py:667-701` (`prepare` conversion loop):** iterates `cfg.files`; skips `recursive`; eligible iff `remote_lower.endswith(".csv") or .parquet`; `upload_as_csv=True` bypasses; `local.exists()` guard; then `_convert_to_parquet(local, entry_tmp, delimiter=cfg.csv_delimiter)`. Result stored in `converted: dict[remote_key -> (parquet_path, csv_path, original_remote)]`. Parity/size checks run only on converted set; staging step 5 copies converted via `parquet_remote_for`, step 7 copies everything else via `copy_to_mirror`.

* **Converter — `src/sofer/prepare.py:270-326` (`_convert_to_parquet`):** CSV-only. Sniffs delimiter, `pc.read_csv` with `ParseOptions(delimiter)`, parity check (`_check_conversion_parity`), null-column cast, `pq.write_table(compression=config.PARQUET_COMPRESSION, row_group_size=config.PARQUET_ROW_GROUP_SIZE)`, shard-size warning, returns `Path | None` on failure (caller falls back to staging CSV).

* **Delimiters — `src/sofer/prepare.py:83-134` + `src/sofer/config.py:47,49`:** `_sniff_csv_delimiter` / `_count_delimiters_outside_quotes` counts `config.SNIFF_DELIMITERS=[";",",","\t"]`; used only for CSV. No delimiter concept for xlsx/jsonl.

* **Parity — `src/sofer/prepare.py:184-267` (`_check_conversion_parity`):** hard checks row count / col count / col names; soft check value alteration (leading zeros, comma decimals) by comparing CSV string sets vs Parquet stringified sets. Entirely CSV-str vs Parquet typed-value. No equivalent for xlsx/jsonl (e.g. Excel float vs int, jsonl nested keys).

* **Mirror helpers — `src/sofer/_mirror.py`:**
  - `parquet_remote_for(remote)` (line 53): suffix flip to `.parquet`, agnostic to extension but only invoked for `.csv` in `planned_remotes` / `prepare`.
  - `planned_remotes(cfg, keep_csv)` (line 119): `elif remote.lower().endswith(".csv") and not upload_as_csv: -> parquet_remote_for`; else passthrough. All non-CSV (tsv/xlsx/jsonl/parquet) fall to `else: planned.append(remote)`.
  - `_validate_case_fold_collisions` (line 75): only scans `.csv` entries — would miss `data.tsv` vs `data.csv` collision after universal conversion.
  - `_check_local_overwrite` in `prepare.py:553-592` mirrors the same `.csv` gate.

* **Publish — `src/sofer/publish.py`:**
  - `_needs_prepare` (386): already format-agnostic (checks `*.parquet` existence + mtime of any `e.resolve(base).exists()` source) — no change needed.
  - `_repo_diff_summary` (201): same `.csv` gate as `planned_remotes` (duplicated logic, not delegating).
  - `_copy_package` (444): same `.csv` gate for Parquet staging + keep_csv handling.
  - `publish` flow (535): auto-prepare, dry-run uses `planned_remotes`, hf staging uses `_copy_package` — all downstream of the gate.

* **Schema report — `src/sofer/repo_compliance.py:436-688`:** `_build_schema_report_impl` iterates entries, filters `if entry.recursive or not remote.endswith(".csv"): continue`. So tsv/xlsx/jsonl never contribute to schema; parquet branch only triggers when staged Parquet exists for a CSV. Card `configs.data_files` via `planned_remotes` would also list original `data.tsv` rather than `data.parquet`.

* **Quality — `src/sofer/quality.py` + `src/sofer/_formats.py:26-27`:** `TEXT_SUFFIXES={".csv",".tsv"}` gates P0 checks; `_process_file` early-returns if `not is_text_eligible(resolved)`. So TSV is currently quality-checked, XLSX/JSONL/Parquet are not — unchanged by conversion but codebook already reads all formats.

* **Codebook — `src/sofer/codebook.py:78-244`:** Already has format-specific readers `_read_csv`, `_read_tsv`, `_read_parquet`, `_read_xlsx`, `_read_jsonl`, dispatcher `_read_file`, and markdown builder. Proven pattern to reuse for conversion.

* **Model — `src/sofer/model.py:59-83`: FileEntry has `upload_as_csv: bool = False` (only CSV opt-out). No generic opt-out. TOML parsing `entry.get("upload_as_csv", False)` — adding new flag requires model + docs.

* **Config — `src/sofer/config.py` + `pyproject.toml [tool.sofer]`:** `PARQUET_COMPRESSION="zstd"`, `PARQUET_ROW_GROUP_SIZE=100_000`, `CSV_DELIMITER=";"`, `SNIFF_DELIMITERS`, `PARQUET_SHARD_WARNING_MB=500`. No knobs for xlsx sheet selection, jsonl batch size, tsv delimiter override.

* **Scanner — `src/sofer/scanner.py` + `src/sofer/_formats.py:18-24`:** `SUPPORTED_FORMATS` = {csv, tsv, parquet, xlsx, jsonl}. Discovery/merging already supports all five; only `prepare` conversion filter blocks them.

* **README — `README.md:268-278`:** Table says `prepare` converts CSV to Parquet unless `upload_as_csv=true`; every other format is staged as-is. Footnote `¹` explicitly documents the current CSV-only behavior — must be updated.

### Test coverage that locks current behavior

* `tests/test_prepare.py`: `TestPrepareConversion` asserts converted parquets mirror remote layout, `test_upload_as_csv_keeps_csv`, `test_conversion_failure_falls_back_to_csv`, `test_parquet_passthrough_staged_as_is`.
* `tests/test_parquet_conversion.py`: `TestConversionPipeline.test_non_csv_file_passthrough` asserts `meta.json` passes through without conversion; `TestPlanned` etc expect 0 parquet for non-CSV. Changing to universal conversion will break these unless migrated.
* `tests/test_mirror.py`: `TestPlannedRemotes` only asserts CSV→parquet mapping; non-CSV passthrough assertions (`test_non_csv_file_passthrough`) would need updating.
* `tests/test_repo_compliance.py` + `tests/test_codebook.py` already cover multi-format reading (reuse opportunity).

### Dependencies in play

* `pyarrow>=14.0` already required: `pyarrow.csv`, `pyarrow.parquet`, and `pyarrow.json` (for jsonl) are available without new deps.
* `openpyxl>=3.1` already required: used by `codebook._read_xlsx`; can be reused for xlsx→parquet but is the heaviest path (read_only, data_only, first-sheet only).
* `huggingface-hub` transitive includes `pyarrow` — no new dependency needed.

## Affected Areas

- `src/sofer/prepare.py` — conversion loop gate, `_convert_to_parquet`, `_sniff_csv_delimiter`, `_check_conversion_parity`, `_cast_null_columns_to_string`, `_assert_cross_file_schema`, `_check_large_values`, `_check_local_overwrite`, `_assert_card_dtypes_match_parquet` (loop at 702-710; all assume CSV sources)
- `src/sofer/_mirror.py` — `planned_remotes`, `_validate_case_fold_collisions`, `parquet_remote_for` usage scope
- `src/sofer/publish.py` — `_repo_diff_summary`, `_copy_package`, `planned_remotes` duplication (should delegate)
- `src/sofer/repo_compliance.py` — `_build_schema_report_impl` CSV-only filter, `build_dataset_card` `configs.data_files` via `planned_remotes`
- `src/sofer/model.py` — `FileEntry.upload_as_csv` semantics, new opt-out flag
- `src/sofer/config.py` + `pyproject.toml [tool.sofer]` — potential new knobs: conversion opt-out, tsv delimiter, xlsx sheet, jsonl mode (if not hardcoded)
- `src/sofer/codebook.py` — reference implementation for format-specific readers (not changed, but pattern to follow)
- `src/sofer/quality.py` / `src/sofer/_formats.py` — TEXT_SUFFIXES unchanged but document interaction with conversion
- `tests/test_prepare.py`, `tests/test_parquet_conversion.py`, `tests/test_mirror.py`, `tests/test_repo_compliance.py`, `tests/test_publish.py` — expectations for passthrough vs converted
- `README.md` + `README_ES.md` + `docs/configuration.md` — data format support table + footnote + TOML reference
- `openspec/specs/` — data-quality / prepare / publish specs if they exist

## Approaches

### 1. Approach A — Extend `_convert_to_parquet` into a multi-format converter (single dispatcher, reuse existing parity/size checks)

Add a format dispatcher inside `prepare.py`: detect `Path.suffix.lower()`, route to `pyarrow.csv` (csv), `pyarrow.csv` with `delimiter="\t"` (tsv), `openpyxl` → `pa.Table` (xlsx), `pyarrow.json.read_json` (jsonl), passthrough for `.parquet`. Keep one `_convert_to_parquet`-style entry point (renamed to `_convert_to_parquet` or `_convert_file_to_parquet`) that returns `Path | None` and shares: null-column handling, `pq.write_table` with `config.PARQUET_COMPRESSION/ROW_GROUP_SIZE`, shard warning, large-value warning, cross-file schema assertion. Parity check becomes per-format: CSV/TSV reuse row/col/name + value-altered warning; XLSX parity compares `openpyxl` header vs Parquet column names/row counts; JSONL parity compares unified keys vs Parquet columns, row count. Copy logic in `_mirror.planned_remotes` and `_validate_case_fold_collisions` broadened from `endswith(".csv")` to `endswith(SUPPORTED_FORMATS - {".parquet"})` or explicit set.

- Pros:
  - Minimal new surface; reuses proven compression/row-group/shard/large-value/cross-file logic.
  - One place to maintain Parquet write options (compression, page index).
  - Matches existing `codebook._read_file` pattern — familiar to contributors.
  - Lowest churn for `publish.py` (just broadens the gate).
  - TSV trivially solved (delimiter `\t`).

- Cons:
  - `_convert_to_parquet` grows branching; Excel/JSONL error modes differ (merged cells, formulas, nested JSON) — parity logic must be forked anyway.
  - JSONL schema can be heterogeneous (sparse keys) — pyarrow.json inference may produce `null` vs `string` vs `list`; need explicit handling.
  - XLSX via openpyxl loads first sheet only (existing codebook precedent) — may surprise users with multi-sheet workbooks.
  - Single function accumulates format-specific options (sheet, delimiter) → signature creep.

- Effort: Medium

### 2. Approach B — Separate converters per format (one function per suffix, shared writer utility)

Create `_convert_csv_to_parquet`, `_convert_tsv_to_parquet`, `_convert_xlsx_to_parquet`, `_convert_jsonl_to_parquet`, plus `_write_parquet_table(table, staging_dir, stem)` helper that centralizes `pq.write_table`, null-column cast, shard check. Dispatcher maps suffix → function. Parity checks become format-native: CSV/TSV use existing string-set comparison; XLSX uses openpyxl raw values vs Parquet values; JSONL uses JSON key union vs Parquet names; each can emit format-specific warnings. `_mirror` helpers gain per-format collision/remote logic but stay thin.

- Pros:
  - Clear separation of concerns; each converter testable in isolation.
  - Easy to add future formats (ods, arrow) without touching shared pipeline.
  - Parity and error messages can be format-specific and precise.
  - Aligns with AGENTS.md rule 10: one module per concern (consider extracting `src/sofer/_converters.py`).

- Cons:
  - More files/functions to create and maintain; duplication risk if writer helper not strictly enforced.
  - Slightly higher upfront implementation cost (4 converters vs 1 extended function).
  - Requires deciding where converters live (`prepare.py` vs new `src/sofer/_converters.py` + `src/sofer/_parquet_helpers.py`).

- Effort: Medium-High

### 3. Approach C — Always-convert with opt-out flag (flag design, orthogonal to A/B)

Whether A or B, decide the opt-out surface. Today `upload_as_csv` means "do not convert this CSV". For universal conversion need a generic analog. Options:

* **C1 — Reuse/rename to `upload_as_parquet=false` or `keep_original=true`:** `FileEntry` gains `convert_to_parquet: bool = True` (or `upload_as_parquet: bool = True` / `skip_conversion: bool = False`). TOML `convert_to_parquet = false` keeps original suffix. Pros: explicit, self-documenting. Cons: rename breaks backward compat unless `upload_as_csv` kept as deprecated alias.
* **C2 — Keep `upload_as_csv` and add per-format flags:** e.g. `upload_as_tsv`, etc. Pros: no breaking change. Cons: flag sprawl, inconsistent API.
* **C3 — Always convert, no opt-out:** Simplest, no new field. Pros: zero config. Cons: breaks users who intentionally stage XLSX for viewer reasons; no escape hatch for corrupt/unsupported files (currently fallback is staging CSV — should extend to any format).

- Pros (of having an opt-out, C1): preserves escape hatch; fallback on conversion failure (staging original) plus explicit opt-out are complementary; required for sensitive workflows where original Excel formatting must be preserved.
- Cons: new config field, docs, validation, and `planned_remotes` branching; deprecation path for `upload_as_csv` if renamed.

- Effort: Low (if C1 with alias) — but must be decided before spec.

## Recommendation

**Recommended: Approach A implemented via a new `src/sofer/_converters.py` module (hybrid A+B) with opt-out via `convert_to_parquet` (C1 with deprecated alias).**

Rationale: A gives the smallest diff for the parquet write path (reuse compression/row-group/shard/large-value/cross-file), but extracting converters into `_converters.py` (B's modularity) avoids bloating `prepare.py` (already 811 lines). The dispatcher in `_converters.py` maps suffix → converter function; `prepare.py` keeps only the orchestration loop and imports the dispatcher. This satisfies AGENTS.md rule 10 (one module per concern) and rule 4 (no duplicated `_parquet_to_hf_dtype` — centralize `write_parquet` helper).

For the flag, introduce `FileEntry.convert_to_parquet: bool = True` (or `skip_conversion: bool = False` — bikeshed in proposal) and keep `upload_as_csv` as a deprecated alias that sets `convert_to_parquet=False` when `remote` is `.csv` (with a deprecation warning). This preserves backward compat while providing a uniform opt-out for all formats. The TOML docs and README table then read: "all data files are converted to Parquet unless `convert_to_parquet = false`".

Detailed flag naming should be locked in the proposal phase; the explore recommends `convert_to_parquet` (positive, matches `parquet_remote_for` naming) over `keep_original` (ambiguous about which original).

## Risks

- **Breaking change for existing datasets:** Users who declare `data/report.xlsx` today expect `report.xlsx` in the Hub; after change they get `report.parquet`. Without a migration note and the opt-out flag, existing `dataset.toml` files will produce different artifacts. Mitigation: keep `upload_as_csv` alias, document `convert_to_parquet=false` for XLSX that must stay Excel, add a `--keep-original` analog to `--keep-csv` if needed.
- **Delimiter handling divergence:** TSV must use `\t` always, not sniffed `;`. CSV sniffing from first line is already fragile; TSV sniffing would mis-detect. Mitigation: hardcode `\t` for `.tsv`, keep sniff only for `.csv`, ignore delimiter for xlsx/jsonl.
- **Parity checks are CSV-specific:** Value-altered warning (leading zeros, comma decimals) assumes CSV string values; XLSX numeric types may already be typed, JSONL values may be nested. Reusing the same parity naively will false-positive. Mitigation: per-format parity (section above) — at minimum row/col/name checks for all, value-altered only for CSV/TSV.
- **Large-value warnings assume Parquet string columns:** `_check_large_values` reads `pa.string`/`large_string` from first `REPORT_MAX_ITEMS` rows — still valid for all converted formats, but XLSX with embedded images or JSONL with nested objects may produce `list`/`struct` types that the check skips. No regression, but document scope.
- **Cross-file schema check scope expands:** Today it only compares converted CSVs; after change TSV/XLSX/JSONL Parquets participate. Multi-table datasets (e.g. `CPV2010` + `HOGAR` with disjoint columns) already handled via column-set grouping, but heterogeneous JSONL keys could create spurious groups. Mitigation: keep grouping by sorted column names; jsonl keys already unified in discovery order — stable.
- **Split detection on remotes changes:** `detect_splits` reads `planned_remotes` (now `.parquet` for xlsx/jsonl). Splits keyed on `train/test` keywords in remote paths still work, but users who relied on `data.xlsx` being unclassified may see split assignment change. Low risk; detection is keyword-based on full path.
- **Excel scope — first sheet only, memory:** `codebook._read_xlsx` reads `wb.active` with `read_only=True, data_only=True` — consistent precedent but may surprise multi-sheet workbooks; large XLSX (>100k rows) can spike memory via `openpyxl` → `pa.Table` conversion. Mitigation: document first-sheet-only, cap rows or stream if needed (defer unless proven).
- **JSONL schema heterogeneity:** `pyarrow.json.read_json` infers from first blocks; sparse keys produce `null` columns that `_cast_null_columns_to_string` must handle (already does for CSV nulls). Nested objects become `struct`/`list` — `_map_parquet_type` and `_parquet_to_hf_dtype` handle them as `string`/`unknown` — acceptable but card may show `unknown`. Mitigation: document that nested JSONL yields stringified values.
- **Overwrite protection and case-fold collisions:** `_validate_case_fold_collisions` only scans `.csv` — after change `data/report.xlsx` and `data/REPORT.XLSX` would collide on `data/report.parquet` and `data/REPORT.parquet` case-insensitively. Must broaden to all convertible suffixes. Similarly `_check_local_overwrite` must check `output_dir / parquet_remote_for(remote)` for any convertible file.
- **Test churn:** `test_prepare.test_conversion_failure_falls_back_to_csv`, `test_parquet_conversion.TestConversionPipeline.test_non_csv_file_passthrough`, `test_mirror.TestPlannedRemotes` all assert passthrough for non-CSV. They must be updated to assert conversion; add new tests for TSV/XLSX/JSONL conversion and for `convert_to_parquet=false` passthrough.
- **Documentation drift:** `README.md` footnote `¹` and table row for `prepare` currently say only CSV converts — must update together with `README_ES.md` (AGENTS rule 13).
- **Dependency weight:** No new deps, but `openpyxl` path is heavier than `pyarrow.csv`; conversion of many XLSX files sequentially may be slow. Mitigation: keep per-entry temp subdir pattern (already isolates same-stem collisions) and reuse `pyarrow.json` for jsonl (fast).

## Open Questions

1. **Flag name and deprecation path:** Keep `upload_as_csv` as deprecated alias vs rename to `convert_to_parquet` / `skip_conversion`? Which default? Proposal must lock the name and migration note.
2. **XLSX sheet selection:** Always first sheet (`wb.active`) matching codebook, or add `xlsx_sheet` config? Defer unless user reports multi-sheet need.
3. **TSV delimiter override:** Should `cfg.csv_delimiter` apply to TSV or is `\t` hardcoded? Recommend hardcoded `\t` for `.tsv` (TSV is by definition tab-delimited); keep `csv_delimiter` for `.csv` only.
4. **JSONL reader choice:** `pyarrow.json.read_json` (fast, strict) vs Python `json` + `pa.Table.from_pylist` (handles sparse keys gracefully)? Recommend `pyarrow.json` to match `pyarrow.csv` stack, with fallback to python parser on failure.
5. **Parquet passthrough interaction:** `.parquet` entries stay passthrough (no conversion) — confirm no flag needed for them.
6. **Keep-original for non-CSV:** Should `publish --keep-csv` generalize to `--keep-original` (keep source alongside Parquet) or stay CSV-only? Defer to proposal; at minimum document that `--keep-csv` only affects CSV.
7. **Spec scope:** Does the schema report (`repo_compliance._build_schema_report_impl`) need to include converted TSV/XLSX/JSONL columns in the Dataset Card, or stay CSV-only and let Parquet-derived types drive the card? Recommend broadening to all convertible formats now that they are Parquet-backed.
8. **Breaking change versioning:** This is a minor breaking change (artifact paths change). Should it bump `0.x` minor (per AGENTS rule 12: 0.x minor may carry breaking changes, documented) and note in release notes?
