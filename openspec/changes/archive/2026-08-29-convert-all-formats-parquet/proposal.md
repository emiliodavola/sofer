# Proposal: convert-all-formats-parquet

## Intent

Universal: `csv/tsv/xlsx/jsonl` → normalized `.parquet` by default in `prepare`/`publish`; `.parquet` passthrough. Excel → one Parquet per sheet; remotes normalized (lowercase, accent-stripped).

## Scope

### In Scope
- Broaden `prepare` gate; new `src/sofer/_converters.py` dispatcher + shared writer (`zstd`, 100k row_group, null-cast, shard warn).
- `normalize_parquet_remote()` + sheet sanitizer; normalize before collision/overwrite checks.
- Excel all sheets → N Parquets (`stem__{sheet}.parquet` flat `__`).
- Extend `_mirror.planned_remotes`, `_validate_case_fold_collisions`, `prepare._check_local_overwrite`, `publish._repo_diff_summary`/`_copy_package`, `repo_compliance` schema to all convertible suffixes.
- `FileEntry.convert_to_parquet: bool=True`; `upload_as_csv` deprecated alias; docs/TOML; `README`/`README_ES` sync; per-format tests.

### Out of Scope
- New providers, ML pipeline, quality beyond collisions, `--keep-original` (keep `--keep-csv` CSV-only), XLSX sheet selection config.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `parquet-conversion`: CSV-only → universal `csv/tsv/xlsx/jsonl→parquet`; per-format readers/parity; normalized remotes; multi-sheet Excel.
- `prepare`: gate/parity/overwrite/cross-schema for all convertible formats.
- `publish`: diff/copy delegate to `_mirror.planned_remotes`.
- `repo-compliance`: schema via staged Parquet for TSV/XLSX/JSONL.

## Approach

- **Dispatcher** `_converters.py`: `.csv`→`pyarrow.csv` (sniff `;|,|\t`), `.tsv`→`\t`, `.xlsx`→`openpyxl` all `sheetnames` (read_only,data_only, `pa.Table` per sheet), `.jsonl`→`pyarrow.json`+`json` fallback, `.parquet`→passthrough; shared `_write_parquet`.
- **Parity**: CSV/TSV row/col/name+value-altered; XLSX row/col/name; JSONL key-union+row count.
- **Excel**: 1 sheet→`stem.parquet`; N→`stem__{sanitized}.parquet` (flat `__`).
- **Normalization** `normalize_parquet_remote(s)`: lowercase, NFKD→ASCII, spaces→`_`, `[^a-z0-9_./-]`→`_`, collapse `__+`; collisions on `lower(normalized(key))`→error; sheet dupes→`_{n}`.
- **Flag**: `convert_to_parquet=True` (positive). `upload_as_csv=True` on `.csv`→`convert_to_parquet=False`+warning. TOML `convert_to_parquet=false` keeps original.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/_converters.py` | New | Dispatcher, converters, writer, normalizer |
| `src/sofer/prepare.py` | Modified | Gate, parity, overwrite |
| `src/sofer/_mirror.py` | Modified | `planned_remotes`, collisions, normalizer |
| `src/sofer/publish.py` | Modified | Delegate to `_mirror` |
| `src/sofer/repo_compliance.py` | Modified | Schema for all formats |
| `src/sofer/model.py` | Modified | Flag + alias |
| `README.md`, `README_ES.md` | Modified | Table + footnote ¹ |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Breaking: `.xlsx`→`.parquet` (+N files) | High | Opt-out `convert_to_parquet=false`; fallback on failure; 0.x minor bump (AGENTS 12) |
| Normalized/case-fold collisions | Med | Validate `lower(normalized(key))`; sheet `_{n}` dedup |
| Parity false positives / JSONL sparse schema / XLSX memory | Med | Per-format parity; `pyarrow.json` fallback; `read_only,data_only` |

## Rollback Plan

Revert gate to `.csv`-only; `convert_to_parquet`/normalizer removal backward-compatible (`upload_as_csv` remains). Per-file `convert_to_parquet=false` achieves same without code change; originals untouched in staging.

## Dependencies

`pyarrow>=14.0`, `openpyxl>=3.1`; no new deps. Based on `explore.md` hybrid A+B + C1.

## Success Criteria

- [ ] `csv/tsv/xlsx/jsonl` → normalized `.parquet`; `.parquet` passthrough; multi-sheet `__` split
- [ ] `convert_to_parquet=false` + `upload_as_csv` alias work
- [ ] Collisions/overwrite cover all suffixes + normalized keys
- [ ] Schema + `publish` reflect universal remotes; `README_ES` synced; `pytest -q` + `mypy src/` green
