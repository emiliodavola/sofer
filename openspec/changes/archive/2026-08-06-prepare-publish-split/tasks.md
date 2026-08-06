# Tasks: prepare + publish split (upload removal)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~2,900 (range 2,600–3,100): delete 1,075-line `uploader.py`, ~900 new src (`prepare.py` ~380, `publish.py` ~380, `_mirror.py` ~100, cli ~180), ~800 tests (new `test_prepare.py`/`test_publish.py` + ~50 retargeted call sites) |
| 2,000-line budget | **Exceeded** |
| Chained PRs recommended | **Yes** |
| Chain strategy | feature-branch-chain |
| Delivery strategy | auto-forecast |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units (tracker branch `feat/prepare-publish-split`; only tracker merges to main)

| PR | Base | Scope | Est. lines |
|----|------|-------|-----------|
| 1 | tracker | Config foundation (`cache/`, `build_dir`, template, codebook Option B param) + `_mirror.py` + tests — **zero behavior change, full suite green** | ~350 |
| 2 | PR 1 | `prepare.py` + `prepare` subparser + `test_prepare.py`; helpers imported from `uploader.py` (not moved yet); `upload` intact | ~550 |
| 3 | PR 2 | `publish.py` + `publish` subparser + `test_publish.py`; `upload` still alive | ~600 |
| 4 | PR 3 | Move helpers → `prepare.py`, delete `uploader.py` + `upload` subparser, retarget ~50 call sites, RC-R04 tests, README/`__init__`, full verify | ~1,400 |

Every PR stays green independently (intermediate states run `upload` + `prepare` + `publish` together). Rollback = revert tracker merge. Work-unit commits per PR.

## Phase 1: Config foundation
- [x] 1.1 `src/sofer/config.py`: `OUTPUT_DIR` default `"data"` → `"cache"` (docstring updated)
- [x] 1.2 `src/sofer/model.py`: add `build_dir: str = "build"` to `DatasetConfig`; parse `[dataset] build_dir` in `from_toml()` (default `"build"`)
- [x] 1.3 `cli.py` `_INIT_TEMPLATE`: add `build_dir = "build"` under `[dataset]`; usage comment lines → `prepare`/`publish`
- [x] 1.4 `codebook.py`: `generate_all(cfg, output_dir=None)` param; default stays `cache/codebooks/` + root; Option B writes into `output_dir` directly, never mutates cache when called from prepare

## Phase 2: `_mirror.py`
- [x] 2.1 Create `_mirror.py`: `_validate_remote_paths(cfg)`, `planned_remotes(cfg, keep_csv)`, `copy_to_mirror(src, dest_root, remote)` — dir-aware via `copytree(dirs_exist_ok=True)`, never `copy2` on a directory (RC-R04)
- [x] 2.2 Retarget `TestRemotePathValidation` imports `uploader` → `_mirror`; add `planned_remotes` unit tests (keep_csv variants)

## Phase 3: `prepare.py`
- [x] 3.1 Create `prepare.py`; move conversion helpers unchanged from `uploader.py`: `_sniff_csv_delimiter`, `_count_delimiters_outside_quotes`, `_cast_null_columns_to_string`, `_read_csv_raw_values`, `_check_conversion_parity`, `_convert_to_parquet`, `_assert_cross_file_schema`, `_check_large_values`, `_assert_card_dtypes_match_parquet`
- [x] 3.2 `prepare(cfg, output_dir, all_files, no_checks, force) -> int`: conversion loop (parity, cast-null, large-values), NOT FOUND report, cross-file schema assert → exit 1, `build_schema_report(staging_dir=output_dir)`, README + LICENSE — zero network, no HF_TOKEN (PRP-01..03)
- [x] 3.3 Option B codebooks: `--all-files` → `generate_all(cfg, output_dir)` staging `codebooks/` mirror + root `codebook.md`; without flag, no codebooks + advisory (PRP-04)
- [x] 3.4 `resolve_output_dir(cfg, override) = cfg._base_dir / (override or cfg.build_dir)`; `_check_local_overwrite` refusal without `--force` (PRP-07); `--verify` loads generated parquets locally (PRP-08); checks non-blocking, `--no-checks` skips (PRP-05)

