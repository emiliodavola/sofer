# Design: fix-xlsx-staged-parquet-warning (issue #150)

**Status**: complete (ready for tasks phase)
**Change**: `fix-xlsx-staged-parquet-warning`
**Branch**: `fix/150-xlsx-staged-warning` (fresh from `dev` @ merge 4a9e0d4)
**Phase**: design — after exploration + proposal + change-local spec delta. Strict-TDD off (`config.yaml strict_tdd: false`); tests follow specs, placement documented below.
**Windows note**: run any verification with `PYTHONIOENCODING=utf-8` (console stdout encodes warning strings).

---

## 1. Problem statement (one paragraph)

`sofer prepare` prints a misleading non-blocking `[!]` warning for multi-sheet XLSX —
`Staged Parquet 'data_got_all.parquet' not found in staging directory; falling back to CSV inference.` —
even though the real staged artifacts exist under **collapsed single-underscore** names
(`data_got_all_aristas.parquet`, `data_got_all_nodos.parquet`). The consumer
(`_build_schema_report_impl`, `src/sofer/repo_compliance.py`) searches only the spec-layout
double-underscore glob `stem__*.parquet` (L513, L555) plus the bare base `stem.parquet`
(L514-516, L556), and `normalize_parquet_remote` collapses `__+`→`_` on the producer side
(`src/sofer/_converters.py:70`, applied at `src/sofer/prepare.py:771-778`), so the base key is
**never produced** for multi-sheet XLSX. The warning is not merely noisy: when it fires, the
schema falls back to re-reading only `sheetnames[0]` (L704), silently dropping sheets ≥ 2
from the schema report and Dataset Card. The repo has already solved this exact
producer/consumer mismatch twice — `_mirror.expanded_planned_remotes` (`_mirror.py:238-248`)
and `prepare._check_local_overwrite` (`prepare.py:620-624`) both try `stem__*` then fall back
to `stem_*` excluding the bare placeholder. This change replicates that established pattern
inside `repo_compliance.py` and makes the four warning tails format-generic.

## 2. Design decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D1 | Fix shape | **Add single-underscore fallback glob** (dual-layout lookup), not skip-the-warning | The warning is the visible tip of silent first-sheet-only schema loss; the fallback restores the behavior RC-Universal §4.19 already specifies. Skipping the warning would hide the degradation entirely |
| D2 | Helper extraction | **One module-private `_staged_xlsx_sheet_parquets` in `repo_compliance.py`**, used by BOTH glob sites | AGENTS.md rule 4 (no duplicated logic): the two sites (L513 + L555) currently duplicate the `base_parent`/`base_stem`/`search_dir` derivation + glob + filter; both must see identical results so the `use_parquet` flag (first site) and the per-sheet loop (second site) always agree |
| D3 | Cross-module consolidation | **Out of scope** — `expanded_planned_remotes` / `_check_local_overwrite` stay untouched | Their logic is already correct + test-covered; unifying them widens the blast radius beyond #150. Tracked as follow-up (see §8) |
| D4 | Warning wording | **Reword all four tails** to `falling back to original-file inference.` via **two module-level template constants** | The old tail is factually wrong for `.xlsx` (workbook re-read, L702-730) and `.jsonl` (JSON-lines read, L732-746); leaving any site un-reworded keeps a known-false claim on genuine-miss paths. No test, README, or CI gate asserts the tail (verified in exploration §1.2) — only `[!]`, `Staged Parquet`, and key substrings are asserted (`test_repo_compliance.py:2135-2138, 2165-2166`) |
| D5 | Genuine multi-sheet miss | **Keep first-sheet-only source fallback (L704), document as unchanged** | Per-sheet source re-reads are a behavior/semantics change beyond #150; documented in RC-R22 so the degradation is explicit rather than silent |
| D6 | Row-counts keys | **Unchanged**: `entry.remote::<sheet_origin>` (per-sheet L594), `entry.remote` (single-file L646 / fallback L758) | Card consumer sums values only (`repo_compliance.py:1124-1125`); rekeying ripples into `build_dataset_card` for zero user-visible gain |
| D7 | Non-XLSX branch | **Logic untouched** — only the shared warning string substitution | Existing warn-path tests (L2120/L2151) exercise exactly this path and must stay green |

