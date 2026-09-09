# Tasks: fix/dataset-config-type-validation

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~260 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR (`fix/118-config-type-validation` → dev) |
| Decision needed before apply | No |

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Type validation in model.py + config.py + tests + spec sync | PR 1 | Single PR to `dev` |

## Phase 1: Type validation for the dataset TOML (`model.py`)

- [x] 1.1 `_validate_config_types` module helper (model.py) invoked first in `DatasetConfig.validate()`: `csv_delimiter` (single-char str), `csv_encoding` (non-empty str), `repo_type` (non-empty str), `confidential`/`private`/`skip_cross_file_schema` (strict bool), `min_files` (non-bool int ≥ 0), `min_total_size_mb` (non-bool number ≥ 0).
- [x] 1.2 No silent truthiness coercion: `min_files = true` rejected; `confidential = "yes"` rejected.
- [x] 1.3 `[[quality]]` numeric fields (`max_null_pct`, `min`, `max`, `min_unique`) validated as numbers when present; `[[check]]` column `expected` validated as list-of-strings. **Not in this cut**: per-`[[file]]` booleans (`convert_to_parquet`/`upload_as_csv`) — `from_toml` coerces them with `bool()` before assignment, so the raw TOML type is lost by `validate()` time; tracked as follow-up inside #118 (issue stays open with this documented gap).
- [x] 1.4 Stable diagnostics naming key + expected type + received value (e.g. `csv_delimiter must be a single-character string, got int: 5`).

## Phase 2: Tighten the `[tool.sofer]` merge loop (`config.py`)

- [x] 2.1 Merge loop now type-checks every key against its `_DEFAULTS` type: list keys keep the documented string→[string] coercion; int/float keys reject non-numbers and bools; str keys reject non-strings. Keys with dedicated post-loop validation (`semantic_priors`, `profile_dir`, `render_dir`, `card_collapse_threshold`) keep their specific diagnostics.
- [x] 2.2 Wrong types raise a stable `ValueError` naming key + expected type (no silent default fallback).

## Phase 3: Determinism + integration tests

- [x] 3.1 Unit tests (tests/test_model.py): 8 new — delimiter int, multi-char delimiter, encoding list, confidential str, min_files str/bool, negative min_files, min_total_size_mb list, real-TOML surface in validate().
- [x] 3.2 tests/test_config.py: 5 new — wrong type for int/str/float keys, bool-for-int, string→list coercion preserved.
- [x] 3.3 MCP integration (tests/test_mcp_server.py): `test_invalid_csv_delimiter_type_ok_false` — `ok:false, exit_code:1`, diagnostic in `config_errors` (auth_status surface; the stable `error_code` mechanism for the exception path is the existing `CONFIG_ERROR` envelope).
- [x] 3.4 CLI integration (tests/test_cli.py): `test_invalid_csv_delimiter_type_validate_returns_1` — rc 1 + diagnostic on stdout.
- [x] 3.5 Profile determinism (tests/test_profile.py): **profiling was not deterministic** — `generated.timestamp` differed between runs. Fixed by honoring `SOURCE_DATE_EPOCH` (reproducible-builds convention) in `profile._now_iso()`: fixed epoch → byte-identical `metadata.yaml` across runs; absent the env var the current UTC time is used (backwards compatible). Test: `test_deterministic_metadata_with_source_date_epoch`.

## Phase 4: Spec sync + docs

- [x] 4.1 **TC-13** (base already used TC-11 for profile_dir/render_dir, TC-12 for card_collapse_threshold): delta synced into `openspec/specs/tool-config/spec.md` (requirement + 9 scenarios incl. SOURCE_DATE_EPOCH determinism).
- [x] 4.2 Verification: full suite **1440 passed, 6 skipped** (was 1424), `ruff check` clean, `ruff format --check` clean, `mypy src/` clean, `git diff --check` clean.

## Phase 5: Archive

- [x] 5.1 `archive-report.md`; move to `openspec/changes/archive/2026-09-09-fix-dataset-config-type-validation/`; commit `chore(sdd): archive fix-dataset-config-type-validation — sync tool-config TC-13 and move to archive`.
- [x] 5.2 Branch `fix/118-config-type-validation` prepared for PR → `dev`; close #118 with per-criterion evidence post-merge (intentionally left OPEN until the PR lands and the `[[file]]`-boolean follow-up is tracked).