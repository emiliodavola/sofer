# Delta for parquet-conversion

## ADDED Requirements

### Requirement: Universal File-to-Parquet Conversion (PC-U01)

The system MUST convert every `[[file]]` with suffix `.csv/.tsv/.xlsx/.jsonl` to Parquet unless `convert_to_parquet=false`; `.parquet` MUST be passthrough and `recursive` entries SHALL be skipped. Readers SHALL be:

| Suffix | Reader |
|--------|--------|
| `.csv` | `pyarrow.csv.read_csv` sniffing `config.SNIFF_DELIMITERS` with `config.CSV_ENCODING` |
| `.tsv` | `pyarrow.csv.read_csv` with `delimiter="\t"` (hardcoded) |
| `.xlsx` | `openpyxl` `read_only,data_only`, all `wb.sheetnames` → `pa.Table` per sheet |
| `.jsonl` | `pyarrow.json.read_json` with `json`+`pa.Table.from_pylist` fallback |
| `.parquet` | Passthrough |

Writer MUST use `config.PARQUET_COMPRESSION`/`config.PARQUET_ROW_GROUP_SIZE`, cast null-col to string, warn at `config.PARQUET_SHARD_WARNING_MB`. Per-file failure SHALL warn and stage original.

#### Scenario: CSV sniff
- GIVEN `a.csv` with `;` delimiter
- WHEN dispatcher runs
- THEN `pyarrow.csv` SHALL sniff `;` and write normalized `a.parquet`

#### Scenario: TSV hardcoded tab
- GIVEN `b.tsv` tab-separated
- WHEN dispatcher runs
- THEN reader SHALL use `"\t"` and produce `b.parquet`

#### Scenario: JSONL fallback
- GIVEN `c.jsonl` with sparse keys where `pyarrow.json` raises
- WHEN fallback runs
- THEN `json`+`pa.Table.from_pylist` SHALL produce `c.parquet`

#### Scenario: Parquet passthrough and recursive skip
- GIVEN `d.parquet` and `recursive` dir entry
- WHEN pipeline runs
- THEN both SHALL be staged without conversion

### Requirement: Remote Normalization (PC-U02)

`normalize_parquet_remote(s)` MUST: lowercase, NFKD→ASCII strip, spaces→`_`, `[^a-z0-9_./-]`→`_`, collapse `__+`, preserve lowercased dirs. Case-fold collision on `lower(normalized)` MUST error naming both remotes. Values MUST be read from `config.py`/`[tool.sofer]`, never hardcoded.

#### Scenario: Accented and spaced file
- GIVEN `DATA GÖT Año.XLSX`
- WHEN normalized
- THEN result SHALL be `data_got_ano.parquet`

#### Scenario: Case-fold collision
- GIVEN `data/report.XLSX` and `DATA/report.xlsx` → same `data/report.parquet`
- WHEN `_validate_case_fold_collisions` runs
- THEN error naming both SHALL exit 1 before write

### Requirement: Excel Multi-Sheet Handling (PC-U03)

For `.xlsx`: 1 sheet→`stem.parquet`; N sheets→N files `stem__{sanitized}.parquet` (flat `__`). Sanitizer SHALL reuse normalization rules. Dupes MUST dedup `_{n}`; empty sheet with header SHALL still produce Parquet with 0 rows.

#### Scenario: Single vs multi-sheet
- GIVEN `report.xlsx` with 1 sheet vs 2 sheets `Ventas`,`Costos`
- WHEN converted
- THEN SHALL produce `report.parquet` vs `report__ventas.parquet`+`report__costos.parquet`

#### Scenario: Dedup and empty
- GIVEN sheets `A B`/`A-B` both `a_b` and an empty header-only sheet
- WHEN converted
- THEN SHALL produce `stem__a_b.parquet`+`stem__a_b_2.parquet` and header-only Parquet with `num_rows=0`

### Requirement: Opt-Out Flag (PC-U04)

`FileEntry.convert_to_parquet: bool` SHALL default `true`. `upload_as_csv` SHALL remain deprecated alias ONLY for `.csv`: `upload_as_csv=true` → `convert_to_parquet=false` with deprecation warning. Explicit `convert_to_parquet` takes precedence. Non-csv `upload_as_csv=true` SHALL be ignored with warning.

#### Scenario: Default converts
- GIVEN `[[file]] remote="a.csv"` without flags
- WHEN parsed
- THEN `convert_to_parquet=true` and output `a.parquet` SHALL exist

#### Scenario: Explicit opt-out
- GIVEN `remote="b.xlsx" convert_to_parquet=false`
- WHEN pipeline runs
- THEN no conversion SHALL occur and remote stays `b.xlsx`

#### Scenario: Alias honored for csv
- GIVEN `remote="c.csv" upload_as_csv=true`
- WHEN parsed
- THEN `convert_to_parquet=false` with deprecation warning and `c.csv` staged as-is

### Requirement: Breaking Change Documentation (PC-U05)

This is 0.x minor breaking change. Docs MUST state `tsv/xlsx/jsonl` previously staged as-is, now normalized `.parquet` (xlsx→N). Migration SHALL be `convert_to_parquet=false` per entry. Collision errors MUST name both remotes.

#### Scenario: Migration documented
- GIVEN `report.xlsx` previously expected as `report.xlsx`
- WHEN docs consulted
- THEN migration `convert_to_parquet=false` to keep `report.xlsx` SHALL be described

## MODIFIED Requirements

### Requirement: CSV→Parquet Conversion Pipeline (Previously: CSV-only `_convert_to_parquet` + conversion loop)

System SHALL convert all eligible `.csv/.tsv/.xlsx/.jsonl` via `src/sofer/_converters.py` dispatcher and shared writer, preserving normalized dir structure. Parity: CSV/TSV row/col/name+value-altered; XLSX row/col/name; JSONL key-union+row count. Overwrite/collision SHALL use normalized keys. `keep_csv` SHALL remain CSV-only.

(Previously: only `.csv` converted; others via `copy_to_mirror`; parity CSV-only; gates scanned only `.csv`.)

#### Scenario: Mixed universal conversion
- GIVEN `a.csv`, `b.tsv`, `c.xlsx` (2 sheets), `d.jsonl`, `e.parquet`
- WHEN `prepare` runs
- THEN outputs SHALL be `a.parquet`, `b.parquet`, `c__s1.parquet`, `c__s2.parquet`, `d.parquet`, `e.parquet`

#### Scenario: keep_csv stays CSV-only
- GIVEN `a.csv` and `b.xlsx` with `--keep-csv`
- WHEN publish stages
- THEN `a.csv` SHALL be kept alongside `a.parquet`; `b.xlsx` SHALL NOT
