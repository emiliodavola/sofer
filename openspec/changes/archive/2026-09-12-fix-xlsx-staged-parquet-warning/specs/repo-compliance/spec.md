# Delta for repo-compliance — staged per-sheet Parquet lookup (dual-layout) and format-generic warning wording

> Change-local delta for `fix-xlsx-staged-parquet-warning` (closes #150). Block
> format follows the repo's archived change specs; canonical requirement IDs
> continue from `openspec/specs/repo-compliance/spec.md` (RC-R01..RC-R21,
> RC-Universal, RC-Universal-Card — RC-R22 is the next free ID). Applies to the
> canonical spec on merge.
>
> Repo convention note: the canonical capability spec uses numbered sections
> (`### 4.N … (RC-Rxx)`), so each delta block carries the canonical section +
> ID tag it replaces at archive time.

Scenario → test mapping (AGENTS.md rule 6 / config.yaml: every spec scenario
MUST have a corresponding test):

| RC-R22 scenario | Corresponding test(s) |
|---|---|
| Multi-sheet XLSX with collapsed single-underscore per-sheet Parquets stays silent | `test_multi_sheet_collapsed_staged_parquets_stay_silent` (new, `TestBuildSchemaReportXlsxStaged`) |
| Spec-layout double-underscore names still recognized | `test_multi_sheet_spec_layout_double_underscore_stays_silent` (new) |
| Single-sheet XLSX stays silent | `test_single_sheet_staged_parquet_stays_silent` (new) |
| Genuine non-XLSX single-file miss still warns once | `test_missing_parquet_warns_once_and_falls_back_to_csv`, `test_missing_parquet_warns_once_per_unique_key` (existing, kept green unmodified) |
| Genuine multi-sheet XLSX miss warns once with the corrected tail | `test_multi_sheet_missing_staged_parquet_still_warns_once` (new) |

## ADDED Requirements

### Requirement: RC-R22 — Staged per-sheet Parquet lookup accepts collapsed single-underscore names

> Added by change `fix-xlsx-staged-parquet-warning` (closes #150).

The staged-Parquet presence check in `_build_schema_report_impl` (backing both
`build_schema_report` and `build_schema_report_with_rows`) SHALL resolve
per-sheet Parquets for multi-sheet XLSX entries with a dual-layout lookup
implemented by ONE module-private shared helper used by BOTH glob sites (no
duplicated logic, AGENTS.md rule 4): the spec double-underscore layout
`stem__*.parquet` SHALL be the primary match; when it yields no files, the
collapsed single-underscore layout `stem_*.parquet` SHALL be searched — the
exact name `prepare` writes after `normalize_parquet_remote` collapses runs of
`__+` to `_` — EXCLUDING the bare base `stem.parquet` placeholder (the
`c.stem != stem` exclusion mirrored from `_mirror.expanded_planned_remotes`
and `prepare._check_local_overwrite`), so a single-sheet artifact is never
mistaken for a sheet file.

When per-sheet Parquets exist under either layout, the system MUST NOT emit a
staged-Parquet `[!]` warning on the base/remote key (e.g.
`data_got_all.parquet`), which is never produced for multi-sheet XLSX; the
per-sheet branch SHALL instead run — every sheet's columns with `origin` set to
its remote-relative staged key, and exact row counts keyed
`entry.remote::<sheet_origin>` (RC-R07 keying preserved; the Dataset Card
consumer sums values only).

A GENUINELY missing staged Parquet SHALL still warn: exactly one `[!]` warning
naming the expected normalized `.parquet` key, warn-once per key per run
(RC-R14/RC-R17 contract via `_warned_missing`), then the original-file fallback
SHALL run without raising. For a multi-sheet XLSX with no staged Parquet under
either layout, that fallback source read covers only the FIRST sheet
(`sheetnames[0]`) — this degradation is documented and explicitly UNCHANGED by
this change (per-sheet source re-reads are out of scope).

All four staged-Parquet warning templates — the two "not found in staging
directory" sites and the two "exists but could not be read ({failure_class})"
sites — SHALL be backed by the same two module-level format constants and SHALL
use a format-generic tail: **"falling back to original-file inference."** —
accurate for `.csv/.tsv/.xlsx/.jsonl` sources, replacing the factually wrong
"CSV inference" tail. The `[!]` marker, the `Staged Parquet '{key}'` prefix,
the "falling back to …" shape, the `({failure_class})` fragment, and warn-once
semantics SHALL remain stable.

#### Scenario: Multi-sheet XLSX with collapsed single-underscore per-sheet Parquets stays silent

- GIVEN `DATA_GOT_ALL.xlsx` (sheets `aristas`, `nodos`) with staged per-sheet
  Parquets `data_got_all_aristas.parquet` and `data_got_all_nodos.parquet`
  (collapsed single-underscore layout) and NO base `data_got_all.parquet`
- WHEN the schema report is built with `staging_dir`
- THEN no `[!]` warning SHALL be emitted for the base key `data_got_all.parquet`
- AND columns from both sheets SHALL appear with `origin`
  `data_got_all_aristas.parquet` and `data_got_all_nodos.parquet`
- AND row counts SHALL be keyed
  `{"<remote>::data_got_all_aristas.parquet": n1, "<remote>::data_got_all_nodos.parquet": n2}`

*Test: `test_multi_sheet_collapsed_staged_parquets_stay_silent` (new).*

#### Scenario: Spec-layout double-underscore names still recognized

- GIVEN `report.xlsx` with staged per-sheet Parquets `report__ventas.parquet`
  and `report__costos.parquet` (double-underscore spec layout) and no matching
  single-underscore files
- WHEN the schema report is built with `staging_dir`
- THEN the double-underscore Parquets SHALL be used (primary layout wins)
- AND no `[!]` warning SHALL be emitted

*Test: `test_multi_sheet_spec_layout_double_underscore_stays_silent` (new,
duality regression guard for `test_mirror`/`TestExpandedCard` stubs).*

#### Scenario: Single-sheet XLSX stays silent

- GIVEN single-sheet `report.xlsx` with staged `report.parquet`
  (artifact == key)
- WHEN the schema report is built with `staging_dir`
- THEN the single Parquet SHALL be read (base key, NOT treated as a sheet file)
- AND no `[!]` warning SHALL be emitted
- AND `origin` SHALL be `report.parquet`

*Test: `test_single_sheet_staged_parquet_stays_silent` (new).*

#### Scenario: Genuine non-XLSX single-file miss still warns once

- GIVEN an eligible `.csv`/`.tsv`/`.jsonl` entry whose staged Parquet is absent
  under its normalized key
- WHEN the schema report is built with `staging_dir`
- THEN exactly one `[!] Staged Parquet '{key}'` warning SHALL be emitted
- AND columns SHALL come from the original-file fallback
- AND two entries sharing one key SHALL still warn exactly once total
  (warn-once per key preserved — RC-R14)

*Tests: existing `test_missing_parquet_warns_once_and_falls_back_to_csv` and
`test_missing_parquet_warns_once_per_unique_key` (kept green, unmodified).*

#### Scenario: Genuine multi-sheet XLSX miss warns once with the corrected tail

- GIVEN a multi-sheet XLSX entry with NO staged per-sheet Parquet under either
  layout and no base Parquet
- WHEN the schema report is built with `staging_dir`
- THEN exactly one `[!]` warning SHALL name the normalized key and contain the
  corrected format-generic tail "original-file inference" (pins the reword)
- AND columns SHALL come from a source read of the FIRST sheet only
  (`sheetnames[0]`) — the documented, unchanged degradation
- AND sheet 2+ columns and per-sheet row counts SHALL NOT be attributed

*Test: `test_multi_sheet_missing_staged_parquet_still_warns_once` (new).*

## MODIFIED Requirements

### Requirement: 4.19 Schema report via staged Parquet for all convertible formats (RC-Universal) — Universal (Modified 2026-08-29, convert-all-formats-parquet; modified by fix-xlsx-staged-parquet-warning)

> Added by change `convert-all-formats-parquet` (archived 2026-08-29). Modified
> by change `fix-xlsx-staged-parquet-warning` (closes #150).

`build_schema_report(cfg, staging_dir)` MUST include columns from every convertible entry (`.csv/.tsv/.xlsx/.jsonl`) that is not `recursive` and not excluded by `include_in_schema=false`, reading staged Parquet when present at normalized key `staging_dir / normalize_parquet_remote(parquet_remote_for(entry.remote))` else falling back to original file. For `.xlsx`, each sheet-produced Parquet contributes columns with `origin` set to its staged key — the spec layout `stem__sheet.parquet` or, equally, the collapsed single-underscore name `stem_sheet.parquet` that `prepare` actually writes (`normalize_parquet_remote` collapses `__+` to `_`), both resolved by the RC-R22 staged lookup. When a multi-sheet XLSX entry has NO staged Parquet under either layout, the original-file fallback reads only the first sheet (`sheetnames[0]`); this degradation is documented and UNCHANGED by RC-R22 (`fix-xlsx-staged-parquet-warning` does not fix it). `ColumnSchema.dtype/nullable/unique/missing` semantics unchanged; sample size governed by `config.SCHEMA_SAMPLE_SIZE`. Types for XLSX/JSONL-derived Parquets map via existing Parquet physical-type → `dtype` table.

(Previously: only `.csv` remotes contributed; `.tsv/.xlsx/.jsonl` skipped via `if not remote.endswith(".csv"): continue`; parquet branch keyed by `staging_dir / <stem>.parquet` ignoring normalized remotes and multi-sheet.)
(Previously, by `fix-xlsx-staged-parquet-warning`: the origin-key wording assumed only the `stem__sheet.parquet` layout; the staged lookup now also accepts the collapsed `stem_sheet.parquet` layout (RC-R22), and the first-sheet-only fallback for genuinely-missing multi-sheet Parquets is now made explicit rather than silent. Scenario text below is unchanged; the canonical XLSX scenario remains valid under the dual-layout lookup.)

#### Scenario: TSV contributes via its Parquet
- GIVEN `data/b.tsv` converted to `data/b.parquet` in staging
- WHEN `build_schema_report(cfg, staging_dir=...)` runs
- THEN returned list SHALL contain columns from `b.parquet` with origin `data/b.parquet`

#### Scenario: XLSX multi-sheet contributes per-sheet
- GIVEN `report.xlsx` producing `report__ventas.parquet` and `report__costos.parquet`
- WHEN schema report runs
- THEN columns from both sheets SHALL appear with distinct origins `report__ventas.parquet` and `report__costos.parquet`

#### Scenario: JSONL contributes via staged Parquet
- GIVEN `data/c.jsonl` converted to `data/c.parquet`
- WHEN schema report runs
- THEN columns SHALL be read from `data/c.parquet` (key-union derived)

#### Scenario: Fallback to original when Parquet missing or opt-out
- GIVEN entry `raw.xlsx` with `convert_to_parquet=false` or missing staged Parquet
- WHEN schema report runs
- THEN columns SHALL be read via `_read_file` fallback (CSV/TSV/XLSX/JSONL readers) and origin SHALL be declared remote

#### Scenario: Same-stem nested remotes resolve independently via normalized keys
- GIVEN remotes `survey.csv` and `data/survey.tsv` each with distinct staged Parquets
- WHEN schema report builds
- THEN each SHALL resolve to its own normalized Parquet (`survey.parquet` vs `data/survey.parquet`) without cross-contamination

#### Scenario: Missing staged Parquet warns once then falls back
- GIVEN eligible `a.tsv` whose `a.parquet` is absent under normalized key
- WHEN schema report builds
- THEN exactly one `[!]` warning naming `a.parquet` SHALL be emitted and columns SHALL come from TSV fallback

### Requirement: 4.15 Missing staged Parquet warns deterministically, then falls back to CSV (RC-R14)

> Added by change `staged-parquet-stem-collision` (archived 2026-08-26). Modified
> by change `fix-xlsx-staged-parquet-warning` (closes #150).

If the expected staged Parquet does not exist for an eligible entry, the
system MUST emit exactly one `[!]` warning naming the expected remote-relative
`.parquet` key, then fall back to the source-file fallback path (the original
file is re-read — CSV for `.csv` remotes, workbook for `.xlsx`, JSON lines for
`.jsonl`), matching the format-generic warning wording of RC-R22. The fallback
MUST NOT raise. Following the RC-R11 convention, the warning MUST be
deterministic (same input → same single message) and MUST NOT abort the run.

An entry is eligible for staged-Parquet reading (and thus for the
missing-Parquet `[!]` warning) iff it declares a CSV remote
(`remote.lower().endswith(".csv")`), is NOT `recursive=true`, is NOT
`upload_as_csv=true`, and has `include_in_schema` respected for schema
collection. Entries outside this set never warn and never consult
`staging_dir`.

(Previously: the prose said the fallback went to the "CSV inference path".
`fix-xlsx-staged-parquet-warning` aligns the prose with the format-generic
"original-file inference" warning tail of RC-R22; scenario text below and the
eligibility prose are untouched to keep the delta minimal.)

#### Scenario: Missing parquet warns once and falls back

- GIVEN an eligible CSV entry whose expected staged Parquet is absent from
  `staging_dir`
- WHEN the schema report is built
- THEN exactly one `[!]` warning naming the expected `.parquet` key SHALL be
      emitted
- AND the entry's columns SHALL come from the CSV fallback path

#### Scenario: Present parquet stays silent

- GIVEN every eligible entry's staged Parquet exists at its remote-relative
  key
- WHEN the schema report is built
- THEN no missing-parquet warning SHALL be emitted