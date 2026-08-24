# Design: Codebook Redesign

## Technical Approach

Lightweight multi-reader architecture (Approach 1 from exploration). Format-specific readers
return a uniform `(headers, columns, dtypes?)` tuple consumed by format-agnostic analysis and
markdown rendering. Zero regression on CSV — existing `csv.reader` path is extracted into
`_read_csv`, not replaced. Single new dependency: `openpyxl`.

## Architecture Decisions

| Decision | Options | Tradeoffs | Choice |
|----------|---------|-----------|--------|
| Read backend | 1) Format-native 2) Pandas 3) Pyarrow CSV+Parquet | Pandas changes CSV semantics (~30 MB). Pyarrow CSV risks subtle CSV regressions. Format-native preserves current CSV output byte-for-byte and adds only `openpyxl`. | **Approach 1** — format-native readers |
| Reader contract | Return raw rows vs. columnar data | Row-based mirrors current `csv.reader` loop but complicates type inference. Columnar (`list[list[str]]` per column) is the natural input to `infer_column_type`. | **Columnar** — `(headers, columns, dtypes?)` |
| Dtype column | Always show vs. only for typed formats | `None` dtypes for CSV/TSV/JSONL avoid a useless column. Parquet/XLSX surface actual dtype when available. | **Optional column** — extra `\| Actual Type \|` column only when `dtypes is not None` |
| CLI backward compat | Rename arg vs. keep name | Renaming `csv` → `file` breaks scripts. Keeping `csv` with `metavar="FILE"` preserves automation. | **Keep `csv`**, add `metavar="FILE"`, make `nargs="?"` |
| Output collision | Silent overwrite vs. format suffix vs. error | Overwrite loses data. Error blocks batch. Format suffix (`codebook_parquet.md`) is explicit and safe. | **Format suffix** + warning |

## Data Flow

```
CLI (--all-files)                     CLI (<file>)
      │                                    │
      ▼                                    ▼
generate_all(cfg)                   generate(file_path)
      │                                    │
      ▼                                    ▼
 iterate [[file]] entries          _read_file(path)
      │                             │
      ▼                             ▼
_read_file(local_path)        _build_markdown(...)
      │
      ▼
  [suffix router]
  │    │     │      │     │
.csv  .tsv .parquet .xlsx .jsonl
  │    │     │      │     │
  ▼    ▼     ▼      ▼     ▼
 (headers, columns, dtypes?)
      │
      ▼
_build_markdown(headers, columns, dtypes, path, max_sample)
      │
      ▼
  Write codebook.md per file → write root index
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/codebook.py` | Modify | Add `_read_csv`, `_read_tsv`, `_read_parquet`, `_read_xlsx`, `_read_jsonl`, `_read_file`, `_build_markdown`, `generate_all`. Refactor `generate` to compose `_read_file` + `_build_markdown`. Keep `infer_column_type` and `_infer_type` unchanged. |
| `src/sofer/cli.py` | Modify | `codebook` subparser: `csv` gains `nargs="?"` + `metavar="FILE"`. Add `--all-files` (flag) and `--config` (TOML path). Handler dispatches batch or single-file. |
| `tests/test_codebook.py` | Modify | Add format-specific fixtures (`.tsv`, `.parquet`, `.xlsx`, `.jsonl`), batch generation tests, output placement tests, root index tests. |
| `pyproject.toml` | Modify | Add `openpyxl` to `dependencies`. |

## Interfaces / Contracts

```python
# ── Reader contract ──
def _read_csv(path: str, encoding: str = "utf-8-sig", delimiter: str = ";")
    -> tuple[list[str], list[list[str]], None]
def _read_tsv(path: str, encoding: str = "utf-8-sig")
    -> tuple[list[str], list[list[str]], None]
def _read_parquet(path: str)
    -> tuple[list[str], list[list[str]], dict[str, str]]
def _read_xlsx(path: str)
    -> tuple[list[str], list[list[str]], dict[str, str] | None]
def _read_jsonl(path: str)
    -> tuple[list[str], list[list[str]], None]

# ── Dispatcher ──
def _read_file(path: str)
    -> tuple[list[str], list[list[str]], dict[str, str] | None]

# ── Markdown builder (extracted from current generate) ──
def _build_markdown(
    headers: list[str],
    columns: list[list[str]],
    dtypes: dict[str, str] | None,
    file_path: str,
    max_sample: int = 100_000,
) -> str

# ── Public API (unchanged signature, refactored body) ──
def generate(
    file_path: str,
    output_path: str | None = None,
    delimiter: str = ";",
    encoding: str = "utf-8-sig",
    max_sample: int = 100_000,
) -> str

# ── Batch (new) ──
def generate_all(cfg: DatasetConfig) -> list[str]
```

### Root Index Structure

```markdown
# Codebook Index: {dataset.name}

**Repository:** `{repo_id}`  
**Tables:** {N} | **Total columns:** {M}

## Contents
- [`data/table_a.csv`](data/codebook.md) — 5 columns
- [`data/table_b.parquet`](data/codebook_parquet.md) — 12 columns
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Each `_read_*` returns correct shape | Temp files per format, verify headers + column count + types |
| Unit | `_read_file` dispatches correctly | 5 files, 5 formats, verify routed to correct reader |
| Unit | `_build_markdown` output matches current `generate` | Feed pre-built `(headers, columns)` and diff output |
| Unit | `infer_column_type` unchanged | Existing 10 tests pass untouched |
| Regression | `generate` CSV output identical | Current 7 CSV tests pass unchanged |
| Integration | `generate_all` from TOML | Create `dataset.toml` with 2-3 `[[file]]` entries, verify per-file codebooks + root index |
| Edge | Unsupported format, missing file, empty file | Parametrize: `.txt` → warning, non-existent → warning, header-only → "unknown" types |
| Edge | Output collision | Two files sharing parent dir → `codebook_parquet.md` + `codebook_csv.md` |

## Migration / Rollout

No migration required. `openpyxl` added as hard dependency to `pyproject.toml`. Rollback: revert 3 files,
remove `openpyxl`.

## Open Questions

- [ ] Root index: generate unconditionally with `--all-files` or gate behind `--index` flag? Spec says CB-R04 uses `--all-files` — leaning toward unconditional.
