# Proposal: Fix multisheet profile/render (all xlsx sheets)

## Intent

`profile`/`render` (CLI+MCP) only read first sheet of `.xlsx` (`_read_dataset_for_profile` via `_read_xlsx` = `next(iter(sheets))`, 1:1 `generate_all_*`). N-1 sheets silently lost. `codebook`/`prepare`/`repo_compliance` already expand as `stem__sheet`. Fix parity so `metadata.yaml`/`README.md` cover all sheets.

## Scope

### In Scope
- Batch `generate_all_profiles`/`generate_all_renders` expand `.xlsx` 1:N if N>1; single-sheet stays 1:1
- Reuse `sanitize_sheet_name` + `seen` dedup `_{n}`, collision `__+`->`_`, partial-write-then-`ValueError`

### Out of Scope
- Option B `sheets[]` aggregation (evaluated, rejected)
- `prepare`/parquet or non-xlsx changes, new config keys

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `profile`: batch emits N `profiles/<rel>/<stem>__<sanitized>.metadata.yaml` (single-sheet compat)
- `render`: batch emits N `renders/<rel>/<stem>__<sanitized>.README.md` (same collision/anchoring)
- `mcp-server` (implicit): `sofer_profile`/`sofer_render` `all_files` inherit expansion

## Approach

**Decision: Option A 1:N over Option B `sheets[]`.**

- Why 1:N: parity with `codebook` (`codebooks/<stem>__<sheet>.md`) and `prepare` (`stem__sheet.parquet`); flat `Metadata`, HF staging per-sheet, no schema break. Option B changes `Metadata`/`card`/`publish` — higher churn.
- Reuse: `_read_xlsx_sheets` + `sanitize_sheet_name` (`lower->NFKD->ascii->space->_->[^a-z0-9_-]->_->__+->_->strip`, empty->`sheet`) + `seen` dedup verbatim (`codebook.py:141`/`_converters.py:76`).
- Layout: `base_dir.resolve()`, `data_dir=base_dir/config.OUTPUT_DIR`, `rel_stem` via `relative_to(data_dir)` else `base_dir`, `PurePath.suffixes` replace last suffix only, insert `__<sanitized>`, read `PROFILE_DIR`/`RENDER_DIR` from `config.py`.
- Collision: precompute `expanded=[(local,sanitized|None,out)]`, normalized `re.sub(r"__+","_",path)` so `a__ventas`≈`a_ventas`; write non-colliding then `ValueError` naming `::sheet` sources. `len==1`->no suffix; empty->placeholder.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/profile.py` | Modified | Replace first-sheet read with `_read_xlsx_sheets`; 1:N batch + sheet-expanded collisions |
| `src/sofer/render.py` | Modified | 1:N per-sheet `metadata.yaml`->`README.md` with same logic |
| `src/sofer/_converters.py` | Reused | `sanitize_sheet_name` unchanged |
| `src/sofer/mcp_server.py` | Indirect | `sofer_profile`/`render` `all_files` inherit |
| `tests/test_profile.py`, `tests/test_render.py` | Modified | 2-sheet openpyxl + `__` collision tests |
| `README.md`, `README_ES.md` | Modified | Document multisheet parity |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Collisions (`A__B` vs `A_B`, dups) | Med | `__+`->`_` + `seen _{n}` from codebook; partial-write-then-ValueError |
| Single-sheet regression | Low | `len==1` suffix-less + regression test |
| MCP `output_dir` escape | Low | Anchor relative `output_dir` to `base_dir`, reuse containment |

## Rollback Plan

Revert `profile.py`/`render.py` to 1:1; delete `*__*.metadata.yaml`/`*__*.README.md` if needed — derived artifacts, no migration. `git revert <commit>`.

## Dependencies

- `openpyxl` (present), `config.py` `PROFILE_DIR`/`RENDER_DIR`/`OUTPUT_DIR`, `DatasetConfig` `[[file]]`

## Success Criteria

- [ ] 2-sheet workbook (`Sales:id,amount` / `Inventory:sku,qty`) via `profile --all-files` yields `profiles/<stem>__sales.metadata.yaml` + `__inventory.metadata.yaml` with correct per-sheet schema/rows
- [ ] Same via `render --all-files` yields 2 `renders/__*.README.md`; single-sheet stays `stem.metadata.yaml`/`.README.md`
- [ ] Collision `A__B` sheet vs `A_B.csv` raises `ValueError` after non-colliding writes
- [ ] `sanitize_sheet_name("DATA GOT Año")`->`data_got_ano`; dup `Ventas`->`ventas, ventas_2`
- [ ] MCP `sofer_profile`/`sofer_render` `all_files:true` show N outputs
- [ ] `uv run pytest tests/ -q` + `ruff check`/`mypy` pass; no hardcoded `";"`/`"utf-8-sig"` outside `config.py`
