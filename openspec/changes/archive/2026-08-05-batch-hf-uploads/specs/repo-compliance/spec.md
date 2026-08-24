# Delta for repo-compliance — Batch Hugging Face Uploads

## MODIFIED Requirements

### Requirement: Upload orchestration uses batch `upload_folder` instead of individual `upload_file`

The `upload()` function SHALL stage ALL files — data (.parquet), compliance (README.md, LICENSE),
and codebooks — into the existing `tmpdir` staging directory, mirroring the target HF repository
structure. Instead of calling `HfApi.upload_file()` individually for each file, `upload()` SHALL
call `HfApi.upload_folder(tmpdir, repo_id=cfg.repo_id, repo_type=cfg.repo_type, path_in_repo="")`
exactly once after staging is complete.

(Previously: individual `_hf_upload()` calls for each data file, compliance file, and codebook.)

#### Scenario: Batch upload stages all files and uploads atomically

- GIVEN a valid DatasetConfig with 65 CSV file entries, license="cc0-1.0", and generated codebooks
- WHEN upload(cfg) is called
- THEN ALL data .parquet files SHALL be placed in `tmpdir/` preserving remote path structure
- AND README.md and LICENSE SHALL be written to `tmpdir/`
- AND all codebooks SHALL be placed in `tmpdir/codebooks/` mirroring their remote paths
- AND `HfApi.upload_folder(tmpdir, …)` SHALL be called exactly once
- AND NO individual `upload_file` calls SHALL be made for staged files
- AND the function SHALL return 0 on success

#### Scenario: `upload_folder` failure is reported as a single failure

- GIVEN staged files are ready in `tmpdir/`
- WHEN `HfApi.upload_folder()` raises an exception
- THEN the error SHALL be printed
- AND `fail` counter SHALL be set to 1
- AND the function SHALL return 1
- AND the tmpdir SHALL be cleaned up

#### Scenario: Dry-run does NOT stage or upload

- GIVEN a valid DatasetConfig and `dry_run=True`
- WHEN upload(cfg, dry_run=True) is called
- THEN `_repo_diff_summary` and `_check_overwrite_protection` SHALL run as before
- AND NO files SHALL be staged in tmpdir beyond compliance generation
- AND NO `upload_folder` or `upload_file` calls SHALL be made
- AND the function SHALL return 0

### Requirement: Codebooks are staged and uploaded as part of the batch (RC-C01)

The `upload()` function SHALL copy generated codebook artifacts into `tmpdir/` preserving their
remote path structure (e.g., `data/codebooks/DPTO.md` → `tmpdir/codebooks/DPTO.md`,
`codebook.md` → `tmpdir/codebook.md`). Codebooks SHALL be uploaded as part of the single
`upload_folder()` call, NOT via individual `_hf_upload()` calls.

(Previously: codebooks were uploaded individually via `_hf_upload()` after data files.)

#### Scenario: Codebooks are staged and uploaded in batch

- GIVEN `codebook.md` and `data/codebooks/DPTO.md` exist on disk
- WHEN upload(cfg) is called
- THEN `codebook.md` SHALL be copied to `tmpdir/codebook.md`
- AND `data/codebooks/DPTO.md` SHALL be copied to `tmpdir/codebooks/DPTO.md`
- AND `HfApi.upload_folder(tmpdir, …)` SHALL include both codebook files
- AND NO individual `_hf_upload()` calls SHALL be made for codebooks

#### Scenario: Upload proceeds normally when no codebooks exist

- GIVEN no `codebook.md` and no `data/codebooks/` directory on disk
- WHEN upload(cfg) is called
- THEN the advisory message to run `sofer codebook --all-files` SHALL still print
- AND the upload SHALL proceed with only data and compliance files staged
- AND upload(cfg) SHALL return 0

### Requirement: User feedback adapts to batch upload progress

The upload progress SHALL use `upload_folder`'s built-in `hf_xet` progress bar instead of
per-file `↑ file → remote` / `✓ file` lines. The pre-upload diff summary and post-upload split
report SHALL remain unchanged.

(Previously: every file printed `↑ label → remote` and `✓ label` individually.)

## ADDED Requirements

### Requirement: tmpdir mirrors the HF repository structure

The staging directory `tmpdir` SHALL contain ALL files to be uploaded, organized with the
same directory structure they will have on the Hugging Face Hub. Data files go in their
remote-relative paths, compliance files at root, and codebooks under `codebooks/`.

#### Scenario: tmpdir structure matches remote layout

- GIVEN a DatasetConfig with `remote = "data/PROV/train.csv"` and `remote = "data/DPTO/train.csv"`
- AND both CSV files are converted to .parquet
- WHEN staging is complete
- THEN `tmpdir/data/PROV/train.parquet` SHALL exist
- AND `tmpdir/data/DPTO/train.parquet` SHALL exist
- AND `tmpdir/README.md` SHALL exist
- AND `tmpdir/LICENSE` SHALL exist

## REMOVED Requirements

None.

## RENAMED Requirements

None.
