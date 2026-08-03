# Tasks: hf-dataset-compliance

## Review Workload Forecast

| Metric | Value |
|--------|-------|
| Files touched | 7 (2 new, 5 modified) |
| Estimated new/modified lines | ~480 |
| Review budget | 1200 lines |
| Budget headroom | ~720 lines (60% buffer) |
| Chained PRs needed | **No** — well within single-PR tolerance |

**Risk assessment**: Low. Three pure functions, no net-new runtime deps (PyYAML replaces tomli-w), backward-compatible TOML, all new fields optional.

---

## Phase 1 — Model & Config

- [x] **1.1** Add `language`, `pretty_name`, `task_categories`, `size_categories`, `citation`, `collection_method`, `csv_delimiter`, `csv_encoding` fields to `DatasetConfig` dataclass in `model.py` — all optional with defaults per design table
- [x] **1.2** Update `DatasetConfig.from_toml()` to read new `[meta]` fields via `.get()` with defaults — zero breakage for existing configs
- [x] **1.3** Replace `tomli-w>=1.0` with `pyyaml>=6.0` in `pyproject.toml` `dependencies`

## Phase 2 — Core Compliance Module

- [x] **2.1** Create `ColumnSchema` dataclass in `repo_compliance.py` with `name: str`, `dtype: str`, `nullable: bool`, `example: str`, `unique: int`, `missing: float`
- [x] **2.2** Define module-level `_LICENSE_TEMPLATES: dict[str, str]` with 7 embedded templates: `cc0-1.0`, `cc-by-4.0`, `cc-by-sa-4.0`, `mit`, `apache-2.0`, `unlicense`, `pddl`
- [x] **2.3** Implement `build_license_file(license_id: str) -> str` — known SPDX → template text, unknown → descriptive fallback with `choosealicense.com` link, empty/`"restricted"` → generic fallback
- [x] **2.4** Implement `build_schema_report(cfg, csv_delimiter=None, csv_encoding="utf-8-sig") -> list[ColumnSchema]` — iterate CSV files, read headers + up to `_SCHEMA_SAMPLE_SIZE` rows, infer types via `infer_column_type`, disambiguate duplicate column names across files with `::` prefix, skip missing files gracefully
- [x] **2.5** Implement `build_dataset_card(cfg, schema, recipe_content=None) -> str` — build filtered YAML frontmatter dict → `yaml.safe_dump()` with `---` delimiters, append Markdown body with 7 sections (Dataset Description, Raw Data Provenance, Tidy Data Description, Codebook table, Processing Recipe, Citation, License), `"[Not specified]"` placeholders for missing data

## Phase 3 — Wiring

- [x] **3.1** Rename `codebook._infer_type` to public `infer_column_type`, add `"unknown"` to docstring return values; update `codebook.generate()` call site

## Phase 3 — Wiring

- [x] **3.1** Rename `codebook._infer_type` to public `infer_column_type`, add `"unknown"` to docstring return values; update `codebook.generate()` call site
- [x] **3.2** Add compliance orchestration in `uploader.upload()`: read recipe content, call `build_schema_report` → `build_dataset_card` → `build_license_file`, write to `tempfile.mkdtemp()`, upload `README.md` → `LICENSE` → data files, cleanup via `try/finally`
- [x] **3.3** Add progress print lines in `uploader.upload()` for each compliance step (card generation, license generation, per-file upload status)
- [x] **3.4** Add commented-out new `[meta]` fields (`language`, `pretty_name`, `task_categories`, `size_categories`, `citation`, `collection_method`, `csv_delimiter`) to `cli.py` `_INIT_TEMPLATE`

## Phase 4 — Tests

- [x] **4.1** `TestBuildDatasetCard`: full-meta happy path, minimal config, empty schema, recipe inlined, recipe missing (None case), all 7 body sections always present
- [x] **4.2** `TestBuildLicenseFile`: all 7 known SPDX return correct text, unknown SPDX returns descriptive fallback, empty and `"restricted"` return generic fallback
- [x] **4.3** `TestBuildSchemaReport`: single numeric+text CSV, missing values with missing%, no CSV files (empty list), column name collision across two files (`::` prefix), file-not-found skipped silently
- [x] **4.4** `TestColumnSchema`: field types, defaults, dataclass instantiation
- [x] **4.5** `TestUploadCompliance` (mocked integration): `build_schema_report` called first, upload order `README.md` → `LICENSE` → data files, tempdir cleanup on success and exception, exception propagation when schema raises

## Phase 5 — Verification

- [x] **5.1** `pytest tests/ -v` — all 92 tests pass (54 existing + 38 new)
- [x] **5.2** `ruff check src/sofer/ tests/` — no lint errors
- [x] **5.3** `mypy src/sofer/` — no type errors (with `repo_compliance.py` added to coverage)
