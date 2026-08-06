# Tasks: Fix Codebook Index Links and YOUR_USER Placeholder

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~55 (14 production + ~40 test) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Fix links + placeholder validation + all tests | PR 1 | Self-contained, ~55 lines total |

## Phase 1: Fix Root Index Links (TDD: RED → GREEN)

- [x] 1.1 (RED) Update `test_root_index_has_correct_links` in `tests/test_codebook.py` — change expected link from `data/codebooks/f.md` to `codebooks/f.md`
- [x] 1.2 (RED) Add test for nested subdirectory links in `tests/test_codebook.py` — verify `codebooks/Labels/etiquetas_a.md` in root index
- [x] 1.3 (GREEN) Fix link anchor in `generate_all()` at `src/sofer/codebook.py:496` — replace `out_path.relative_to(base_dir)` with `out_path.relative_to(data_dir).as_posix()`

## Phase 2: Placeholder Validation (TDD: RED → GREEN)

- [x] 2.1 (RED) Add model tests in `tests/test_model.py` — `YOUR_USER/dataset`, `YOUR_ORG/dataset`, `your-username/dataset`, `YOUR_ORGANIZATION/dataset` rejected; valid `alice/my-dataset` passes; multi-segment `your-username/sub/project` rejected
- [x] 2.2 (RED) Add CLI tests in `tests/test_cli.py` — placeholder TOML exits 1 with stderr message; valid TOML still generates codebook
- [x] 2.3 (GREEN) Add `_PLACEHOLDERS` frozenset and case-insensitive check in `DatasetConfig.validate()` at `src/sofer/model.py:439` — before regex, split on `/`, check `user_part.lower()`
- [x] 2.4 (GREEN) Call `cfg.validate()` in `_cmd_codebook()` at `src/sofer/cli.py:125` — iterate errors to stderr, `return 1` before `generate_all_codebooks(cfg)`

## Phase 3: Verify

- [x] 3.1 Run `uv run pytest tests/ -q` — all tests pass
- [x] 3.2 Run `uv run ruff check src/ tests/` — no lint errors
- [x] 3.3 Run `uv run mypy src/` — no type errors
