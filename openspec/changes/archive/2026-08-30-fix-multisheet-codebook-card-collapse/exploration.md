# Exploration: fix-multisheet-codebook-card-collapse

> Change: `fix-multisheet-codebook-card-collapse` — #97 multisheet codebook (wb.active bug) + #98 collapsible Data Fields per-sheet
> Date: 2026-08-30 | Author: sdd-explore sub-agent | Store: hybrid

## 1. Current codebook flow

### 1.1 `_read_xlsx` — the bug

`src/sofer/codebook.py:139-184` (`_read_xlsx`):

```python
wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
ws = wb.active   # <-- only first sheet
header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
...
```

* Reads `wb.active` exclusively; `wb.sheetnames` never consulted.
* No `sanitize_sheet_name` usage. Caller `_read_file:240` dispatches `.xlsx -> _read_xlsx` and expects a single `(headers, columns, dtypes)` tuple.
* `generate(csv_path):376-384` calls `_read_file` → `_build_markdown` once; `max_sample` resolved from `config.CODEBOOK_MAX_SAMPLE` at call time (never frozen).

### 1.2 `generate()` vs `generate_all()`

* `generate()`: single-file, writes to `output_path` or returns string. Format-agnostic after `_read_file`; `_build_markdown:252-340` renders one table (with optional Actual Type column when `dtypes is not None`). Empty `headers==[]` renders placeholder `**No data rows found**` (adv5).
* `generate_all(cfg, output_dir?)`: `src/sofer/codebook.py:387-566` — batch entry point.
  * Resolves `delimiter = cfg.csv_delimiter if None`, `encoding = cfg.csv_encoding` (rule-3 fix, never hardcoded `;`).
  * `base_dir = cfg._base_dir.resolve()`, `data_dir = base_dir / config.OUTPUT_DIR` (`cache/`).
  * First pass collects `entries: list[(Path,suffix)]`, skipping dirs/missing/unsupported with stderr warnings.
  * **Collision map** (`477-503`): derives `rel_stem` via `local.is_relative_to(data_dir) ? relative_to(data_dir) : relative_to(base_dir)`, then `out = (codebooks_dir / rel_stem).with_suffix(.md)` (handles `a.b.csv → a.md` via `PurePath.suffixes`). Detects multi-entry same `out` (e.g. `PROV.csv` vs `PROV.tsv` → `PROV.md`). Pattern: non-colliding written first, then `raise ValueError` naming all colliding sources (no codebook for colliding, no root index).
  * Per-file loop `509-527`: single `_read_file` call, single `_build_markdown`, single output. Tracks `outputs: list[(Path,n_cols)]` for index.
  * Root index `545-564`: `# Codebook Index: {cfg.name}`, `Tables: N | Total columns: sum`, `## Contents` with `- [codebooks/rel.md](codebooks/rel.md) — N columns` (relative to `write_root`, never absolute), never written on collision.
  * Option B (`output_dir is not None`): anchored via `base_dir / output_dir` if relative (PRP-06), `write_root = out.resolve()`, `codebooks_dir = write_root / config.CODEBOOKS_DIR`, `root_path = write_root / codebook.md`.

### 1.3 How output stems are built & collision logic

* Stem = `rel_stem` with single suffix replaced by `.md`. No format suffix appended (spec CB-R03).
* Collision key = final `out: Path`. Because sheets are invisible (single call per XLSX), a 2-sheet XLSX currently collides with *itself* only if we naively emitted two same stems — today it emits **one** stem, masking the bug.

### 1.4 Index generation

* Written only when no collisions. Source: `outputs` collected during loop. Never writes `base_dir/codebook.md` (R04 fix); standalone `codebooks_dir` is under `cache/`.

### 1.5 `sanitize_sheet_name` — divergence

* `src/sofer/_converters.py:76-99` `sanitize_sheet_name(name)`: lower, NFKD→ASCII, space→`_`, `[^a-z0-9_-]`→`_`, collapse `__+`→`_`, `strip("_")`, fallback `"sheet"`. Dedup `_{n}` handled by caller.
* Used ONLY in `_converters._convert_xlsx_to_parquet:367-486` — correctly iterates `wb.sheetnames`, sanitizes each, dedups via `seen: dict[str,int]` (`a_b, a_b_2, ...`), writes `stem` or `stem__sanitized` per sheet, handles empty sheets (zero-row Parquet). `convert_file_to_parquet:586-587` returns `dict[stem__sheet → Path]` for XLSX, `{stem: path}` for single formats.
* **Not used** in `codebook.py` at all. Fix must reuse same function (+ same dedup) to keep prepare-stage parquets and codebook filenames in sync.

