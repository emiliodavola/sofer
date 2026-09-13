# Proposal: fix-xlsx-staged-parquet-warning

## Intent

Close GitHub issue #150: `sofer_prepare` prints a misleading non-blocking
warning for multi-sheet XLSX —

```
[!] Staged Parquet 'data_got_all.parquet' not found in staging directory; falling back to CSV inference.
```

— although per-sheet parquets ARE the real staged artifacts, stored under
collapsed single-underscore names (`data_got_all_aristas.parquet`,
`data_got_all_nodos.parquet`), and the "CSV inference" tail is factually wrong
for `.xlsx`/`.jsonl` (the original file is re-read, not a CSV).

Root cause is a producer/consumer naming mismatch, not a missing file:

- **Producer** (`prepare.py:771-779` + `_converters.py:70`): multi-sheet XLSX
  keys start as `stem__sheet` and are collapsed by `normalize_parquet_remote`
  (`__+` → `_`) at apply time, so the on-disk artifact is always
  `stem_sheet.parquet` (single underscore). `stem.parquet` is **never**
  produced for multi-sheet XLSX.
- **Consumer** (`repo_compliance.py:513, 555` in `_build_schema_report_impl`):
  searches only `stem__*.parquet` (double-underscore, spec layout) plus base
  `stem.parquet`. Neither matches the collapsed names → misleading warning
  fires, and the schema silently degrades to re-reading **only sheet[0]**
  (`repo_compliance.py:704`) — other sheets' columns and per-sheet row counts
  are dropped from the schema/Dataset Card.

The repo has already solved this exact mismatch twice: `_mirror.expanded_planned_remotes`
(`_mirror.py:238-248`) and `prepare._check_local_overwrite` (`prepare.py:620-624`)
both try `stem__*` first, then fall back to `stem_*` while excluding the bare
placeholder (`c.stem != stem`). This change replicates that established pattern
in `_build_schema_report_impl` and corrects the warning wording, per the
confirmed handoff. No behavior change beyond the warning/schema-path.

## Scope

### In Scope

- `src/sofer/repo_compliance.py` — `_build_schema_report_impl`:
  - One shared helper resolving staged per-sheet parquets for an XLSX entry,
    dual-layout aware (primary `stem__*.parquet`; fallback `stem_*.parquet`
    excluding the bare `stem.parquet` placeholder), used by BOTH glob sites
    (`:513` and `:555`) — AGENTS.md rule 4 (no duplicated logic).
  - Multi-sheet XLSX entries with staged per-sheet parquets MUST NOT warn on
    the base/remote key.
  - Genuine missing-staged-parquet cases (non-XLSX single-file, or truly
    absent staged parquet) MUST still warn — existing behavior unchanged.
  - Single-sheet XLSX remains silent (artifact == key).
  - Consistent reword of the four warning tails (see Decision Point 3) to a
    format-generic phrase; keep `[!]`, the `Staged Parquet '{key}'` prefix, and
    the "falling back to …" shape stable (only substring-asserted by tests).
- Spec delta (change-local `specs/repo-compliance/spec.md`, applied to
  canonical on merge): NEW **RC-R22** (staged per-sheet lookup accepts
  collapsed single-underscore names) + amend RC-Universal §4.19 XLSX scenario
  prose to dual-layout wording; document the first-sheet-only fallback caveat
  for genuinely-missing staged parquet as explicitly-unchanged.
- `tests/test_repo_compliance.py` — new `TestBuildSchemaReportXlsxStaged`
  regression class (4 tests, see Approach); every new spec scenario gets a test
  (AGENTS.md rule 6).

### Out of Scope

- Row-counts rekeying: keys stay `entry.remote::<sheet_origin>` (per-sheet) and
  `entry.remote` (single/fallback) exactly as today; the Dataset Card consumer
  only sums values (`repo_compliance.py:1124-1125`), so no downstream change.
- First-sheet-only source fallback semantics for genuinely-missing staged
  parquet (`repo_compliance.py:704` reads `sheetnames[0]` only) — documented in
  RC-R22 as a known degradation, NOT fixed here.
- CLI/MCP surfaces: no flags, tools, or config keys added; pure
  reporting-path/schema-path change.
