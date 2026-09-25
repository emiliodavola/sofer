# Delta for ci

> **Change** `fix-release-gate-integrity` (GitHub #233; internal CI-03/CI-10 contradiction) ·
> branch `ci/release-gate-integrity` · store **hybrid** (this file + Engram mirror under topic key
> `sdd/fix-release-gate-integrity/spec`).
>
> **One modification, one addition.** CI-10 ("Release test job parity with CI") keeps its test-job
> clauses and its first two scenarios byte-for-byte; the two statements that contradict shipped
> CI-03 — the note sentence naming the COV-06 gate as separately tracked under issue #185, and the
> scenario "COV-06 stays cross-referenced as issue #185" — are removed, because #185 is closed and
> `release.yml`'s `coverage` job runs `bash scripts/check_core_coverage.sh` (CI-03). A new
> requirement **CI-12** carries the release `lint`-job parity (GitHub #233), with three scenarios
> and three Test Mapping rows.
>
> **Rule-6 resolution.** CI-12 S1–S3 map to static guards in `tests/test_ci_workflows.py`. CI-10's
> surviving scenarios keep their existing guards; the removed scenario's guard assertion is dropped
> with it.

## MODIFIED Requirements

### Requirement: Release test job parity with CI (CI-10)

> Added by change `2026-09-24-fix-release-test-parity` (GitHub #209). The release workflow's
> header claims to run the same quality gates as CI, so its `test` job SHALL mirror the CI
> `test` job's OS axis (`ubuntu-latest` + `windows-latest`, driven by
> `runs-on: ${{ matrix.os }}`) and SHALL run the same CLI help smoke test
> (`uv run sofer --help`) after the full-suite step. The COV-06 core-coverage gate in the
> release `coverage` job is owned by CI-03 (GitHub #185, shipped) — this requirement SHALL NOT
> re-implement it.

(Previously: the note claimed the COV-06 gate was "deliberately separate and tracked as issue
#185" and a third scenario required the release header to cross-reference that pending issue;
issue #185 has since shipped and is CI-03's, so both statements contradicted CI-03.)

#### Scenario: Test job OS axis matches CI

- GIVEN `.github/workflows/ci.yml` and `.github/workflows/release.yml`
- WHEN the `test` job matrix declarations are compared
- THEN the release `test` job SHALL run on `${{ matrix.os }}` and SHALL declare the
  same `os` list as the CI `test` job (`ubuntu-latest` and `windows-latest`)

#### Scenario: CLI help smoke test runs at tag time

- GIVEN the release workflow's `test` job steps
- WHEN they are inspected for the entrypoint smoke test
- THEN a step named `Run CLI help smoke test` SHALL run `uv run sofer --help` after
  the `uv run pytest -v` full-suite step, matching `ci.yml`

## ADDED Requirements

### Requirement: Release lint job parity with CI (CI-12)

> Added by change `fix-release-gate-integrity` (GitHub #233). The release workflow header claims
> to run the same quality gates as CI; CI-10 covers the `test` job and this requirement closes the
> `lint` job gap. Before this change the release `lint` job ran only `ruff check` and `mypy`, so a
> formatting regression, a pyright error, or a broken spec↔test mapping could not block a tag even
> though each blocks a PR.

The `lint` job of `.github/workflows/release.yml` SHALL run the same gates as the `lint` job of
`.github/workflows/ci.yml`, in the same order: exactly `uv run ruff check src/ tests/ scripts/`,
then exactly `uv run ruff format --check src/ tests/`, then exactly
`uv run mypy src/ scripts/`, then exactly the bare `uv run pyright`, then exactly
`uv run python scripts/check_test_mapping.py`. No step SHALL re-implement a gate the CI job
delegates: the format gate's scope stays `src/ tests/` (CI-11), pyright stays bare and
config-driven (CI-09), and the mapping checker stays a single direct invocation (MC-07). The
release `lint` job SHALL keep its single `ubuntu-latest` / `"3.13"` axis, so a tag is gated on the
same interpreter the PR pipeline uses. The release workflow header comment SHALL state the
lint-job parity and SHALL NOT claim the COV-06 gate is pending or tracked separately (CI-03 owns
that gate).

#### Scenario: Release lint job runs the three missing gates

- GIVEN `.github/workflows/release.yml`
- WHEN the `lint` job steps are inspected
- THEN a step SHALL run exactly `uv run ruff format --check src/ tests/`
- AND a step SHALL run exactly the bare `uv run pyright`
- AND a step SHALL run exactly `uv run python scripts/check_test_mapping.py`
- AND each SHALL keep the `lint` job's single `ubuntu-latest` / `"3.13"` runner axis

#### Scenario: Release lint gate invocations match the CI lint job

- GIVEN `.github/workflows/ci.yml` and `.github/workflows/release.yml`
- WHEN the ordered gate invocations of both `lint` jobs are compared
- THEN the release `lint` job's gate commands SHALL equal the CI `lint` job's gate commands in the
  same order: `uv run ruff check src/ tests/ scripts/`, `uv run ruff format --check src/ tests/`,
  `uv run mypy src/ scripts/`, `uv run pyright`, `uv run python scripts/check_test_mapping.py`

#### Scenario: Release header states the enforced parity

- GIVEN the release workflow header comment
- WHEN it is read for the parity claim
- THEN it SHALL state that the `lint` job mirrors `ci.yml`'s lint gates
- AND it SHALL NOT describe the COV-06 core-coverage gate as pending or "tracked separately"