## 3. Detailed design

### 3.1 Shared helper `_staged_xlsx_sheet_parquets`

Module-private, placed immediately above `_build_schema_report_impl` (after `_read_parquet_sample`,
~L435). Uses only module-level imports already present (`Path`, `PurePosixPath`); no new imports.

```python
def _staged_xlsx_sheet_parquets(staging_dir: Path, parquet_key: str) -> list[Path]:
    """Return staged per-sheet Parquets for an XLSX entry, dual-layout aware.

    Primary (spec) layout: ``stem__*.parquet`` double-underscore sheet files.
    Fallback (current prepare staging, backward compat): ``stem_*.parquet``
    collapsed single-underscore names — ``normalize_parquet_remote`` collapses
    runs of ``__+`` to ``_`` (``_converters.py``), so ``prepare`` writes
    ``data_got_all_aristas.parquet``, never ``data_got_all__aristas.parquet``
    and never a bare base ``data_got_all.parquet`` for multi-sheet sources.

    The fallback EXCLUDES the bare base placeholder (``c.stem != base_stem``)
    so a single-sheet artifact ``stem.parquet`` is never mistaken for a sheet
    file. Mirrors the established precedent in
    ``_mirror.expanded_planned_remotes`` (PUB-10) and
    ``prepare._check_local_overwrite`` (PRP-07); base-vs-sheet collisions are
    therefore no more permissive than ``allowed_output_remotes``.

    Returns ``[]`` when the search directory is missing or nothing matches;
    callers then independently check the single-file ``stem.parquet`` case
    and, failing that, emit the missing-Parquet warning.
    """
    base_parent = PurePosixPath(parquet_key).parent
    base_stem = PurePosixPath(parquet_key).stem
    search_dir = staging_dir / base_parent if str(base_parent) != "." else staging_dir
    if not search_dir.is_dir():
        return []
    primary = sorted(search_dir.glob(f"{base_stem}__*.parquet"))
    primary = [p for p in primary if p.is_file()]
    if primary:
        return primary
    alt = sorted(search_dir.glob(f"{base_stem}_*.parquet"))
    return [p for p in alt if p.is_file() and p.stem != base_stem]
```

Contract notes:

- **Inputs**: `staging_dir` (mirror output directory, non-None — callers already gated on
  `staging_dir is not None and bool(entry.convert_to_parquet)` before calling), `parquet_key`
  (the **normalized** remote-relative `.parquet` key, lowercase — L504 contract).
- **Outputs**: sorted list of matching sheet paths, files only; `[]` on no match / missing dir.
  Never includes the bare base `stem.parquet` (the exclusion, belt-and-suspenders with the
  precedents: `.` ≠ `_` means the glob cannot match it anyway, but the guard future-proofs).
- **Dual-layout match**: primary `stem__*.parquet` wins when non-empty; only then is the
  `stem_*.parquet` fallback consulted — byte-for-byte the `_mirror.py:238-248` ordering, so
  spec-layout stubs (`test_mirror.py:309-322`, `TestExpandedCard` `test_repo_compliance.py:3053-3054`)
  keep resolving.
- **Why callers append `stem.parquet` themselves (not the helper)**: the single-file artifact is
  a *sheet-like* candidate, not a *sheet* — the helper contract returns sheet files only; the
  caller decides the single-file handling (append-if-file, then warn if the combined list is
  empty). Keeps the helper symmetric with `expanded_planned_remotes`, which also handles the
  single-sheet placeholder separately.

