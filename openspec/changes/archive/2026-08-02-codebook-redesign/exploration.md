## Exploration: codebook-redesign

### Current State

**`codebook.py`** (~125 lines) is a single-purpose CSV analyser:

- `infer_column_type(values: list[str]) -> str` — classifies a column as `"numeric"`, `"categorical/text"`, `"mixed (mostly numeric)"`, or `"unknown"` by checking what ratio of values parse as `float`. Works exclusively on raw strings from `csv.reader`.
- `generate(csv_path, output_path, delimiter, encoding, max_sample) -> str` — opens a CSV with `csv.reader`, reads up to `max_sample` rows, builds a markdown table with column index, name, type, unique count, missing %, and a sample value. Returns the markdown string; writes to `output_path` if given.
- `_infer_type` is a backward-compat alias for `infer_column_type`.

**`cli.py`** codebook subcommand:
- Positional arg: `csv` (path to CSV file), optional `-o/--output`, `--max-sample` (default 100k)
- Handler `_cmd_codebook` calls `generate(args.csv, output_path=args.output, max_sample=args.max_sample)` and prints to stdout if no `--output`.
- No TOML awareness, no multi-file support, no format detection.

**`model.py`** provides the TOML-backed data model:
- `FileEntry.local: Path` and `FileEntry.remote: str` — each `[[file]]` entry maps a local path to a remote HF path.
- `FileEntry.resolve(base_dir: Path) -> Path` resolves relative paths against the TOML file's directory.
- `DatasetConfig.files: list[FileEntry]` holds all registered files.
- `DatasetConfig.codebook: str | None` is the legacy `[meta]` field for a single *declared* codebook file (analogous to `readme`). This is different from *generated* per-dataset codebooks.

**`_formats.py`** — `SUPPORTED_FORMATS` registry: `.csv`, `.tsv`, `.parquet`, `.xlsx`, `.jsonl`. The scan command uses this to discover files; the codebook command does not.

**`_sentinels.py`** — `MISSING_VALUE_SENTINELS: frozenset[str]` shared across the codebase. Already used by `codebook.py` to detect missing values.

**Tests** (`test_codebook.py`, 10 tests):
- `TestInferType` (7 tests): type inference for numeric, decimal, categorical, mixed, empty, all-missing, single-value.
- `TestInferColumnType` (2 tests): public API existence + equivalence with private alias.
- `TestGenerate` (7 tests): basic structure, missing values, file output, row count, large-file sampling, small-file full scan, numeric/categorical column labeling.
- All tests create temporary CSV files with `csv.writer(delimiter=";")`. No Parquet/XLSX/TSV/JSONL fixtures exist.

### Affected Areas

- **`src/sofer/codebook.py`** — Heavy refactor. The `generate()` function is hardwired to `csv.reader`. Must be split into format-specific read + common analysis + markdown rendering. The column analysis logic (`infer_column_type`) works on strings; for typed formats (Parquet, JSONL), a parallel dtype-based path is needed.
- **`src/sofer/cli.py`** — New args: `--config` (TOML path), `--all-files` flag, positional arg becomes optional with `--all-files`. New handler logic for batch generation, output location strategy.
- **`src/sofer/model.py`** — Minor. `DatasetConfig` already provides `files`, `_base_dir`, and format info via `FileEntry.local.suffix`. May need a helper to filter files eligible for codebook generation.
- **`src/sofer/_formats.py`** — Minimal. Already has the format registry; codebook just needs to consume it.
- **`tests/test_codebook.py`** — Significant expansion. Need test fixtures for each supported format (`.parquet`, `.xlsx`, `.tsv`, `.jsonl`). Need tests for batch generation from TOML. Need tests for output placement strategy. Need regression tests to confirm single-file CSV generation is unchanged.
- **`pyproject.toml`** — New dependencies: `openpyxl` (for `.xlsx` reading) at minimum; possibly `pandas` if chosen as the read backend.

### Approaches

#### Approach 1: Minimal — Add openpyxl, keep CSV native, add pyarrow for Parquet/TSV, stdlib for JSONL