### 1.6 Why prepare artifacts already use `__<sheet>` but disk uses `_`

* `normalize_parquet_remote:37-73` collapses `__+`→`_`, so `stem__sheet.parquet` on dispatch becomes `stem_sheet.parquet` on disk (e.g. `DATA_GOT_ALL.xlsx` → `data_got_all_aristas.parquet`, `data_got_all_nodos.parquet`). Guards in `prepare.py:848/603/364`, `_mirror.expanded_planned_remotes`, `_clean.allowed_output_remotes` were fixed 2026-08-30 to match **both** `__` and `_` (search `__*.parquet` then fallback `_*.parquet` filtered by `c.stem != stem`). Codebook fix must be consistent: logical key may be `__`, but filesystem check/normalization collapses.

## 2. Current HF card / README rendering

### 2.1 `prepare.py` + `repo_compliance.py` — the card's Data Fields

* `prepare.prepare:802-853` builds `schema, row_counts = build_schema_report_with_rows(cfg, staging_dir=output_dir)` against the **staged** Parquet (native types, not CSV fallback). `_build_schema_report_impl:482-638` now handles XLSX multi-sheet: when `staging_dir` contains `stem__*.parquet` (or fallback `_*.parquet`), it iterates each sheet Parquet via `_read_parquet_sample`, appending `ColumnSchema(origin=sheet_origin)` per sheet, with `row_counts.setdefault(entry.remote + "::" + sheet_origin, ...)`. CSV fallback path `698-700` still does `wb[wb.sheetnames[0]]` (single sheet fallback). **Important**: after `continue` on line 638, XLSX multi-sheet skips the single-file fallback, but the fallback path's single-sheet XLSX read is inconsistent with the staged path (should reuse sanitized iteration if we fix).
* `build_dataset_card:1182-1203` renders **one** `### Data Fields` table unconditionally when `schema:` non-empty: header `| Column | Type | File | …` then one row per `ColumnSchema` (`origin` → File column). Footnote `*Statistics … based on {SCHEMA_SAMPLE_SIZE:,}-row sample*`. `configs.data_files`/`Dataset Structure` use `expanded_planned_remotes` when `staging_dir` exists, so the card's file list already expands multisheet (RC-Universal-Card). The schema loop, however, already iterates multi-sheet `ColumnSchema` list — the table is just **one enormous paste** (all sheets concatenated). Issue #98 asks to make it usable.
* `dataset_info.features` (`1039-1045`) also concatenates all columns (`{name, dtype: hf_dtype or fallback}`) — no per-sheet grouping in frontmatter; that part should stay aggregated (HF viewer expects flat features). Collapsing is **body-only**.

### 2.2 `render.py` — the metadata → README pipeline

* `render.render:45-93` (single-file RND-01/02) resolves `metadata.yaml` via `_resolve_metadata_path` (file vs dir, force guard), `load()`, `_render_readme()`, writes beside metadata or to `output_dir`.
* `_render_readme:269-326`: pure projection, no recomputation. Title fallback `meta.dataset.name or meta.file.path or "Dataset"`, `description/license/source or "unknown"` (RND-03). Schema rows: `schema_rows = [f"| {col.name} | {col.storage_type} | {_render_semantic(col.semantic_type)} | {_render_pii(col.pii)} |" for col in meta.structure.schema]`, then `## Schema` table `| Column | Storage type | Semantic type | PII |` + rows. `generate_all_renders:96-252` mirrors profile batch (rel_stem derivation, collision map, output_dir Option B, `render_dir`/`profile_dir` via config). Same single-table problem.

### 2.3 Where `build/README.md` template lives

* There is no file template — `build_dataset_card` **is** the template (pure function returning string). Called only in `prepare.py:831-848`. No `templates/` dir. Changing it means editing `repo_compliance.py:1128+` lines. `render.py` has its own separate template (`_render_readme`).

### 2.4 How per-file schemas could be injected (Parquet stems already `__<sheet>`)

