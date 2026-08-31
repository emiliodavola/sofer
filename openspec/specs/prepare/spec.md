# Prepare Specification

## Purpose

Local, offline generation of every artifact that makes up a dataset package:
CSV→Parquet conversion, Dataset Card (`README.md`), `LICENSE`, codebooks, and
quality/schema reports. `prepare` never contacts the network and never requires
Hugging Face credentials, so artifacts can be inspected and edited before they
are published.

## Requirements

### Requirement: Local-only generation, zero network calls (PRP-01)

`prepare` SHALL generate all artifacts entirely on the local machine. The command
MUST NOT make any network calls, MUST NOT require Hugging Face authentication,
and MUST succeed without any `HF_TOKEN` or Hub access.

#### Scenario: Full run produces artifacts offline

- GIVEN a valid TOML config with CSV file entries
- WHEN `sofer prepare dataset.toml` executes with no network access
- THEN all artifacts SHALL be generated in the output directory
- AND no network request SHALL be made

#### Scenario: No credentials required

- GIVEN no `HF_TOKEN` set and no Hub connectivity
- WHEN `sofer prepare dataset.toml` executes
- THEN generation SHALL complete successfully
- AND the exit code SHALL be 0

---

### Requirement: CSV→Parquet conversion preserved in output dir (PRP-02) — Universal (Modified 2026-08-30, fix-prepare-multisheet-xlsx-copy)

`prepare` SHALL convert every eligible `.csv/.tsv/.xlsx/.jsonl` entry to Parquet at the normalized remote (`normalize_parquet_remote(parquet_remote_for(remote))`). Eligible: NOT `recursive`, suffix in convertible set, `convert_to_parquet != false` (`upload_as_csv` alias for csv with deprecation warning), `local` exists; `.parquet` SHALL be passthrough. Converted keys use normalized form: `__+` → `_` collapses `stem__sheet` → `stem_sheet`, so multisheet XLSX with N sheets SHALL produce N files at `stem_{sanitized}.parquet` (single `_`). Guards (`is_converted` staging check, `_check_local_overwrite`, `_validate_case_fold_collisions`, `_assert_cross_file_schema`, `expanded_planned_remotes` fallback) SHALL match **both** `__` and `_` sheet suffixes. When any XLSX sheet converts, original `.xlsx` SHALL NOT be staged; `build/` SHALL contain only normalized `.parquet` per sheet. Single-sheet XLSX SHALL produce single `stem.parquet` (key == `norm_key`). Overwrite/collision gates MUST scan normalized keys. Conversion MUST use `config.PARQUET_COMPRESSION`/`PARQUET_ROW_GROUP_SIZE`; no hardcoded literals.

(Previously: guards checked `__` only; normalized keys collapse to `_`, so `prepare.py:848/603/364` missed multisheet sheets and leaked the workbook into `build/`.)

#### Scenario: Converted parquets mirror normalized remote layout

- GIVEN `data/PROV/train.csv` and `data/DPTO/train.TSV`
- WHEN `prepare` completes
- THEN `data/prov/train.parquet` and `data/dpto/train.parquet` SHALL exist

#### Scenario: XLSX multi-sheet expanded (normalized)

- GIVEN `Report.XLSX` with sheets `Ventas`, `Costos`
- WHEN `prepare` completes
- THEN `report_ventas.parquet` and `report_costos.parquet` SHALL exist (single `_`)
- AND `report.xlsx` SHALL NOT exist in output

#### Scenario: Multisheet stages only parquet — no source leak

- GIVEN `DATA_GOT_ALL.xlsx` with sheets `aristas`/`nodos`
- WHEN `sofer prepare` into clean `build/` completes
- THEN `build/` SHALL contain `data_got_all_aristas.parquet` and `data_got_all_nodos.parquet`
- AND `build/` SHALL contain no `*.xlsx`

#### Scenario: Single-sheet XLSX unchanged

- GIVEN `dataset.xlsx` with one sheet
- WHEN `prepare` completes
- THEN exactly one `dataset.parquet` SHALL exist
- AND no `dataset_*.parquet` sheet file SHALL exist

#### Scenario: convert_to_parquet=false keeps original suffix

- GIVEN `raw.xlsx` with `convert_to_parquet=false`
- WHEN `prepare` completes
- THEN no Parquet SHALL be generated and `raw.xlsx` SHALL be staged

#### Scenario: upload_as_csv alias still honored for csv

- GIVEN `raw.csv` with `upload_as_csv=true`
- WHEN `prepare` completes
- THEN deprecation warning SHALL be printed and `raw.csv` SHALL be staged