Use format-specific readers, no heavy dependency:
- CSV: keep `csv.reader` (zero regression risk)
- TSV: same `csv.reader` with `delimiter="\t"`
- Parquet: `pyarrow.parquet.read_table()` → convert to row-of-strings for analysis (pyarrow already in dep tree via `huggingface-hub`)
- XLSX: `openpyxl.load_workbook()` (lightweight, ~200KB)
- JSONL: stdlib `json.loads()` line-by-line

Common analysis pipeline: read → extract headers + column-value-lists → pass through existing `infer_column_type` on stringified values → render markdown.

- **Pros**: Lightweight (only add `openpyxl`), zero regression risk for CSV path, pyarrow already transitive, each format reader is simple and testable in isolation.
- **Cons**: More book-keeping code (5 format readers), Parquet metadata (actual dtypes) unused (analysis treats everything as strings), no unified DataFrame abstraction.
- **Effort**: Medium

#### Approach 2: Unified — Add pandas as single read backend

Replace all format-specific reading with `pd.read_csv()`, `pd.read_parquet()`, `pd.read_excel()`, `pd.read_json(lines=True)`.

- **Pros**: One API for all formats, built-in dtype detection, simpler code, pandas handles edge cases (encoding, date parsing, multi-sheet).
- **Cons**: Heavy dependency (~30-50MB install), changes analysis semantics (pandas dtype inference differs from `csv.reader` + manual `float()` parsing), column uniqueness and missing-value detection work on pandas objects not raw strings, may subtly alter existing CSV codebook output.
- **Effort**: Low

#### Approach 3: Two-tier — Keep CSV native, pyarrow for everything else

Use `pyarrow.csv.read_csv()` and `pyarrow.parquet.read_table()` for all formats except XLSX (needs `openpyxl`). Pyarrow handles CSV, TSV, Parquet; openpyxl for XLSX; stdlib for JSONL.

- **Pros**: Pyarrow already transitive, single engine for 4/5 formats, typed column support for Parquet (richer codebooks), lighter than pandas.
- **Cons**: Pyarrow CSV reader has different defaults (delimiter detection, encoding) vs `csv.reader`, potential subtle regression on CSV path, still need openpyxl.
- **Effort**: Medium

### Recommendation

**Approach 1** — Lightweight multi-reader with format-specific reading and a unified abstract analysis layer.

Rationale:
1. Zero regression on the CSV path. The existing `csv.reader` pipeline stays exactly as-is for CSV and extends cleanly to TSV (same reader, different delimiter).
2. Minimal dependency footprint. Only `openpyxl` is new — a ~200KB pure-Python library. No pandas, no schema migration.
3. Parquet via pyarrow is already available (transitive via `huggingface-hub`). JSONL via stdlib costs nothing.
4. The format-dispatch pattern (`_read_csv`, `_read_parquet`, `_read_xlsx`, `_read_jsonl`, `_read_tsv`) returning a uniform `(headers: list[str], columns: list[list[str]])` tuple keeps the markdown generator agnostic.
5. Parquet dtype metadata can be surfaced as an *extra* column (`Actual Type`) alongside the inferred string-based type, adding value without breaking the existing schema.

### Architecture Sketch

```
codebook.py:
├── _infer_type(values: list[str]) -> str           # unchanged
├── _read_csv(path) -> (headers, columns)            # existing csv.reader logic extracted
├── _read_tsv(path) -> (headers, columns)            # csv.reader with \t
├── _read_parquet(path) -> (headers, columns, dtypes)# pyarrow
├── _read_xlsx(path) -> (headers, columns)           # openpyxl
├── _read_jsonl(path) -> (headers, columns)          # stdlib json
├── _read_file(path) -> (headers, columns, dtypes?)  # format dispatcher
├── _build_markdown(headers, columns, file_info) -> str  # extracted from generate()
├── generate(file_path, output_path, max_sample) -> str  # single-file (BACKWARD COMPAT)
└── generate_all(cfg: DatasetConfig, output_root?) -> list[str]  # NEW: batch from TOML
```