* Staged Parquets already provide ground truth: `stem__sanitized.parquet` (or `_` after normalization). `_build_schema_report_impl` already enumerates them per XLSX. So per-sheet injection options:
  * **Codebook**: since codebook reads source file directly (not staged), per-sheet must re-read XLSX sheets (reuse `_convert_xlsx_to_parquet` iteration logic).
  * **Card**: schema already per-sheet in memory (`ColumnSchema.origin == "data_got_all_aristas.parquet"`); grouping by `origin` to render per-sheet tables is trivial; no new reader needed.
  * **Render**: `meta.structure.schema` currently has no `origin`; would need to extend `profile.py` to populate provenance per column or adapt card-side grouping before render can group. For this change, collapsing the card (prepare) does not require render changes unless metadata is also multi-sheet.

## 3. Existing tests & fixtures

### 3.1 Codebook tests (`tests/test_codebook.py`, 1122 lines, ~42 tests)

* `TestInferType/TestInferColumnType` — inference logic.
* `TestGenerate` — structure, missing, write-to-file, row counts, sampling.
* `TestRead*` — `_read_csv/tsv/parquet/xlsx/jsonl`, empty, dtypes. `TestReadXlsx:296-331` only covers single-sheet; `test_empty_xlsx` asserts `unknown` dtypes for header-only sheet. No multi-sheet test (bug hidden).
* `TestReadFileDispatcher` — routing + unsupported error.
* `TestBuildMarkdown` — builder diff, Actual Type column, sentinel unique counts (CB-R07).
* `TestGenerateAll` + `TestGenerateAllOutputDir` — TOML-driven batch, `cache/codebooks/` + `cache/codebook.md` link format, Option B isolation.
* `TestEdgeCases` — same-stem collision (`PROV.csv` vs `PROV.tsv` → ValueError), partial-write semantics, rel-stem cache vs base_dir, empty/header-only, `bool/int` Parquet, `xlsx/jsonl` single-file.
* `TestCodebookCLI` / `TestEmptyInputPlaceholder` / `TestGenerateAllDelimiterSeam` — CLI flag handling, delimiter seam (`cfg.csv_delimiter`).
* **Gap**: no multisheet XLSX test, no sheet-sanitization test, no per-sheet codebook test.

### 3.2 Render tests (`tests/test_render.py`, 462 lines)

* `TestPercentRounding`, `TestSemanticRendering` (RND-03), `TestRenderResolvesPackagePath` (RND-01), `TestReadmeContent`, `TestRenderCli`, `TestRenderBatchRnd04` (batch N-renders, collision, custom output absolute/relative, `render_dir` config, missing metadata skip), `TestRenderForceGuardRnd05`.
* No Data Fields collapsing test.

### 3.3 Prepare tests (`tests/test_prepare.py`)

* ~1000 lines. Covers `resolve_output_dir`, overwrite protection, CSV→Parquet conversion, cross-file schema, large-value warnings, **multisheet leak regression** (`TestMultisheetLeakRegression`): `_make_xlsx` helper, `DATA_GOT_ALL.xlsx` with sheets `aristas`/`nodos` → asserts `data_got_all_aristas.parquet` + `data_got_all_nodos.parquet` exist, no `.xlsx` leak (`test_multisheet_stages_only_parquet_no_source_leak`, single-sheet case, etc.). No codebook-per-sheet test.

### 3.4 Repo-compliance tests (`tests/test_repo_compliance.py`, ~1400 lines)

* `TestBuildSchemaReportParquet`, `TestBuildSchemaReportParquetFallback`, `TestBuildSchemaReportSampling`, etc. No multisheet schema grouping test. `TestBuildDatasetCard` checks frontmatter/body sections but not collapsing.

### 3.5 Fixtures

* No `tests/fixtures/DATA_GOT_ALL.xlsx` committed; tests build XLSX on the fly via `_make_xlsx(path, sheets: dict[str, list[list[object]]])` (`test_prepare.py`) / `openpyxl.Workbook` inline (`test_codebook.py`). Pattern to follow: programmatically create 2-sheet workbook per test.

### 3.6 Converter tests (`tests/test_converters.py`)

* `TestNormalizeParquetRemote`, `TestSanitizeSheetName` (`DATA GÖT Año.XLSX → data_got_ano.xlsx`), dedup not explicitly covered.

## 4. Openspec specs affected & missing scenarios