## Phase 4: `publish.py`
- [x] 4.1 Create `publish.py`; move `_ensure_repo`, `_inspect_repo`, `_repo_diff_summary`, `_check_overwrite_protection` (extend `_AUTO_GENERATED` with codebook paths — PUB-05), `_print_split_report`, `_print_split_mapping_validation`
- [x] 4.2 `_needs_prepare(cfg, output_dir)`: true if no parquet OR TOML mtime newer than newest parquet OR any declared source (all `SUPPORTED_FORMATS`) newer; auto-prepare always `force=True`; `--dry-run` never prepares (PUB-03/04)
- [x] 4.3 `publish(cfg, target, output_dir, force, keep_csv, dry_run, quality_report=None) -> int`: hf = staging tmpdir from output_dir planned remotes → single `upload_folder`; local = copy package to `--output`, no network, `--output` omitted = in-place summary; quality gate blocks → exit 1 (PUB-01/02/05/07)
- [x] 4.4 Staging copies planned remotes only (never blanket — `--output` at config dir safe); `--keep-csv` hf-only; no post-upload verify (verify belongs to prepare)

## Phase 5: CLI wiring + docs
- [x] 5.1 `cli.py`: delete `upload` subparser + `_cmd_upload`; add `prepare` (CONFIG, `--output/--all-files/--no-checks/--force`) + `publish` (CONFIG, `--target hf|local/--output/--force/--verify/--keep-csv/--dry-run`) with accurate help/description (CLI-R01/R02)
- [x] 5.2 Extract `_load_and_validate(args)` (cfg load + config errors + validator + quality) shared by `validate`/`prepare`/`publish`; `--no-checks` skips `QualityValidator`
- [x] 5.3 Delete `src/sofer/uploader.py`; update `__init__.py` + `README.md`: `upload` → `prepare`/`publish`, `data/` → `cache/`, document `build_dir` (rule 7)

## Phase 6: Tests (retarget + new, per spec scenarios)
- [x] 6.1 `test_uploader.py`: 16 `upload()` calls → `publish(cfg)` with identical `tmp_path`/`mkdtemp`/`_api` mocks; `TestUploadQualityGate` → `TestPublishQualityGate` (failing report returns 1 pre-network)
- [x] 6.2 `test_parquet_conversion.py`: ~40 helper imports → `sofer.prepare`; 10 `upload()` calls → `publish`; assertions unchanged
- [x] 6.3 `test_repo_compliance.py`: 6 `upload()` calls → `publish`; `build_schema_report` tests untouched
- [x] 6.4 New `test_prepare.py` (PRP-01..07): offline run (patch network layer to raise), mirror layout incl. `upload_as_csv` not converted + recursive trees, card/LICENSE content + `readme` override, codebook Option B isolation, `--no-checks`, `--output` isolation, `--force` refusal/overwrite
- [x] 6.5 New `test_publish.py` (PUB-01..07 + RC-R04): retarget staging tests, local target writes package offline + in-place summary, auto-prepare 3 cases (missing parquet / TOML newer / up-to-date), `--dry-run` no output mutation, `--keep-csv`, `upload_folder` failure → exit 1, recursive dir with nested subdirs + empty dir stage without exception
- [x] 6.6 `test_cli.py`: `upload` parse fails exit 2; `prepare`/`publish` `--help` lists exact flags; `_INIT_TEMPLATE`/description carry no `upload` references

## Phase 7: Verify
- [x] 7.1 `uv run pytest tests/ -q` — full suite green, no coverage reduction
- [x] 7.2 `uv run ruff check src/ tests/` && `uv run mypy src/` (pre-commit parity)
- [x] 7.3 Manual smoke: `sofer prepare dataset.toml` offline; `sofer publish --target local --output ./out/`; `sofer upload` → exit 2; `recursive=true` dataset stages cleanly