#### Scenario: Conversion failure falls back to original for any format

- GIVEN `bad.tsv` that fails to parse
- WHEN `prepare` runs the conversion loop
- THEN warning naming `bad.tsv` SHALL be printed and original `bad.tsv` SHALL be staged

#### Scenario: Overwrite protection covers all suffixes normalized (XLSX fallback)

- GIVEN `data/prov/train.parquet` exists and `train.tsv` maps to same normalized key
- WHEN `sofer prepare` without `--force` runs
- THEN error naming `data/prov/train.parquet` SHALL be printed and exit SHALL be 1
- AND GIVEN `report_ventas.parquet` (single `_`) exists from prior run
- WHEN new `Report.XLSX` covering that sheet runs without `--force`
- THEN guard SHALL detect via `_` fallback glob and refuse with exit 1; with `--force` it SHALL overwrite

#### Scenario: Case-fold collision on normalized remotes refused before write

- GIVEN `Data/Prov/Train.CSV` and `data/prov/train.tsv` both normalize to `data/prov/train.parquet`
- WHEN `prepare` validates
- THEN error naming both remotes SHALL be emitted and exit SHALL be 1 before write

#### Scenario: Cross-file schema grouping handles both underscore forms

- GIVEN converted keys include `data_got_all_aristas.parquet` (single `_`)
- WHEN `_assert_cross_file_schema` groups sheets for `DATA_GOT_ALL.xlsx`
- THEN it SHALL match via both `stem__*` and `stem_*` (excluding `norm_key`) so grouping works regardless of normalization

#### Scenario: Legacy CSV scenarios preserved

- GIVEN `data/PROV/train.csv` and `data/DPTO/train.csv`
- WHEN `prepare` completes
- THEN `data/prov/train.parquet` SHALL exist (normalized lowercase)

#### Scenario: upload_as_csv entries keep their CSV (legacy)

- GIVEN entry with `upload_as_csv=true`
- WHEN `prepare` completes
- THEN no Parquet SHALL be generated and original CSV SHALL be staged

#### Scenario: Conversion failure falls back to CSV (legacy)

- GIVEN CSV entry that fails to parse
- WHEN conversion loop runs
- THEN warning SHALL be printed and original CSV SHALL be staged

### Requirement: Cross-file schema and parity for all formats (PRP-02a) — Added 2026-08-29

`prepare` SHALL run cross-file schema assertion and per-format parity on all converted parquets (`.csv/.tsv/.xlsx/.jsonl`). CSV/TSV parity checks row/col/name and soft value-altered warning; XLSX checks row/col/name per sheet; JSONL checks key-union vs column names and row count. Thresholds for sample sizes and shard warnings SHALL be read from `config.py` (`SCHEMA_SAMPLE_SIZE`, `PARQUET_SHARD_WARNING_MB`).

(Previously: cross-file schema and parity covered only converted `.csv`.)

#### Scenario: Cross-file grouping includes tsv
- GIVEN `a.csv` and `b.tsv` with disjoint column sets now both converted
- WHEN cross-file schema assertion runs
- THEN grouping SHALL include both parquets without spurious collision from hardcoded csv-only filter

### Requirement: Normalization precedes overwrite and collision gates (PRP-02b) — Added 2026-08-29

The system MUST normalize every convertible remote via `normalize_parquet_remote` BEFORE checking `_check_local_overwrite` and `_validate_case_fold_collisions`. Raw `entry.remote` values SHALL NOT be compared directly for convertible files.

#### Scenario: Normalized collision not missed due to accents
- GIVEN remotes `DATA GÖT Año.csv` and `data_got_ano.tsv` both normalizing to `data_got_ano.parquet`
- WHEN validation runs
- THEN collision error SHALL be emitted naming both originals

---

### Requirement: Dataset Card and LICENSE generated (PRP-03)

`prepare` SHALL generate `README.md` (Dataset Card, via `build_dataset_card`)
and `LICENSE` (via `build_license_file`) at the root of the output directory.
When `cfg.readme` points to an existing file, its content SHALL be used instead
of the generated card.

#### Scenario: Card and license written to output root

- GIVEN a config with `license = "cc0-1.0"` and CSV entries
- WHEN `prepare` completes
- THEN `README.md` SHALL exist at the output root
- AND `LICENSE` SHALL exist at the output root
- AND the card SHALL embed the schema codebook table

#### Scenario: Custom README overrides generation

- GIVEN `cfg.readme` pointing to an existing markdown file
- WHEN `prepare` completes
- THEN the output `README.md` SHALL equal the custom file's content

