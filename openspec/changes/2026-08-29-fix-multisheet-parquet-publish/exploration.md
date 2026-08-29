# Exploration: fix-multisheet-parquet-publish — xlsx multisheet generates `__sheet` but publish misses it

## Current State

### How multisheet xlsx is detected and converted to `__sheet` parquets

* **Format registry is NOT involved.** `src/sofer/_formats.py` only defines `SUPPORTED_FORMATS` / `TEXT_SUFFIXES` — it has no sheet logic. All sheet handling lives in `src/sofer/_converters.py` (the universal dispatch introduced in `0cbea73 feat(parquet): universal csv/tsv/xlsx/jsonl -> normalized parquet`).

* **`sanitize_sheet_name(name)` (`_converters.py:76`)** — normalises a raw Excel sheet name to a stem fragment: `lower → NFKD→ASCII strip → spaces→_ → [^a-z0-9_-]→_ → collapse __+ → strip _`. Empty result falls back to `"sheet"`. Dedup `_{n}` is handled by the caller.

* **`_convert_xlsx_to_parquet(local, staging_dir)` (`_converters.py:367`)** — the single home of the suffix rule:
  - Opens via `openpyxl.load_workbook(read_only=True, data_only=True)`, iterates `wb.sheetnames`.
  - `is_single = len(sheet_names) == 1` determines the naming branch.
  - Per sheet: `sanitized = sanitize_sheet_name(sheet_name)` + dedup (`a_b`, `a_b_2`, …) via `seen` dict.
  - Builds an Arrow table per sheet (empty/header-only sheets → 0-row table, padding/truncating to header length, all-null columns cast to `string`).
  - **Suffix appended:** `stem = local.stem` when single → `stem.parquet`; otherwise `stem = f"{local.stem}__{sanitized}"` → `f"{stem}.parquet"` via `_write_parquet_table`. Returns `dict[stem_key → Path]` where keys are the stems (`single` or `multi__ventas_2024`).
  - `_write_parquet_table` uses `config.PARQUET_COMPRESSION` / `PARQUET_ROW_GROUP_SIZE` and warns above `PARQUET_SHARD_WARNING_MB`.

* **Single-sheet vs multisheet:** Branch on `is_single`. Single-sheet preserves the exact `stem.parquet` contract (no suffix, no breaking change). Multi-sheet expands to N files with `__{sanitized}`. Verified by `tests/test_converters.py:test_xlsx_single_sheet` (asserts `single in result`) and `test_xlsx_multi_sheet` (asserts `multi__ventas_2024` + `multi__other`, `len==2`) plus `test_dedup_via_converter`.

### How prepare builds the publish plan and where the name diverges

* **Prepare conversion loop (`prepare.py:712-768`)** — correctly handles expansion. For each `FileEntry` gated by `CONVERTIBLE_SUFFIXES + convert_to_parquet + not recursive + not .parquet`, it calls `convert_file_to_parquet(local, entry_tmp)`. For `suffix == ".xlsx"`, `stem_key` already contains `stem__sheet` or `stem`, so it builds the normalized remote via `normalize_parquet_remote(str(parent / f"{stem_key}.parquet"))` and keys `converted[normalized_remote] = (parquet_path, local, entry.remote)`. Then `copy_to_mirror(parquet_path, output_dir, normalized_remote)` stages into the mirror layout. This path is correct — `prepare` does expand to N remotes and does not miss sheets.

* **Staging & overwrite helpers already glob-aware:** `_check_local_overwrite` and `_assert_cross_file_schema` in `prepare.py` both glob `stem__*.parquet` for `.xlsx` entries, so the check/assertion layers do not miss sheets.

* **`_mirror.planned_remotes(cfg, keep_csv)` (`_mirror.py:127`) is the single source for the publish plan (PUB-09).** Its docstring explicitly admits the gap: *"XLSX with N sheets would ideally expand to N remotes — but sheet names are not known without opening the file, so we emit the single normalised stem remote here"*. For eligible convertible entries it emits `normalize_parquet_remote(parquet_remote_for(entry.remote))` — one entry per xlsx, e.g. `data/prov/train.parquet`. The comment proposes the mirror glob as the compensating mechanism.

