# Tasks: Fix multisheet profile/render (all xlsx sheets)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 280–340 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | single PR (helpers + 1:N + tests + docs) |
| Delivery strategy | auto-chain |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Helpers + profile/render 1:N + tests + docs | PR 1 | base fix/multisheet-profile-render; standalone, under 400 lines |

## Phase 1: Foundation — Helpers & Plumbing

- [x] 1.1 Add `_profile_output_for_rel(dir, rel, sheet)` in `src/sofer/profile.py` — PurePath.suffixes last→`.metadata.yaml`, `__<sanitized>` if sheet (mirror `codebook._codebook_output_for_rel`)
- [x] 1.2 Add `_normalize_profile_collision_key(p: Path)` (`re.sub(r"__+","_",p.as_posix())`) in `src/sofer/profile.py`
- [x] 1.3 Add `_render_output_for_rel` + `_normalize_render_collision_key` in `src/sofer/render.py` — same logic, `→.README.md`
- [x] 1.4 Import `re`, `sanitize_sheet_name` (`_converters`), `_read_xlsx_sheets` (`codebook`) in both modules (no hardcoded `;`/`utf-8-sig`)

## Phase 2: Core Implementation — 1:N Batch Expansion

- [x] 2.1 Refactor `generate_all_profiles` in `src/sofer/profile.py` to 1:N: `expanded=[(local,sanitized|None,out)]` via `_read_xlsx_sheets`+`seen _{n}`; `len==1`→None; cache sheets
- [x] 2.2 Collision map `profile.py`: `re.sub(r"__+","_",path)`→sources; write non-colliding `metadata.yaml` per sheet; partial-write then `ValueError "<rel>::<sheet>"`
- [x] 2.3 Option B anchoring `profile.py`: `base_dir.resolve()`, `data_dir=base_dir/OUTPUT_DIR`, `write_root=base_dir/output` if relative, `profiles_dir=write_root/PROFILE_DIR`
- [x] 2.4 Refactor `generate_all_renders` in `src/sofer/render.py` to 1:N parity: resolve `metadata.yaml` from `profiles_dir`; reuse `sanitize+seen`; skip missing with warning
- [x] 2.5 Collision + partial-write `render.py`: normalized `__+→_`, write non-colliding `README.md`, then `ValueError ::sheet`
- [x] 2.6 Per-sheet dispatch: non-xlsx via streamed CSV, xlsx via cached `(headers,columns)` — rows reflect single sheet

## Phase 3: Testing — Multisheet & Collision

- [x] 3.1 `tests/test_profile.py`: 2-sheet openpyxl `Sales(id,amount)`+`Inventory(sku,qty)` via `DatasetConfig` → `report__sales`+`__inventory.metadata.yaml` schema/rows per sheet
- [x] 3.2 `tests/test_profile.py`: single-sheet stays suffix-less byte-identical; `sanitize("DATA GOT Año")→data_got_ano`, empty→`sheet`; dedup `Ventas/VENTAS→ventas, ventas_2/_3`
- [x] 3.3 `tests/test_profile.py`: collision `a__ventas.xlsx::Ventas` vs `a_ventas.csv` normalized `__+→_` raises `ValueError ::Ventas` after `ok.csv` persisted
- [x] 3.4 `tests/test_render.py`: 2-sheet `report__sales/README.md`+`__inventory/README.md` per-sheet schema; single-sheet suffix-less; dedup parity
- [x] 3.5 `tests/test_render.py`: collision normalized raises `ValueError ::sheet`; missing `metadata.yaml` warns skips; Option B relative anchored to `base_dir` via `monkeypatch.chdir`
- [x] 3.6 Verify: `uv run pytest tests/test_profile.py tests/test_render.py -q` + `uv run pytest tests/ -q`; `ruff check` + `mypy src/` green

## Phase 4: Docs & Verification

- [x] 4.1 Update `README.md` + `README_ES.md`: document `profile`/`render --all-files` `stem__sheet`, `sanitize→seen _{n}`, `__+→_` collision, partial-write
- [x] 4.2 Run `ruff check` + `mypy src/` + `pytest tests/ -q` — no hardcoded `";"`/`"utf-8-sig"` outside `config.py`