- Unification of `_mirror.expanded_planned_remotes` / `prepare._check_local_overwrite`
  onto the new helper: rule 4 is satisfied within the changed module; the
  cross-module consolidation is tracked as a follow-up (their behavior is
  already correct and test-covered; touching them widens the blast radius
  beyond issue #150).
- RC-R14 eligibility prose modernization (it still says "CSV remote"; RC-Universal
  §4.19 already supersedes it) — left untouched to keep the delta minimal.
- README/README_ES: no documented warning string (grep confirmed), no sync
  required per AGENTS.md rule 13.

## Capabilities

### New Capabilities

None. This is a correction to existing reporting behavior, not a new user
capability.

### Modified Capabilities

- **repo-compliance / schema report (reporting)**: staged per-sheet lookup now
  recognizes collapsed single-underscore names in addition to the spec
  double-underscore layout. Net effect for multi-sheet XLSX with staged
  parquets: no spurious `[!]` warning, and the schema/Dataset Card regains the
  per-sheet columns and `::`-keyed row counts that the buggy path silently
  dropped (the fix restores the behavior RC-Universal §4.19 already specifies).
- **repo-compliance / warning family**: the four staged-parquet warning tails
  ("falling back to CSV inference") become format-generic, accurate for
  `.csv/.tsv/.xlsx/.jsonl` source fallbacks.

## Approach

1. **Shared helper** (module-private in `repo_compliance.py`, next to
   `_build_schema_report_impl`):

   ```python
   def _staged_xlsx_sheet_parquets(staging_dir: Path, parquet_key: str) -> list[Path]:
       """Return staged per-sheet Parquets for an XLSX entry, dual-layout aware.

       Primary layout (spec): ``stem__*.parquet`` double-underscore sheet files.
       Fallback (current prepare staging): ``stem_*.parquet`` collapsed
       single-underscore names (normalize_parquet_remote collapses ``__+``),
       EXCLUDING the bare base ``stem.parquet`` so a single-sheet artifact is
       not mistaken for a sheet file. Mirrors
       ``_mirror.expanded_planned_remotes`` (PUB-10) and
       ``prepare._check_local_overwrite`` (PRP-07). Returns ``[]`` when
       nothing matches (caller then checks the single-file case and warns).
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

   Both glob sites delegate to it:
   - First XLSX branch (`:506-534`): `sheet_paths = _staged_xlsx_sheet_parquets(staging_dir, parquet_key)`; keep the existing `single = staging_dir / PurePosixPath(parquet_key)` append + `is_file()` filter, then the same `if sheet_paths: use_parquet = True … elif warn` decision shape.
   - Second XLSX collection (`:548-561`): `xlsx_sheet_paths = _staged_xlsx_sheet_parquets(staging_dir, parquet_key)` + the same single-file append — the `is_dir()` guard moves into the helper (removes the current duplicate `base_parent/base_stem/search_dir` derivation at `:508-510` and `:551-553`).

   The `c.stem != stem` exclusion is belt-and-suspenders with the precedent:
   `stem.parquet` cannot match the `stem_*.parquet` glob (`.` ≠ `_`), but it
   protects against future placeholder shapes and keeps the helper byte-for-byte
   consistent with `_mirror.py:247` / `prepare.py:375-376, 623-624, 866-868`.

2. **Non-XLSX branch** (`:536-547`): untouched — still warns on a genuinely
   missing `staging_dir/parquet_key` (dedup via `_warned_missing`, keyed by
   `parquet_key`). The multi-sheet XLSX entry no longer adds that key, so the
   warn-once-per-key contract (`test_repo_compliance.py:2151-2167`) is preserved.

3. **Warning wording** — two module-level format-string constants replacing the
   quadruplicated literals (same dedup rationale as rule 4), new generic tail:

   - not-found: `"  [!] Staged Parquet '{key}' not found in staging directory; falling back to original-file inference."`
   - unreadable: `"  [!] Staged Parquet '{key}' exists but could not be read ({failure_class}); falling back to original-file inference."`

   Substituted at all four sites (`:532-533`, `:544-545`, `:572-573`, `:589-590`).
   Verified test-compatible: no test asserts the old tail; only `[!]` +
   `Staged Parquet` + key substrings are asserted (`:2135-2138`, `:2165-2166`);
   README/README_ES carry no such string.

4. **Spec delta** — change-local `specs/repo-compliance/spec.md`:
   - NEW **RC-R22 — Staged per-sheet Parquet lookup accepts collapsed
     single-underscore names**: prose + three scenarios (multi-sheet collapsed
     stays silent with per-sheet origins/`::` row counts; spec-layout
     double-underscore still resolves — dual modality; genuine miss still warns
     exactly once naming the normalized key, then falls back to first-sheet-only
     source read, caveat documented as unchanged).
   - RC-Universal §4.19 XLSX scenario: amend prose to "each sheet-produced
     Parquet (spec `stem__sheet.parquet` or collapsed `stem_sheet.parquet`)
     contributes columns with `origin` set to its staged key".
   - RC-R14 prose tail "falls back to the CSV inference path" → "source-file
     fallback path" (prose only; scenario text untouched).

5. **Tests** — new `TestBuildSchemaReportXlsxStaged` in `tests/test_repo_compliance.py`
   (sibling of `TestStagedParquetRemoteRelativeLookup` at `:2039`), reusing the
   `_stage_parquet` pyarrow-direct pattern (`test_clean.py:56-73` style; source
   file need not be readable when staged parquets are found — the branch reads
   only parquet): 
   - `test_multi_sheet_collapsed_staged_parquets_stay_silent`: stage
     `data_got_all_aristas.parquet` + `data_got_all_nodos.parquet` → no `[!]`;
     column origins == collapsed keys; row_counts ==
     `{"<remote>::data_got_all_aristas.parquet": n1, "<remote>::data_got_all_nodos.parquet": n2}`.
   - `test_multi_sheet_spec_layout_double_underscore_stays_silent`: stage
     `report__ventas.parquet` + `report__costos.parquet` → no warning
     (dual-modality regression guard for `test_mirror`/`TestExpandedCard` stubs).
   - `test_single_sheet_staged_parquet_stays_silent`: stage `report.parquet`
     only → no warning, single origin `report.parquet` (artifact == key).
   - `test_multi_sheet_missing_staged_parquet_still_warns_once`: real multi-sheet
     xlsx via a local `_make_xlsx` copy (matches the existing 5-file convention;
     needed so the fallback path runs deterministically), no staged files →
     exactly one `[!]` naming the normalized key AND containing the corrected
     `original-file inference` tail (pins the reword).
   - Keep `:2120` / `:2151` warn-path tests green unmodified.

6. **Verification**: `uv run pytest tests/ -q` (additive), `uv run ruff check
   src/ tests/`, `uv run mypy src/`, pre-commit hooks (ruff fix+format+mypy).

## Decision Points

| # | Decision | Recommendation | Tradeoff |
|---|----------|----------------|----------|
| 1 | Fix shape: fallback glob vs skip-warning | **Fallback glob** (replicate `_mirror.py:238-248` / `prepare.py:620-624`) | Skip-warning would silence the noise but leave the real degradation — first-sheet-only schema and missing per-sheet row counts — invisible; the glob fallback restores the behavior RC-Universal §4.19 already specifies |
| 2 | Helper extraction & placement | **One module-private `_staged_xlsx_sheet_parquets` in `repo_compliance.py`** used by both glob sites (`:513`, `:555`) | Satisfies rule 4 within the changed module with the smallest blast radius; consolidating `_mirror`/`prepare` onto it is tracked as a follow-up (their logic is identical but already correct and test-covered) |
| 3 | Wording scope | **Reword all four tails** to "falling back to original-file inference." via two shared format constants | The tail is equally wrong for `.xlsx` (workbook re-read) and `.jsonl` (JSON-lines read); leaving any site un-reworded keeps a known-false claim on genuinely-missing cases. No test/README asserts the phrase; prefixes stay stable and are newly pinned by the miss-test |
| 4 | Genuinely-missing staged parquet for multi-sheet XLSX | **Keep first-sheet-only source fallback** (`:704`), document it in RC-R22 | Fixing per-sheet fallback would require openpyxl re-reads of every sheet — a behavior/semantics change beyond issue #150; documenting makes the degradation explicit rather than silent |
| 5 | Row-counts key shape | **Unchanged** — `entry.remote::<sheet_origin>` for per-sheet, `entry.remote` otherwise | Card consumer sums values only; rekeying would ripple into `build_dataset_card` and card-frontmatter tests for zero user-visible gain |

## Proposal question round (discharged by the confirmed handoff)

No question round was run: the handoff confirmed the product decisions below,
and the session is in auto mode. If any assumption is wrong, correct it before
the specs/tasks phases:

1. **Business problem**: a misleading non-blocking warning on every multi-sheet
   XLSX prepare run (issue #150) that misnames a never-produced artifact and
   describes the fallback wrongly; it also masks silent first-sheet-only schema
   data loss for those entries.
2. **Target users/situations**: dataset publishers running `sofer prepare` on
   GitHub Actions or locally with multi-sheet XLSX sources.
3. **Business rules preserved**: genuine missing-staged-parquet cases must
   still warn; single-sheet XLSX stays silent; row-count scenario shape
   (`entry.remote::<sheet>` keys) is unchanged; spec-layout (`stem__*`) stays
   supported.
4. **Product outcome**: zero spurious warnings on valid prepares; the Dataset
   Card shows all per-sheet columns/row counts (restoring RC-Universal §4.19);
   warnings that do fire are accurate.
5. **Current-state gap**: consumer globs the spec-layout `stem__*` while the
   producer writes collapsed `stem_*` names; the warning family says "CSV
   inference" for formats that re-read the original file.
6. **Implications/impact**: schema report + Dataset Card for multi-sheet XLSX
   change (more columns, `::` row counts) — a fix of the bug, not a regression
   to existing tests (none cover this path today); no CLI/MCP/config surface.
7. **Edge cases**: single-sheet XLSX (placeholder exclusion), empty staging
   dirs, nested remotes, dual-layout stubs, base-vs-sheet name collisions
   (pre-existing, allowlist parity), `_warned_missing` warn-once contract.
8. **Decision gaps**: none open — the two real forks (fix shape, wording
   scope) are decided in the Decision Points table above.
9. **Scope boundaries/non-goals**: no rekeying, no first-sheet-fallback
   semantics change, no CLI/MCP changes, no cross-module helper unification.
10. **Business risk/tradeoff**: widening the consumer glob re-exposes the
   pre-existing base-vs-sheet collision hazard — accepted because
   `expanded_planned_remotes`/`allowed_output_remotes` already encode the same
   single-underscore reality (the allowlist is the clean/prune ground truth).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/repo_compliance.py` | Modified | New `_staged_xlsx_sheet_parquets` helper; both XLSX glob sites (`:513`, `:555`) delegate; two shared warning-template constants; four warning tails reworded (`:532-533`, `:544-545`, `:572-573`, `:589-590`) |
| `openspec/changes/fix-xlsx-staged-parquet-warning/specs/repo-compliance/spec.md` | New | NEW RC-R22 + RC-Universal §4.19 XLSX-scenario prose amendment + RC-R14 prose tail alignment (applied to canonical on merge) |
| `tests/test_repo_compliance.py` | Modified | New `TestBuildSchemaReportXlsxStaged` (4 tests) in the RC-R13/R14 area; existing warn-path tests untouched and green |
| `openspec/changes/fix-xlsx-staged-parquet-warning/tasks.md` | New | This change's implementation/verify phases |
| `openspec/changes/fix-xlsx-staged-parquet-warning/verify.md` | New | Verify report incl. full-suite + ruff + mypy results |
| `README.md`, `README_ES.md` | Unchanged | No documented warning string; no sync required |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Single-underscore fallback matches an unrelated same-stem staged file (base-vs-sheet collision — pre-existing: `data.xlsx` sheet `extra` and `data_extra.xlsx` both normalize to `data_extra.parquet`) | Med (pre-existing) | `c.stem != stem` exclusion; fallback is no more permissive than `expanded_planned_remotes`/`allowed_output_remotes`, which already live with the hazard and are the clean/prune ground truth; `test_clean` DATA_GOT_ALL fixture is the canonical accept-regression |
| Single-sheet XLSX mis-scanned as multi-sheet if the placeholder is not excluded | Low | `stem.parquet` cannot match the `stem_*.parquet` glob; exclusion is belt-and-suspenders with the three `_mirror`/`prepare` precedents; `test_single_sheet_staged_parquet_stays_silent` covers it |
| Spec-layout (`stem__*`) compat with `test_mirror` stubs (`test_mirror.py:309-322`) and `TestExpandedCard` (`:3053-3054`) | Low | Primary double-underscore glob kept first; dual-layout regression test added |
| Reword breaks a test asserting the "CSV inference" tail | None (confirmed no test, no README string) | Prefixes + key preserved; corrected tail pinned by the new miss-test |
| row-counts `::` key-shape confusion in new tests | Med | New tests assert exact keys per the existing `:594` contract; production keys unchanged; card consumer sums only |
| First-sheet-only fallback for genuinely-missing staged parquet silently drops sheets ≥ 2 | Certain (by design) | Documented in RC-R22 as explicitly-unchanged; the noisy-warning fix removes the *false* warning while genuine misses remain visible and predictable |
| Full-suite drift / performance | Low | Additive tests only; no new dependencies; `uv run pytest tests/ -q` gate |

## Rollback

Single-commit rollback: revert the `repo_compliance.py` + test edits and delete
the change-local spec delta. The lookup returns to the double-underscore-only
glob (pre-fix behavior); no data migration, config, or on-disk artifact is
touched by this change, so rollback is a pure code revert with zero state
implications.

## Success Criteria

- `uv run pytest tests/ -q` green with the 4 new tests; existing warn-path tests
  (`test_repo_compliance.py:2120-2167`) pass unmodified.
- Multi-sheet XLSX + staged collapsed parquets (`DATA_GOT_ALL.xlsx` aristas/nodos
  scenario): zero `[!]` warnings; per-sheet column origins and
  `entry.remote::<sheet_origin>` row counts present in the schema report.
- Genuine misses (non-XLSX single-file; truly absent staged parquet) still
  produce exactly one `[!]` naming the normalized key, with the corrected
  format-generic tail.
- Single-sheet XLSX with staged `stem.parquet` stays silent.
- `uv run ruff check src/ tests/` and `uv run mypy src/` clean; pre-commit
  hooks pass.
- Spec delta (RC-R22 + §4.19 amendment) written in change-local form and
  applied to canonical `openspec/specs/repo-compliance/spec.md` on merge.