CLI changes:
```
sofer codebook <file>              # single file (current behavior, unchanged)
sofer codebook --config <toml> --all-files  # batch from TOML
sofer codebook --config <toml> --all-files --index  # batch + root index
```

Output placement for `--all-files`:
- Each codebook is written to `<file_dir>/codebook.md` (same directory as data file).
- Default for single-file with `-o` is unchanged.
- `--index` writes `<config_dir>/codebook.md` as a table-of-contents index.

### Risks

1. **Multi-format type inference mismatch**: CSV columns are always strings; Parquet columns have native types. Using stringified Parquet values through `infer_column_type` gives different results than inspecting actual dtypes. A numeric Parquet column stringified as `"1.0"`, `"2.0"` looks numeric, but `"True"`, `"False"` from a bool column looks categorical. Risk: Parquet bool columns labeled "categorical/text" instead of "boolean". Mitigation: surface actual dtype as a separate column when available.

2. **Dependency on openpyxl**: XLSX support requires a new dependency. This is lightweight but must be declared in `pyproject.toml`. Risk: if omitted, XLSX codebook generation crashes at runtime. Mitigation: make it an optional dependency with a clear error message.

3. **TOML-driven batch generation edge cases**: What if a `[[file]]` entry points to a directory (`recursive=true`)? Codebook currently works on single files. Risk: unclear whether to generate codebooks for each file inside a recursive directory. Mitigation: skip directory entries, generate only for individual file entries, or add `--recursive` flag.

4. **Output collision**: If `data/PROV/PROV.parquet` and `data/PROV/PROV.csv` both exist, they'd both try to write `data/PROV/codebook.md`. Risk: last-write-wins silently. Mitigation: use format-specific suffix like `codebook_parquet.md` when multiple files share a directory, or warn and skip on collision.

5. **Root index ordering**: If datasets are in nested subdirectories (`data/PROV/subregion/file.parquet`), the root index needs a sane ordering (depth-first, alphabetical) and relative links. Risk: broken relative links if the index references `../data/PROV/codebook.md` incorrectly. Mitigation: compute all paths relative to the index location.

6. **Backward compatibility contract**: The positional `csv` arg must remain. Renaming it to `file` changes the CLI contract. Risk: existing scripts break. Mitigation: keep `csv` as a positional arg with a renamed `metavar="FILE"` for help text, or add `file` as an alias and deprecate `csv`.

7. **Encoding consistency**: CSV uses `utf-8-sig` by default (Excel compat). Parquet has no encoding concern. XLSX is binary. JSONL is typically UTF-8. Risk: encoding parameter only relevant to CSV/TSV, should not leak into multi-format API. Mitigation: make encoding a CSV/TSV-specific parameter, not a general parameter.

### Edge Cases Identified

| Edge Case | Impact | Mitigation |
|-----------|--------|------------|
| TOML has `[[file]]` pointing to unsupported format (`.docx`, `.sql`) | Skip or error | Check extension against `SUPPORTED_FORMATS`, skip with warning |
| TOML has `[[file]]` pointing to non-existent path | Error | Log warning, continue to next file |
| Single-file codebook on Parquet | Works but uses stringified values for type inference | Surface actual dtypes when available |
| Very wide datasets (100+ columns) | Markdown table width becomes unreadable | Truncate sample values, consider separate per-column sections |
| File with no rows (headers only) | `infer_column_type` returns "unknown" for all columns | Already handled: empty sample → type = "categorical/text" |
| Nested `data/` subdirectories (3+ levels deep) | Codebook placement must mirror structure | `Path.parent / "codebook.md"` handles any depth |
| Files not in `data/` (registered with absolute paths) | Codebook placement unclear | Place alongside the file, not under `data/` |

### Ready for Proposal

**Yes** — the current state is well-understood, the affected areas are mapped, the architectural approach is clear with tradeoffs documented, and risks are identified. The proposal should lock in Approach 1 (lightweight multi-reader) and define the exact CLI contract.
