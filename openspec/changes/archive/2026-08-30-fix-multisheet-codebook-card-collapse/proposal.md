# Proposal: fix-multisheet-codebook-card-collapse

## Intent

Fix #97 (codebook reads only `wb.active` → sheets lost) + #98 (card one mega Data Fields table). Restore `sheet → stem__sheet.parquet → stem__sheet.md → per-sheet <details>` provenance matching `prepare` N-Parquet split. Constraint: *cada tabla por separado* (each table own `<details>`).

## Scope

### In Scope
- `codebook.py`: `_read_xlsx_sheets` via `sanitize_sheet_name`+`seen` dedup; `generate()` single-sheet; `generate_all()` N-files `codebooks/<rel>/<stem>__<sanitized>.md` (1 sheet→`stem.md`), sheet-aware collision/index.
- `repo_compliance.py`: group `ColumnSchema` by `origin`, per-group `<details><summary>Data Fields -- <sheet> (N cols)</summary>` with blank line, gated by `card_collapse_threshold`; single table below threshold unwrapped.
- `config.py`+`pyproject.toml`: `card_collapse_threshold=15` (`_DEFAULTS`, `reload`, int>=0).
- Specs: `codebook` CB-R09, `repo-compliance` collapsible, `tool-config` threshold; `README/ES` sync.
- Tests: codebook multisheet/collision/index, card collapse, prepare build.

### Out of Scope
- `render.py` per-sheet (needs profile provenance); umbrella hybrid; `features` stays flat; `generate()` CLI compat unchanged.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `codebook`: multisheet, sanitized `__` stems+dedup, N codebooks, sheet collision/index.
- `repo-compliance`: per-sheet `<details>` + threshold.
- `prepare`: inherits N-files (spec only).
- `tool-config`: `card_collapse_threshold`.

## Approach

**A: N-files one-per-sheet** reusing `sanitize_sheet_name` verbatim. HF requires blank line after `<summary>`. Wrap when `len(group)>15` or `len(groups)>1`. Single-sheet → `stem.md`.

Rejected: **B** one file N sections (long doc, breaks Parquet 1:1) and **C** hybrid umbrella (duplication). A keeps Parquet↔codebook↔card aligned and gives card grouping for free.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/codebook.py` | Modified | Sheet loop, N-files, collision/index |
| `src/sofer/repo_compliance.py` | Modified | Group by origin, per-sheet `<details>` |
| `src/sofer/config.py`, `pyproject.toml` | Modified | Threshold 15 |
| `openspec/specs/codebook,repo-compliance,tool-config` | Modified | Delta specs |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `__` vs `_` collision | Med | Sheet-expanded keys; dual guards |
| Dedup drift | Med | Import `sanitize_sheet_name` verbatim |
| Empty sheets crash | Low | `header_row is None` → placeholder |
| Row_counts inflation | Low | Sum per-sheet `origin` only |
| HF blank-line quirk | Med | Emit blank line inside `<details>` |
| Hardcoded threshold | Low | `config.CARD_COLLAPSE_THRESHOLD` |

## Rollback Plan

Revert source+`pyproject.toml`; or set `card_collapse_threshold=999` to force unwrapped. Single-sheet unchanged — no migration.

## Dependencies

#97/#98, `sanitize_sheet_name` contract, `normalize_parquet_remote` duality, `prepare` N-Parquet.

## Success Criteria

- [ ] #97: 2 sheets → 2 `__<sanitized>.md` (dedup `_{n}`, empty placeholder, `Ventas`/`VENTAS`→`_2`); single-sheet → `stem.md`; collision sheet-aware; index sums sheets.
- [ ] #98: 2 sheets → 2 independent `<details>` with blank line; single-file below 15 unwrapped; both sheets appear; `features` flat.
- [ ] Threshold in `[tool.sofer]` default 15 via `reload`, no literals; `uv run pytest tests/ -q` green.
