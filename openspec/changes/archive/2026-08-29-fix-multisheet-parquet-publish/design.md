# Design: fix-multisheet-parquet-publish

## Technical Approach

Mirror-grounded expansion. Keep `planned_remotes(cfg, keep_csv)` as logical placeholder (1 per xlsx) for dry-run-before-prepare. Add `expanded_planned_remotes(cfg, keep_csv, staging_dir)` in `src/sofer/_mirror.py` that returns ground truth when `staging_dir` exists else delegates to `planned_remotes`. All publish paths and `build_dataset_card` consume the expanded set. XLSX sheets inferred by `staging_dir/<dir>/<stem>__*.parquet` glob — no workbook I/O, dedup/normalization already in staged filenames. Single-sheet: no `__` hit → single `stem.parquet`, no phantom.

## Architecture Decisions

| Decision | Option | Tradeoff | Choice |
|----------|--------|----------|--------|
| Helper location | `_mirror.py` vs `publish.py` vs new module | `_mirror` keeps `parquet_remote_for` co-located, no cycle (`_converters` never imports `_mirror`); other options duplicate or add module | ** `_mirror.py`** |
| Expansion source | workbook I/O vs glob staging vs manifest | Workbook makes plan impure + slow; manifest needs migration; glob is ground truth, zero cost, reuses `prepare` output | **Glob staging**, fallback to placeholder |
| XLSX eligibility | naive `endswith(.xlsx)` vs gated | Must match PUB-09: CONVERTIBLE_SUFFIXES + `convert_to_parquet` + NOT `recursive` | **Gated** via `_is_convertible_entry` + `bool(convert_to_parquet)`; `keep_csv` only for `*.csv` |
| Reuse sanitize/normalize | duplicate vs import | Duplicate drifts on accents | **Import** for rationale only; glob needs no sanitize — names already sanitized |
| Copy strategy | inline glob vs expanded list | Inline glob scatters, easy to regress | **Expanded list**: `_copy_package` iterates expanded remotes via `copy_to_mirror` |

## Data Flow

```
cfg.files → planned_remotes (logical)
              ↓
       expanded_planned_remotes(cfg, keep_csv, staging_dir)
              │ glob <dir>/<stem>__*.parquet (sorted), fallback single
              ↓
publish.publish ┬─→ _repo_diff_summary → diff (N per-sheet)
                ├─→ _check_overwrite_protection (per-sheet)
                ├─→ _print_split_mapping_validation / detect_splits (count N)
                ├─→ _copy_package (copy each expanded remote)
                └─→ dry-run (same set, [] existing)
build_dataset_card(cfg, ..., staging_dir?) → configs.data_files + Dataset Structure
                                              (row_counts stays keyed by verbatim remote)
```

`publish` resolves `staging_dir` via `resolve_output_dir(cfg, output_dir)` (hf source). Card gets explicit `staging_dir` param, `None` → fallback.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/_mirror.py` | Modify | Add `expanded_planned_remotes`; doc `planned_remotes` as logical; glob+normalize; handle `recursive`/`keep_csv` |
| `src/sofer/publish.py` | Modify | Expand before diff/protection/splits/dry-run/staging; `_repo_diff_summary` takes `staging_dir`; `_copy_package` consumes expanded list; drop inline XLSX glob |
| `src/sofer/repo_compliance.py` | Modify | `build_dataset_card(..., staging_dir=None)` uses expanded for `configs.data_files` + Structure |
| `src/sofer/_converters.py` | Unchanged | Only reused `sanitize_sheet_name`/`normalize_parquet_remote` |
| `tests/test_mirror.py` | Modify | Multi-sheet, single-sheet, fallback, recursive/`keep_csv` |
| `tests/test_publish.py` | Modify | 2-sheet staging mock, assert diff/protection/splits/copy; single-sheet regression |
| `tests/test_repo_compliance.py` | Modify | Card N remotes with staging, fallback without; no local path leak |

## Interfaces / Contracts

```python
def expanded_planned_remotes(cfg: DatasetConfig, keep_csv: bool, staging_dir: Path | None) -> list[str]:
    """If staging_dir is None/not dir: return planned_remotes(cfg, keep_csv).
    Else for eligible .xlsx: glob <parent>/<stem>__*.parquet (sorted);
    emit normalized remotes if any else single normalized stem.parquet.
    Others follow planned_remotes; keep_csv only for .csv."""
```

`publish._repo_diff_summary(cfg, existing, keep_csv, codebook_remotes=None, staging_dir=None)` — expanded before `*` marker. `build_dataset_card(..., keep_csv=False, staging_dir=None)` — expanded when `staging_dir.is_dir()`.

Invariants: recursive passthrough; collisions via `_validate_case_fold_collisions` unchanged; order = declaration → per-xlsx sorted glob.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit `test_mirror` | N remotes, single stays single, fallback, recursive/keep_csv | `tmp_path` + `Path.touch` for `__*.parquet`; no openpyxl |
| Unit `test_repo_compliance` | card lists N with staging, fallback, `configs==Structure` | `DatasetConfig` + `tmp_path` with 2 sheets |
| Integration `test_publish` | diff N, per-sheet protection, copy stages N, splits=2, dry-run N | Mock `HfApi`, fake staging dir, check copies + diff output |
| Regression | single-sheet no phantom `__` | staging with only `single.parquet` |

Edge: empty staging → fallback; `convert_to_parquet=False` → passthrough; mixed csv/tsv/xlsx/jsonl → diff==staged.

## Migration / Rollout

No migration. Placeholder `report.parquet` compatible pre-prepare; `prepare`+`publish` auto-expands. Rollback = revert helper + call sites. No CLI or manifest.

## Open Questions

- [ ] `build_dataset_card` caller in `prepare.py` should pass `staging_dir=output_dir` explicitly vs `None` for pre-prepare.
- [ ] Local target card: use source mirror (prepare output) as ground truth, not destination.
