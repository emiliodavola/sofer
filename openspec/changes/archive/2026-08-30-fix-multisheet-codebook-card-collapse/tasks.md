# Tasks: fix-multisheet-codebook-card-collapse

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 320–360 (impl ~175 + tests ~140 + docs ~25) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR (no chain) |
| Delivery strategy | auto-chain (auto-forecast) |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Config + codebook multisheet + card collapse + tests + docs | PR 1 → main | Single PR; 320 < 400 and < 2000 budget |

## Execution Estimate

| Task | Est. lines | Size | Parallel |
|------|------------|------|----------|
| 1.1 config threshold | ~15 | S | — |
| 2.1 _read_xlsx_sheets | ~30 | M | after 1.1, with 2.4 |
| 2.2 _read_xlsx wrapper | ~10 | XS | after 2.1 |
| 2.3 generate_all N-files | ~60 | M | after 2.1 |
| 2.4 card grouping/details | ~55 | M | after 1.1, with 2.1 |
| 3.1 prepare inheritance | 0 | XS | after 2.3 |
| 4.1 tests codebook | ~80 | M | after 2.3 |
| 4.2 tests card | ~60 | M | after 2.4 |
| 5.1 README/ES docs | ~20 | S | with 4.x |
| 5.2 verification | 0 | S | last |

## Phase 1: Foundation / Config

- [x] 1.1 Add `card_collapse_threshold=15` to `pyproject.toml`/`config.py` `_DEFAULTS`, bind `CARD_COLLAPSE_THRESHOLD`, validate `int>=0`, rebind in `reload`, doc in `docs/configuration.md` — no literal `15`

## Phase 2: Core Implementation

- [x] 2.1 Implement `_read_xlsx_sheets` in `src/sofer/codebook.py` reusing `sanitize_sheet_name`+`seen` verbatim; handle `header_row is None` → placeholder, empty sheets, return `dict[sanitized->(headers,columns,dtypes)]`
- [x] 2.2 Refactor `_read_xlsx` to delegate to `_read_xlsx_sheets[0]`; keep `generate()` backward compat for csv/parquet/jsonl/tsv
- [x] 2.3 Expand `generate_all` to sheet-expanded `output_paths` with dual `__`/`_` guard, N files `stem__sheet.md` (1 sheet→`stem.md`), per-sheet `_build_markdown`, fix index aggregation, keep partial-write-then-`ValueError`
- [x] 2.4 Add `_group_by_origin` + per-group `<details>` in `src/sofer/repo_compliance.py`; group by `origin`, wrap when `len(cols)>thr OR len(groups)>1`, blank line after `</summary>`, `features` flat

## Phase 3: Integration

- [x] 3.1 Verify `prepare` inherits N-codebooks via `generate_all(output_dir=build)` 1:1 with parquets, dual guard + orphan pruning; no new XLSX logic in `prepare.py`

## Phase 4: Testing

- [x] 4.1 Tests codebook in `tests/test_codebook.py`: `_make_xlsx` 2 sheets, single vs multi, batch N+index, dedup `Ventas`→`_2`, empty placeholder, `__`/`_` collision
- [x] 4.2 Tests card in `tests/test_repo_compliance.py`: single ≤thr no `<details>`, groups>1 per-table `<details>`, >thr wraps, blank line, `15` flat/`16` wrap, reload override

## Phase 5: Docs & Verification

- [x] 5.1 Update `README.md`/`README_ES.md` codebook multisheet + HF collapsible per-table sections, note `<details>` HF-compatible, *cada tabla por separado*
- [x] 5.2 Run `ruff`/`mypy`/`pytest`; manual repro `DATA_GOT_ALL.xlsx` → 2 parquets + 2 codebooks + per-sheet `<details>`

### Dependency Order

1.1 → (2.1∥2.4) → 2.2/2.3 → 3.1 → (4.1∥4.2) → 5.1/5.2. Critical: 1.1→2.1→2.3→4.1→5.2.

