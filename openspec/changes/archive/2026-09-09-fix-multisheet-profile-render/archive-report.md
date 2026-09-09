# Archive Report — fix-multisheet-profile-render

**Change**: fix-multisheet-profile-render
**Issue**: GitHub #108 / PR #108 (merge `8a40a89`)
**Date**: 2026-09-09
**Artifact store**: hybrid (OpenSpec files + Engram)
**Status**: archived
**Verify verdict**: PASS by merge — PR #108 merged to `dev` as `8a40a89` (2026-08-31), CI green; content re-verified in the #115/#116 batch (1421 passed, 6 skipped)
**Branch**: fix/116-pr4 @ 6f9dc76 (PR #138 landing)

## Summary

Batch fix for `--all-files` profile/render on multi-sheet workbooks. Before this change a `.xlsx` with N>1 sheets emitted only the first sheet (`next(iter(sheets))`); after it, profile expands to N `metadata.yaml` files and render to N `README.md` files, one per sheet, using the shared `sanitize_sheet_name` + `seen` `_{n}` dedup and a `stem__<sanitized>` output naming scheme with parity across `codebook`/`prepare`/`profile`/`render`. Sheet-expanded outputs are normalized (`re.sub(r"__+", "_", ...)`) before the collision map is computed, so `a__ventas.xlsx::Ventas` and `a_ventas.csv` collide and raise a sheet-suffixed `ValueError` after non-colliding outputs are written. Single-sheet `.xlsx` and non-`.xlsx` entries stay suffix-less.

Live implementation: `src/sofer/_converters.py` (`sanitize_sheet_name`), `src/sofer/codebook.py` (`_read_xlsx_sheets`), `src/sofer/profile.py` (batch expansion, L278+), `src/sofer/render.py`.

## Spec Sync

- **Domain**: `profile` — live spec `openspec/specs/profile/spec.md` updated.
- **Domain**: `render` — live spec `openspec/specs/render/spec.md` updated.
- **Requirements modified (2)**: PRF-05 (Batch profile via `--all-files`) and RND-04 (Batch render via `--all-files`) — merged the MODIFIED delta into the live requirement blocks. The live blocks (as synced by the `feat-profile-render-all-files` archive) already carried the post-merge refinements `rel_stem` derivation, pre-computed `output → [sources]` collision map, Option B `--output` anchoring, and root-index exclusion; the delta added the multi-sheet expansion clause (`_read_xlsx_sheets`, `sanitize_sheet_name`, `seen` `_{n}`, `stem__<sanitized>` naming, `__+`→`_` normalized collision keys, `<path>::<sheet>` naming) plus 5 new PRF-05 scenarios and 6 new RND-04 scenarios. Merge was additive: base text retained, delta clauses/scenarios spliced in, delta's "Same-stem collision" scenario upgraded with the `plus raw/ok.csv` partial-write proof. No other requirement blocks touched.
- **Delta**: `openspec/changes/fix-multisheet-profile-render/specs/{profile,render}/spec.md` (MODIFIED-only).

## Verification Evidence

| Gate | Result |
|------|--------|
| Merge | PR #108 merged `8a40a89` to `dev` (2026-08-31), CI green |
| Suite (post-batch) | `uv run pytest tests/ -q` → 1421 passed, 6 skipped (fix/116-pr4, 2026-09-09) |
| Lint/type | `ruff check` clean, `mypy src/` clean (same run) |
| Live code match | `profile.py` L209/L278-287 and `_converters.py`/`codebook.py` implement the multi-sheet contract |

## Archive Mechanics

- Move: `git mv openspec/changes/fix-multisheet-profile-render openspec/changes/archive/2026-09-09-fix-multisheet-profile-render`.
- Readback: spec sync verified structurally (PRF-05 → 13 scenarios, RND-04 → 12 scenarios, matching the deltas) and by `git diff` (+83/−8 across the two live specs).
- `archive-report.md` additive; active changes dir no longer contains `fix-multisheet-profile-render`.
