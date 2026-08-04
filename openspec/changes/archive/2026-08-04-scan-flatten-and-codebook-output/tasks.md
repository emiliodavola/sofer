# Tasks: Scan Flatten & Per-File Codebook Output

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~620 (add+del) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 config+scan → PR 2 codebook → PR 3 upload+docs |
| Delivery strategy | force-chained |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Batch Estimates

| Batch | Est. lines | Risk |
|-------|-----------|------|
| 1 Config foundation | ~8 | Low |
| 2 Scan flatten | ~170 | Med |
| 3 Codebook layout | ~240 | Med |
| 4 Upload RC-C01 | ~165 | Med |
| 5 Docs | ~35 | Low |
| 6 Verify | 0 | Low |

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Batches 1-2: config + scan flatten + collision gate | PR 1 | Base: tracker branch |
| 2 | Batch 3: per-file codebook layout | PR 2 | Base: PR 1 branch |
| 3 | Batches 4-6: upload RC-C01 + README + verify | PR 3 | Base: PR 2 branch |

## Phase 1: Foundation (PR 1)

- [x] 1.1 `pyproject.toml` `[tool.sofer]`: add `codebooks_dir = "codebooks"`.
- [x] 1.2 `src/sofer/config.py`: `_DEFAULTS["codebooks_dir"]` + public `CODEBOOKS_DIR` constant.

## Phase 2: Scan flatten (PR 1)

- [x] 2.1 RED `tests/test_scanner.py`: add `test_flatten_first_level_{root_file,single_dir,nested}`.
- [x] 2.2 GREEN `scanner.py`: `flatten_first_level(relative) -> Path` — drop first segment; `len(parts)<=1` unchanged; public, docstring.
- [x] 2.3 RED: add `test_flatten_collision_raises_naming_sources`, `test_flatten_collision_single_source_ok`.
- [x] 2.4 GREEN `scanner.py`: `check_flatten_collisions(discovered, base_dir)` → `ValueError` naming every flattened dest + sources.
- [x] 2.5 RED→GREEN `merge_entries` (SCN-02): update `test_remote_uses_posix_separators` (→`"nested/a.csv"`); add `test_merge_flattened_local_and_remote`, `test_root_level_file_keeps_name`; dest = `data_dir / flatten_first_level(relative)`.
- [x] 2.6 RED→GREEN `copy_files` (SCN-03): update `test_creates_subdirs_lazily` (→`data/nested/a.csv`); same helper.
- [x] 2.7 RED→GREEN `cli.py _cmd_scan` (SCN-06): add `test_scan_collision_exits_1_no_copy`, `test_scan_dry_run_reports_flattened_paths`, `test_scan_preview_shows_flattened_paths`; gate after discovery, before merge/prompt; `ValueError`→stderr→exit 1; preview/report show flattened paths; scan `help=`.
- [x] 2.8 `uv run pytest tests/test_scanner.py -q` green.

## Phase 3: Codebook per-file layout (PR 2)

- [x] 3.1 RED `tests/test_codebook.py` (CB-R03/R04): update `test_generates_for_all_toml_entries` (→`data/codebooks/{a,b}.md`), `test_root_index_has_correct_links` (→`data/codebooks/f.md`); replace `test_output_collision_uses_suffixes`→`test_same_stem_collision_errors`; add `test_rel_stem_{under,outside}_data`, `test_collision_partial_write_non_colliding`, `test_no_index_on_failed_run`.
- [x] 3.2 GREEN `codebook.py`: rewrite `generate_all(cfg)` — drop `dir_counts`/`fmt_label`; output `CODEBOOKS_DIR/<rel-stem>.md` (rel to `data/`, fallback `base_dir`, `with_suffix(".md")`); partition colliding/non-colliding; write non-colliding; raise `ValueError` listing colliding sources, no index; success → root index links from actual outputs.
- [x] 3.3 RED→GREEN `cli.py _cmd_codebook`: add `test_codebook_cli_collision_exits_1`; catch `ValueError`→stderr→exit 1; codebook `help=`.
- [x] 3.4 `uv run pytest tests/test_codebook.py -q` green.

## Phase 4: Upload RC-C01 (PR 3)

- [x] 4.1 RED `tests/test_uploader.py`: rework `test_codebook_uploaded_to_codebook_subpath` (order; `codebooks/DPTO.md`; `codebook.md`); replace `test_codebook_missing_file_warns`→`test_no_codebooks_generated_skips`; add `test_legacy_codebook_not_uploaded`, `test_codebook_upload_order_data_first`, `test_root_index_uploaded_as_codebook_md`, `test_repo_diff_summary_lists_codebook_remotes`.
- [x] 4.2 GREEN `uploader.py`: delete legacy `cfg.codebook` block (≈884-893, 984-990); after data loop walk `data/codebooks/**/*.md` sorted → `_hf_upload` rel-to-data-dir; upload root `codebook.md`; missing dir/index → skip silently; `_repo_diff_summary` lists codebook remotes; docstring.
- [x] 4.3 `uv run pytest tests/test_uploader.py -q` green.

## Phase 5: Docs (PR 3)

- [x] 5.1 `README.md`: scan flatten + collision, codebook `--all-files` layout, upload codebook convention.

## Phase 6: Verification (PR 3)

- [x] 6.1 `uv run ruff check src/ tests/ && uv run ruff format`.
- [x] 6.2 `uv run mypy src/`.
- [x] 6.3 `uv run pytest tests/ -q` — 448 green (422+).
