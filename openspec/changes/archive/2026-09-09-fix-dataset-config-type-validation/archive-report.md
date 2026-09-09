# Archive Report — fix-dataset-config-type-validation

**Archived**: 2026-09-09
**Issue**: GitHub #118 (child of epic #115)
**Branch**: `fix/118-config-type-validation`
**Archiving commit**: `chore(sdd): archive fix-dataset-config-type-validation — sync tool-config TC-13 to base`

## Summary

Closed the #118 delta: invalid TOML configuration values no longer reach
readers or comparisons as arbitrary Python types. The dataset TOML layer
(`DatasetConfig`) validates types at `validate()` time with stable
diagnostics; the `[tool.sofer]` merge loop rejects wrong types instead of
passing them through; and profile generation is now deterministic under
`SOURCE_DATE_EPOCH`.

## Spec Sync

- **`openspec/specs/tool-config/spec.md` — ADDED `TC-13`** (Configuration type
  validation with stable diagnostics) with 9 scenarios. Requirement IDs were
  renumbered from the draft (`TC-11`) because the base spec already used
  TC-11 (profile_dir/render_dir) and TC-12 (card_collapse_threshold); the
  delta in this archive carries the final TC-13 ID.
- Sync was **additive**: the existing TC-02 note (dataset `[meta]
  csv_delimiter` is the profile reader's source) remains; TC-13 documents the
  rejection behavior layered on top.
- Determinism: TC-13 includes the scenario "Profile generation is
  deterministic under SOURCE_DATE_EPOCH".

## Verification Evidence

- Full suite: **1440 passed, 6 skipped** (was 1424 before this change) — run
  on `fix/118-config-type-validation @ c8682c7`.
- `ruff check` clean; `ruff format --check` clean; `mypy src/` clean;
  `git diff --check` clean.
- New tests by file:
  - `tests/test_model.py` (8): delimiter int, multi-char delimiter, encoding
    list, confidential str, min_files str/bool, negative min_files,
    min_total_size_mb list, real-TOML surface in `validate()`.
  - `tests/test_config.py` (5): wrong type for int/str/float keys,
    bool-for-int, string→list coercion preserved.
  - `tests/test_cli.py` (1): `test_invalid_csv_delimiter_type_validate_returns_1`
    (rc 1 + diagnostic).
  - `tests/test_mcp_server.py` (1): `test_invalid_csv_delimiter_type_ok_false`
    (ok:false, exit_code 1, diagnostic in `config_errors`).
  - `tests/test_profile.py` (1): `test_deterministic_metadata_with_source_date_epoch`
    (byte-identical metadata.yaml).

## Archive Mechanics

- Change directory moved: `openspec/changes/fix-dataset-config-type-validation/`
  → `openspec/changes/archive/2026-09-09-fix-dataset-config-type-validation/`.
- Left open by design: #118 is NOT closed by this archive — it stays open as
  the tracker for the per-`[[file]]` boolean fields (`convert_to_parquet` /
  `upload_as_csv`) whose raw TOML type is lost to `bool()` coercion inside
  `from_toml`; closing #118 happens post-PR-merge with per-criterion evidence.