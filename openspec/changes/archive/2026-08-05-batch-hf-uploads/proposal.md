# Proposal: Batch Hugging Face Uploads via `upload_folder`

## Intent

`sofer upload` calls `HfApi.upload_file()` individually for each file (~132 files = ~132 commits
for a 65-CSV dataset). Hugging Face enforces a 128-commit/hour rate limit for low-storage repos,
causing `429 Too Many Requests`. Replace individual uploads with a single `HfApi.upload_folder()`
call that stages all files in the existing `tmpdir` and uploads atomically with auto-batched commits.

## Scope

### In Scope
- Stage ALL files (data .parquet, README.md, LICENSE, codebooks) into the existing `tmpdir`
  before upload, mirroring the HF repo structure
- Replace the individual-upload loop (data files + compliance + codebooks) with ONE
  `HfApi.upload_folder(tmpdir, repo_id=cfg.repo_id, repo_type=cfg.repo_type, path_in_repo="")`
- Adapt `ok`/`fail` counter semantics to batch-upload (single pass/fail or per‑file tracking)
- Keep `_hf_upload` and `_hf_upload_folder` as legacy helpers (may be removed later)

### Out of Scope
- Changing `_repo_diff_summary` or `_check_overwrite_protection` (both run BEFORE staging)
- Adding resume/resumable-upload logic (already built into `upload_folder`)
- Modifying the `--dry-run` path (already stops before upload)
- Removing `_hf_upload` / `_hf_upload_folder` in this change (deferred cleanup)

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `repo-compliance`: upload orchestration changes from individual `upload_file` calls to a
  single `upload_folder` call. The staging directory expands to hold ALL files (data, compliance,
  codebooks) mirroring the target HF repo structure.

## Approach

1. **Stage everything in `tmpdir`**: after conversion and compliance generation, copy/move
   converted .parquet files and codebooks into `tmpdir` preserving their remote paths.
   README.md and LICENSE are already written there.
2. **Single `upload_folder` call**: replace the three upload stages (compliance files L930–934,
   data file loop L936–989, codebook loop L991–1012) with one `HfApi.upload_folder(tmpdir, …)`.
3. **Progress feedback**: `upload_folder` provides its own progress bar via `hf_xet`.
   Keep the pre‑upload diff summary, and report pass/fail from `upload_folder`'s return value.
4. **Counter adaptation**: `ok` = 1 on success (whole folder), `fail` = 1 on failure,
   or count staged files for equivalent reporting.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/uploader.py` | Modified | Replace individual upload loops with staging + single `upload_folder` call |
| `openspec/specs/repo-compliance/spec.md` | Modified | Upload orchestration spec updated for batch behaviour |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `upload_folder` fails mid‑batch (network) | Low | `upload_folder` is resumable — re‑run skips already‑uploaded files |
| Staging directory structure mismatch with HF repo layout | Med | Verify with `--dry-run` + inspect tmpdir tree before upload |
| Regression in overwrite protection | Low | `_check_overwrite_protection` runs BEFORE staging; unchanged |

## Rollback Plan

Revert `uploader.py` to the individual‑upload loop. `_hf_upload` and `_hf_upload_folder` helpers
are preserved as legacy — the revert is a single-file change.

## Dependencies

- `huggingface_hub` version with `upload_folder` support (already satisfied — function exists at L91–114)
- No new packages required

## Success Criteria

- [ ] `sofer upload` completes without 429 errors for datasets with ≥65 CSV files
- [ ] ALL files (data, compliance, codebooks) appear at the correct remote paths
- [ ] `--dry-run` output is unchanged (inspecting repo state before staging)
- [ ] Existing tests pass; new tests cover `tmpdir` staging structure and `upload_folder` call
