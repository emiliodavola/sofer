# Tasks: Batch Hugging Face Uploads via `upload_folder`

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~110 (uploader.py) + ~80 (tests) = ~190 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |
| Chain strategy | single-pr |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: single-pr
400-line budget risk: Low

## Phase 1: Staging restructure

- [x] 1.1 Modify conversion loop (L808–838): compute `parquet_remote` from `entry.remote` with `.parquet` extension, write to `tmpdir / parquet_remote`, create parent dirs via `mkdir(parents=True, exist_ok=True)`. Update `converted` dict to store `parquet_remote` path.
- [x] 1.2 Add codebook staging step (after L906, before compliance upload): copy `data/codebooks/**/*.md` to `tmpdir/codebooks/` and `codebook.md` to `tmpdir/codebook.md`, preserving subdirectory structure with `shutil.copy2`.
- [x] 1.3 Move per-file NOT FOUND check from upload loop (L944–947) to staging phase — skip files that don't exist before conversion attempt.

## Phase 2: Replace upload loops

- [x] 2.1 Replace compliance file upload calls (L930–934) with no-op: README.md and LICENSE are already in `tmpdir`, will be uploaded by `upload_folder`.
- [x] 2.2 Replace data file upload loop (L936–989) + codebook upload loop (L991–1012) with single `_hf_upload_folder(cfg.repo_id, tmpdir, "", cfg.repo_type)` call.
- [x] 2.3 Adapt `ok`/`fail` counter: `ok = 1` on `upload_folder` success, `fail = 1` on exception. Print summary with staged file count (from `converted` + compliance + codebooks).

## Phase 3: Tests (TDD: RED → GREEN → REFACTOR)

- [x] 3.1 Write test: `test_staging_mirrors_repo_structure` — verify `.parquet` files placed in `tmpdir/<remote-path>/` subdirs, not flat. Use `tmp_path` + mock cfg.
- [x] 3.2 Write test: `test_codebooks_staged_in_tmpdir` — verify `data/codebooks/DPTO.md` → `tmpdir/codebooks/DPTO.md`.
- [x] 3.3 Write test: `test_upload_folder_called_once` — mock `_hf_upload_folder`, verify call count = 1, verify `_hf_upload` call count = 0.
- [x] 3.4 Write test: `test_upload_folder_failure_sets_fail` — mock `_hf_upload_folder` to raise, verify return code = 1, tmpdir cleaned up.
- [x] 3.5 Run `uv run pytest tests/ -q` — all 422 existing tests MUST pass.

## Phase 4: Cleanup

- [x] 4.1 Update `upload()` docstring to reflect batch upload behavior and new staging structure.
- [x] 4.2 Run `uv run ruff check src/ tests/ && uv run mypy src/` — zero new errors.
