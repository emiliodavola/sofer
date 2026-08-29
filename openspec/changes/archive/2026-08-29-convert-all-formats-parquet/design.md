# Design: convert-all-formats-parquet

## Technical Approach

Universal `csv/tsv/xlsx/jsonl`->normalized `.parquet` (`.parquet` passthrough). New `_converters.py` dispatcher + `_write_parquet_table` centralizes `PARQUET_COMPRESSION`/`ROW_GROUP_SIZE`, null-cast, shard warning. Normalize via `normalize_parquet_remote` before gates. Excel multi-sheet -> N `stem__{sheet}.parquet`. `prepare` orchestrates; `_mirror.planned_remotes` is single source. Covers PC-U01..U05, PRP-02/02a/02b, PUB-01/09, RC-Universal.

## Architecture Decisions

| Decision | Choice | Alternatives | Rationale |
|---|---|---|---|
| Converter location | New `src/sofer/_converters.py` | Extend `prepare.py` inline | `prepare.py` 811 LoC; rule 10 one-module-per-concern; testable without orchestrator |
| Normalizer home | Define in `_converters`, re-export from `_mirror` | Duplicate; only in `_mirror` | Single source; DAG `prepare->_converters`, `prepare->_mirror->_converters` avoids cycle; `_converters` never imports `prepare`/`_mirror` |
| Sheet separator | Flat `__` (`stem__sheet.parquet`) | Nested `stem/sheet.parquet` | Avoids `detect_splits` confusion; `planned_remotes` stays file list |
| TSV delimiter | Hardcoded `"\t"` | Sniff `SNIFF_DELIMITERS` | TSV is tab by definition; sniff mis-detects quoted tabs |
| JSONL reader | `pyarrow.json` then `json`+`from_pylist` fallback | Single engine | Fast path + sparse-schema fallback |
| Flag | `convert_to_parquet=True` + deprecated `upload_as_csv` (csv-only) | `keep_original`, per-format flags | Positive boolean matches naming; single flag; alias preserves compat |
| Publish gate | Delegate `_repo_diff_summary`/`_copy_package` to `planned_remotes` | Duplicated `endswith` gate | One definition (PUB-09); diff and staging cannot diverge |

## Data Flow

```
files -> normalized overwrite/collision check -> conversion loop (CONVERTIBLE={.csv,.tsv,.xlsx,.jsonl}, !recursive, convert_to_parquet, exists)
  -> convert_file_to_parquet(local, staging_dir/idx) [csv: sniff, tsv: \t, xlsx: openpyxl all sheets, jsonl: pyarrow.json|fallback]
  -> converted: dict[normalize(parquet_remote_for(remote)) -> (path,local,orig)]  (xlsx N->N)
  -> per-format parity -> cross-file schema -> _check_large_values -> copy_to_mirror(converted)
  -> schema report/card via staged normalized keys -> mirror non-converted/recursive/keep_csv -> codebooks
```

Gate: `.csv|.parquet` -> convertible set. `tmpdir/idx` isolates same-stem after normalization. Parity: CSV/TSV row/col/name+value; XLSX row/col/name; JSONL key-union+row.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/_converters.py` | Create | Dispatcher, 4 converters, `_write_parquet_table`, `normalize_parquet_remote`, `sanitize_sheet_name`, parity, `CONVERTIBLE_SUFFIXES` |
| `src/sofer/prepare.py` | Modify | Gate 671 to convertible set; import dispatcher; key `converted` by normalized remote; update `_check_local_overwrite`, `_assert_cross_file_schema` loops; tmp idx kept |
| `src/sofer/_mirror.py` | Modify | `planned_remotes`/`_validate_case_fold_collisions` to convertible+normalized; import normalizer from `_converters` |
| `src/sofer/publish.py` | Modify | `_repo_diff_summary`/`_copy_package` delegate to `planned_remotes`; expand N remotes for xlsx; local `keep_csv=False` |
| `src/sofer/repo_compliance.py` | Modify | `_build_schema_report_impl` over convertible suffixes; resolve `staging_dir/normalize(parquet_remote_for(remote))` + multi-sheet; card via `planned_remotes` |
| `src/sofer/model.py` | Modify | `FileEntry.convert_to_parquet=True`; `upload_as_csv` deprecated alias (csv-only, warns); `from_toml` precedence: explicit flag wins |
| `README.md`/`README_ES.md` | Modify | Table + footnote 1 sync (AGENTS 13); English literals in both |
| `docs/configuration.md` | Modify | `convert_to_parquet` per-file docs |

## Interfaces / Contracts

```python
# _converters.py
CONVERTIBLE_SUFFIXES: frozenset[str] = {".csv",".tsv",".xlsx",".jsonl"}
def normalize_parquet_remote(remote: str) -> str: ...  # lowercase, NFKD->ASCII, spaces->_,
                                                       # [^a-z0-9_./-]->_, collapse __+