#### Scenario: No license declared still succeeds

- GIVEN `license = ""`
- WHEN `prepare` completes
- THEN `LICENSE` SHALL contain the fallback message
- AND the exit code SHALL be 0

---

### Requirement: Codebooks generated directly into output (PRP-04)

With `--all-files`, `prepare` SHALL generate per-file codebooks and write them
under `codebooks/` in the output directory mirroring their relative paths, plus
the root `codebook.md` index. Codebooks SHALL be written DIRECTLY into the
output directory — the shared `cache/codebooks/` directory SHALL NOT be
mutated by `prepare`. Without `--all-files`, no codebooks SHALL be generated.

#### Scenario: Batch codebooks staged in output

- GIVEN `--all-files` and codebooks for `data/DPTO.csv` and `data/Labels/etiquetas_a.csv`
- WHEN `prepare --all-files --output ./build/` completes
- THEN `build/codebooks/DPTO.md` SHALL exist
- AND `build/codebooks/Labels/etiquetas_a.md` SHALL exist
- AND `build/codebook.md` SHALL exist
- AND `cache/codebooks/` SHALL NOT be modified (Option B — no cache mutation)

#### Scenario: No codebooks requested

- GIVEN `prepare` without `--all-files`
- WHEN the command completes
- THEN no `codebooks/` directory SHALL be created
- AND an advisory to run `sofer codebook --all-files` SHALL be printed

---

### Requirement: Quality checks run unless --no-checks (PRP-05)

`prepare` SHALL run the structural checks (`DatasetValidator`) and quality
checks (`QualityValidator`) and print their results. `--no-checks` SHALL skip
both. Failing checks SHALL be reported but SHALL NOT block generation — the
blocking gate is enforced by `publish`.

#### Scenario: Checks run by default

- GIVEN a config whose file violates a column check
- WHEN `sofer prepare dataset.toml` executes
- THEN the check failures SHALL appear in the printed report
- AND generation SHALL still complete

#### Scenario: --no-checks skips validation

- GIVEN `sofer prepare dataset.toml --no-checks`
- WHEN the command executes
- THEN no check report SHALL be printed
- AND all artifacts SHALL still be generated

---

### Requirement: --output controls destination, default from dataset.toml (PRP-06)

`--output <dir>` SHALL select the artifact destination directory, overriding
the per-dataset default for that run. When omitted, the destination SHALL be
`<config-dir>/<build_dir>` where `build_dir` comes from `[dataset] build_dir`
in `dataset.toml` (default `"build"`).

#### Scenario: Custom output directory overrides build_dir

- GIVEN `sofer prepare dataset.toml --output ./staging/`
- WHEN the command executes
- THEN every artifact SHALL be written under `./staging/`
- AND nothing SHALL be written to `./build/`

#### Scenario: Default output is build_dir from TOML

- GIVEN no `--output` and `[dataset] build_dir = "build"` in `dataset.toml`
- WHEN `sofer prepare dataset.toml` executes
- THEN artifacts SHALL be written under `<config-dir>/build/`

#### Scenario: build_dir omitted in TOML defaults to build

- GIVEN a `dataset.toml` without a `build_dir` key
- WHEN `sofer prepare dataset.toml` executes
- THEN artifacts SHALL be written under `<config-dir>/build/`

---

### Requirement: --verify loads generated package locally (PRP-08)

`prepare --verify` SHALL run `datasets.load_dataset()` against the generated
output directory and print a verification report with PASSED/FAILED status.
Verification failure SHALL be reported but SHALL NOT block generation.

#### Scenario: Successful local verification

- GIVEN `sofer prepare dataset.toml --verify`
- WHEN generation completes
- THEN `load_dataset()` SHALL be invoked against the output directory
- AND the report SHALL state PASSED when loading succeeds

#### Scenario: Failed local verification is reported

- GIVEN the generated package cannot be loaded
- WHEN `prepare --verify` completes
- THEN the report SHALL state FAILED
- AND the exit code SHALL still be 0

---

### Requirement: --force overwrites existing generated files (PRP-07)

When a generated artifact already exists in the output directory, `prepare`
SHALL refuse to overwrite it unless `--force` is given. Without `--force`,
`prepare` SHALL report the conflicting files and exit 1 without modifying them.
With `--force`, existing artifacts SHALL be regenerated and overwritten
silently.

#### Scenario: Existing artifacts block regeneration

- GIVEN `data/PROV/train.parquet` already exists from a prior run
- WHEN `sofer prepare dataset.toml` executes without `--force`
- THEN an error naming the existing file SHALL be printed
- AND the exit code SHALL be 1
- AND the existing file SHALL be unchanged

