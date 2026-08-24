# Tasks: Scan Command

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~330 |
| 2000-line budget risk | Low |
| Chained PRs recommended | No |
| Delivery strategy | auto-forecast |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

## Phase 1: Foundation

- [x] 1.1 Create `src/sofer/_formats.py` — `SUPPORTED_FORMATS: dict[str, str]` with `.csv`, `.tsv`, `.parquet`, `.xlsx`, `.jsonl` (SCN-01)
- [x] 1.2 Add `tomli_w` to `pyproject.toml` `dependencies` and run `uv sync`

## Phase 2: Core — Scanner Module

- [x] 2.1 Implement `discover_files(root, extensions, exclude_dirs)` in `src/sofer/scanner.py` — `pathlib.rglob`, skip excluded dirs by checking all path parts, filter by suffix, return sorted list (SCN-01)
- [x] 2.2 Implement `merge_entries(discovered, raw_toml, base_dir, data_dir)` — dedup by resolved dest path, append new `[[file]]` with `local`/`remote` using `PurePosixPath`, preserve non-file sections (SCN-02, SCN-05)
- [x] 2.3 Implement `copy_files(discovered, base_dir, data_dir, *, dry_run, force)` — `shutil.copy2` with lazy `mkdir`, `FileExistsError` unless `--force` (SCN-03)
- [x] 2.4 Implement `write_toml(raw_toml, config_path)` — `tomli_w.dumps()` → overwrite file (SCN-02)

## Phase 3: CLI Wiring

- [x] 3.1 Add `scan` subparser to `_build_parser()` in `src/sofer/cli.py` — positional `[config]` (default `dataset.toml`), `--dry-run`, `--force`, `--ext` with choices from `SUPPORTED_FORMATS` (SCN-04)
- [x] 3.2 Implement `_cmd_scan(args)` — orchestrate load→discover→merge→copy→write, catch exceptions, print to stderr, return exit code (SCN-04, SCN-06)
- [x] 3.3 Update `src/sofer/__init__.py` docstring to include `scan` in usage block

## Phase 4: Testing

- [x] 4.1 Write `tests/test_scanner.py` — `TestDiscoverFiles` (extension filter, excluded dirs, `--ext`, empty results) using `tmp_path` (SCN-01 scenarios)
- [x] 4.2 Write `tests/test_scanner.py` — `TestMergeEntries` (new entries, dedup by resolved path, section preservation, idempotency) (SCN-02, SCN-05 scenarios)
- [x] 4.3 Write `tests/test_scanner.py` — `TestCopyFiles` (subdir creation, dry-run no-op, `FileExistsError`, original untouched) (SCN-03 scenarios)
- [x] 4.4 Write `tests/test_scanner.py` — `TestIntegration` full pipeline: build tree + TOML fixture, run `_cmd_scan`, verify output parses via `DatasetConfig.from_toml()` + `validate()` passes (end-to-end)
- [x] 4.5 Add `tests/test_cli.py` — `TestScanParser` class: default config, `--dry-run`, `--force`, `--ext`, explicit config path, `SystemExit` on missing config (SCN-04, SCN-06 scenarios)