* **`publish.py` consumes `planned_remotes` in 4 places — only one is compensated:**
  1. **`_repo_diff_summary(cfg, existing, keep_csv, codebook_remotes)` (publish.py:201)** — builds `planned = ["README.md","LICENSE"] + raw_planned` plus `*` for recursive entries. For xlsx it shows the single placeholder (`train.parquet`) as ADDED/OVERWRITTEN. The actual N sheet files are invisible in the diff. Dry-run also prints from this same single-entry list.
  2. **`_copy_package(cfg, source, dest, keep_csv, protected)` (publish.py:446)** — **this IS compensated**: for `suffix == ".xlsx"` + `is_converted`, it globs `search_dir.glob(f"{base_stem}__*.parquet")` plus the single file, then `copy_to_mirror(src, dest, rel)` per match. So the staged upload *does* include all sheets despite the single planned entry. This is the only place the multi-sheet contract is honoured.
  3. **`_check_overwrite_protection(existing, force, planned_files=planned)` (publish.py:731)** — receives the single-entry `planned` list. Protection therefore only guards `train.parquet`, not `train__ventas_2024.parquet`. Existing sheet files on the Hub are never protected; conversely if the placeholder is protected the copy branch (`if planned_remote.lower() in skip: pass`) would skip the entire xlsx (sheets included) — the opposite of the desired granularity.
  4. **`_print_split_mapping_validation(planned)` + `detect_splits(planned)` (publish.py:686,739)** — split detection/validation runs on the single placeholder, so multi-sheet datasets report wrong split counts.

* **Resulting user-visible failure:** `prepare` correctly produces `mi_dataset__Sheet1.parquet + mi_dataset__Sheet2.parquet` in the mirror, but `publish`'s human-facing plan (diff, dry-run, split report, overwrite guard) describes `mi_dataset.parquet` — which does not exist for multi-sheet workbooks. The copy *would* still upload the sheets thanks to the glob in `_copy_package`, but the discrepancy causes the reported bug: publish appears to miss `__sheet` files (diff shows wrong names, protection bypass, split metadata wrong). In the pre-glob code the copy itself also missed sheets (the original issue).

### Repo-compliance / schema report

`repo_compliance._build_schema_report_impl` now handles multi-sheet: when staging_dir is set and entry is xlsx + convert_to_parquet, it globs `base_stem__*.parquet` plus single, then iterates each `sheet_path` via `_read_parquet_sample`, appending per-sheet columns with `origin = sheet_path.relative_to(staging_dir).as_posix()` and `row_counts[entry.remote + "::" + sheet_origin]`. Fallback reads only the first sheet via openpyxl if no staged parquets exist. `build_dataset_card` uses `planned_remotes(cfg, keep_csv)` for the file list in "Dataset Structure" — so the card also lists only the single placeholder, not the N sheets (card/configs data_files would point at a non-existent remote).

### Existing tests for xlsx/parquet conversion

* `tests/test_converters.py` — covers `normalize_parquet_remote`, `sanitize_sheet_name`, dup dedup, `_write_parquet_table` (null→string, compression, parent dirs), and `convert_file_to_parquet` dispatcher: `test_xlsx_single_sheet`, `test_xlsx_multi_sheet`, `test_jsonl`, `test_parquet_passthrough`, `test_unknown_suffix`. The multi-sheet test asserts the two `__sheet` keys and file existence but does not test publish.
* `tests/test_mirror.py` — tests `planned_remotes` (csv→parquet, keep_csv, recursive, non-csv passthrough, mixed order, nested dir lowercasing) but **no xlsx multi-sheet case**. `parquet_remote_for` and `copy_to_mirror` / `_validate_case_fold_collisions` have coverage; `_validate_case_fold_collisions` is universal across `CONVERTIBLE_SUFFIXES`.
* `tests/test_prepare.py` — e2e `prepare(cfg,out)` for mirror layout (same-stem distinct dirs, backslash remote), codebooks, checks, force, verify, recursive staging. No xlsx multi-sheet e2e.
* `tests/test_publish.py` — extensive PUB-01..08 coverage (quality gate, local target, dry-run, auto-prepare, hf staging, codebooks, overwrite protection, batch staging, readme override) but **no xlsx multi-sheet publish test**.
* `tests/test_parquet_conversion.py` / `test_repo_compliance.py` / `test_codebook.py` — touch xlsx reading (_read_xlsx) but not the publish path.

