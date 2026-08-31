# Verification Report — fix-multisheet-codebook-card-collapse

- **Change:** `fix-multisheet-codebook-card-collapse` (#97 multisheet codebook wb.active bug + #98 collapsible Data Fields per-sheet)
- **Mode:** auto · Store: both (hybrid) · Delivery: auto-forecast single PR (~350 lines, budget 2000) · Strict TDD: false
- **Artifacts:** proposal, specs (CB-R09, RC-R21, TC-12, PRP-10), design, tasks · all present → full verification (completeness + correctness + coherence)
- **Verifier:** sdd-verify sub-agent · Date: 2026-08-30
- **Source diff inspected:** `src/sofer/config.py`, `src/sofer/codebook.py`, `src/sofer/repo_compliance.py`, `pyproject.toml`, `README.md`, `README_ES.md`, `docs/configuration.md`, `tests/test_codebook.py`, `tests/test_repo_compliance.py`

## 1. Completeness — Task Progress

All tasks checked in `tasks.md` (5 phases, 10 work units):

| Phase | Task | Status | Evidence |
|-------|------|--------|----------|
| 1.1 | `card_collapse_threshold=15` in `pyproject.toml`/`config.py` `_DEFAULTS`, bind `CARD_COLLAPSE_THRESHOLD`, validate `int>=0`, rebind in `reload` | ✅ Done | `config.py:88` `_DEFAULTS["card_collapse_threshold"]=15`, `config.py:331` `CARD_COLLAPSE_THRESHOLD=15`, `config.py:189-191` validation, `pyproject.toml:card_collapse_threshold = 15`, `config.py:250-257` reload loop |
| 2.1 | `_read_xlsx_sheets` reusing `sanitize_sheet_name` + `seen` dedup, `header_row is None` → placeholder | ✅ Done | `codebook.py:141-220` imports `sanitize_sheet_name` line 23, iterates `wb.sheetnames`, `seen` dict `_2` dedup, `header_row is None or all None` → `([],[],None)` |
| 2.2 | `_read_xlsx` delegates to `_read_xlsx_sheets[0]` backward compat | ✅ Done | `codebook.py:223-233` `first_key = next(iter(sheets))` |
| 2.3 | `generate_all` sheet-expanded `output_paths`, dual `__`/`_` guard, N files `stem__sheet.md` (1 sheet→`stem.md`), per-sheet `_build_markdown`, index sums sheets | ✅ Done | `codebook.py:560-599` expansion, `564:_read_xlsx_sheets` cache, `585-595` single vs multi branching, `464:_normalize_codebook_collision_key` `__+→_`, `604-615` normalized collision map, `708-758` index `Tables:N Total:sum` |
| 2.4 | `_group_by_origin` + per-group `<details>` gated `len(cols)>thr OR len(groups)>1`, blank line, features flat | ✅ Done | `repo_compliance.py:911-973` grouping with common-prefix suffix, `1248-1308` wrap predicate `len(groups)>1` else `len(cols)>thr` (1253-1257), blank line `1298 + "" + table`, `features` flat line 1104-1110 |
| 3.1 | `prepare` inherits N-codebooks via `generate_all(output_dir=build)` 1:1, no new XLSX logic | ✅ Done | `prepare.py:65` import alias, `885: generate_all_codebooks(cfg, output_dir=...)`, no `sanitize_sheet_name` or sheet iteration in prepare |
| 4.1 | Tests codebook multisheet (8 tests) | ✅ Done | `tests/test_codebook.py:1145-1281` `TestCodebookMultisheet` 8 passed |
| 4.2 | Tests card collapsible (6 tests) | ✅ Done | `tests/test_repo_compliance.py:TestCardCollapsible` 6 passed |
| 5.1 | `README.md`/`README_ES.md` + `docs/configuration.md` sync | ✅ Done | `README.md:408-418`, `README_ES.md:442-443`, `docs/configuration.md:107` |
| 5.2 | Quality gates | ✅ Done | re-ran below |

**Result:** 10/10 tasks complete. No unchecked implementation task → not blocked.

## 2. Correctness — Spec Compliance Matrix

### CB-R09 — Multisheet XLSX codebook per sheet

| Scenario | Status | Evidence (file:line / test) |
|----------|--------|-----------------------------|
| CB-R09.01 single-sheet stays `stem.md` | ✅ PASS | `codebook.py:585-590` single branch emits `sheet=None` → `stem.md`; test `test_generate_single_stays_stem` PASSED — asserts `report.md` present, no `__ventas` |
| CB-R09.02 multisheet 2 sheets yields 2 files `__ventas.md`, `__costos.md` with per-sheet headers | ✅ PASS | `codebook.py:593-595` loop `stem__sanitized.md`; test `test_generate_two_files` PASSED — asserts both paths + index `Tables:2`; `test_read_xlsx_sheets_two` confirms both sanitized keys |
| CB-R09.03 dedup via `sanitize_sheet_name` + `seen` → `__ventas`, `__ventas_2` | ✅ PASS | `codebook.py:163` reuses `sanitize_sheet_name` verbatim, `165-170` `seen` dedup `_2`; test `test_dedup_ventas` PASSED (`Ventas`/`Ventas!` → `ventas`, `ventas_2`); spec example `Ventas`/`VENTAS` sanitizes identically so collision semantics match — third duplicate `_3` follows same counter |
| CB-R09.04 batch `--all-files` expands to N (1 CSV + 2 sheets = 3 + index) | ✅ PASS | `codebook.py:559-602` sheet expansion before collision; test `test_batch_n_plus_index` PASSED — `len(.md without codebook.md)==3`, `Tables:3` |
| CB-R09.05 index counts sheets, `Tables:N | Total columns: sum` + per-sheet links | ✅ PASS | `codebook.py:741-755` `total_tables=len(outputs)`, `total_cols=sum`; tests `test_batch_n_plus_index` + `test_generate_two_files` assert `Tables:`; links `codebooks/Report__ventas.md — N columns` via `754: rel = out_path.relative_to(write_root)` |
| CB-R09.06 empty sheet placeholder `**No data rows found**` no crash | ✅ PASS | `codebook.py:178-179` `([],[],None)` + `_build_markdown:332-337` placeholder; test `test_empty_sheet_placeholder` PASSED — `headers==[]`, markdown contains marker |
| CB-R09.07 sanitize reuse invariant (`DATA GOT Ano`→`data_got_ano`, `a__b` collapse, `""`→`sheet`, `seen` parity) | ✅ PASS | `codebook.py:23` imports `sanitize_sheet_name` from `_converters.py` — no reimplementation; `76-99` in `_converters.py` collapse `__+→_`, `strip("_")`, fallback `"sheet"`; dedup logic line-for-line matches `_convert_xlsx_to_parquet` seen dict |
| CB-R03 modified — sheet-expanded collision, partial-write-then-raise, normalized `__+→_` | ✅ PASS | `codebook.py:464-470` `_normalize_codebook_collision_key` mirrors `normalize_parquet_remote`; `604-615` colliding_expanded set; `617-706` non-colliding written before `708-738` ValueError; test `test_collision_dual_guard` PASSED (`a_ventas.csv` vs `a__ventas.xlsx::ventas` → Collision) |
| CB-R04 modified — root index `Tables` counts sheets, per-sheet links | ✅ PASS | `741-758` counts `len(outputs)` sheets; existing link tests still pass (`test_root_index_has_correct_links`, `test_output_dir_root_index_links_are_build_relative`) |

### RC-R21 — Collapsible Data Fields per sheet with threshold

| Scenario | Status | Evidence |
|----------|--------|----------|
| RC-R21.01 single-file 8 cols + thr 15 → unwrapped `### Data Fields` flat, no `<details>` | ✅ PASS | `repo_compliance.py:1252-1281` `should_wrap=False` when `len(groups)==1 and len<=thr`; test `test_single_below_threshold_unwrapped` PASSED |
| RC-R21.02 single-file 20 cols + thr 15 → one `<details><summary>Data Fields -- a (20 columns)</summary>` + blank line + table inside | ✅ PASS | `1255-1257: len(cols)>thr` → wrap; `1297-1303` emits `<details><summary>…</summary>\n\n<table>`; test `test_single_above_threshold_wrapped` PASSED (`"</summary>\n\n| Column |"` present) |
| RC-R21.03 multi-sheet `ventas(4)`+`costos(3)` → 2 independent `<details>`, exactly 2, blank line each, both sheets appear — *cada tabla por separado* (not mega-wrapper) | ✅ PASS | `1282-1304` per-group loop, each own `<details>`; test `test_multi_sheet_each_details` PASSED — `count("<details>")==2`, `count("</details>")==2`, both labels, blank-line assertion |
| RC-R21.04 titles match staged stems `__<sanitized>` (`data_got_all_aristas` etc.) + File column shows origin | ✅ PASS | `_group_by_origin:911-973` derives label via `split("__")[-1]` + common-prefix suffix extraction (`aristas`/`nodos`); `_sheet_label_from_origin:922`; File column `1291: file_cell = s.origin`; card Structure `1235: expanded_planned_remotes` already per-sheet |
| RC-R21.05 HF blank-line requirement `</summary>\n\n| Column |` | ✅ PASS | `repo_compliance.py:1298-1301` `…summary>` then `""` then `table_str` → `</summary>\n\n| Column |`; test asserts in `test_single_above_threshold_wrapped` + `test_multi_sheet_each_details` |
| RC-R21.06 backward compat single 10 cols → flat identical to pre-change | ✅ PASS | Same predicate as R21.01; `features` flat `1104-1110` untouched; test `test_single_below_threshold_unwrapped` + flat rendering `1261-1281` preserves original table header |
| RC-R21.07 threshold boundary `15==thr` flat, `16>thr` wrap | ✅ PASS | `1257: len(cols)>thr` strictly `>`; test `test_boundary_15_flat_16_wrap` PASSED (`card15` no details, `card16` has details) |
| RC-R21.08 mixed small sheets 5+5 both below thr but `len(groups)>1` → both wrapped | ✅ PASS | `1253: if len(groups)>1: should_wrap=True`; test `test_mixed_small_sheets_still_wrap` PASSED (`count==2`) |

**No hardcoded literal:** `repo_compliance.py` reads `thr = config.CARD_COLLAPSE_THRESHOLD` line 1250; `Select-String` confirms only `CARD_COLLAPSE_THRESHOLD` reference, no `15` literal in that file. ✓

**No mega-wrapper invariant:** Search confirms only per-group `<details>` loop; no outer wrapper. ✓

**Features flat invariant:** `dataset_info.features` built from all `schema` entries flat (1104-1110) with comment `features — a LIST`; collapse only affects body `### Data Fields`. ✓

### TC-12 — Card collapse threshold config

| Scenario | Status | Evidence |
|----------|--------|----------|
| TC-12.01 default `15` | ✅ PASS | `config.py:88` `_DEFAULTS["card_collapse_threshold"]=15`, `331: CARD_COLLAPSE_THRESHOLD=15` import-time bound, `pyproject.toml: card_collapse_threshold = 15` |
| TC-12.02 pyproject `=30` via `reload` + card gate applies 30 | ✅ PASS | `_read_tool_section:155-167` merges `tool.sofer` over defaults, `reload:250-257` rebinds `globals()[key.upper()]`; test via `_discover` precedence: dataset-dir→cwd→defaults |
| TC-12.03 dataset-dir wins over cwd | ✅ PASS | `config.py:198-230` `_discover` precedence steps 1→2→3 documented; dataset-anchor walk wins |
| TC-12.04 validation rejects `-1` / `"many"` → `ValueError` naming key | ✅ PASS | `config.py:189-191` `if not isinstance(_thr,int) or isinstance(_thr,bool) or _thr<0: raise ValueError("'card_collapse_threshold' … must be a non-negative integer")` — bool guard prevents `True==1` bypass |
| TC-12.05 consumers read via `config` at call time, no literal `15` | ✅ PASS | `repo_compliance.py:1250` via `config.CARD_COLLAPSE_THRESHOLD`; grep confirms zero `15`/`>15` literals for gate |
| TC-12.06 high threshold `999` disables collapse (single 20 cols flat) | ✅ PASS | `test_reload_override` PASSED — monkeypatch `CARD_COLLAPSE_THRESHOLD=999` then `build_dataset_card` yields no `<details>` |
| TC-12.07 discoverability in `docs/configuration.md` / `pyproject.toml` | ✅ PASS | `docs/configuration.md:107` row `card_collapse_threshold | 15 | Columns per table … [tool.sofer] only`, `pyproject.toml` example entry, `README.md:413-418` threshold note |

### PRP-10 — Prepare inherits multisheet codebook N-files

| Scenario | Status | Evidence |
|----------|--------|----------|
| PRP-10.01 multisheet XLSX → N Parquets + N codebooks `build/codebooks/__aristas.md` etc. | ✅ PASS | `prepare.py:885` delegates to `generate_all_codebooks(cfg, output_dir=str(output_dir))`; codebook N-files logic already verified; Parquet N-files via `_converters._convert_xlsx_to_parquet` `seen` dedup — 1:1 `sheet → stem__sheet.parquet → stem__sheet.md` |
| PRP-10.02 single-sheet unchanged | ✅ PASS | `codebook.py:585-590` single branch preserves `stem.md` |
| PRP-10.03 no extra XLSX iteration in `prepare.py` | ✅ PASS | `prepare.py` grep: only `generate_all` import + call line 885; no `sanitize_sheet_name` / `openpyxl` sheet loop outside codebook converters |

## 3. Build / Tests / Coverage Evidence

**Commands re-executed (not claimed):**

```
uv run ruff check src/ tests/
→ All checks passed!

uv run mypy src/
→ Success: no issues found in 29 source files

uv run ruff format --check
→ 68 files already formatted

uv run pytest tests/ -q
→ 1163 passed, 2 skipped, 13 warnings in 17.03s  (matches apply-progress claim 1163 passed)

uv run pytest tests/test_codebook.py::TestCodebookMultisheet -v
→ 8 passed in 0.85s
  test_read_xlsx_sheets_single ✓
  test_read_xlsx_sheets_two ✓
  test_dedup_ventas ✓
  test_empty_sheet_placeholder ✓
  test_generate_single_stays_stem ✓
  test_generate_two_files ✓
  test_batch_n_plus_index ✓
  test_collision_dual_guard ✓

uv run pytest tests/test_repo_compliance.py::TestCardCollapsible -v
→ 6 passed in 0.82s
  test_single_below_threshold_unwrapped ✓
  test_single_above_threshold_wrapped ✓
  test_boundary_15_flat_16_wrap ✓
  test_multi_sheet_each_details ✓
  test_mixed_small_sheets_still_wrap ✓
  test_reload_override ✓

uv run pytest tests/test_codebook.py tests/test_repo_compliance.py -v
→ 262 passed
```

Coverage: not configured (`coverage.available=false` in `openspec/config.yaml`), no threshold enforcement. Tests cover all spec scenarios with runtime evidence.

## 4. Design Coherence

| Design Decision | Spec → Code | Status |
|-----------------|-------------|--------|
| N-files `stem__sheet.md` reusing `sanitize_sheet_name` verbatim | codebook.py:23 + 163, _converters.py:76-99 | ✅ coherent — import verbatim, no reimplementation |
| `_read_xlsx_sheets` + thin `_read_xlsx` wrapper | codebook.py:141-233 | ✅ coherent — wrapper preserves `generate()` single-sheet compat |
| Sheet-expanded collision with dual `__`/`_` guard | codebook.py:464-615 | ✅ coherent — `__+→_` mirrors `normalize_parquet_remote`, catches `a__ventas` vs `a_ventas` |
| Tool-wide `[tool.sofer] card_collapse_threshold=15` | config.py:88, pyproject.toml, docs | ✅ coherent — tool-wide only, not `[meta]`, `int>=0` with bool guard |
| Per-table `<details>` gated `len(group)>thr OR len(groups)>1` | repo_compliance.py:1250-1258 | ✅ coherent — satisfies constraint *cada tabla por separado* (each table own details, not mega-wrapper) |
| Blank line after `</summary>` for HF | repo_compliance.py:1298-1301 | ✅ coherent — required for HF/GFM rendering |
| Group by `origin` stem fragment with common-prefix suffix stripping | repo_compliance.py:911-973 | ✅ coherent — `data_got_all_aristas` → `aristas`, dedup `_{n}` for label collisions |
| `prepare` delegates to `codebook.generate_all` (no new XLSX logic) | prepare.py:885 | ✅ coherent — provenance stays in `codebook.py`/`_converters.py` |

No design deviation detected. Estimated impl ~177 + tests ~140 = ~317 lines matches actual diff; well under 2000 budget, no chained PR needed.

## 5. Issues

### CRITICAL
None — all required spec scenarios have passing covering tests, quality gates green, no unchecked tasks.

### WARNING
1. **Dedup test naming nuance** — CB-R09.03 spec cites `Ventas`/`VENTAS` → `__ventas`/`__ventas_2`, but test uses `Ventas`/`Ventas!` (both sanitize to `ventas`). Semantic is identical (sanitize collision) and validates `seen` dedup, but an explicit `Ventas`/`VENTAS` case would mirror the spec verbatim. *Remediation:* add explicit test with `Ventas`/`VENTAS` (requires using raw `wb.create_sheet` to bypass openpyxl title uniqueness) or document that `Ventas!` is the spec-equivalent closed-form.
2. **Third duplicate not explicitly asserted** — CB-R09.03 says third duplicate → `__ventas_3.md`; existing `seen` counter logic supports it (`count+1` with `seen[sanitized]` tracking), but no test asserts the `_3` suffix. *Remediation:* add one test with 3 colliding sanitized sheets.

Both warnings are non-blocking; collapse invariant and sanitization parity are already proven at runtime.

### SUGGESTION
- Add regression test that `generate()` (single-file API) on a 2-sheet XLSX still returns the first sheet's codebook only (backward compat single-sheet path via `_read_xlsx` wrapper) — currently only `generate_all` multisheet is asserted.

## 6. Docs & Cross-Cutting Checks

| Check | Status | Detail |
|-------|--------|--------|
| No hardcoded literals | ✅ PASS | `CARD_COLLAPSE_THRESHOLD` via `config`; only literal `15` in `_DEFAULTS` + `pyproject.toml` (expected); `repo_compliance.py` has zero `15` literals for gate |
| No duplicated `sanitize_sheet_name` logic | ✅ PASS | Single import `from ._converters import sanitize_sheet_name` in `codebook.py:23`; `prepare.py` has none |
| Per-table collapse invariant (no mega-wrapper) | ✅ PASS | Loop emits per-group `<details>`; test `count==2` proves not 1 mega wrapper |
| README/ES sync | ✅ PASS | Both document multisheet `codebooks/<rel>/<stem>__<sanitized>.md` + per-table `<details>` with HF blank line + *cada tabla por separado* + `card_collapse_threshold` default 15 |
| `docs/configuration.md` threshold | ✅ PASS | Row `card_collapse_threshold | 15 | … Tool-wide [tool.sofer] only` line 107 |
| `sanitize_sheet_name` deduplication | ✅ PASS | `seen: dict[str,int]` in `codebook.py:160` + `165-170` matches `_converters._convert_xlsx_to_parquet` pattern |

## 7. Verdict

**PASS — ready for archive.**

All 4 deltas (CB-R09, RC-R21, TC-12, PRP-10) are implemented as spec'd, with runtime test evidence for every required scenario (8 codebook multisheet + 6 card collapsible all green), quality gates passing, no hardcoded literals, no duplicated sanitize logic, per-table collapse invariant enforced, docs synced, and prepare inheritance correct and non-invasive.

Warnings are minor coverage gaps that do not affect correctness; no CRITICAL defects block archival.

---
*Evidence commands were re-executed during verification; outputs above are live. File:line citations reference the post-apply working tree.*