### 3.2 Shared warning template constants (two, not four)

Module-level constants placed next to the helper (before `_build_schema_report_impl`),
replacing the quadruplicated inline f-string literals (same dedup rationale as AGENTS.md rule 4):

```python
_WARN_STAGED_PARQUET_MISSING = (
    "  [!] Staged Parquet '{key}' not found in staging directory; "
    "falling back to original-file inference."
)
_WARN_STAGED_PARQUET_UNREADABLE = (
    "  [!] Staged Parquet '{key}' exists but could not be read "
    "({failure_class}); falling back to original-file inference."
)
```

- Both are `.format(key=..., failure_class=...)` style (the `{key}` slot receives either the
  normalized `parquet_key` or, at the per-sheet site, `sheet_origin`; `{failure_class}` is only
  substituted at the two unreadable sites).
- **Stable fragments preserved**: leading `"  [!] "` prefix (exactly two spaces, as today),
  `Staged Parquet '{key}'`, `not found in staging directory;` /
  `exists but could not be read ({failure_class});`, and the `falling back to … inference.`
  shape. Only the tail object changes: `original-file` (generic) replaces the format-specific
  `CSV`.
- Test-compatibility confirmed (exploration §1.2): `test_repo_compliance.py:2135-2138`
  filters `"[!]" in ln and "Staged Parquet" in ln` and asserts key substrings; `:2165-2166`
  filters `"Staged Parquet" in ln` and asserts `shared.parquet`; neither touches the tail.
  README/README_ES carry no such string → no AGENTS.md rule 13 sync.

### 3.3 Edits at the four sites (all in `_build_schema_report_impl`)

| Site | Current (L) | After edit |
|------|-------------|------------|
| First XLSX branch glob | L508-516: derive `base_parent/base_stem/search_dir`, `if search_dir.is_dir():` glob `stem__*`, append `single`, filter | `sheet_paths = _staged_xlsx_sheet_parquets(staging_dir, parquet_key)`; then unconditional `single = staging_dir / PurePosixPath(parquet_key); if single.is_file(): sheet_paths.append(single)` |
| First XLSX warn | L525-534: `elif parquet_key not in _warned_missing:` → `print(f"  [!] … CSV inference.")` | same shape, `print(_WARN_STAGED_PARQUET_MISSING.format(key=parquet_key))` |
| Non-XLSX branch | L536-547: logic untouched | only the print swaps to `_WARN_STAGED_PARQUET_MISSING.format(key=parquet_key)` |
| Second XLSX collection | L548-561: duplicate derivation + glob at L555 + single append + filter | `xlsx_sheet_paths = _staged_xlsx_sheet_parquets(staging_dir, parquet_key)`; `single` append as above; dead comments removed |
| Single-file unreadable | L570-574 | `print(_WARN_STAGED_PARQUET_UNREADABLE.format(key=parquet_key, failure_class=failure_class))` |
| Per-sheet unreadable | L587-591 | `print(_WARN_STAGED_PARQUET_UNREADABLE.format(key=sheet_origin, failure_class=failure_class))` |

Behavior-neutral refactors to call out (deterministic equivalence, verified against the current
control flow):

- The `if search_dir.is_dir():` wrapper in both XLSX blocks disappears (moves into the helper).
  The previously-gated `single` append becomes unconditional: `single.is_file()` is `False`
  whenever the parent dir is missing, so no observable change.
- The first site's `sheet_paths: list[Path] = []` initialization and the post-glob
  `[p for p in sheet_paths if p.is_file()]` filter are subsumed by the helper (helper returns
  files only); the single-append result needs no re-filter (guarded by `is_file()`).
- The per-sheet loop guard `if use_parquet and is_xlsx and xlsx_sheet_paths and staging_dir is not None:`
  (L577) is untouched; both sites now derive from the identical helper call, so the
  `use_parquet` flag and the loop's file list can never disagree.