## Affected Areas

- `src/sofer/_converters.py` — source of truth for `__sheet` naming; no change needed unless dedup/sanitize contract changes, but any publish fix must not duplicate its logic.
- `src/sofer/_mirror.py` — `planned_remotes` is the declared publish plan; currently single-entry for xlsx. Any fix that enumerates sheets must either expand here (requires opening workbook) or document single-placeholder + glob as the contract and fix consumers.
- `src/sofer/publish.py` — principal bug surface: `_repo_diff_summary`, `_check_overwrite_protection`, `_copy_package` (already patched for copy), `_print_split_mapping_validation`/`detect_splits`, dry-run path, `protected_out` side channel. `keep_csv` path also assumes single planned entry.
- `src/sofer/prepare.py` — already correct for staging; only needs attention for `_check_local_overwrite` consistency and for any shared helper extracted.
- `src/sofer/repo_compliance.py` — schema report already expands; `build_dataset_card` (`planned_remotes` call at line ~1156) and `configs.data_files` need to emit N remotes or the card will reference a phantom file.
- `src/sofer/cli.py` / `src/sofer/splits.py` / `src/sofer/verification.py` — indirect: split detection and verification consume the remote list downstream.
- `tests/test_mirror.py`, `tests/test_publish.py`, `tests/test_prepare.py`, `tests/test_converters.py` — need new multi-sheet publish scenarios.

## Approaches

1. **A — Keep `planned_remotes` single, make `publish` glob-aware everywhere (current `_copy_package` pattern extended).**
   - Pros: No need to open xlsx at plan time; `planned_remotes` stays pure and fast; minimal change to the mirrored contract; `_copy_package` already implements this for staging.
   - Cons: Every consumer of `planned_remotes` must remember to glob — diff, overwrite protection, split validation, card generation each reimplement the expansion, easy to regress; planned list and actual staged set diverge (hard to test, surprising for callers).
   - Effort: Medium (4-5 call sites to patch + tests).

2. **B — Expand `planned_remotes` to N sheet remotes by opening the workbook at plan time.**
   - Pros: Single source expands once; all downstream consumers (diff, protection, splits, card) automatically correct; `planned_remotes == actual staged set`; easiest to reason about and test.
   - Cons: `planned_remotes` becomes I/O (needs `_base_dir`, must handle missing/corrupt xlsx, dedup, accent normalisation, empty workbook); blurs the "pure remote derivation" contract; caching/staleness concerns if workbook changed after `prepare`.
   - Effort: Medium (requires new `planned_remotes` signature `planned_remotes(cfg, keep_csv, base_dir?)` or a separate `expanded_planned_remotes` helper, plus fallback to single placeholder when file unavailable).

3. **C — Hybrid: `planned_remotes` stays single, but `publish`/`card` expand by scanning the mirror layout (staging dir) instead of reopening xlsx.**
   - Pros: No workbook I/O, ground truth is what `prepare` actually wrote; aligns diff/card with reality; handles dedup/normalisation exactly as staged.
   - Cons: Requires the mirror to exist (dry-run before prepare would still show single placeholder); ties planning to filesystem state; local-target without `--output` path needs care.
   - Effort: Medium (new `expand_planned_remotes_from_mirror(cfg, source_dir)` helper used by `_repo_diff_summary` and `_copy_package`).

