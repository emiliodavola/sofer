# Design: fix-multisheet-codebook-card-collapse

## Technical Approach

Restore `sheet → stem__sheet.parquet → stem__sheet.md → per-sheet <details>` provenance.
Reuse `sanitize_sheet_name` + `seen` dedup verbatim from `_converters.py` so prepare's
N-Parquets and codebook N-markdowns stay in sync. Single-sheet XLSX stays `stem.md`
(backward compat). Card groups `ColumnSchema` by `origin` sheet fragment and wraps
per-table `<details>` gated by a tool-wide `card_collapse_threshold=15`.
Maps to CB-R09, RC-R21, TC-12, PRP-10 deltas.

## Architecture Decisions

| Decision | Options | Tradeoff | Choice |
|---|---|---|---|
| **N-files vs one-file** | A N files `stem__sheet.md` / B one file N sections / C hybrid | B breaks Parquet 1:1, long doc; C duplicates | **A N-files** — mirrors `_convert_xlsx_to_parquet` `dict[stem__sheet]`, card grouping free |
| **Sheet iteration owner** | New helper in `codebook.py` vs inline in `_converters` | Reusing writer couples domains | **New `_read_xlsx_sheets` + thin `_read_xlsx` wrapper**; imports `sanitize_sheet_name` verbatim |
| **Collision key** | Per-entry vs sheet-expanded | Per-entry masks `a__ventas.xlsx` vs `a_ventas.csv` (`__+→_`) | **Sheet-expanded `output_paths` pre-write** with dual guards; partial-write-then-raise kept |
| **Threshold scope** | Per-dataset `[meta]` vs tool-wide `[tool.sofer]` | Per-dataset fragments UX; literal violates rule 1 | **Tool-wide only** `[tool.sofer] card_collapse_threshold=15`, `_DEFAULTS`, `int>=0` |
| **Card grouping key** | Parse `origin` vs new field | New field needs profile change | **Group by `origin` stem fragment** (already per-sheet); `features` stays flat |
| **Collapse predicate** | Threshold only / groups>1 / OR | Single large table vs small multi-sheet | **OR `len(group)>thr or len(groups)>1`** — single ≤thr flat, else per-sheet `<details>` |

## Data Flow

```
.xlsx (N sheets)
  │ sanitize_sheet_name + seen dedup → sanitized[0..N-1]
  ├─→ _convert_xlsx_to_parquet ─→ staging/stem__sanitized.parquet (prepare)
  │         │ normalize_parquet_remote (__+→_) for disk/remotes
  │         └─→ expanded_planned_remotes / build_schema_report_with_rows → ColumnSchema(origin=sheet.parquet)
  │
  └─→ _read_xlsx_sheets(path) ─→ {sanitized: (headers,columns,dtypes)} ─┐
              │ empty header_row→([],[],{col:"unknown"}) placeholder        │
              └─→ generate() [sheet0 only] OR generate_all ─→ N codebooks  │
                     codebooks/<rel>/stem__sanitized.md (1 sheet→stem.md)  │
                     outputs=[(path,ncols)] → index "Tables:N Total:sum"    │
                                                                            │
ColumnSchema[] ──group by origin sheet fragment──→ dict[label→cols] ──→ build_dataset_card
    │ per-group table | Column | Type | File | → wrap decision ─→ <details> or flat
    └─ features flat (no collapse)
```

## File Changes

| File | Action | Description | Est. |
|------|--------|-------------|------|
| `src/sofer/codebook.py` | Modify | Add `_read_xlsx_sheets` (`wb.sheetnames` + `sanitize_sheet_name`/`seen`); `_read_xlsx` delegates to `sheets[0]`; `generate_all` uses sheet-expanded collision/index + per-sheet `_build_markdown` | ~90 |
| `src/sofer/repo_compliance.py` | Modify | Add `_group_by_origin` + HF wrapper; Data Fields → per-group `<details><summary>Data Fields -- {label} (N cols)</summary>\n\n| Column|` gated by `config.CARD_COLLAPSE_THRESHOLD` | ~55 |
| `src/sofer/config.py` | Modify | `_DEFAULTS["card_collapse_threshold"]=15`, const `CARD_COLLAPSE_THRESHOLD`, `int>=0` validation, `reload` rebinding | ~15 |
| `pyproject.toml` | Modify | `[tool.sofer] card_collapse_threshold = 15` | 2 |
| `docs/configuration.md` + `README*` | Modify | Document threshold | ~15 |
| `src/sofer/prepare.py` | No change | Inherits via `generate_all(output_dir=build)` | 0 |
| `tests/test_codebook.py` | Modify | `_make_xlsx` fixtures: 2 sheets→2 files, dedup, empty, batch N, sheet-aware collision, index sums | ~80 |
| `tests/test_repo_compliance.py` | Modify | Card: flat vs wrap, 2 `<details>` + blank line, boundary `==15`, mixed-small wraps | ~60 |

**Total impl ~177 + tests ~140 = ~317 lines vs 2000 budget. 400-line budget risk: Low. Chained PRs: No.**

## Interfaces / Contracts

```python
# codebook.py — new internal helper
def _read_xlsx_sheets(path: str) -> dict[str, tuple[list[str], list[list[str]], dict[str,str]]]:
    """wb.sheetnames → sanitized deduped key; empty sheet → ([],[],{"unknown"}) placeholder."""

# repo_compliance.py — no public sig change
def build_dataset_card(..., staging_dir: Path|None=None) -> str:
    # groups = group_by_origin(schema)
    # wrap if len(cols)>config.CARD_COLLAPSE_THRESHOLD or len(groups)>1:
    #   f"<details><summary>Data Fields -- {label} ({len(cols)} columns)</summary>\n\n{table}\n\n</details>"
```

`card_collapse_threshold:int=15` in `[tool.sofer]` → `_DEFAULTS` → `_read_tool_section` validates `int>=0` else `ValueError` → `reload` rebinds `CARD_COLLAPSE_THRESHOLD` (TC-02/TC-06).

## Edge Handling

Empty sheet (`header_row is None`) → placeholder markdown, no crash. Dedup collision uses `seen[base]→_{n}` + tracking deduped name. `__/__` duality: codebook emits `__` logical key, collision/index normalize via `__+→_`. `row_counts` sums per-sheet `origin` only, no inflation. Unreadable sheet skipped with stderr, non-colliding still written.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Dedup parity | `_make_xlsx` `Ventas`/`VENTAS` → `ventas, ventas_2` |
| Unit | `_read_xlsx_sheets` empty/header-only | `_make_xlsx` fixtures, assert placeholder no crash |
| Unit | Card blank line | Assert `</summary>\n\n| Column` in output |
| Integration | `generate_all` 2 sheets → 2 `__md` + dual-guard collision | `DatasetConfig` `a.csv` + `report.xlsx(2)` → 3 codebooks + index sums |
| Integration | Card boundaries | 4+3 cols multi→2 `<details>`; 16 single→wrap; 15 single→flat; 5+5 multi→wrap via `groups>1` |
| Regression | Prepare N-Parquets + N-codebooks sync | `_make_xlsx aristas/nodos` → `prepare` builds both parquets + matching codebooks |

## Migration / Rollout

No migration. Single-sheet unchanged. Rollback: revert sources or set `card_collapse_threshold=999`.

## Open Questions

- None blocking — `render.py` per-sheet out of scope.
```