| Spec domain | File | Status | Missing scenario |
|-------------|------|--------|------------------|
| `codebook` | `openspec/specs/codebook/spec.md` | covers CB-R01..R08 | **No R09 for multisheet**: reading all sheets, sanitized `__` stems, dedup `_{n}`, N codebooks per XLSX, index aggregation, collision with sheet suffixes |
| `prepare` | `openspec/specs/prepare/spec.md` | PRP-02 already documents normalized single-`_` multisheet (2026-08-30) | Card's `### Data Fields` collapsing not specced; codebook generation via `prepare --all-files` still calls single-file `generate_all` — spec should state prepare inherits codebook's N-files behavior |
| `render` | `openspec/specs/render/spec.md` | RND-01..05 | No collapsible requirement |
| `repo-compliance` | `openspec/specs/repo-compliance/spec.md` | schema/card generation | No per-sheet Data Fields grouping / collapsible |
| `parquet-conversion` | `openspec/specs/parquet-conversion/spec.md` | validated | No codebook linkage |
| `tool-config` | `openspec/specs/tool-config/spec.md` | lists known keys | Missing `card_collapse_threshold` |

Suggested delta placement (for spec phase):
* `codebook/spec.md` — new `CB-R09 multisheet XLSX` (scenarios below) + amend CB-R03 collision to handle `stem__sheet` suffixes.
* `repo-compliance/spec.md` (or `prepare/spec.md`) — new `PRP-10 / RC-Rxx collapsible Data Fields` (per-sheet `<details>` with threshold).
* `tool-config/spec.md` — add `card_collapse_threshold`.

Missing scenarios to add:
* Codebook: `.xlsx` with 2 sheets → 2 codebooks under `codebooks/<stem>__<sanitized>.md` (sanitization via `sanitize_sheet_name`, dedup `_{n}`), third sheet empty → zero-row placeholder, sanitized collision `Ventas`/`VENTAS` → dedup, root index counts each sheet as a table and sums columns.
* Codebook single-sheet stays `stem.md` (backward compat).
* Codebook collision: `data/a.xlsx` sheet `Ventas` vs `data/a_ventas.parquet`'s stem collision handled via normalized key.
* Card: `DATA_GOT_ALL.xlsx` with `aristas(4 cols)` + `nodos(3 cols)` → `README.md` renders **two** `### Data Fields` sections or two `<details>` blocks (one per sheet), each table isolated, summary `Data Fields -- aristas (4 columns)`, second `nodos (3 columns)`; when only one file, single table unwrapped; threshold gating.
* Threshold: `card_collapse_threshold = N` → collapse only when per-sheet column count > N or total columns > N (define).

## 5. Approaches — per-sheet codebook (N files vs N sections in one file)

| # | Approach | Description | Pros | Cons | Effort | Consistent with prepare? |
|---|----------|-------------|------|------|--------|--------------------------|
| A | **N files: one codebook per sheet** (`stem__sanitized.md`) | `generate_all` detects `.xlsx` with >1 sheet, iterates sheets, calls `_build_markdown` per sheet with per-sheet headers/columns/dtypes, writes `codebooks/<rel>/<stem>__<sanitized>.md` (reusing `sanitize_sheet_name` + same dedup as `_convert_xlsx_to_parquet`). `generate(file)` with `.xlsx` could either keep single-active-sheet (backward compat for positional CLI) or loop and print concatenated; recommend **batch N-files, single-file stays single-sheet** (explicit `generate_all` multi, `generate` single-sheet + log note about remaining sheets). | Matches prepare's N Parquet artifacts 1:1; no information loss; individual tables stay small; `codebooks/` provenance maps directly to `build/` parquets; collision logic extends naturally (sheet suffix is part of stem); future `profile`/`render` per-sheet extensions align | More files (2-10× for XLSX); requires extending collision key to include sheet suffix; need to update `_read_xlsx` signature or add `_read_xlsx_sheets` iterator; index must sum across sheets | Medium | **Yes** — mirrors `convert_file_to_parquet` returning `dict[stem__sheet]` and `expanded_planned_remotes` ground truth. **Recommended.** |
| B | **One file, N sections** (`stem.md` with `## Sheet: ventas`) | Single markdown per XLSX, `_build_markdown` extended to emit `## Sheet: <name> (N columns)` + table per sheet, single output path unchanged. | Fewer files; no collision-map change; simple `_read_xlsx` → `list[(headers,columns,dtypes,sheet_name)]` | Sheet tables still live in one long document (defeats per-sheet isolation for large XLSX); breaks 1:1 with prepare's N Parquets; per-sheet `Unique/Missing` stats harder to attribute; HTML collapsible would need per-section `<details>` inside one file (mixing concerns); inconsistent with `profile` per-file granularity | Low-Med | No — prepare splits, codebook would not. |
| C | **Hybrid: N files + umbrella file** | Write both per-sheet files plus a `stem.md` index linking to sheets | Self-documenting umbrella | Duplication, 2× write cost, confusing for consumers (which to read?) | Med-High | Over-engineered |