4. **D — Introduce a manifest: `prepare` writes `.sofer_manifest.json` listing every staged parquet (including `__sheet` expansions); `publish` reads it.**
   - Pros: Makes the contract explicit and auditable; decouples plan from both workbook I/O and mirror scan; easy to version.
   - Cons: New artifact, migration, staleness if manifest not present (old builds); adds a file to the package that must be excluded from upload; most invasive.
   - Effort: High.

## Recommendation

**Short-term fix: Approach A (extend the existing glob) + Approach C helper extracted.**

The codebase already committed to the glob in `_copy_package` — the cheapest consistent fix is to extract a shared helper `expand_xlsx_remotes(planned, source_dir)` (or `mirror_expand_for_xlsx(entry, planned_remote, source)`) and apply it in the three remaining publish consumers:

* `_repo_diff_summary` — expand before new/modified classification,
* `_check_overwrite_protection` caller in `publish()` — expand `planned` before guarding,
* `_print_split_mapping_validation` / `detect_splits` — expand before validation,
* `repo_compliance.build_dataset_card` — expand the `planned_remotes` call for "Dataset Structure" and for `configs.data_files` (or at least the former).

For `planned_remotes` itself, keep the single-placeholder return but document it as "logical remote" and add an `expanded_planned_remotes(cfg, keep_csv, staging_dir)` wrapper that returns the filesystem-grounded list when the mirror exists, falling back to the single placeholder otherwise. This preserves the pure fast path for dry-run-before-prepare while guaranteeing correctness post-prepare.

Longer term, if the team wants `planned_remotes == staged set` unconditionally, migrate to **B** (workbook-opening) behind a feature flag, reusing `sanitize_sheet_name`/`_convert_xlsx_to_parquet` dedup logic via a shared `sheet_remote_names(local_path, normalized_stem)` helper.

Key invariant to preserve: `is_single` → no suffix, so any expansion must check mirror existence first (single-sheet workbook produces no `__*` files) and not fabricate phantom `__sheet` entries.

## Risks

- **Silent omission if glob is forgotten at any new call site** — any future code that calls `planned_remotes` directly will still see the single placeholder. Mitigate with a wrapper and a lint comment, or by renaming `planned_remotes` to `logical_planned_remotes`.
- **Overwrite protection granularity** — current protection guards the placeholder, not sheets. Expanding before the guard is required; otherwise existing sheets on the Hub are silently overwritten or all sheets are skipped together.
- **Card/configs mismatch** — `configs.data_files` in the Dataset Card currently points at a non-existent remote for multi-sheet xlsx; expanding only the card body but not `configs` leaves HF `load_dataset` broken for those sheets.
- **Dry-run before first prepare** — mirror scan (approach C) has no files to expand from, so dry-run must fall back to the single placeholder and warn: "N unknown until prepare — showing stem placeholder".
- **Dedup and normalisation drift** — reimplementing `sanitize_sheet_name` + dedup + `normalize_parquet_remote` in the expansion helper must reuse the same functions, not copy them, or accent/collision handling will diverge.
- **Recursive/xlsx interaction** — `recursive=true` entries are not convertible; the expansion must not treat them as xlsx.
- **Test gap** — no current test covers multi-sheet publish; adding one requires `openpyxl` workbook fixture + temp mirror + mocked `HfApi`.

## Ready for Proposal

Yes — the defect is isolated to the plan-vs-mirror expansion boundary. The orchestrator can propose `fix-multisheet-parquet-publish` with scope: expand `publish`'s diff/protection/split/card paths via a mirror-backed helper sharing `_converters.sanitize_sheet_name` + `_mirror.normalize`, keep single-sheet intact, add `test_publish` multi-sheet (2+ sheets) mock test + `test_mirror` xlsx expansion test. No CLI surface change; no new artifact required for the minimal fix (manifest is optional future).