Untouched by the edit (behavior preservation, per the spec delta):
- `_warned_missing` / `_warned_unreadable` warn-once-per-key semantics (keyed by `parquet_key`
  resp. `sheet_origin`) — with the fix, a multi-sheet XLSX with found sheets simply never adds
  the base key, preserving the warn-once contract tested at L2151-2167.
- Per-sheet loop internals (L579-637): `sheet_origin` derivation, per-sheet schema columns,
  `row_counts.setdefault(entry.remote + f"::{sheet_origin}", …)` at L594, `continue` at L637.
- Single-file parquet read (L646), source fallback xlsx/jsonl/csv (`ws_f = wb_f[wb_f.sheetnames[0]]`
  at L704 — first-sheet-only, unchanged and documented).
- `_read_parquet_sample` / `_classify_parquet_read_failure` (RC-R17) — only the printed string
  changes.

## 4. Data flow (post-fix)

```
entry (cfg.files)
  ├─ recursive or suffix ∉ CONVERTIBLE_SUFFIXES            → skip (L487-489)
  ├─ include_in_schema false                               → skip
  ├─ staging_dir None or convert_to_parquet false          → skip staging lookup (L502)
  └─ parquet_key = normalize_parquet_remote(parquet_remote_for(entry.remote))   (L504)
      ├─ is_xlsx?
      │    ├─ sheet_paths = _staged_xlsx_sheet_parquets(staging_dir, parquet_key)   ← NEW
      │    │     primary stem__*.parquet → else stem_*.parquet (excl. stem.parquet) → []
      │    ├─ + single stem.parquet if file
      │    ├─ if sheet_paths:  use_parquet=True; parquet_path=sheet_paths[0]         (L518-522)
      │    ├─ elif key ∉ _warned_missing: warn once (NEW wording)                    (L525-534)
      │    └─ xlsx_sheet_paths = same helper call (+ single append)                  (NEW)
      │         └─ if use_parquet and xlsx_sheet_paths: per-sheet loop → origin=rel key,
      │            row_counts[entry.remote::sheet_origin] → continue                 (L577-637)
      └─ non-xlsx:
           ├─ candidate = staging_dir/parquet_key exists → single-file read (L646 key) (L537-540)
           └─ else warn once (NEW wording) → source fallback                          (L541-546)
```

## 5. Files changed

| File | Change | Est. delta |
|------|--------|------------|
| `src/sofer/repo_compliance.py` | +`_staged_xlsx_sheet_parquets` (before `_build_schema_report_impl`); +2 module constants; both XLSX glob sites delegate; four prints swap to constants | ~ +45 / −50 |
| `tests/test_repo_compliance.py` | Promote `_stage_parquet` to a module-level helper (existing static method delegates); add module-local `_make_xlsx(path, sheets)` (5th+1 duplicate, matching the existing convention); add `TestBuildSchemaReportXlsxStaged` (4 tests) after `TestStagedParquetRemoteRelativeLookup` (~L2210) | ~ +170 |
| `openspec/changes/fix-xlsx-staged-parquet-warning/specs/repo-compliance/spec.md` | Already written in proposal phase (RC-R22 + §4.19 amendment + RC-R14 prose tail) | — |
| `openspec/changes/fix-xlsx-staged-parquet-warning/tasks.md` | Next phase | — |
| `README.md`, `README_ES.md` | Unchanged (no documented string; grep-verified) | — |

Review-budget check: ~+215/−50 net ≈ 265 changed lines, well inside the 800-line budget; a
single incremental PR.

## 6. Test design

### 6.1 Shared helpers changes (rule 4 within tests)

- Promote the existing `TestStagedParquetRemoteRelativeLookup._stage_parquet` static method
  body to a module-level `_stage_parquet(stage, remote_key, table)` (pyarrow-direct
  `pq.write_table` at remote-relative key, `test_clean.py:56-73` style). The old class keeps its
  static method as a one-line delegation (`return _stage_parquet(...)` via the module global),
  so all existing call sites (`self._stage_parquet`) keep working unmodified. The new class
  calls the module function directly. Zero duplicated logic.