**Recommendation: Approach A — N files one-per-sheet.**

Rationale: the project already committed to N Parquets per XLSX (spec PRP-02 normalized single-`_`); the codebook is the human companion to each Parquet. One codebook per Parquet preserves the provenance chain `source sheet → parquet → codebook → card section`. Index generation already does `sum(n_cols)` and `total_tables = len(outputs)` — extending `outputs` to one entry per sheet is a localized change. Approach B collapses distinct tables into one file, contradicting the multisheet split's intent and making the collapsible card harder (see §6 — per-sheet `<details>` wants per-sheet granularity; N files gives it for free).

Backward compat: single-sheet XLSX currently `stem.md` — with A, single-sheet still `stem.md` (no suffix), identical to today. Only multi-sheet changes.

## 6. Collapsible Data Fields in HF README

### 6.1 HF/GHF `<details>` support

* HF Hub dataset cards render GitHub-Flavored Markdown; `<details><summary>…</summary> … </details>` is supported (GHF spec, widely used on HF). Verified in prior specs/project: HF frontmatter cards with `<details>` render collapsed by default. Must emit **HTML**, not Markdown `+++` extensions.
* Required shape:
  ```html
  <details><summary>Data Fields -- aristas (4 columns)</summary>

  | Column | Type | File | … |
  |--------|------|------|
  | ... |

  </details>
  ```
  Blank line after `<summary>` is required for the table to render inside `<details>` on GHF.

### 6.2 User constraint — per-table collapse, not mega-details

Flujo pedido: *al colapsar las tablas en el readme se colapse CADA TABLA POR SEPARADO no todas juntas*. Means each per-file (or per-sheet) table must be wrapped in its own `<details><summary>Data Fields -- <sheet> (N columns)</summary> … </details>`, NOT one mega `<details>` around all tables. When the dataset has `a.csv` + `DATA_GOT_ALL.xlsx(2 sheets)` → 3 independent collapsibles, each expandable individually.

### 6.3 Threshold config

* Propose `tool.sofer.card_collapse_threshold: int = <default>` in `pyproject.toml [tool.sofer]` and `src/sofer/config.py:_DEFAULTS` (e.g. 20 or 30). Semantics: collapse a table when its column count > threshold **or** when total columns across all tables > threshold (or simpler: collapse iff number of Data Fields blocks > 1 or `len(schema) > threshold`). Minimal v1: collapse unconditionally when `len(schema) > 15` or when grouping yields >1 block — but configurable is required per AGENTS rule 1 (no hardcoded truncation limits like `[:10]`).
* Must be read via `config.CARD_COLLAPSE_THRESHOLD` (or `card_collapse_threshold`), rebound by `config.reload`, not hardcoded in `repo_compliance.py`.
* AGENTS rule 13: README_ES sync — `build_dataset_card` prose stays English; threshold comment in TOML stays English.

### 6.4 Single-file backward compat vs multi-file collapse

* Single file, single table, below threshold → render plain `### Data Fields` table as today (no `<details>`), preserving existing tests (`test_repo_compliance.py` asserts `### Data Fields` + `| Column | Type | …`).
* Multi-file or per-sheet grouping → wrap **each** group. When expanded grouping yields 1 block, still wrap only if above threshold (avoid unnecessary `<details>` for tiny datasets).
* Card's `dataset_info.features` stays flat (no collapse); collapse affects only the body `### Data Fields` (and potentially `Dataset Structure` already via `expanded_planned_remotes`).
* `render.py` change is optional: if metadata later carries per-sheet provenance, `render._render_readme` could also emit per-sheet `<details>` using same threshold; for this change the card (`repo_compliance.py`) is the target, `render.py` stays single-table unless `profile` is extended.

### 6.5 Implementation sketch (not yet code)

