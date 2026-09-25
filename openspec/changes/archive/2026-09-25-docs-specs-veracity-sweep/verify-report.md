# Verify Report: Specs/docs veracity sweep — uploader.py, inventories, project.md (#188, #236, #187, #184)

**Change**: `docs-specs-veracity-sweep`
**Branch**: `docs/specs-veracity-sweep`
**Work-unit commits**: `bd91eee`, `8e51139`, `4e67352`, `ffa55b5`
**Mode**: ODD (documentation/spec prose; no runtime boundary)

## Scope Verified

| Issue | Acceptance criterion | Result |
|-------|----------------------|--------|
| #188 | Every `uploader.py` requirement retargeted or marked superseded | PASS |
| #188 | The duplicated per-module coverage floor defers to the `coverage` capability | PASS |
| #188 | `openspec/specs/cli/spec.md:20` untouched | PASS (not in diff) |
| #236 | No live doc names `uploader.py` as a live module; layout uses `raw/`; no version-constant claim | PASS |
| #187 | AGENTS rule 10 + CONTRIBUTING tree cover the module set or defer to the directory | PASS |
| #187 | CONTRIBUTING names `[tool.ruff]` in `pyproject.toml`; no `ruff.toml` | PASS |
| #184 | `project.md` records coverage as installed; four stale statements corrected, counts dropped | PASS |
| #180 | No `user="emiliodavola"` in canonical specs | PASS |
| rule 6 | test-mapping contract holds | PASS |

## Runtime Evidence

| Command | Exit | Observed |
|---------|------|----------|
| `uv run python scripts/check_test_mapping.py` | 0 | `OK: test-mapping contract holds` |
| `uv run pytest tests/test_ci_workflows.py -q` | 0 | `39 passed in 6.68s` |
| `uv run pytest tests/ -q` | 0 | `1849 passed, 2 skipped, 1 warning in 284.92s (0:04:44)` |
| `uv run ruff check src/ tests/ scripts/` | 0 | `All checks passed!` |
| `uv run ruff format --check src/ tests/` | 0 | `70 files already formatted` |
| `uv run mypy src/ scripts/` | 0 | `Success: no issues found in 35 source files` |
| `uv run pyright` | 0 | `0 errors, 1 warning, 0 informations` |

The single pyright warning (`src/sofer/_toml.py:27` — `tomli` could not be resolved from
source) is pre-existing on `dev`; the source tree is unchanged.

## Static Evidence

- `git grep -n 'uploader\.py' -- openspec/specs` returns only explicitly historical/superseded
  mentions (parquet-conversion §4 heading/banner/checklist; repo-compliance checklist note).
- `git grep -n 'user="emiliodavola"' -- openspec/specs` → empty.
- `git grep -n 'ruff\.toml' -- CONTRIBUTING.md` → empty; `ruff.toml` does not exist.
- `git grep -n '1342\|29 files\|not installed' -- openspec/project.md` → empty.
- The CONTRIBUTING tree module set equals `git ls-files src/sofer/*.py` (33/33).
- `src/sofer/uploader.py` does not exist; `__init__.py` exports no version constant and
  `_version.py` resolves from installed metadata.

## Independent Verification

A separate read-only sub-agent verified all six claim groups against the tree and returned
`OVERALL: PASS`, confirming the spec owners, the coverage deferrals, the inventories
(33/33 modules), the `[tool.ruff]` location, the `project.md` corrections, the de-identification,
`check_test_mapping.py` OK, and `test_ci_workflows.py` green.

Its one adversarial caveat found two residual stale `uploader` references outside the literal
`uploader.py` pattern — `repo-compliance/spec.md` §7.3 (`uploader.upload()`) and
`codebook/spec.md` CB-R04 (`uploader's HF staging`). Both were **closed in `ffa55b5`** after
verification; the follow-up touches only those two prose lines.

## Limitations

- The independent verification ran at the three-commit boundary (`4e67352`); the follow-up
  `ffa55b5` is two prose-line changes whose greps are re-derived in Static Evidence above and
  whose full-suite result is the HEAD run reported in Runtime Evidence.
- No spec-governed behavior changes, so there is no scenario-mapped guard for the
  documentation; evidence is static inspection, the checker, and the suite.

## Result

All acceptance criteria verified; full suite and gates green at HEAD. Ready for archive.