#### Scenario: --force regenerates everything

- GIVEN stale artifacts exist in the output directory
- WHEN `sofer prepare dataset.toml --force` executes
- THEN all artifacts SHALL be overwritten
- AND the exit code SHALL be 0

---

### Requirement: Orphan pruning on force prepare (PRP-09)

`prepare(force=True)` MUST prune orphan files under `output_dir` after staging (converted parquets, codebooks). The allowlist MUST be `allowed_output_remotes = expanded_planned_remotes(cfg, keep_csv, output_dir) ∪ {README.md, LICENSE, codebook.md, codebooks/**} ∪ keep_csv CSV remotes`. `expanded_planned_remotes` MUST reuse `sanitize_sheet_name`/`normalize_parquet_remote` with dual `__`/`_` guard identical to `prepare.py:615-622`, so single-underscore sheets (e.g., `DATA_GOT_ALL.xlsx` → `data_got_all_aristas.parquet`, `data_got_all_nodos.parquet`) are recognized as owned, not orphan. Pruning MUST be idempotent and MUST NOT run when `force` is false.

#### Scenario: Single-underscore orphan deleted on force

- GIVEN `build/` contains `data_got_all_aristas.parquet` but TOML no longer declares that sheet
- WHEN `prepare(force=True)` completes
- THEN that orphan file SHALL be removed and only `expanded_planned_remotes` members SHALL remain

#### Scenario: Stale file from removed TOML entry pruned

- GIVEN a prior `[[file]]` entry was removed leaving `old.parquet` in `build/`
- WHEN `prepare(force=True)` completes
- THEN `old.parquet` SHALL be removed

#### Scenario: Compliance auto-generated files retained

- GIVEN `build/` contains `README.md`, `LICENSE`, `codebook.md`, `codebooks/a.md`
- WHEN `prepare(force=True)` completes
- THEN all compliance files SHALL remain (not treated as orphans)

#### Scenario: keep_csv originals retained

- GIVEN `keep_csv=true` and `build/` contains `data/foo.csv` alongside `data/foo.parquet`
- WHEN `prepare(force=True)` completes
- THEN `data/foo.csv` SHALL remain

#### Scenario: Idempotent second force run

- GIVEN `prepare(force=True)` already pruned orphans
- WHEN `prepare(force=True)` runs again without config change
- THEN no further files SHALL be deleted and exit SHALL be 0

#### Scenario: Non-force run does not prune

- GIVEN an orphan `stale.parquet` exists in `build/`
- WHEN `prepare` runs without `--force`
- THEN `stale.parquet` SHALL remain and orphan scan SHALL not execute

---

### Requirement: Prepare inherits multisheet codebook N-files (PRP-10)

When `prepare` invokes codebook generation with `--all-files` (via `generate_all(..., output_dir=build_dir)`), it MUST inherit CB-R09's N-files behavior: a multisheet `.xlsx` SHALL produce N codebooks `build/codebooks/<stem>__<sanitized>.md` (single sheet → `stem.md`), reusing `sanitize_sheet_name`/`seen` dedup identical to Parquet conversion. Staged Parquets already per-sheet; codebooks SHALL mirror them 1:1 (`sheet → stem_sheet.parquet → stem__sheet.md`). `prepare` SHALL NOT reimplement sanitization; it SHALL delegate to `codebook.generate_all`.

#### Scenario: PRP-10.01 multisheet XLSX yields N Parquets and N codebooks in build

- GIVEN `DATA_GOT_ALL.xlsx` with sheets `aristas` and `nodos`
- WHEN `sofer prepare --all-files` completes
- THEN `build/` SHALL contain `data_got_all_aristas.parquet` and `data_got_all_nodos.parquet`
- AND `build/codebooks/DATA_GOT_ALL__aristas.md` and `build/codebooks/DATA_GOT_ALL__nodos.md` SHALL both exist (or normalized `__` stems)

#### Scenario: PRP-10.02 single-sheet unchanged

- GIVEN `dataset.xlsx` with one sheet
- WHEN `prepare --all-files` completes
- THEN exactly one `build/<stem>.parquet` and one `build/codebooks/<stem>.md` SHALL exist

#### Scenario: PRP-10.03 no extra conversion logic in prepare

- GIVEN a multisheet XLSX
- WHEN `prepare` stages codebooks
- THEN no XLSX sheet iteration SHALL exist in `prepare.py` beyond the `generate_all` delegation (provenance stays in `codebook.py`/`_converters.py`)