* `repo_compliance.build_dataset_card` today: `if schema: lines.append("### Data Fields"); lines.append(table)`.
* New: build `groups: dict[str, list[ColumnSchema]]` keyed by `origin` (or `stem__sheet` sheet name derived from `origin`). When `staging_dir` provided and XLSX sheets present, `origin` is `data_got_all_aristas.parquet` → group `aristas`. When no grouping needed, single group `""`.
* For each `(label, cols)` group: build markdown table lines for that group; if `should_collapse(len(cols), config.CARD_COLLAPSE_THRESHOLD)` wrap with `<details><summary>Data Fields -- {label} ({len(cols)} columns)</summary>\n\n{table}\n\n</details>`.
* Label derivation: sheet suffix after `__` (or `_` normalized) → `sanitize_sheet_name` inverse is lossy, so reuse `origin`'s sheet fragment or the staged filename stem. Prepare already writes `data_got_all_aristas.parquet`; card can display `aristas`.

## 7. Risks

* **Naming collisions — `__` namespace**: XLSX sheet `Ventas` → `stem__ventas.md`; an existing file `stem_ventas.csv` could normalize to same logical key after `normalize_parquet_remote`'s `__+`→`_`. Risk mitigated by extending `collision_sources` to use sheet-expanded keys (reuse `sanitize_sheet_name` + dedup before computing `out`), and by making `expanded_planned_remotes` dual-guard authoritative (both `__` and `_`).
* **Dedup of sheet names**: `_convert_xlsx_to_parquet` dedups `a_b, a_b_2, a_b_3` case-insensitively via `seen`. Codebook must reuse **identical** algorithm; divergence (e.g., codebook using raw sheet name vs sanitized) would cause `build/` parquet `ventas_2.parquet` but codebook `ventas.md` mismatch. Must extract dedup into shared helper or import `sanitize_sheet_name` and replicate the `seen` logic verbatim.
* **Inferred vs confirmed state per-sheet**: Codebook `infer_column_type` is per-sheet evidence; `profile` inference (`confirm_threshold=0.8`, `min_threshold=0.5`) will run per-sheet Parquet after prepare, so each sheet's semantic/PII inference is isolated. Card groups must not merge stats across sheets (unique/missing per column must stay sheet-local), otherwise `N=4 sheets × 10 cols` concatenated table misattributes sample size.
* **Empty / header-only sheets**: `_convert_xlsx_to_parquet` emits 0-row Parquet for empty sheets; codebook must emit placeholder (`**No data rows found**` or zero-row table with `unknown` types), not crash on `StopIteration`. `ws.iter_rows` returns `header_row is None` case must be handled (already in converter).
* **Root index aggregation**: Current index sums `total_cols` and `total_tables = len(outputs)`. With N sheets, `total_tables` becomes number of Parquet-backed tables (e.g. 3 files → 4 tables if one XLSX has 2 sheets) — spec/CLI output message must clarify (e.g. `Result: 3 source files → 4 table(s)`). Tests expecting `len(results) >= 3` will still pass but exact assertions need update.
* **Threshold hardcoding**: If `build_dataset_card` hardcodes `if len(schema) > 10: collapse`, violates AGENTS rule 1 and bypasses `[tool.sofer]`. Must add `card_collapse_threshold` to `_DEFAULTS` and `pyproject.toml [tool.sofer]`.
* **HF rendering quirks**: `<details>` inside a codebook index (`cache/codebooks/`) is not needed; only the card's Data Fields should collapse. Ensure tables remain valid Markdown inside `<details>` (blank lines before/after). Some HF viewers strip HTML if not well-formed — test with `---\n` frontmatter + HTML body.
* **Staged-file divergence**: `_build_schema_report_impl`'s XLSX multi-sheet path currently does `row_counts.setdefault(entry.remote + "::" + sheet_origin, ...)` (composite key). Card's `num_examples` sum will double-count if not careful; row_counts consumer sums values — composite keys inflate. Keep per-sheet counts but sum correctly (sum of distinct sheet files, not `entry.remote` duplicates).

## 8. Affected Areas

