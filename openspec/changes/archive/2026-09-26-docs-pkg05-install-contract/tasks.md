# Tasks: PKG-05 install contract (#259)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~30 authored (spec + test) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Delivery strategy | single-pr |

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command |
|------|------|-----------|----------------------|
| 1 | PKG-05 states the real git-tag install contract and is tested | PR 1 | `uv run pytest tests/test_packaging.py -q -k readme` |

## Phase 1: Spec

- [x] 1.1 PKG-05 canonical requirement + scenario → git-tag install contract; provenance note.
- [x] 1.2 Delta spec mirrors the canonical block.

## Phase 2: Test

- [x] 2.1 `_project_homepage` + `_documented_git_tag_commands` helpers.
- [x] 2.2 `test_readme_documents_the_git_tag_install_paths` for README.md + README_ES.md.
- [x] 2.3 Module docstring updated.

## Phase 3: Verify

- [x] 3.1 Focused test + negative controls.
- [x] 3.2 Full suite green; ruff/mypy/pyright clean.
- [x] 3.3 `scripts/check_test_mapping.py` exit 0 (packaging stays a registered backlog spec).
- [x] 3.4 Independent read-only verification.
- [x] 3.5 Record evidence + scenario mapping in `verify-report.md`.

## Phase 4: Archive

- [x] 4.1 Move the change folder to `openspec/changes/archive/2026-09-26-docs-pkg05-install-contract/`.
