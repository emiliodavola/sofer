# Delta for parquet-conversion

> Change `2026-09-14-fix-prepare-csv-config-tier` (issue #181). Canonical target:
> `openspec/specs/parquet-conversion/spec.md` §13, requirement **PC-U01**.
> Precedence clause lives here (not in `tool-config`) because this file owns the
> reader table that names the caller; `tool-config`'s **TC-04** note is amended to
> point at it, so both canonical texts read true after the archive-time sync.

## MODIFIED Requirements

### Requirement: Universal File-to-Parquet Conversion (PC-U01)

The system MUST convert every `[[file]]` with suffix `.csv/.tsv/.xlsx/.jsonl` to Parquet unless `convert_to_parquet=false`; `.parquet` MUST be passthrough and `recursive` entries SHALL be skipped. Readers SHALL be:

| Suffix | Reader |
|--------|--------|
| `.csv` | `pyarrow.csv.read_csv` using the dataset's declared `[meta] csv_delimiter`/`csv_encoding` when declared; otherwise sniffing `config.SNIFF_DELIMITERS` with `config.CSV_ENCODING` |
| `.tsv` | `pyarrow.csv.read_csv` with `delimiter="\t"` (hardcoded) |
| `.xlsx` | `openpyxl` `read_only,data_only`, all `wb.sheetnames` → `pa.Table` per sheet |
| `.jsonl` | `pyarrow.json.read_json` with `json`+`pa.Table.from_pylist` fallback |
| `.parquet` | Passthrough |

For `.csv`, the resolution order SHALL be: (1) the dataset-declared `[meta] csv_delimiter`/`csv_encoding`, which WINS; (2) where the dataset declares no dialect, the existing sniff + tool-wide `config.CSV_ENCODING` behaviour, unchanged. "Declared" MUST be observable independently of the value, so a dataset declaring `;` remains distinguishable from one declaring nothing. The declared `csv_encoding` MUST actually govern the read — the reader SHALL NOT read raw bytes and ignore it. When the declared delimiter differs from the delimiter the sniff would have chosen, conversion SHALL emit a non-blocking warning naming BOTH values and SHALL still honour the declared one; it SHALL NOT fail. Conversion reader logic SHALL have exactly one home.

Writer MUST use `config.PARQUET_COMPRESSION`/`config.PARQUET_ROW_GROUP_SIZE`, cast null-col to string, warn at `config.PARQUET_SHARD_WARNING_MB`. Per-file failure SHALL warn and stage original.

(Previously: the `.csv` row resolved tool-wide only — sniff of `config.SNIFF_DELIMITERS` with `config.CSV_ENCODING` — and `csv_encoding` was never consulted.)

#### Scenario: CSV sniff when nothing is declared
- GIVEN `a.csv` with `;` delimiter and a dataset TOML declaring no dialect
- WHEN the dispatcher runs
- THEN the reader SHALL sniff `;` and write normalized `a.parquet`

#### Scenario: Declared delimiter outside the sniff set wins (mis-split catcher)
- GIVEN `a.csv` is `|`-separated and `[meta] csv_delimiter = "|"` is declared (`|` ∉ `config.SNIFF_DELIMITERS`)
- WHEN the dispatcher runs end-to-end
- THEN `a.parquet` SHALL hold the file's true column count and SHALL NOT collapse the header into one column
- AND the parity check SHALL be structurally unable to agree with a wrong delimiter

#### Scenario: Declared encoding is honoured
- GIVEN `a.csv` is not UTF-8 and `[meta] csv_encoding` declares its actual encoding
- WHEN the dispatcher runs
- THEN `a.parquet` SHALL be written with correctly decoded values and the original CSV SHALL NOT be staged

#### Scenario: Declaration disagrees with the file — warn, keep declared
- GIVEN `a.csv` is `,`-separated and `[meta] csv_delimiter = ";"` is declared
- WHEN the dispatcher runs
- THEN conversion SHALL still use `;` and SHALL print one non-blocking warning naming both `,` and `;`

#### Scenario: No declared dialect is byte-identical to today
- GIVEN a dataset TOML declaring no `csv_delimiter`/`csv_encoding`
- WHEN conversion runs
- THEN the produced Parquet SHALL be byte-identical to the pre-change output for the same input

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

## ADDED Requirements

### Requirement: Single CSV conversion reader (PC-U06)

`src/sofer/prepare.py` SHALL NOT contain a second copy of the CSV→Parquet conversion cluster (the five helper/reader copies plus `_convert_to_parquet`); no module under `src/sofer/` or `tests/` SHALL import those helpers, and the surviving reader logic SHALL have exactly one home in `src/sofer/_converters.py` (AGENTS.md rule 4). Removal SHALL delete code only and SHALL NOT weaken any coverage floor.

#### Scenario: The duplicated cluster is gone and unreferenced
- GIVEN the branch after the fix
- WHEN `src/sofer/prepare.py` and both `src/` and `tests/` are inspected
- THEN the cluster SHALL be absent from `prepare.py` and no `src/`- or `tests/`-module SHALL reference its symbols

#### Scenario: Single home is exercised
- GIVEN a declared-dialect CSV conversion
- WHEN the conversion runs
- THEN the same `_converters.py` entry point SHALL serve CLI `prepare` and library callers, with no parallel reader left to drift

## Evidence (AGENTS.md rule 6)

`src/sofer/prepare.py` is NOT in the four-module COV-06 100.00% set; no existing floor is weakened by this delta.

| Scenario | Test file |
|----------|-----------|
| CSV sniff when nothing is declared | `tests/test_parquet_conversion.py` |
| Declared delimiter outside the sniff set wins | `tests/test_parquet_conversion.py` (NEW — no end-to-end delimiter test exists today; the only one asserts `data.parquet` exists and `data.csv` does not, which a one-column Parquet satisfies) |
| Declared encoding is honoured | `tests/test_parquet_conversion.py` (NEW) + `tests/test_converters.py` (unit) |
| Declaration disagrees — warn, keep declared | `tests/test_converters.py` |
| No declared dialect byte-identical | `tests/test_parquet_conversion.py` |
| TSV hardcoded tab / JSONL fallback / Parquet passthrough | `tests/test_parquet_conversion.py` (existing, preserved) |
| Cluster gone and unreferenced | `tests/test_prepare.py` (structural; weaker evidence than behavioural — import/absence assertion, flagged) |
| Single home exercised | `tests/test_converters.py` |

## Delivery note

Maintainer explicitly authorized `size:exception` up to **1500 changed lines** (review budget 1500) so the ~249-line `prepare.py:81-329` deletion rides with the fix. The 43 call sites (27 `tests/test_parquet_conversion.py`, 16 `tests/test_prepare.py`) are retargeted to the `_converters` seam or deleted as already covered by `tests/test_converters.py`.
