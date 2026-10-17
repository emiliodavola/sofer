# Tasks: fix-coverage-guard-freshness

**Change** `2026-10-15-fix-coverage-guard-freshness` (GitHub **#305**) · branch
`fix/305-coverage-guard-freshness` from `dev@fad1b00` · store **hybrid**.

**One-line outcome:** the local coverage pin asserts only on a database it can
vouch for — present, not in flight, and at least as new as every file it measured
— and skips with a named reason otherwise.

---

## TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`. The carrier is a real
red-then-green:

- **RED (measured):** `uv run pytest tests/test_coverage_contract.py -q` after
  adding the policy tests and rewiring the guard, before implementing the helper
  → **7 failed, 2 passed** (`NameError: name '_vouch_for_coverage_data' is not
  defined`).
- **GREEN (measured):** the same selection → **8 passed, 1 skipped** (the skip is
  the guard, correctly declining a database the branch switch had made stale).
- **REFACTOR:** the six policy tests were moved from a class to module-level
  functions, matching the file's existing style and the mapping checker's
  single-`::` node-id grammar; the policy stayed green after the move.

---

## Tasks

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | RED: policy tests for `_vouch_for_coverage_data` (missing file, in-flight run, stale database, vanished measured path, equal-mtime and newer-database acceptance) | done | `7 failed, 2 passed` (`NameError`) |
| T2 | Implement the helper and wire the guard (replacing `skipif` with the helper's reason; re-checking after load) | done | `8 passed, 1 skipped` → `8 passed, 1 skipped` after the refactor |
| T3 | Keep the regressions green: fresh database still asserts; clean checkout still skips | done | pending the post-coverage run recorded in `archive-report.md` |
| T4 | `coverage` spec delta + canonical amendment (COV-01 clause, new scenario, `## Test Mapping` row, COV-07 (b)) | done | `openspec/specs/coverage/spec.md`; checker reports `coverage: 18 scenario(s), mapped` |
| T5 | Live demonstration on the real artifact: a database predating its sources makes the guard skip with a named reason instead of failing | done | `SKIPPED [1] ...: stale coverage database: it is older than a file it measured (_converters.py) — run `uv run coverage run -m pytest` for current numbers` |
| T6 | Gates: full suite, ruff/format/mypy/pyright, `check_test_mapping.py`, archive report, commit | done | see `archive-report.md` (T7 push/PR is parent-owned and pending) |

## Notes

- The guard's own skip is **observable** in this branch's history: switching to
  `dev` rewrote `src/sofer/repo_compliance.py` (removing the #304 change), which
  made the existing fresh database older than a file it measured, and the guard
  skipped instead of asserting — the intended behaviour for a tree the database
  no longer describes.
- `tests/test_ci_workflows.py` is untouched: no workflow, gate script or
  `pyproject.toml` key changed, so the two ban-pinning guards stay green
  unmodified (COV-07).
