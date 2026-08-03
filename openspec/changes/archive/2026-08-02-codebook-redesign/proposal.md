# Proposal: Codebook Redesign

## Intent

The `codebook` command only analyses CSV files via `csv.reader`. Datasets with `.parquet`, `.tsv`, `.xlsx`, or `.jsonl` files get no codebook. Users with multi-file TOML datasets must run codebook manually per file. This redesign adds multi-format support and batch generation from TOML config, making codebook a first-class data-documentation tool for any registered dataset.

## Scope

### In Scope
- Multi-format reading: `.csv`, `.tsv`, `.parquet`, `.xlsx`, `.jsonl`
- `--all-files` flag for batch generation from `[[file]]` entries
- Per-dataset output: `data/<TABLE>/codebook.md`
- Root index `codebook.md` at config root (always with `--all-files`)
- Single-file CSV generation preserved (backward-compatible CLI)

### Out of Scope
- Column-level statistics beyond current (min/max/stddev)
- Recursive directory codebooks
- Custom codebook templates
- Export formats (HTML, PDF, JSON)
- Integration with `validate`/`upload` pipeline

## Capabilities

### New Capabilities
- `codebook`: multi-format codebook generation with single-file and batch modes, root index, TOML-driven discovery

### Modified Capabilities
None — existing specs unchanged.

## Approach

**Lightweight multi-reader** — format-specific readers return uniform `(headers: list[str], columns: list[list[str]])`, preserving the existing `infer_column_type` analysis unchanged.

| Format   | Reader            | New Dep?       |
|----------|-------------------|----------------|
| CSV/TSV  | `csv.reader`      | No             |
| Parquet  | `pyarrow`         | No (transitive)|
| XLSX     | `openpyxl`        | **Yes**        |
| JSONL    | `json.loads()`    | No             |

Output collision (multiple formats in same dir) warns and uses format-specific suffix: `codebook_parquet.md`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/data_uploader/codebook.py` | Modified | Split into format readers + abstract analysis + markdown renderer; add `generate_all()` |
| `src/data_uploader/cli.py` | Modified | New `--all-files` flag; positional arg becomes optional (`nargs="?"`) |
| `tests/test_codebook.py` | Modified | Parquet/XLSX/TSV/JSONL fixtures; batch generation tests; output placement tests |
| `pyproject.toml` | Modified | Add `openpyxl` dependency |
| `src/data_uploader/_formats.py` | Read-only | Consumed by format dispatcher |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Parquet bool columns mislabeled as "categorical/text" | Medium | Surface actual dtype as extra column when available |
| `openpyxl` missing at runtime | Low | Make optional with clear error message |
| Output collision with same-dir multi-format | Low | Warn + format-specific suffix |
| `--all-files` skips non-existent paths silently | Low | Log warning per missing file |

## Rollback Plan

Revert `codebook.py`, `cli.py`, and `test_codebook.py` to HEAD~1. Remove `openpyxl` from `pyproject.toml`. No DB migrations, no persistent state.

## Dependencies

- `openpyxl` (new, ~200 KB)
- `pyarrow` (already transitive via `huggingface-hub`)

## Success Criteria

- [ ] `codebook data/file.parquet` produces valid markdown codebook
- [ ] `codebook data/file.xlsx` produces valid markdown codebook
- [ ] `codebook --all-files` generates codebooks for all TOML `[[file]]` entries
- [ ] Root `codebook.md` index exists after `--all-files`
- [ ] `codebook data/file.csv` output unchanged (regression)
- [ ] All existing CSV tests pass unchanged
