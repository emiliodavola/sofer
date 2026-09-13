# Exploration: fix-xlsx-staged-parquet-warning

**Status**: complete
**Change**: `fix-xlsx-staged-parquet-warning` (issue #150)
**Branch**: `fix/150-xlsx-staged-warning` (fresh from `dev` @ merge 4a9e0d4)
**Phase**: explore (read-only) — no files edited, no design decisions made

---

## 1. Root-cause confirmation (exact code regions)

### 1.1 `_build_schema_report_impl` — shared body of `build_schema_report` / `build_schema_report_with_rows`

- Function spans `src/sofer/repo_compliance.py:436-841` (docstring contract: row_counts keyed by verbatim `entry.remote`, `repo_compliance.py:453-459`).
- Per-entry pre-filter: `src/sofer/repo_compliance.py:485-489` — `suffix = PurePosixPath(entry.remote.replace("\\", "/")).suffix.lower()`; `if entry.recursive or suffix not in CONVERTIBLE_SUFFIXES: continue`. Recursive/dir entries never reach the staging lookup.
- Staging gate (only entries with `staging_dir` AND `convert_to_parquet` are looked up): `src/sofer/repo_compliance.py:502` — `if staging_dir is not None and bool(entry.convert_to_parquet):`.
- Staged key derivation — `src/sofer/repo_compliance.py:504`:
  `parquet_key = normalize_parquet_remote(parquet_remote_for(entry.remote))`
  - `parquet_remote_for` (`src/sofer/_mirror.py:55-72`): POSIX-normalize + `with_suffix(".parquet")`, case preserved.
  - `normalize_parquet_remote` (`src/sofer/_converters.py:37-76`): lowercase, NFKD→ASCII, spaces→`_`, `[^a-z0-9_./-]`→`_`, and **collapses runs `__+`→`_`** (`_converters.py:70`: `s = re.sub(r"__+", "_", s)`).
- **XLSX branch (the bug)**: `repo_compliance.py:506-534`
  - `repo_compliance.py:508-510`: derive `base_parent`, `base_stem`, `search_dir` from `parquet_key`.
  - `repo_compliance.py:513`: `sheet_paths = sorted(search_dir.glob(f"{base_stem}__*.parquet"))` — **double-underscore glob** (`stem__*.parquet`).
  - `repo_compliance.py:514-516`: checks the single base file `single = staging_dir / PurePosixPath(parquet_key)` (i.e. `stem.parquet`).
  - `repo_compliance.py:518-522`: if `sheet_paths` non-empty → `use_parquet = True`, placeholder `parquet_path = sheet_paths[0]`.
  - `repo_compliance.py:525-534`: elif — **the mis-firing warning**: `f"  [!] Staged Parquet '{parquet_key}' not found in staging directory; falling back to CSV inference."`, deduplicated by `_warned_missing` (`:527-528`).
- **Non-XLSX branch (must KEEP warning)**: `repo_compliance.py:536-547`
  - `repo_compliance.py:537`: `candidate = staging_dir / PurePosixPath(parquet_key)`; `:538-540` `exists()` → parquet path; `:541-546` elif → identical warning string (dedup same `_warned_missing` set).
- **Second duplicate XLSX sheet collection** (dead-duplicate of the branch above): `repo_compliance.py:548-561`, glob again at `repo_compliance.py:555` (`xlsx_sheet_paths = sorted(search_dir.glob(f"{base_stem}__*.parquet"))`), single-file append at `:556`. A fix must touch BOTH glob sites (`:513` and `:555`) or extract a helper (AGENTS.md rule 4 — no duplicated logic).
- Single-file parquet read guard: `repo_compliance.py:562-563` (`use_parquet and parquet_path is not None and not is_xlsx`); unreadable-parquet warning `:570-574` (`"exists but could not be read ({failure_class}); falling back to CSV inference."`).
- **XLSX per-sheet column loop**: `repo_compliance.py:577-638` — triggered by `if use_parquet and is_xlsx and xlsx_sheet_paths and staging_dir is not None:` (`:577`); per-sheet origin `sheet_origin = sheet_path.relative_to(staging_dir).as_posix()` (derived `:579-580`); per-sheet unreadable warn `:587-591`; **row-counts key**: `repo_compliance.py:594` — `row_counts.setdefault(entry.remote + f"::{sheet_origin}", pf_s.metadata.num_rows)`; ends with `continue` (`:637`) so a multi-sheet entry never reaches the single-file or source-fallback paths when parquets are found.
- Single-file parquet row-count key: `repo_compliance.py:646` — `row_counts.setdefault(entry.remote, pf.metadata.num_rows)`.
- **Source fallback (incl. XLSX first-sheet-only re-read)**: `repo_compliance.py:694-756`; xlsx branch `:702-730` with `wb_f = openpyxl.load_workbook(local, read_only=True, data_only=True)` (`:703`) and **`ws_f = wb_f[wb_f.sheetnames[0]]` — sheet index 0 only** (`:704`); fallback row-counts key `repo_compliance.py:758` — `row_counts.setdefault(entry.remote, len(rows))` (no `::` suffix).

**Mechanism (confirmed)**: for multi-sheet XLSX, prepare stages per-sheet parquets named with a **single** underscore (`data_got_all_aristas.parquet`, `data_got_all_nodos.parquet` — see §2). `repo_compliance` looks for `stem__*.parquet` (double) and `stem.parquet` (base) — neither matches the single-underscore per-sheet files → `:525-534` warns → falls through to the source fallback which silently reads **only the first sheet** (`:704`). The warning is not just noise: the state it indicates loses all non-first-sheet columns and row counts from the schema/Dataset Card.

### 1.2 The warning strings (all four sites)

| Line | Text |
|------|------|
| `repo_compliance.py:532-533` | `[!] Staged Parquet '{parquet_key}' not found in staging directory; falling back to CSV inference.` (XLSX missing branch) |
| `repo_compliance.py:544-545` | identical (non-XLSX missing branch — MUST keep) |
| `repo_compliance.py:572-573` | `[!] Staged Parquet '{parquet_key}' exists but could not be read ({failure_class}); falling back to CSV inference.` |
| `repo_compliance.py:589-590` | same "could not be read" variant with `{sheet_origin}` |

**Wording inaccuracy (confirmed)**: the tail "falling back to CSV inference" is wrong for `.xlsx` (fallback re-opens the workbook, `:702-730`) and equally wrong for `.jsonl` (`:732-746` reads JSON lines). The `::`-keyed `sheet_origin` and `entry.remote` variants mean the "not found" message fired for multi-sheet XLSX names the **base** key (`data_got_all.parquet`) that is *never produced* — misleading by construction.

**Does a reword break tests?** No. No test asserts the "CSV inference" tail. The only string assertions are:
- `tests/test_repo_compliance.py:2135` filters `"[!]" in ln and "Staged Parquet" in ln` and `:2137-2138` asserts count + key substring (`data/a/train.parquet`).
- `tests/test_repo_compliance.py:2165-2166` filters `"Staged Parquet" in ln`, asserts `"shared.parquet" in warnings[0]`.
A reword that preserves `[!]`, the `Staged Parquet '{key}'` prefix, and the "falling back to …" shape is fully test-compatible. README/README_ES do not document the string (grep of `README.md` for `Staged Parquet`/`CSV inference`/`falling back` → no hits).

---

## 2. `prepare.py` staging/naming — how `normalize_parquet_remote` is applied

- Conversion loop: `src/sofer/prepare.py:712-782` (comment at `:722-725`: "XLSX multi-sheet expands to N entries").
- **XLSX normalized remote built from the converter's `stem__sheet` key, then collapsed**: `src/sofer/prepare.py:771-779`:
  ```python
  # XLSX: stem_key is already stem__sheet or stem
  parquet_remote = parquet_remote_for(entry.remote)
  base_remote = PurePosixPath(parquet_remote)
  normalized_remote = normalize_parquet_remote(
      str(base_remote.parent / f"{stem_key}.parquet")
      if str(base_remote.parent) != "."
      else f"{stem_key}.parquet"
  )
  ```
  Because `normalize_parquet_remote` collapses `__+`→`_` (`_converters.py:70`), **the key stored in `converted[normalized_remote]` and later staged on disk is `stem_sheet.parquet` (single underscore)** — e.g. `data_got_all_aristas.parquet`.
- Staging copy: `src/sofer/prepare.py:793-795` → `copy_to_mirror(parquet_path, output_dir, normalized_remote)`; `copy_to_mirror` writes at `dest_root / remote` exactly (`src/sofer/_mirror.py:294-305`). So the final artifact name == the collapsed normalized remote. **Confirmed: base/remote `stem.parquet` is NEVER produced for multi-sheet XLSX** — `converted` contains only `stem_sheet.parquet` keys (plus, for single-sheet XLSX, exactly `stem.parquet`).
- Source of `stem__sheet` keys — `_convert_xlsx_to_parquet` (`src/sofer/_converters.py:367-485`):
  - Docstring `:372-377`: "Single sheet → `stem.parquet`; N sheets → `stem__sanitised.parquet` with dedup `_{n}`."
  - `is_single = len(sheet_names) == 1` (`:393`); single → `key_stem = local.stem` (`:466-467`); multi → `stem = f"{local.stem}__{sanitized}"` (`:469-470`); dedup `._{n}` via `seen` (`:398-406`); `sanitize_sheet_name` (`_converters.py:79-97`) for the sheet fragment.
- Other `normalize_parquet_remote` consumers in prepare (all three already carry the single-underscore fallback — precedents):
  - `_assert_cross_file_schema` match set: `src/sofer/prepare.py:361-380` — includes `k.startswith(norm_stem + "_") and k != norm_key` (`:375-376`).
  - `_check_local_overwrite` (PRP-07): `src/sofer/prepare.py:594-631` — primary `stem__*.parquet` glob then fallback `alt = sorted(search_dir.glob(f"{stem}_*.parquet"))` filtered `p.stem != stem` (`:620-624`), comment "Fallback for single-underscore normalized layout (mirrors _mirror.py PUB-10)".
  - prepare step-7 "is_converted" check: `src/sofer/prepare.py:862-869` — `(k.startswith(norm_stem + "_") and k != norm_key)` (`:865-866`).
- Only schema-consumer: `build_schema_report_with_rows(cfg, ..., staging_dir=output_dir)` at `src/sofer/prepare.py:803`; `repo_compliance.py` definitions at `:844` / `:877`, both delegating to `_build_schema_report_impl` (`:873`, `:903`). No other caller passes `staging_dir`.

---

## 3. `_mirror.py` `expanded_planned_remotes` — the established single-underscore precedent

Quoted from `src/sofer/_mirror.py:231-253` (function def at `:225`; docstring `:227-231`):

```python
            if eligible and suffix == ".xlsx":
                placeholder = normalize_parquet_remote(parquet_remote_for(entry.remote))
                parent = PurePosixPath(placeholder).parent
                stem = PurePosixPath(placeholder).stem
                search_dir = Path(staging_dir) / parent if str(parent) != "." else Path(staging_dir)
                candidates: list[Path] = []
                if search_dir.is_dir():
                    # Primary: double-underscore sheet files (spec)
                    candidates = sorted(search_dir.glob(f"{stem}__*.parquet"))
                    candidates = [c for c in candidates if c.is_file()]
                    # Fallback for current single-underscore staging (backward compat)
                    # when prepare stored sheets as report_ventas.parquet (collapsed).
                    if not candidates:
                        alt = sorted(search_dir.glob(f"{stem}_*.parquet"))
                        # Filter to keep only those that look like sheet files
                        # (exclude the placeholder itself).  For single-underscore
                        # layout, sheet files are report_ventas.parquet vs
                        # placeholder report.parquet — they differ by suffix.
                        alt = [c for c in alt if c.is_file() and c.stem != stem]
                        if alt:
                            candidates = alt
                if candidates:
                    for cand in candidates:
                        rel = cand.relative_to(Path(staging_dir)).as_posix()
                        expanded.append(rel)
                    continue
                # No sheets found — single-sheet fallback
                expanded.append(placeholder)
                continue
```

Key detail for the fix: the single-underscore fallback **excludes the bare placeholder** (`c.stem != stem`, `_mirror.py:247`) so a single-sheet `stem.parquet` is not treated as a sheet file. The same exclusion exists in prepare (`k != norm_key`, `prepare.py:375-376, 623-624, 866-868`). `repo_compliance` appends the single file explicitly (`:516`, `:556`) before filtering, so its fallback must do the same exclusion to avoid double-scanning the single-sheet artifact.

Also `parquet_remote_for` is the single shared key-derivation contract (`_mirror.py:55-72`, "shared by every producer (prepare staging) and consumer (publish, schema-report lookup)").

---

## 4. Test coverage of this area

**`tests/test_repo_compliance.py` (3166 lines)** — module header imports `build_schema_report`, `build_schema_report_with_rows` (`:18-21`).

- **`TestStagedParquetRemoteRelativeLookup`** (`:2039-2209`) — RC-R13/R14/R05 — is the natural home for the regression tests. Helpers:
  - `_stage_parquet(stage, remote_key, table)` (`:2044-2051`): writes a pyarrow table at its remote-relative key in a staging dir.
  - `TestBuildSchemaReportParquet._write_parquet()` (`:536-542`).
- Existing warn-path tests (must keep passing):
  - `test_missing_parquet_warns_once_and_falls_back_to_csv` (`:2120-2149`): two CSV entries, one staged parquet → exactly 2 `[!] Staged Parquet` warnings naming normalized keys, CSV fallback columns + row counts `{"data/A/train.csv": 3, ...}`.
  - `test_missing_parquet_warns_once_per_unique_key` (`:2151-2167`): two entries sharing `shared.csv` → exactly ONE warning naming `shared.parquet`.
  - `test_present_parquets_stay_silent` (`:2169-2186`): all parquets present → no `[!]`.
  - Plus nested-origin `test_nested_parquet_origins_distinguish_same_stem` (`:2188-2209`).
- **Gap: NO build_schema_report test with an XLSX entry + staging exists.** Every `.xlsx` FileEntry in `test_repo_compliance.py` is in `TestExpandedCard` (`:3043-3110`, exercises `build_dataset_card` with `staging_dir`, double-underscore `report__ventas.parquet` stubs at `:3053-3054`). The XLSX branch of `_build_schema_report_impl` (`:506-534`) and the per-sheet loop (`:577-638`) are untested.
- **Fixture helpers for building multi-sheet XLSX quickly**: `_make_xlsx(path, sheets: dict[str, list[list[object]]])` (openpyxl, sheet→rows header-first) is duplicated module-locally in 5 test files — `tests/test_clean.py:32`, `tests/test_codebook.py:1128`, `tests/test_profile.py:511`, `tests/test_prepare.py:919`, `tests/test_render.py:470` — but **not** in `test_repo_compliance.py` (no shared conftest helper; it would be duplicated again, consistent with existing convention).
- **The exact issue dataset fixture already exists** in `tests/test_clean.py` `TestAllowedOutputRemotes.test_single_underscore_data_got_all_sheets_in_allowlist` (`:54-73`): `DATA_GOT_ALL.xlsx` with `aristas`/`nodos` sheets via `_make_xlsx`, staged parquets written directly as `data_got_all_aristas.parquet` / `data_got_all_nodos.parquet` (pyarrow), asserts both are allowed remotes. This proves prepare's on-disk single-underscore layout is the recognised reality (`allowed_output_remotes` delegates to `expanded_planned_remotes`, `_clean.py:58-68`).
- **Converter-level multi-sheet fixture**: `tests/test_converters.py:213-231` (`test_xlsx_multi_sheet`): `multi.xlsx` with `Ventas 2024!` + `Other` → keys `multi__ventas_2024`, `multi__other`.
- **`expanded_planned_remotes` tests**: `tests/test_mirror.py:309-322` (double-underscore expansion), `:326-332` (single-sheet `single.parquet`), `:336-346` (staging None / not-dir fallback), `:349-355` (recursive passthrough), `:390-396` (non-convertible passthrough), `:416-425` (nested path). No test directly exercises the single-underscore fallback glob of `expanded_planned_remotes` (only indirectly via `test_clean`); the fallback is untested at the mirror level.

**Where the regression tests should live**: inside `TestStagedParquetRemoteRelativeLookup` (`test_repo_compliance.py:2039`) or a sibling `TestBuildSchemaReportXlsxStaged`. Two mandatory cases:
1. **Multi-sheet XLSX + staged single-underscore sheet parquets → no `[!]` warning**, per-sheet columns with `origin` = per-sheet remote-relative parquet path, row_counts keyed `entry.remote::<sheet_parquet>`; ideally also with double-underscore staged files (spec layout) still working if the fix keeps the primary glob for compat.
2. **Genuine single-file miss still warns**: CSV (or XLSX with missing parquet) → exactly one `[!] Staged Parquet '{key}'` (already covered by `:2120` / `:2151`, keep them green).

Fixture pattern: either a local `_make_xlsx` copy (openpyxl; matches 5 existing duplicates) or direct `pq.write_table` at the expected collapsed names (fastest, `test_clean.py:56-73` style, no openpyxl needed) — but note the source `local` must resolve for the fallback path; if staged parquets are found, the source file need not be read (single-file branch reads only the staged parquet), matching `test_mirror`'s `.touch()`-stub style.

---

## 5. Message-wording decision inputs

- The phrase "falling back to CSV inference" is factually wrong for `.xlsx` (workbook re-read, `repo_compliance.py:702-730`, first sheet only) and `.jsonl` (`:732-746`).
- No test, README, or CI gate asserts the phrase (only `[!]` + `Staged Parquet` + key substrings — `test_repo_compliance.py:2135-2138, 2165-2166`). A reword is therefore **low-risk and test-compatible**; a behavior-only change would keep the inaccurate phrase firing for genuinely-missing multi-sheet parquets and for jsonl/tsv misses.
- If reworded, both "not found in staging" sites (`:532`, `:544`) and the two "could not be read" sites (`:572`, `:589`) share the tail; a wording change should be consistent across all four.
- README/README_ES sync not required (no documented string).

---

## 6. Risk / edge cases for the implementation phase

1. **Two glob sites, one fix**: `repo_compliance.py:513` (first XLSX branch) and `:555` (second `xlsx_sheet_paths` block) must both gain the single-underscore fallback; the first branch's result drives the warn decision (`:525-534`), the second drives the actual per-sheet read (`:577-638`). AGENTS.md rule 4 (no duplicated logic) favors extracting a shared helper (e.g. in `_mirror.py` next to `expanded_planned_remotes`, or module-local).
2. **Single-sheet XLSX must stay silent**: the `single = staging_dir / parquet_key` check (`:514-516`, `:556`) already covers single-sheet (`stem.parquet`); the added `stem_*.parquet` fallback MUST exclude `stem.parquet` (the `c.stem != stem` / `k != norm_key` exclusion pattern from `_mirror.py:247`, `prepare.py:375-376/623-624/866-868`) so the single-sheet artifact is not double-counted or double-warned.
3. **Keep the double-underscore glob as primary**: `_mirror.py:240` treats `stem__*.parquet` as the spec layout; `test_mirror.py:309-322` and `TestExpandedCard` (`test_repo_compliance.py:3053-3054`) stub double-underscore files. The fix should try double first, then single (mirroring `_mirror.py:240-248`), or the fallback glob must also match double-underscore names.
4. **Base-vs-sheet collisions (pre-existing)**: `data.xlsx` (sheet `extra`) and `data_extra.xlsx` both normalize to `data_extra.parquet` (`_converters.py:70` collapse). The single-underscore fallback widens what repo_compliance matches; it must be no more permissive than `expanded_planned_remotes`/`allowed_output_remotes`, which already live with this hazard (allowed_remotes is the ground truth for clean; `_clean.py:58-68`).
5. **Recursive entries** (`:487`), **entries without `staging_dir`**, and **`convert_to_parquet=False`** never enter the branch (`:489`, `:502`) — no warning, no change needed.
6. **Case-insensitivity**: `suffix.lower()` gates `is_xlsx` (`:485-486`), and `normalize_parquet_remote` lowercases keys on both the prepare side (`prepare.py:773-778`) and the lookup side (`repo_compliance.py:504`), so `.XLSX` remotes and mixed-case sheet names are consistent between producer and consumer.
7. **Row-counts key asymmetry**: parquet path keyed `entry.remote::<sheet_origin>` (`:594`); any fallback path keys plain `entry.remote` (`:646`, `:758`). The Dataset Card consumer only sums values (`repo_compliance.py:1124-1125`), so the key shape is internal — but tests asserting `row_counts` for multi-sheet must expect the `::` keys.
8. **Source fallback silently drops sheets ≥ 2** (`:704` reads `sheetnames[0]` only). A behavior-only fix (glob fallback) addresses the noisy-warning case; the genuinely-missing staged-parquet XLSX case still degrades to first-sheet-only. Worth a documented note in whatever spec delta is written.
9. **Warn-once semantics**: `_warned_missing` is keyed by `parquet_key` (`:528`, `:542`) — a multi-sheet XLSX and a same-stem CSV entry share the same key; with the fix, the XLSX entry no longer adds the key, preserving the existing warn-once contract tested at `:2151-2167`.
10. **Test-suite size**: `tests/` currently passes (1495+ baseline per latest verify report; 1342 passed/2 skipped per project.md, newer runs 1506 passed) — regression tests must be additive; AGENTS.md rule 6 requires every new spec scenario to have a test.

---

## Key Learnings

- **The bug is a producer/consumer naming mismatch, not a missing file**: prepare stores per-sheet parquets under **collapsed single-underscore** names (`stem_sheet.parquet`, `prepare.py:773-778` + `_converters.py:70`), while `_build_schema_report_impl` searches **double-underscore** (`stem__*.parquet`, `repo_compliance.py:513, 555`). The base `stem.parquet` is never produced for multi-sheet XLSX.
- **The repo already solved this exact mismatch twice**: `_mirror.expanded_planned_remotes` (`_mirror.py:240-248`) and prepare's `_check_local_overwrite` (`prepare.py:620-624`) both try `stem__*` first then fall back to `stem_*` while excluding the bare placeholder. The fix should replicate that established pattern (with `c.stem != stem`-style exclusion) rather than invent a new mechanism.
- **The warning hides a real degradation**: when it fires for multi-sheet XLSX, the schema falls back to re-reading only sheet[0] (`repo_compliance.py:704`), silently dropping other sheets' columns and per-sheet row counts — the noisy message is the visible tip of silent data loss in the card/schema.
- **Dual-modality layouts exist**: double-underscore is "the spec" (`_mirror.py:239`), single-underscore is "current staging (backward compat)" (`_mirror.py:242-243`); tests stub both (`test_mirror.py:314`, `test_clean.py:68-69`). Any fix must keep both working.
- **No test asserts the "CSV inference" tail** — reword is safe; but the phrase is also wrong for jsonl, so any wording change should cover all four warning sites consistently.
- **Warning-site duplication**: the two XLSX glob blocks and the four-string family are ripe for a shared helper; AGENTS.md rule 4 explicitly prohibits duplicated logic.
- **Test gap**: `repo_compliance` XLSX+staging paths are entirely untested (all `.xlsx` entries in `test_repo_compliance.py` hit `build_dataset_card`, not `build_schema_report*`). The `DATA_GOT_ALL` aristas/nodos fixture in `test_clean.py:54-73` is the canonical reproducer.