# Delta for data-quality

## ADDED Requirements

### Requirement: Text-eligible scope for all P0 checks

All P0 checks (§4) MUST apply only to text-eligible files where `Path.suffix.lower()` is in `TEXT_SUFFIXES = {".csv",".tsv"}` via `is_text_eligible()` in `src/sofer/_formats.py`. Other suffixes (`.xlsx`, `.parquet`, `.jsonl`, `.csv.gz`→`.gz`, no extension) MUST be skipped: no read, no accumulator update, no `QualityResult`, no `ran_checks` increment. Binary-only datasets MUST yield empty `quality_results`.

#### Scenario: Binary formats skipped

- GIVEN `[[file]]` entries for `.xlsx`, `.parquet`, `.jsonl` (ZIP/parquet/jsonl bytes)
- WHEN `QualityValidator.run()` executes
- THEN `quality_results` SHALL be empty and `ran_checks` SHALL be empty

#### Scenario: TSV is eligible

- GIVEN a `.tsv` with a short row (field count mismatch)
- WHEN `QualityValidator.run()` executes
- THEN a `corrupt_records` `fail` finding SHALL be produced

#### Scenario: Case-insensitive and no-extension skipped

- GIVEN files `DATA.XLSX`, `Report.CSV`, `values.TSV`, `README` (no suffix)
- WHEN `QualityValidator.run()` executes
- THEN `DATA.XLSX` and `README` SHALL be skipped; `Report.CSV` and `values.TSV` SHALL be checked

#### Scenario: Binary-only dataset — no cross-file findings

- GIVEN two `.xlsx` files with identical bytes
- WHEN `QualityValidator.run()` executes
- THEN no `duplicates`/`cross_file_types`/`empty_columns`/`corrupt_records` finding SHALL be produced

### Requirement: UTF-8-only enforcement

`ENCODING_FALLBACKS` in `src/sofer/_csv_reader.py` SHALL be `["utf-8-sig","utf-8"]` only; `latin-1`/`cp1252` MUST NOT be retried. `stream_csv` and `_check_encoding_validation` SHALL share this chain. A `.csv` with non-UTF-8 bytes MUST fail; `ValueError` from `stream_csv` remains the safety net for mislabeled `.csv`.

#### Scenario: latin-1 csv fails

- GIVEN a `.csv` encoded `latin-1` containing `José`
- WHEN encoding validation runs
- THEN a `fail` finding naming the file SHALL be appended

## MODIFIED Requirements

### Requirement: QualityValidator.run() — eligibility-gated dispatch

`QualityValidator.run()` SHALL run checks in fixed order without stopping on first failure. After `exists`/`is_dir` guards it MUST skip any entry where `not is_text_eligible(resolved)` (`path.suffix.lower() not in TEXT_SUFFIXES`). Defensive early-returns SHALL exist in `_check_encoding_validation(resolved)` and `_process_file(resolved)` so direct calls on non-eligible paths produce no finding and no `ran_checks` mutation. Only eligible files SHALL contribute to `ran_checks`.

(Previously: `run()` called both helpers unconditionally for every file; no suffix guard; fallbacks included latin-1/cp1252.)

#### Scenario: run() filters before accumulators

- GIVEN `a.csv`, `b.xlsx`, `c.tsv` (all exist)
- WHEN `QualityValidator.run()` executes
- THEN only `a.csv`/`c.tsv` SHALL reach encoding probe and streaming accumulators

#### Scenario: Defensive helper guard

- GIVEN direct call `_check_encoding_validation(Path("data.xlsx"))` or `_process_file(Path("data.parquet"))`
- WHEN the method executes
- THEN it SHALL return with no `QualityResult` and no `ran_checks` change

#### Scenario: ran_checks empty for binary-only dataset

- GIVEN a dataset with only `.xlsx` files
- WHEN `QualityValidator.run()` completes
- THEN `ran_checks` SHALL be empty and `print_summary()` SHALL show `0 failed` (publish not blocked)

#### Scenario: Mixed dataset ran_checks

- GIVEN `data.csv` (valid) plus `extra.xlsx`
- WHEN `QualityValidator.run()` completes
- THEN `ran_checks` SHALL reflect only work done on `data.csv`

### Requirement: Encoding validation — detect non-UTF-8 files in text-eligible inputs

The system MUST verify each text-eligible (`.csv`/`.tsv`, case-insensitive) file is decodable via `["utf-8-sig","utf-8"]` by reading `config.PROBE_CHUNK_BYTES` (8 KB) and trying `chunk.decode(enc)` in order. If any succeeds the check SHALL pass; only if all fail SHALL a `fail` error naming the file be appended. Non-eligible files SHALL be skipped with no finding and no `ran_checks` entry. `latin-1`/`cp1252` SHALL NOT be retried.

(Previously: `utf-8-sig → utf-8 → latin-1 → cp1252` on every file; binary files produced fail findings blocking publish.)

#### Scenario: Valid UTF-8 csv/tsv pass

- GIVEN a valid UTF-8 `.csv` and a valid UTF-8 `.tsv`
- WHEN `_check_encoding_validation` runs on each
- THEN no error SHALL be appended for either

#### Scenario: Non-UTF-8 csv fails

- GIVEN a `.csv` whose 8 KB chunk fails both `utf-8-sig` and `utf-8`
- WHEN `_check_encoding_validation` runs
- THEN a `fail` error naming the file SHALL be appended

#### Scenario: xlsx skipped regardless of 8 KB content

- GIVEN a `.xlsx` whose first 8 KB happens to be valid UTF-8 (or not)
- WHEN `_check_encoding_validation` runs via `run()` or direct call
- THEN no error SHALL be appended and `ran_checks` SHALL not gain `encoding_validation`
