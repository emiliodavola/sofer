# Tasks: Overwrite Bypass for Auto-Generated Compliance Files

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~40 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

## Batch 1: Implementation (RED → GREEN → VERIFY)

- [x] 1.1 **RED** — `tests/test_uploader.py`: Add `test_readme_license_always_uploaded` (mock `existing_files` with README.md + LICENSE, assert `_check_overwrite_protection` returns empty set). Add `test_missing_codebooks_advisory` (mock absent codebook paths, capture stdout, assert advisory string).
- [x] 1.2 **GREEN** — `src/sofer/uploader.py`: Add `_AUTO_GENERATED = frozenset({"readme.md", "license", "codebook.md"})`. Modify `_check_overwrite_protection` to skip auto-generated files by name and `codebooks/` prefix. Add codebook advisory in `upload()` before RC-C01 block. Update `force` docstring.
- [x] 1.3 **VERIFY** — Run `uv run ruff check src/`, `uv run mypy src/`, `uv run pytest tests/test_uploader.py -q`. All must pass with no regressions.
