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

### Requirement: CSV→Parquet conversion preserved in output dir (PRP-02) — Universal (Modified 2026-08-29, convert-all-formats-parquet)

`prepare` SHALL convert every eligible entry among `.csv/.tsv/.xlsx/.jsonl` to Parquet and write the result into the output directory at the **normalized** remote-relative path (extension replaced with `.parquet`; for `.xlsx` with N sheets, N files at `stem__{sanitized}.parquet`). Eligibility: NOT `recursive`, suffix in convertible set, `convert_to_parquet != false` (alias `upload_as_csv` honored for csv with deprecation warning), `local` exists. `.parquet` entries SHALL be passthrough. `prepare._check_local_overwrite` and `_validate_case_fold_collisions` (via `_mirror`) MUST scan all convertible suffixes on normalized keys (`normalize_parquet_remote(...).lower()`), not just `.csv`. Conversion MUST use `config.PARQUET_COMPRESSION` and `config.PARQUET_ROW_GROUP_SIZE`; no hardcoded compression/row-group literals.

(Previously: only `.csv` eligible; `.tsv/.xlsx/.jsonl` staged as-is via `copy_to_mirror`; overwrite/collision gates scanned only `.csv`.)

#### Scenario: Converted parquets mirror normalized remote layout
- GIVEN entries `remote="data/PROV/train.csv"` and `remote="data/DPTO/train.TSV"`
- WHEN `prepare` completes
- THEN `data/prov/train.parquet` and `data/dpto/train.parquet` SHALL exist in output

#### Scenario: XLSX multi-sheet expanded
- GIVEN `remote="Report.XLSX"` with sheets `Ventas`, `Costos`
- WHEN `prepare` completes
- THEN `report__ventas.parquet` and `report__costos.parquet` SHALL exist (flat `__`)

#### Scenario: convert_to_parquet=false keeps original suffix
- GIVEN `[[file]] remote="raw.xlsx" convert_to_parquet=false`
- WHEN `prepare` completes
- THEN no Parquet SHALL be generated for that entry and `raw.xlsx` SHALL be staged at its declared remote

#### Scenario: upload_as_csv alias still honored for csv
- GIVEN `[[file]] remote="raw.csv" upload_as_csv=true`
- WHEN `prepare` completes
- THEN deprecation warning SHALL be printed, no Parquet SHALL be generated, and `raw.csv` SHALL be staged

#### Scenario: Conversion failure falls back to original for any format
- GIVEN `bad.tsv` that fails to parse
- WHEN `prepare` runs the conversion loop
- THEN warning SHALL be printed naming `bad.tsv` and original `bad.tsv` SHALL be staged at its remote

#### Scenario: Overwrite protection covers all convertible suffixes normalized
- GIVEN `data/prov/train.parquet` already exists in output from prior run and a `train.tsv` entry maps to same normalized key
- WHEN `sofer prepare` executes without `--force`
- THEN error naming the existing `data/prov/train.parquet` SHALL be printed and exit SHALL be 1

#### Scenario: Case-fold collision on normalized remotes refused before write
- GIVEN entries `Data/Prov/Train.CSV` and `data/prov/train.tsv` normalizing to same `data/prov/train.parquet`
- WHEN `prepare` validates
- THEN hard error naming both remotes SHALL be emitted and exit SHALL be 1 before any staging write

#### Scenario: Legacy CSV scenarios preserved

- GIVEN `[[file]]` entries with `remote = "data/PROV/train.csv"` and `remote = "data/DPTO/train.csv"` (case-preserving legacy)
- WHEN `prepare` completes
- THEN `data/prov/train.parquet` SHALL exist (normalized lowercase)

#### Scenario: upload_as_csv entries keep their CSV (legacy)

- GIVEN a `[[file]]` entry with `upload_as_csv = true`
- WHEN `prepare` completes
- THEN no Parquet SHALL be generated for that entry
- AND the original CSV SHALL be staged at its remote path

#### Scenario: Conversion failure falls back to CSV (legacy)

- GIVEN a CSV entry that fails to parse
- WHEN `prepare` runs the conversion loop
- THEN a warning SHALL be printed
- AND the original CSV SHALL be staged at its remote path instead

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
