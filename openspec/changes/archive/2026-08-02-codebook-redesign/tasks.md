# Tasks: Codebook Redesign

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~620 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (readers+dispatcher+tests) → PR 2 (markdown+generate refactor+tests) → PR 3 (batch+CLI+integration tests) |
| Delivery strategy | single-pr (2000-line review budget accepted; size:exception) |
| Chain strategy | N/A (single PR) |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: N/A
400-line budget risk: High (accepted with 2000-line budget)

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Format readers + dispatcher + unit tests | PR 1 | Base for all subsequent work; includes 5 format readers, dispatcher, and their tests (~180 lines) |
| 2 | Markdown builder + generate refactor + regression tests | PR 2 | Bases on PR 1; extracts `_build_markdown`, refactors `generate()` for backward compat, verifies 7 existing CSV tests pass (~170 lines) |
| 3 | Batch generation + CLI + integration/edge tests | PR 3 | Bases on PR 2; `generate_all`, root index, collision handling, error handling, CLI flags, all remaining tests (~270 lines) |

## Phase 1: Foundation — Multi-Format Readers

- [x] 1.1 Add `_read_csv(path, encoding, delimiter)` and `_read_tsv(path, encoding)` to `src/sofer/codebook.py` — extract CSV reading from current `generate()` into `_read_csv`; TSV is CSV with `\t` delimiter; both return `(headers, columns, None)` — covers CB-R01
- [x] 1.2 Add `_read_parquet(path)` to `codebook.py` — use `pyarrow.parquet.read_table`, convert to columnar `list[list[str]]`, return `(headers, columns, dtypes)` — covers CB-R01 scenario "Read Parquet with dtype display"
- [x] 1.3 Add `_read_xlsx(path)` to `codebook.py` — use `openpyxl.load_workbook`, read first sheet, return `(headers, columns, dtypes)` where `dtypes` is `dict[str, str]` from cell types — covers CB-R01 scenario "Read XLSX with multi-format"
- [x] 1.4 Add `_read_jsonl(path)` to `codebook.py` — read line-delimited JSON, unify keys as column headers, return `(headers, columns, None)` — covers CB-R01
- [x] 1.5 Add `_read_file(path)` dispatcher to `codebook.py` — route by file suffix to correct reader; raise `ValueError` for unsupported formats — covers CB-R01, CB-R06 scenario "Unsupported format"
- [x] 1.6 Add `openpyxl` to `dependencies` in `pyproject.toml`

## Phase 2: Core — Markdown Builder & Generate Refactor

- [x] 2.1 Extract `_build_markdown(headers, columns, dtypes, file_path, max_sample)` from current `generate()` — same type-inference logic via `infer_column_type`, same markdown table output; add optional `| Actual Type |` column when `dtypes is not None` — covers CB-R01 dtype display
- [x] 2.2 Refactor `generate(file_path, output_path, delimiter, encoding, max_sample)` to call `_read_file(file_path)` + `_build_markdown(...)`; preserve signature and stdout/file output behavior — covers CB-R02 scenario "CSV backward compatibility"
- [x] 2.3 Verify existing 7 CSV regression tests pass unchanged — confirm `generate()` output is byte-identical to current — covers CB-R02 scenario "CSV backward compatibility", CB-R02 scenario "Output to file"

## Phase 3: Batch Generation & CLI

- [x] 3.1 Add `generate_all(cfg: DatasetConfig) -> list[str]` to `codebook.py` — iterate `cfg.files`, call `_read_file` + `_build_markdown`, write per-file `codebook.md` alongside data — covers CB-R03 scenario "Batch from TOML config"
- [x] 3.2 Add root index generation in `generate_all` — write `codebook.md` at config root with TOC, relative links, dataset summary per design — covers CB-R04 scenario "Root index after batch generation"
- [x] 3.3 Add output collision handling — detect multiple supported files sharing parent dir; use format-specific suffix (`codebook_parquet.md`, `codebook_csv.md`); emit warning — covers CB-R05 scenario "Same-dir multi-format collision"
- [x] 3.4 Add error handling in `generate_all` — skip + warn for unsupported format, missing file, directory entry; minimal codebook for empty file; exit 1 on malformed TOML — covers CB-R06 all scenarios
- [x] 3.5 Update CLI in `src/sofer/cli.py` — make `csv` arg optional (`nargs="?"`), change `metavar` to `"FILE"`; add `--all-files` flag and `--config` option; handler dispatches single-file vs batch — covers CB-R02, CB-R03

## Phase 4: Testing

- [x] 4.1 Unit tests for each `_read_*` reader — temp files per format, verify `(headers, columns)` shape, dtypes presence/absence — covers CB-R01 all scenarios
- [x] 4.2 Unit test for `_read_file` dispatcher — 5 formats route correctly; unsupported format raises `ValueError` — covers CB-R01, CB-R06
- [x] 4.3 Unit test for `_build_markdown` — diff output against current `generate` for identical input — covers CB-R02 backward compat
- [x] 4.4 Integration tests for `generate_all()` — TOML with 2-3 `[[file]]` entries, verify per-file codebooks + root index exist with correct content — covers CB-R03, CB-R04
- [x] 4.5 Edge case tests — parametrized: `.txt` skipped, missing file skipped, empty file produces minimal codebook, output collision uses suffixes — covers CB-R05, CB-R06
- [x] 4.6 CLI tests — `--all-files` without `--config` errors, neither csv nor `--all-files` errors, mutual exclusion, positional file with `--all-files` is ignored or errors — covers CB-R02, CB-R03
