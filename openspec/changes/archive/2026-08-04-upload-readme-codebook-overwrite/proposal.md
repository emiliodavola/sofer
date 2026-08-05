# Proposal: Stop Overwrite-Protecting Auto-Generated Repo Files

**Date:** 2026-08-04

## Intent

`_check_overwrite_protection` treats `README.md` and `LICENSE` as user files — asking
for interactive confirmation before overwriting. But `upload()` auto-generates both on
every run (via `build_dataset_card` / `build_license_file`). Blocking their upload breaks
the upload pipeline in non-interactive mode and adds unnecessary friction in interactive
mode. Separately, when codebooks (`codebook.md` + `data/codebooks/`) haven't been
generated yet, `upload` silently skips them — giving no clue that `codebook --all-files`
should have been run first.

## Scope

### In Scope
- Remove `README.md` and `LICENSE` from `_check_overwrite_protection` — always
  upload/overwrite them unconditionally (they are auto-generated).
- Respect the existing `cfg.readme` override path (uploader.py:869–884) — no change.
- Exclude `codebook.md` (root index) and `codebooks/**/*.md` (per-file RC-C01) from
  any protection — they are auto-generated.
- When `codebook.md` and `data/codebooks/` are missing locally at upload time, print
  a single advisory:  
  `"Run 'sofer codebook --all-files' first to generate codebooks."`
- Remove the `force` parameter's doc-only reference to README.md / LICENSE
  protection (uploader.py:705) — the flag stays for backward compatibility
  but no longer gates compliance files.

### Out of Scope
- Auto-generating codebooks inside `upload()`.
- Changing `--force` semantics for data files.
- Adding codebook overwrite protection (they have none today — we're codifying that).
- Touching `_repo_diff_summary` (it already lists README.md / LICENSE as planned).

## Capabilities

### New Capabilities
None — no new service or module introduced.

### Modified Capabilities
- **`repo-compliance`**: Overwrite-protection gating for auto-generated compliance
  files (README.md, LICENSE, codebooks) is removed. The upload-advisory for missing
  codebooks is added.

## Approach

1. **Extract auto-generated filenames to a constant** `_AUTO_GENERATED: frozenset[str]`
   in `uploader.py`: `{"README.md", "LICENSE", "codebook.md"}`. The codebook prefix
   `"codebooks/"` is handled as a path-prefix check.

2. **Modify `_check_overwrite_protection`** to skip any file whose lowercase name is in
   `_AUTO_GENERATED`.  Since it only loops over `("README.md", "LICENSE")` today, the
   result is that the function always returns an empty set when `force=False` — no
   interactive prompt, no skip.  Logically it's a no-op for these files, but we keep
   the function intact so any future protected files still work.

3. **In `upload()`**, after the existing codebook file-discovery block (lines 752–761),
   add a check: if `codebook.md` doesn't exist *and* `data/codebooks/` is absent or
   empty, print the advisory.  Record it so the same message is not repeated during
   the upload loop (lines 981–996).

4. **Upload loop unchanged** — codebooks are still uploaded if present (lines 981–996),
   and silently skipped if not (existing behaviour + advisory).

5. **Tests**: two new test cases in `tests/test_uploader.py`:
   - `test_readme_license_always_uploaded`: verify `_check_overwrite_protection` returns
     empty set regardless of whether README.md / LICENSE exist in `existing_files`.
   - `test_missing_codebooks_advisory`: capture stdout, call `upload()` in a scenario
     where `codebook.md` and `data/codebooks/` are absent, assert the advisory line appears.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/uploader.py` | Modified | ~20 lines: `_check_overwrite_protection`, `upload()` advisory |
| `tests/test_uploader.py` | New tests | 2 test cases for new behaviour |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Someone relied on `--force` to stop README.md overwrite | Low | Never the intended UX — compliance files should always be uploaded |
| `_check_overwrite_protection` becomes a no-op for current file set | Low | Function stays intact; if new protected files are added later, they still gate |

## Rollback Plan

Revert the two changes in `uploader.py` (restore `("README.md", "LICENSE")` loop in
`_check_overwrite_protection`; remove the codebook advisory).  No data migration
or schema change.

## Dependencies

None — pure behavioural fix, no new libraries or config keys.

## Success Criteria

- [ ] `_check_overwrite_protection` returns empty set when only README.md / LICENSE exist — no prompt, no skip
- [ ] `upload()` with `force=False` always uploads README.md and LICENSE even if they exist in the repo
- [ ] `upload()` prints advisory when `codebook.md` and `data/codebooks/` are absent
- [ ] Custom `cfg.readme` path is still respected (regression-free)
- [ ] `uv run pytest tests/test_uploader.py -q` — new tests pass, no regressions
- [ ] `uv run ruff check src/` and `uv run mypy src/` clean
