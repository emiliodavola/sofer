# Proposal: Fix Codebook Index Links and YOUR_USER Placeholder

## Intent

Two codebook bugs that break the user experience on Hugging Face:

1. **Broken index links (404)**: `codebook.md` links to `data/codebooks/FILE.md`, but the uploader stages codebooks under `codebooks/FILE.md` (strips `data/`). Users clicking index links on HF get 404.
2. **YOUR_USER placeholder**: `sofer init` generates `repo_id = "YOUR_USER/..."` as a template. `validate()` accepts it (regex matches), `_cmd_codebook()` never calls `validate()`. The index emits `Repository: YOUR_USER/dataset`.

## Scope

### In Scope
- Fix `generate_all()` link path: `out_path.relative_to(base_dir)` → `out_path.relative_to(data_dir)`, producing `codebooks/FILE.md` links matching uploader staging.
- Add placeholder detection in `validate()`: reject `YOUR_USER`, `YOUR_ORG`, `your-username`, `YOUR_ORGANIZATION`.
- Add `cfg.validate()` call in `_cmd_codebook()` before `generate_all_codebooks(cfg)`.
- Update `test_root_index_has_correct_links` to expect `codebooks/f.md`.
- Add `test_validate_rejects_placeholder_repo_id`.

### Out of Scope
- Auto-resolution via `HfApi().whoami()` (adds network/auth dependency — deferred).
- Changing `_INIT_TEMPLATE` (the placeholder is intentional — users must replace it).

## Capabilities

### Modified Capabilities
- `codebook`: CB-R04 scenario "Root index after batch generation" — link path changes from `data/codebooks/` to `codebooks/`.
- `repo-compliance`: validate() now rejects placeholder repo_id values; `_cmd_codebook()` calls validate() before generation.

## Approach

| Bug | Fix | Lines |
|-----|-----|-------|
| Broken links | `generate_all()`: `rel = out_path.relative_to(data_dir).as_posix()` | codebook.py:496 |
| YOUR_USER | `validate()`: add known-placeholder check before regex | model.py:435-443 |
| Missing validate | `_cmd_codebook()`: call `cfg.validate()` → errors → stderr + exit 1 | cli.py:125-127 |

## Affected Areas

| File | Impact | Description |
|------|--------|-------------|
| `src/sofer/codebook.py:496` | Modified | Link computation uses `data_dir` as base |
| `src/sofer/model.py:441-443` | Modified | validate() rejects placeholder repo_ids |
| `src/sofer/cli.py:125-127` | Modified | _cmd_codebook() calls validate() |
| `tests/test_codebook.py:549` | Modified | Updated link assertion |
| `openspec/specs/codebook/spec.md` | Modified | CB-R04 link paths |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| validate() in _cmd_codebook() rejects partial configs (file-existence check) | Low | Only codebook --all-files path affected; invalid configs SHOULD fail early |
| Existing test asserts broken behavior | None | Explicitly updated: `data/codebooks/f.md` → `codebooks/f.md` |

## Rollback Plan

Revert 3 lines: (1) `relative_to(base_dir)` back, (2) remove placeholder check, (3) remove `validate()` call. No data migration needed.

## Success Criteria

- [ ] `codebook.md` links point to `codebooks/f.md` (not `data/codebooks/f.md`)
- [ ] `validate()` returns error for `YOUR_USER/dataset`, `YOUR_ORG/x`, `your-username/x`
- [ ] `sofer codebook --config dataset.toml --all-files` with `YOUR_USER` exits 1 with error message
- [ ] All 61 existing codebook tests pass + new placeholder tests