- Add a module-local `_make_xlsx(path, sheets)` copy in `tests/test_repo_compliance.py` —
  identical to the existing 5-file convention (`test_clean.py:32`, `test_codebook.py:1128`,
  `test_profile.py:511`, `test_prepare.py:919`, `test_render.py:470`). A real readable source
  file is required only by test #4 (fallback re-reads it); tests #1-#3 may still build it so the
  fixture mirrors the DATA_GOT_ALL reproducer, but do not depend on its readability (staged
  parquets short-circuit the source read).

### 6.2 `TestBuildSchemaReportXlsxStaged` — 4 scenarios, 1:1 with RC-R22

Class docstring: `"""RC-R22 — dual-layout staged per-sheet Parquet lookup for XLSX (fix #150)."""`
Inserted after `TestStagedParquetRemoteRelativeLookup` (after L2209), before `TestDataFieldsFileColumn`.

| # | Test | GIVEN (fixture) | Key assertions |
|---|------|-----------------|----------------|
| 1 | `test_multi_sheet_collapsed_staged_parquets_stay_silent` | `DATA_GOT_ALL.xlsx` via `_make_xlsx` with sheets `aristas` (`["id","src"]`, 1 row) + `nodos` (`["id","label"]`, 1 row); stage per-sheet collapsed files `data_got_all_aristas.parquet` / `data_got_all_nodos.parquet` (pyarrow-direct); NO base `data_got_all.parquet`; `FileEntry(local=xlsx, remote="DATA_GOT_ALL.xlsx")` (capitalized remote — pins case-insensitive suffix + verbatim-remote keying) | `capsys` out has **no** `[!]`; `{s.origin for s in columns} == {"data_got_all_aristas.parquet", "data_got_all_nodos.parquet"}`; `row_counts == {"DATA_GOT_ALL.xlsx::data_got_all_aristas.parquet": 1, "DATA_GOT_ALL.xlsx::data_got_all_nodos.parquet": 1}`; per-sheet columns present (`src`, `label`) with int64 `hf_dtype` |
| 2 | `test_multi_sheet_spec_layout_double_underscore_stays_silent` | `report.xlsx` (sheets `ventas`, `costos`); stage `report__ventas.parquet` + `report__costos.parquet` only (no single-underscore near-neighbors, per spec GIVEN); remote `report.xlsx` | no `[!]`; `report__ventas.parquet` / `report__costos.parquet` appear in origins; row counts keyed `report.xlsx::report__ventas.parquet` etc. — dual-modality regression guard for `test_mirror.py:309-322` / `TestExpandedCard` stubs (primary-wins ordering is structurally guaranteed by the helper, so no need to stage both layouts) |
| 3 | `test_single_sheet_staged_parquet_stays_silent` | single-sheet `report.xlsx`; stage bare `report.parquet` only (artifact == key, per `_converters` single-sheet contract) | no `[!]`; `origins == {"report.parquet"}`; `row_counts == {"report.xlsx::report.parquet": n}` — pins that the base file flows through the single-item per-sheet loop exactly as today (RC-R07 `::` keying unchanged) |
| 4 | `test_multi_sheet_missing_staged_parquet_still_warns_once` | multi-sheet `DATA_GOT_ALL.xlsx` (**real openpyxl file — fallback path must read it**); empty `stage` dir (or one without any matching files) | exactly one `[!]` line containing `data_got_all.parquet` **and** `original-file inference` (pins the reword); `row_counts == {"DATA_GOT_ALL.xlsx": 1}`; origins == `{"DATA_GOT_ALL.xlsx"}` (fallback origin = verbatim remote); sheet-2 columns (`label`) **absent** — first-sheet-only degradation asserted as documented-unchanged |

