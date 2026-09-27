# Verify Report: add a push trigger to ci.yml (GitHub #262)

**Change**: `2026-09-26-ci-push-trigger`
**Branch**: `ci/262-ci-push-trigger` (base `dev`)
**Mode**: Standard (Strict TDD disabled)

## Scope Verified

| Scenario | Verification | Result |
|----------|--------------|--------|
| CI-16 — Push trigger targets main and dev | `test_ci_has_push_and_pr_triggers_targeting_main_and_dev` | PASS |
| CI-16 — Pull request trigger still targets main and dev | `test_ci_has_push_and_pr_triggers_targeting_main_and_dev` | PASS |

## Runtime Evidence

| Command | Exit | Observed |
|---------|------|----------|
| `uv run pytest tests/test_ci_workflows.py -q` | 0 | `50 passed` |
| `uv run pytest tests/ -q` | 0 | `1994 passed, 2 skipped` |
| `uv run python scripts/check_test_mapping.py` | 0 | `OK: test-mapping contract holds` (`ci: 48 scenario(s), mapped`) |
| `uv run ruff check src/ tests/ scripts/` | 0 | `All checks passed!` |
| `uv run ruff format --check src/ tests/` | 0 | `73 files already formatted` |
| `uv run mypy src/ scripts/` | 0 | `Success: no issues found in 36 source files` |
| `uv run pyright` | 0 | `0 errors, 1 warning, 0 informations` |

No source file changed, so coverage is unchanged from `dev`. The one pyright
warning (`src/sofer/_toml.py:27`) is pre-existing.

## Independent Verification

A separate read-only verifier (fresh context, no edits) confirmed: `ci.yml`'s
parsed trigger map is `push: [main, dev]` and `pull_request: [main, dev]`;
`codeql.yml` already carries the same branch list; the `git diff` against `dev`
touches only the `on:` block (no `permissions`, no job/step changes); the guard
passes by name and would fail if the `push` block were removed (probed in-memory);
CI-16 has exactly two scenarios and two `test:` mapping rows; and the `ci` spec's
48 scenarios map to 48 rows with no bijection break. Verdict: PASS on all claims.

## Limitations

- The end-to-end trigger behaviour is exercised by GitHub on the next push to
  `dev`/`main`, not by a local run.
- Requirement numbering: CI-16 assumes the sibling PR #268 (CI-15) lands first;
  on this branch the canonical spec has CI-14 → CI-16.

## Result

Both CI-16 scenarios verified; full suite and gates green. Ready for archive.
