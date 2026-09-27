# Tasks: codebook dialect defaults moved out of the signatures (GitHub #260)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~120 authored (codebook ~45, profile ~12, cli docs ~8, tests ~55); SDD artifacts excluded from the review budget |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | single PR |
| Delivery strategy | single-pr |
| Chain strategy | size-exception |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Remove the literal dialect defaults and pin the required-arg contract | PR 1 | `uv run pytest tests/test_codebook.py tests/test_config.py tests/test_profile.py -q` | `uv run pytest tests/ -q` | revert `codebook.py`, `profile.py`, `cli.py`, both test files, canonical `codebook` spec |

## Phase 1: Source

- [x] 1.1 `_read_csv`: `encoding`/`delimiter` required keyword-only; docstring states rule 3 (#260).
- [x] 1.2 `_read_tsv`: `encoding` required keyword-only.
- [x] 1.3 `_read_file`: `delimiter`/`encoding` required keyword-only.
- [x] 1.4 `generate`: `delimiter`/`encoding` required keyword-only; docstring updated.
- [x] 1.5 `src/sofer/profile.py`: both non-streamed `_read_file` calls pass `config.CSV_*`.
- [x] 1.6 `src/sofer/cli.py`: docstring/comment truth updated (no behaviour change).

## Phase 2: Tests

- [x] 2.1 Update every `generate`/`_read_csv`/`_read_tsv`/`_read_file` call in `tests/test_codebook.py` to pass the dialect.
- [x] 2.2 Add `TestDialectParametersAreRequired` (four `TypeError` guards, supplied-dialect proof, no-literal-default inspect guard).
- [x] 2.3 Update `tests/test_config.py::TestTc06PostReloadVisibility` to pass the configured dialect.

## Phase 3: Spec

- [x] 3.1 Write the `codebook` delta (MODIFIED CB-R11/CB-R12 + the fail-closed scenario).
- [x] 3.2 Compose the delta into `openspec/specs/codebook/spec.md` via `gentle-ai sdd-archive-compose`.

## Phase 4: Verification

- [x] 4.1 `uv run pytest tests/ -q` green.
- [x] 4.2 `uv run ruff check src/ tests/ scripts/` and `uv run ruff format --check src/ tests/` clean.
- [x] 4.3 `uv run mypy src/ scripts/` and `uv run pyright` clean.
- [x] 4.4 `bash scripts/check_core_coverage.sh` exit 0 (four 100.00% rows).
- [x] 4.5 `uv run python scripts/check_test_mapping.py` exit 0.
- [x] 4.6 Record verify-phase evidence in `verify-report.md`.

## Phase 5: Archive

- [x] 5.1 `git mv` the change folder to `openspec/changes/archive/2026-09-26-refactor-codebook-dialect-config/` and confirm the canonical composition.