All four use `build_schema_report_with_rows(cfg, staging_dir=stage)` (rows variant gives
`row_counts`); `capsys.readouterr()` for warning assertions; `_base_dir=tmp_path` on the
`DatasetConfig`.

### 6.3 Existing warn-path tests stay green (evidence)

`test_missing_parquet_warns_once_and_falls_back_to_csv` (L2120) and
`test_missing_parquet_warns_once_per_unique_key` (L2151) exercise the **non-XLSX** miss path —
the only edit on that path is the print statement swapping to
`_WARN_STAGED_PARQUET_MISSING.format(key=parquet_key)`, which produces
`  [!] Staged Parquet 'data/a/train.parquet' not found in staging directory; falling back to original-file inference.`
The assertions filter `"[!]"` + `Staged Parquet` and substring keys (`data/a/train.parquet`,
`shared.parquet`) — all preserved. No test asserts the old `CSV inference` tail (grep-verified
in exploration §1.2). Keep them byte-identical.

## 7. Edge cases & risks (with mitigations)

1. **Base-vs-sheet collision (pre-existing)**: `data.xlsx` (sheet `extra`) and `data_extra.xlsx`
   both normalize to `data_extra.parquet` after `__+`→`_` collapse. The fallback glob widens
   what the schema report matches. **Mitigation**: `c.stem != base_stem` exclusion; the helper
   is *no more permissive* than `expanded_planned_remotes` / `allowed_output_remotes` (identical
   glob patterns + exclusion), which already live with this hazard and are the clean/prune ground
   truth (`_clean.py:58-68`); `test_clean.py:54-73` is the canonical accept-regression.
   **Do not widen**: keep the two glob patterns byte-identical to `_mirror.py:238-248`.
2. **Single-sheet mis-scan as multi-sheet**: impossible in the literal glob (`stem.parquet` has
   `.` where the pattern requires `_`); the `c.stem != base_stem` guard is belt-and-suspenders
   consistent with the three precedents. Pinned by test #3.
3. **Spec-layout (`stem__*`) compat**: primary glob kept first, fallback only consulted when
   primary is empty — mirrors `_mirror.py:240-248`. Pinned by test #2.
4. **Case-insensitive suffixes**: `suffix.lower()` gates `is_xlsx` (L485-486); both producer
   (`prepare.py:773-778`) and consumer (L504) lowercase keys. Test #1 uses a capitalized remote
   `DATA_GOT_ALL.xlsx` and asserts verbatim-remote row keys to pin both behaviors.
5. **Recursive entries / `staging_dir=None` / `convert_to_parquet=False`**: never reach the
   lookup (L487, L502) — no warning, no change. Non-XLSX branch logic untouched.
6. **Nested remotes**: `base_parent` ≠ `.` → helper searches `staging_dir / base_parent`
   (derived from the normalized key, exactly as the current L508-510 derivation). Covered
   by construction; existing `test_same_stem_root_and_nested_resolve_independently` (L2053)
   exercises the non-XLSX nested path; per-sheet `sheet_origin` stays remote-relative via
   `relative_to(staging_dir)` (L579-580) — unchanged.
7. **Empty / missing staging dir**: helper returns `[]` (guard `search_dir.is_dir()`);
   warn branch fires as today. Behavior-neutral move of the `is_dir()` gate (verified: `stem.parquet`
   cannot `is_file()` when its parent doesn't exist).
8. **Warn-once-by-key**: `_warned_missing` keyed by `parquet_key`; a found multi-sheet entry no
   longer adds the key; the existing two-entries-one-key test (L2151) stays green.
9. **First-sheet-only fallback remains for genuine misses**: intentional (D5); sheets ≥ 2 still
   dropped in that degraded case — now visible (warning) and documented (RC-R22 scenario 5)
   instead of silent-with-false-warning.
10. **Reword regression**: pinned by test #4 (asserts `original-file inference`); prefixes stable.
11. **Test-suite drift**: additive tests only; no new dependencies; full-suite gate below.

## 8. Rollout & follow-ups

- **Implementation order (tasks phase)**: (1) helper + constants + four-site edits in
  `repo_compliance.py`; (2) spec delta already in place; (3) test-helper promotion + new class;
  4) run fast loop → full suite.