def sanitize_sheet_name(name: str) -> str: ...  # same alphabet, dedup _{n} in caller
def convert_file_to_parquet(local: Path, staging_dir: Path, cfg=None) -> dict[str, Path]: ...
def _write_parquet_table(table: pa.Table, staging_dir: Path, stem: str) -> Path: ...
    # cast null->string, pq.write_table(compression=..., row_group_size=..., write_page_index=True),
    # warn if >PARQUET_SHARD_WARNING_MB

# model.py
@dataclass class FileEntry:
    local: Path; remote: str; recursive: bool=False
    convert_to_parquet: bool=True
    upload_as_csv: bool=False  # deprecated, csv-only
    include_in_schema: bool=True
```

Collision: `key = normalize_parquet_remote(parquet_remote_for(remote))`; validate `key.lower()` duplicates naming both originals. Sheet dedup: `a_b`, `a_b_2`, ...

## Module Boundaries

- **prepare**: orchestration + guards + tmp idx + staging. No hardcoded literals.
- **_converters**: pure conversion/parity/writer/normalizer; no `files` loop beyond one file; refs `codebook.py` pattern, no import.
- **_mirror**: planning + collision; imports normalizer; dependents import from `_mirror` (DAG, no cycles).

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit (_converters) | normalize, sanitize dedup, converters, writer opts, JSONL fallback | `tests/test_converters.py` parametrized |
| Unit (mirror/model) | `planned_remotes` N-expansion, `lower(normalized)` collision, alias | `tests/test_mirror.py`, `tests/test_model.py` |
| Integration | prepare mixed formats -> normalized layout; opt-out; failure fallback | Update `test_prepare`, `test_parquet_conversion` |
| Integration | schema via normalized staged keys; multi-sheet origins; missing->warn+fallback | `test_repo_compliance` |
| Integration | publish diff/copy agree; `keep_csv` CSV-only | `test_publish` |
| Type | `mypy src/` | `from __future__ import annotations` |

Migrate: `test_prepare`, `test_parquet_conversion`, `test_mirror`, `test_repo_compliance`.

## Migration / Rollout

0.x minor (AGENTS 12). `report.xlsx` -> `report.parquet` (or N). Migration: `convert_to_parquet=false` keeps original. Failure warns, stages original.

## Error Handling

Conversion exception -> `None` (stage original). Parity hard fail -> `None` (blocked). Warnings advisory. JSONL sparse -> fallback.

## Sequence: _cmd_prepare

```
_cli._cmd_prepare -> config.reload(toml_dir)
 -> _check_local_overwrite(normalized) / _validate_case_fold_collisions(normalized)
 -> validator.run_all (non-blocking) -> conversion loop (dispatcher+parity)
 -> _assert_cross_file_schema (exit 1) -> _check_large_values
 -> copy_to_mirror(converted) -> build_schema_report_with_rows(staging_dir)
 -> build_dataset_card/LICENSE -> copy_to_mirror(non-converted) -> generate_all_codebooks
```

## Open Questions

- [ ] Re-export location review (`_converters` vs `_mirror`) -- current avoids cycle; needs team sign-off.
- [ ] Large XLSX cap -- defer streaming until proven; `read_only` mitigates.

## Risks

Collisions: validated pre-write, both remotes named. XLSX: `read_only,data_only`; doc all-sheets. JSONL sparse: fallback preserves columns.
