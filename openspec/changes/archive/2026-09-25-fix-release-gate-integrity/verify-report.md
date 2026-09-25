# Verify Report: Release gate integrity (CI-03/CI-10 contradiction + #233 lint parity)

**Change**: `fix-release-gate-integrity`
**Branch**: `ci/release-gate-integrity`
**Mode**: Standard (Strict TDD disabled)

## Scope Verified

| Scenario | Verification | Result |
|----------|--------------|--------|
| CI-10 — Test job OS axis matches CI | `test_release_test_job_mirrors_ci_os_axis_and_cli_smoke` | PASS |
| CI-10 — CLI help smoke test runs at tag time | `test_release_test_job_mirrors_ci_os_axis_and_cli_smoke` | PASS |
| CI-12 — Release lint job runs the three missing gates | `test_release_lint_job_runs_the_ci_lint_gates` | PASS |
| CI-12 — Release lint gate invocations match the CI lint job | `test_release_lint_job_mirrors_ci_lint_invocations` | PASS |
| CI-12 — Release header states the enforced parity | `test_release_header_states_lint_parity_without_the_stale_cov06_claim` | PASS |

The removed CI-10 scenario ("COV-06 stays cross-referenced as issue #185") no longer appears in
`openspec/specs/ci/spec.md`, and its Test Mapping row is gone.

## Runtime Evidence

| Command | Exit | Observed |
|---------|------|----------|
| `uv run pytest tests/test_ci_workflows.py -q` | 0 | `39 passed` |
| `uv run pytest tests/ -q` | 0 | `1849 passed, 2 skipped` |
| `uv run python scripts/check_test_mapping.py` | 0 | `INFO: ci: 40 scenario(s), mapped` / `OK: test-mapping contract holds` |
| `uv run ruff check src/ tests/ scripts/` | 0 | `All checks passed!` |
| `uv run ruff format --check src/ tests/` | 0 | `70 files already formatted` |
| `uv run mypy src/ scripts/` | 0 | `Success: no issues found in 35 source files` |
| `uv run pyright` | 0 | `0 errors, 1 warning, 0 informations` |

The single pyright warning (`src/sofer/_toml.py:27` — `tomli` could not be resolved from source)
is pre-existing and unrelated; CI-09's gate contract is errors-only, and the gate exits 0.

## Independent Verification

A separate read-only verifier confirmed, against the working tree: the release `lint` job's
`(name, run)` step sequence equals the CI `lint` job's; the header drops "tracked separately" and
states lint parity; the `"185"` assertion is gone and the three CI-12 guards exist and pass; the
`ci` spec's 40 scenario headings and 40 Test Mapping rows form an exact bijection with no stale
CI-10 #185 row; and an adversarial sweep of `tests/` and `openspec/specs/` found no other
dependency on the old header wording or the removed scenario. Verdict: PASS on all claims.

## Limitations

- Verify-phase runtime evidence is local; the end-to-end tag-time behaviour is exercised by
  `.github/workflows/release.yml` on a future `v*` tag, not by a local run.
- The archive composition ran `gentle-ai sdd-archive-compose` for requirement blocks; the Test
  Mapping table was edited directly because the compose tool merges requirements only.

## Result

All five scenarios verified; full suite and gates green. Ready for archive.
