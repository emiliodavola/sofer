# Delta for coverage

> **Change** `2026-10-15-fix-coverage-guard-freshness` (issue **#305**) · branch
> `fix/305-coverage-guard-freshness` from `dev@fad1b00` · store **hybrid**
> (`odd/tasks/coverage-guard-freshness.md` + this folder).
>
> **Two modifications, no new requirement, no gate armed.** COV-01's optional
> contract guard gains the vouch condition for the local data file it reads;
> COV-07's rationale (b) accounts for the second skip. Nothing is added to
> `scripts/check_core_coverage.sh`, either workflow, or `pyproject.toml`, so
> COV-07's "No gate is armed for the three second-tier floors" scenario stays
> true **unmodified**.

## MODIFIED Requirements

### Requirement: Per-file coverage floor for the three second-tier modules (COV-01)

The floor, its scenarios and its evidence class are unchanged. The optional
guard clause now reads (verbatim, as it reads in the canonical spec after this
change):

The change MAY additionally guard the floors with a `tests/test_coverage_contract.py`
regression guard that asserts the three rows and TOTAL from a local `.coverage`
data file when one is present **and the guard can vouch for it**, and SHALL skip
otherwise — on a clean checkout (the data file is gitignored local state, so a
clean checkout SHALL never fail on its absence), when a measurement is in flight
(`COVERAGE_RUN` is set: `coverage run` flushes its data file at process exit, so
during the run the file on disk belongs to a previous run), and when the database
is older than any file it measured (`db_mtime >= max(measured mtime)`, comparing
with `>=` because filesystem timestamps have limited granularity). The skip SHALL
name the condition that failed.

#### Scenario: Contract guard skips an unvouchable database — issue #305

- GIVEN a local `.coverage` data file that either predates a file it measured, was
  measured by a run still in flight, or measured a path that no longer exists
- WHEN the suite runs
- THEN the contract test SHALL skip, naming the failed condition
- AND the suite SHALL pass without it — a spurious floor failure on numbers that
  describe a different tree is exactly the defect this skip prevents

### Requirement: Second-tier per-file floors are deliberately verify-phase-only (COV-07)

The requirement, its enforcement boundary and its scenario are unchanged; only
the rationale item (b) is amended to account for the second skip:

- (b) the only executable in-repo ≥90 check, `tests/test_coverage_contract.py`,
  skips when no local `.coverage` data file is present **or when it cannot vouch
  for the one that is — a measurement in flight, or a database older than the
  files it measured (issue #305)** — which is exactly the state the CI coverage
  job collects in, and COV-01-S3 declares that skip intended.

The skip is not a gate: it is the same optional, verify-phase-only guard, now
refusing to assert on data it cannot attribute to the current tree. COV-07's
"No gate is armed" scenario remains true unmodified.

## Test Mapping (added row)

The `coverage` spec carries a `## Test Mapping` table (it is not a
declared-backlog spec), so the new scenario is mapped rather than left unmapped:

| Req | Scenario | Verification |
| --- | -------- | ------------ |
| COV-01 | Contract guard skips an unvouchable database — issue #305 | test:tests/test_coverage_contract.py::test_vouch_rejects_stale_database — the policy test for the staleness condition, plus its five siblings (missing file, in-flight run, vanished measured path, and the two vouched-for cases); the guard itself keeps the COV-01-S3 skip behaviour |