- **Verification**: `PYTHONIOENCODING=utf-8 uv run pytest tests/test_repo_compliance.py -q`
  (fast loop, incl. the 4 new + 2 existing warn tests), then `PYTHONIOENCODING=utf-8 uv run pytest tests/ -q`;
  `uv run ruff check src/sofer/repo_compliance.py tests/test_repo_compliance.py` and
  `uv run ruff format --check`; `uv run mypy src/` (CI runs mypy under Python 3.13 —
  do not add mypy to the version matrix, per AGENTS.md rule 12). Pre-commit hooks (ruff
  fix+format+mypy) run automatically — never `--no-verify`.
- **Rollback**: single-commit revert of `repo_compliance.py` + tests; delete change-local spec
  delta. Pure code revert — no data migration, config, or on-disk artifact touched.
- **Follow-up (out of scope, tracked)**: unify `_mirror.expanded_planned_remotes` and
  `prepare._check_local_overwrite` onto `_staged_xlsx_sheet_parquets` (or a shared
  `_mirror`-level helper) in a later change — identical logic, already correct and test-covered.
- **Release**: reporting-path-only change; lands on `dev` per AGENTS.md rule 12 branch flow; no
  version bump (hatch-vcs derives from tag), no CITATION.cff impact.

## 9. Acceptance mapping (spec scenario → test)

| RC-R22 scenario | Test |
|---|---|
| Multi-sheet XLSX, collapsed single-underscore staged parquets, silent | `TestBuildSchemaReportXlsxStaged::test_multi_sheet_collapsed_staged_parquets_stay_silent` (new) |
| Spec-layout double-underscore still recognized | `TestBuildSchemaReportXlsxStaged::test_multi_sheet_spec_layout_double_underscore_stays_silent` (new) |
| Single-sheet XLSX silent | `TestBuildSchemaReportXlsxStaged::test_single_sheet_staged_parquet_stays_silent` (new) |
| Genuine non-XLSX single-file miss warns once | existing `test_missing_parquet_warns_once_and_falls_back_to_csv` + `test_missing_parquet_warns_once_per_unique_key` (green, unmodified) |
| Genuine multi-sheet XLSX miss warns once, corrected tail, first-sheet fallback | `TestBuildSchemaReportXlsxStaged::test_multi_sheet_missing_staged_parquet_still_warns_once` (new) |

---

## Output contract

- **status**: complete
- **executive_summary**: Root cause is a producer/consumer naming mismatch: `prepare` stages
  multi-sheet XLSX per-sheet parquets under collapsed single-underscore names
  (`data_got_all_aristas.parquet`) while `_build_schema_report_impl` globs only the spec
  double-underscore layout plus the never-produced base key — firing a misleading warning and
  silently degrading the schema to first-sheet-only. Design adds one module-private
  dual-layout helper (`_staged_xlsx_sheet_parquets`) used by both glob sites (AGENTS.md rule 4),
  mirroring the `_mirror.expanded_planned_remotes` / `prepare._check_local_overwrite` precedent,
  and rewords all four warning tails to the format-generic "falling back to original-file
  inference." via two shared template constants. Behavior preserved: genuine misses warn once,
  single-sheet stays silent, spec layout keeps working, `::` row-count keys unchanged,
  first-sheet-only fallback unchanged-and-documented. Four new regression tests map 1:1 to the
  RC-R22 spec scenarios; the two existing warn-path tests stay green untouched.