* `src/sofer/codebook.py` — `_read_xlsx` (replace single-sheet with sheet-iterating helper `_read_xlsx_sheets` or `list[tuple[str,headers,columns,dtypes]]`), `generate()` (single-file mode preserves single sheet or concatenates), `generate_all()` (expand XLSX entries to N outputs, extend `output_paths`/`collision_sources` to include sheet suffix, update `outputs`/`total_cols`/`total_tables` aggregation)
* `src/sofer/_converters.py` — no change, but `sanitize_sheet_name` is reused; ensure codebook imports it (avoid duplication)
* `src/sofer/repo_compliance.py` — `_build_schema_report_impl` (XLSX fallback already partially multi-sheet; align with codebook logic), `build_dataset_card` (group `ColumnSchema` by `origin`/sheet, emit per-group `<details>` with threshold from config)
* `src/sofer/config.py` — add `card_collapse_threshold` to `_DEFAULTS`, module constant `CARD_COLLAPSE_THRESHOLD`, reload binding, validation (non-negative int)
* `src/sofer/prepare.py` — no direct change, but inherits codebook N-files behavior via `generate_all_codebooks(cfg, output_dir=...)`; ensure orphan/`expanded_planned_remotes` dual-guard stays consistent (already fixed)
* `src/sofer/_clean.py` / `src/sofer/_mirror.py` — no change (already handle `_`/`__`); verify `allowed_output_remotes` covers `codebooks/**/*.md` per-sheet
* `src/sofer/render.py` — optional: extend `_render_readme` with same grouping if metadata becomes per-sheet; otherwise no change for this slice
* `openspec/specs/codebook/spec.md`, `openspec/specs/repo-compliance/spec.md` (or `prepare`), `openspec/specs/tool-config/spec.md` — delta specs
* `pyproject.toml` — `[tool.sofer] card_collapse_threshold` default
* Tests: `tests/test_codebook.py` (add `TestReadXlsxMultisheet`, `TestGenerateAllMultisheet`, collision-with-sheet), `tests/test_repo_compliance.py` (add `TestCardCollapsibleDataFields`), `tests/test_prepare.py` (assert `build/codebooks/data_got_all_aristas.md` etc.)

## 9. Recommendation

**Adopt Approach A (N files one-per-sheet) for the codebook and per-sheet `<details>` wrapping for the card.**

1. Extract sheet iteration into `_read_xlsx_sheets(path) -> list[(sanitized_sheet, headers, columns, dtypes)]` reusing `sanitize_sheet_name` + identical dedup; `_read_xlsx` stays as single-sheet helper for `generate()` backward compat or delegates to sheets[0].
2. Extend `generate_all` to call `_read_xlsx_sheets` for `.xlsx`, emitting `codebooks/<rel>/<stem>__<sanitized>.md` per sheet (single sheet → `stem.md`). Extend `output_paths`/`collision_sources` to sheet-expanded keys pre-write, preserving partial-write-then-ValueError semantics.
3. Add `card_collapse_threshold` to `config.py` / `pyproject.toml` (default e.g. 15), implement `build_dataset_card` grouping by `origin` sheet fragment, wrapping each group's table in its own `<details><summary>Data Fields -- <sheet> (N columns)</summary>` block when `N > threshold` or `len(groups) > 1`. Single-table below threshold renders unwrapped.

This keeps prepare's Parquet/Codebook/Card trilogy aligned (1 sheet → 1 parquet → 1 codebook → 1 card section), satisfies *cada tabla por separado* (each `<details>` independent), preserves backward compat for single-sheet datasets and existing single-table tests (unwrap path), and avoids the information loss of a single concatenated codebook.

## 10. Ready for Proposal

Yes — exploration is complete. The orchestrator can proceed to `sdd-propose` for `fix-multisheet-codebook-card-collapse`. Proposal should scope #97 (codebook N-files) and #98 (per-sheet collapsible card with `card_collapse_threshold`) together, as they share the XLSX sheet-expansion concern and the `sanitize_sheet_name`/`normalize_parquet_remote` `__`/`_` duality. Acknowledge that `render.py` per-sheet collapsing is out of scope for this change unless `profile` is also extended.

---
*Sources: `src/sofer/codebook.py:139-184`, `src/sofer/_converters.py:76-99,367-486,541-593`, `src/sofer/prepare.py:553-928`, `src/sofer/repo_compliance.py:1173-1203,482-638`, `src/sofer/render.py:269-326,96-252`, `src/sofer/config.py:28-320`, `src/sofer/_mirror.py:180-268`, `src/sofer/_clean.py`, `tests/test_codebook.py`, `tests/test_render.py`, `tests/test_repo_compliance.py`, `tests/test_prepare.py`, `openspec/specs/codebook/spec.md`, `openspec/specs/prepare/spec.md:1-200`, `openspec/config.yaml`.*

