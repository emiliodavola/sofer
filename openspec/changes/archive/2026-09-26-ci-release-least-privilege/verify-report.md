# Verify Report: scope release.yml write access to the release job (GitHub #261)

**Change**: `2026-09-26-ci-release-least-privilege`
**Branch**: `ci/261-release-permissions` (base `dev`)
**Mode**: Standard (Strict TDD disabled)

## Scope Verified

| Scenario | Verification | Result |
|----------|--------------|--------|
| CI-15 — Workflow-level permissions grant no write access | `test_release_workflow_permissions_are_least_privilege` | PASS |
| CI-15 — Only the release job declares contents write | `test_release_workflow_permissions_are_least_privilege` | PASS |

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

The one pyright warning (`src/sofer/_toml.py:27`, `tomli`) is pre-existing; the
gate is errors-only and exits 0. No source file changed, so coverage is unchanged
from `dev`.

## Independent Verification

A separate read-only verifier (fresh context, no edits) confirmed: the
workflow-level `permissions` table is exactly `{contents: read}` with no write
scope; only the `release` job declares `contents: write` (and no other write
scope), justified by its `softprops/action-gh-release@v3` step; `codeql.yml`'s
permissions are unchanged; the guard exists and passes by name; CI-15 carries
exactly two scenarios and two `test:` mapping rows; and no gate/`needs` step was
weakened. Verdict: PASS on all claims.

## Limitations

- The end-to-end token behaviour is exercised by `.github/workflows/release.yml`
  on a future `v*` tag, not by a local run.

## Result

Both CI-15 scenarios verified; full suite and gates green. Ready for archive.