- **artifacts**:
  - `openspec/changes/fix-xlsx-staged-parquet-warning/design.md` (this file, written)
  - Read inputs: `openspec/changes/fix-xlsx-staged-parquet-warning/exploration.md`,
    `…/proposal.md`, `…/specs/repo-compliance/spec.md`
  - Code read: `src/sofer/repo_compliance.py` (L1-70, L436-775), `src/sofer/_mirror.py`
    (L225-260), `src/sofer/prepare.py` (L590-630, L750-805), `src/sofer/_converters.py` (L55-100),
    `tests/test_repo_compliance.py` (L1-45, L2035-2234), `tests/test_clean.py` (L30-80)
- **next_recommended** (tasks):
  1. Implement `_staged_xlsx_sheet_parquets` + the two warning constants in
     `src/sofer/repo_compliance.py`; delegate both glob sites (L513, L555); swap the four
     printing sites (L532-533/L544-545/L572-573/L589-590) to the constants.
  2. Promote `_stage_parquet` to a module-level helper in `tests/test_repo_compliance.py`
     (existing static method delegates); add module-local `_make_xlsx(path, sheets)`.
  3. Add `TestBuildSchemaReportXlsxStaged` (4 tests per §6.2) after
     `TestStagedParquetRemoteRelativeLookup`.
  4. Verify: `PYTHONIOENCODING=utf-8 uv run pytest tests/test_repo_compliance.py -q`; then full
     `uv run pytest tests/ -q`; `uv run ruff check src/ tests/`; `uv run ruff format --check`;
     `uv run mypy src/`.
  5. Write `openspec/changes/fix-xlsx-staged-parquet-warning/tasks.md` + populate verify phase
     after implementation (per SDD flow).
- **risks**: base-vs-sheet collision re-exposure (mitigated by `c.stem != stem` + exact
  `expanded_planned_remotes` parity — pre-existing, allowlist is ground truth); accidental
  divergence of the two glob sites' results (eliminated by the shared helper); reword regressions
  (none possible per grep; pinned by new test #4); test-helper promotion breaking existing call
  sites (delegation keeps `self._stage_parquet` working).
- **skill_resolution**: none (no executor/phase skill path injected; no SDD-design skill present
  in the available-skills list — degraded fallback not required for this read-and-write design
  phase).

## Key Learnings

- **The fix is a naming-shape repair, not a warning-suppression**: the fallback glob restores
  per-sheet columns/`::` row counts that the buggy path silently dropped — the warning was the
  visible tip of first-sheet-only schema degradation.
- **The repo already had the pattern**: `_mirror.expanded_planned_remotes` (PUB-10) and
  `prepare._check_local_overwrite` (PRP-07) solve the identical __-collapsed mismatch with
  primary-then-fallback + `c.stem != stem` exclusion; the correct design reuses that established
  convention rather than inventing a mechanism, and keeps the two xlsx glob sites agreeing by
  construction through one shared helper.
- **Reword safety is evidence-based**: no test/README/CI gate asserts the "CSV inference" tail —
  only `[!]`, `Staged Parquet`, and key substrings — so the format-generic reword is provably
  test-compatible and should extend to all four sites (the tail is equally wrong for `.jsonl`).
- **Single-sheet XLSX already flows through the per-sheet loop**: the base `stem.parquet` is
  appended to the sheet list at both sites, so its row-count key is `entry.remote::stem.parquet`
  (not `entry.remote`) — a subtle contract the new single-sheet test must pin, not "fix".
- **The `is_dir()` gate move is behavior-neutral**: `single.is_file()` is False whenever the
  parent dir is absent, so hoisting the guard into the helper cannot change warnings or reads.
- **Test convenience**: pyarrow-direct staging (`pq.write_table` at the collapsed names,
  `test_clean.py:56-73` style) needs no readable source file for the silent paths; only the
  genuine-miss test needs a real openpyxl workbook because the fallback re-reads the source.