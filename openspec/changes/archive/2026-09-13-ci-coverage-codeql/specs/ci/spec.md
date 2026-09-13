# ci Specification

## Purpose

Contracts for sofer's continuous-integration presence: the total-coverage gate
(CI-01..CI-03), CodeQL scanning cadence and config (CI-04..CI-05), and the
declared config + documentation truth that keeps the gate enforced and
discoverable (CI-06). The `packaging` spec remains the untouched distribution
contract — release gating that stops publishing below the coverage floor lives
here, not in `packaging`. The coverage run SHALL re-execute the complete test
suite, holding the invariant pinned by `process-boundary` PB-05 (which SHALL
remain unchanged), so the gate measures the same suite CI gates today.

## Requirements

### Requirement: Coverage gate in config (CI-01)

Total coverage SHALL be gated at `fail_under = 90` declared in `pyproject.toml`
`[tool.coverage.report]`, next to the existing `show_missing = true`. The
threshold SHALL live in config only: no CI or release workflow incantation SHALL
hardcode a coverage floor, pass a `--fail-under=N` flag, or duplicate the value —
coverage.py SHALL enforce the gate itself by reading `[tool.coverage.report]`
and exiting non-zero below the floor. Changing the floor SHALL be a spec change
to this requirement, never an ad-hoc workflow tweak. The coverage run SHALL
execute the complete suite (`coverage run -m pytest`), consistent with PB-05's
complete-run gate, never a focused subset.

#### Scenario: Config declares the 90% floor

- GIVEN `pyproject.toml` parsed with `tomllib`
- WHEN the `[tool.coverage.report]` table is inspected
- THEN `fail_under = 90` SHALL be present alongside `show_missing = true`

#### Scenario: Gate is config-driven

- GIVEN `[tool.coverage.report] fail_under = 90` and the CI/release workflows
- WHEN the coverage invocations in `.github/workflows/ci.yml` and
  `.github/workflows/release.yml` are inspected
- THEN no threshold literal and no `--fail-under=N` flag SHALL appear — the gate
  SHALL be enforced by coverage.py reading the config
- AND `uv run coverage report -m` SHALL exit 0 when coverage is at or above the
  floor and non-zero below it (verify-phase local gate run)

#### Scenario: Report honors show_missing

- GIVEN `[tool.coverage.report]` with `show_missing = true`
- WHEN `coverage report -m` runs in a coverage job
- THEN the output SHALL list per-file missed lines in the job log

---

### Requirement: Self-hosted coverage evidence (CI-02)

CI SHALL produce self-hosted coverage evidence only: an `htmlcov` directory
uploaded as a GitHub Actions artifact and a missing-lines report in the job log
via `coverage report -m`. Both `ci.yml` and `release.yml` SHALL carry a dedicated
`coverage` job on `ubuntu-latest` with Python 3.13 (one OS × one Python keeps
measurements deterministic) whose gate step is the complete-suite run (PB-05).
Neither workflow SHALL upload XML (Cobertura), reference Codecov, or reference
coverage badges — the only evidence consumers are the artifact and the log.

#### Scenario: htmlcov artifact step present

- GIVEN `ci.yml` and `release.yml`
- WHEN the `coverage` job steps are inspected
- THEN each SHALL run `coverage html` and upload the `htmlcov` directory via
  `actions/upload-artifact`

#### Scenario: Missing-lines list in the job log

- GIVEN the `coverage` job in either workflow
- WHEN the report step is inspected
- THEN it SHALL invoke `coverage report -m`, putting per-file missed-line lists
  in the job log

#### Scenario: No XML or third-party coverage references

- GIVEN both workflow files
- WHEN scanned for `coverage xml`, `codecov`, and badge markers
- THEN zero matches SHALL exist

---

### Requirement: Release gated on the coverage job (CI-03)

The release workflow SHALL gate publishing on the CI-01 coverage gate: a
dedicated `coverage` job SHALL exist in `.github/workflows/release.yml`, and
`build`, `citation-check`, and `release` SHALL each declare it in their `needs`
(the `citation-check` job, which currently runs parallel, SHALL gain `coverage`
in its `needs`). A tag push whose total coverage is below the CI-01 floor SHALL
produce no wheel-build validation and no GitHub Release — there SHALL be no
publish path that skips the gate.

#### Scenario: Coverage job in the release needs chain

- GIVEN `.github/workflows/release.yml`
- WHEN the job dependency graph is inspected
- THEN a `coverage` job SHALL exist, and `build`, `citation-check`, and `release`
  SHALL each declare `coverage` in their `needs`

#### Scenario: Tag push below the floor yields no release

- GIVEN the release `needs` chain terminates in `release` only after `coverage`
- WHEN a tag push triggers release while total coverage is below the CI-01 floor
- THEN the `coverage` job SHALL fail, `build`/`citation-check`/`release` SHALL be
  skipped, and no GitHub Release SHALL be produced

---

### Requirement: CodeQL scan cadence and SARIF upload (CI-04)

CodeQL SHALL scan the Python codebase through a versioned Advanced-Setup
workflow committed at `.github/workflows/codeql.yml` — enabled by the workflow,
never by GitHub's Default Setup UI. Scanning SHALL trigger on push to `main` and
`dev`, on pull requests targeting `main` and `dev`, and on a weekly `schedule`
cron. The workflow SHALL declare `permissions: security-events: write` so the
`analyze` step uploads SARIF results to the Security tab; results SHALL be
informational only (no merge gating).

#### Scenario: Push, PR, and weekly triggers present

- GIVEN `.github/workflows/codeql.yml` parsed
- WHEN the triggers are enumerated
- THEN `push` SHALL target `[main, dev]`, `pull_request` SHALL target
  `[main, dev]`, and a `schedule` with a weekly `cron` SHALL be declared

#### Scenario: Pull request includes dev

- GIVEN the parsed `pull_request` trigger
- WHEN its branch list is inspected
- THEN `dev` SHALL be included alongside `main`

#### Scenario: SARIF upload permission granted

- GIVEN `.github/workflows/codeql.yml`
- WHEN the workflow permissions and the `analyze` step are inspected
- THEN `permissions.security-events` SHALL equal `write` and the `analyze` step
  SHALL declare `languages: python`, uploading SARIF (the default once the
  permission is granted)

---

### Requirement: CodeQL Advanced Setup config with paths-ignore (CI-05)

CodeQL SHALL run with an explicit config file at `.github/codeql/config.yml`
referenced by the `init` step (Advanced Setup), using default queries. The config
SHALL declare `paths-ignore` covering non-code trees — `docs/`, `.github/`,
`openspec/`, and generated artifacts — while SHALL NOT excluding the code tree
(`src/sofer/`), keeping findings code-relevant.

#### Scenario: Config file referenced by init

- GIVEN `.github/workflows/codeql.yml`
- WHEN the `init` step is inspected
- THEN it SHALL pass `config-file: ./.github/codeql/config.yml` and declare
  `languages: python`

#### Scenario: Paths-ignore covers non-code trees

- GIVEN `.github/codeql/config.yml` parsed
- WHEN its `paths-ignore` list is inspected
- THEN `docs/`, `.github/`, and `openspec/` SHALL be present
- AND `src/sofer/` SHALL NOT be listed

---

### Requirement: Declared coverage config and documentation truth (CI-06)

`openspec/config.yaml` SHALL declare coverage available —
`testing.coverage.available: true`, `testing.coverage.command` set to the
coverage invocation, and `rules.verify.coverage_threshold: 90` — so the SDD
verify phase enforces the same floor CI-01 does. CONTRIBUTING.md SHALL document
the 90% floor and the coverage commands, replacing the vague "Target: no drop in
coverage" line. README.md and README_ES.md SHALL carry a mirrored
quality-gates/CI section: headings mirror (AGENTS.md rule 13) and technical
content stays in English in both files; no badge SHALL be added. The PR template
checklist SHALL include a coverage-gate item.

#### Scenario: Config declares coverage available at 90

- GIVEN `openspec/config.yaml` parsed
- WHEN the testing and rules sections are inspected
- THEN `testing.coverage.available` SHALL be true, `testing.coverage.command`
  SHALL be the coverage invocation, and `rules.verify.coverage_threshold` SHALL
  equal 90

#### Scenario: CONTRIBUTING documents the floor

- GIVEN `CONTRIBUTING.md`
- WHEN the Development commands and Testing sections are inspected
- THEN the coverage commands SHALL be documented with the 90% floor, and the
  "no drop in coverage" placeholder SHALL be gone

#### Scenario: README mirrors README_ES

- GIVEN README.md and README_ES.md
- WHEN the quality-gates/CI section is compared across both files
- THEN the section headings SHALL mirror and technical content SHALL be English
  in both files, with no badge added

#### Scenario: PR template checklist item

- GIVEN `.github/PULL_REQUEST_TEMPLATE.md`
- WHEN the Checklist section is inspected
- THEN a coverage-gate checkbox item SHALL be present alongside the existing
  README_ES sync item

---

## Test Mapping

Every scenario SHALL map to a green test or to verify-phase static evidence
(AGENTS.md rule 6; rules.specs). Static workflow/config assertions live in
`tests/test_ci_workflows.py` (pyyaml + tomllib); runtime gate exit-code evidence
comes from the local `uv run coverage report -m` run; the README/README_ES mirror
and release-no-release scenarios follow the PB-05/MSP-R12 precedent of static
evidence recorded in the verify report.

| Req | Scenario | Verification |
| --- | -------- | ------------ |
| CI-01 | Config declares the 90% floor | `tests/test_ci_workflows.py` — tomllib parse of `pyproject.toml` |
| CI-01 | Gate is config-driven | `tests/test_ci_workflows.py` — YAML inspection (no floor literal, no `--fail-under`); local gate run — `uv run coverage report -m` exit code (verify-phase runtime evidence) |
| CI-01 | Report honors show_missing | `tests/test_ci_workflows.py` — tomllib parse of `pyproject.toml` |
| CI-02 | htmlcov artifact step present | `tests/test_ci_workflows.py` — YAML inspection of ci.yml + release.yml |
| CI-02 | Missing-lines list in the job log | `tests/test_ci_workflows.py` — YAML inspection |
| CI-02 | No XML or third-party coverage references | `tests/test_ci_workflows.py` — YAML/full-text scan |
| CI-03 | Coverage job in the release needs chain | `tests/test_ci_workflows.py` — YAML inspection of release.yml `needs` |
| CI-03 | Tag push below the floor yields no release | Verify-phase static evidence — needs-chain proof per the PB-05/MSP-R12 precedent (no release path below the floor) |
| CI-04 | Push, PR, and weekly triggers present | `tests/test_ci_workflows.py` — YAML inspection of codeql.yml |
| CI-04 | Pull request includes dev | `tests/test_ci_workflows.py` — YAML inspection |
| CI-04 | SARIF upload permission granted | `tests/test_ci_workflows.py` — YAML inspection |
| CI-05 | Config file referenced by init | `tests/test_ci_workflows.py` — YAML inspection |
| CI-05 | Paths-ignore covers non-code trees | `tests/test_ci_workflows.py` — YAML inspection of `.github/codeql/config.yml` |
| CI-06 | Config declares coverage available at 90 | `tests/test_ci_workflows.py` — pyyaml parse of `openspec/config.yaml` |
| CI-06 | CONTRIBUTING documents the floor | `tests/test_ci_workflows.py` — text inspection of CONTRIBUTING.md |
| CI-06 | README mirrors README_ES | Verify-phase static evidence — section mirror diff (PB-05/MSP-R12 precedent); not pytest-assertable |
| CI-06 | PR template checklist item | `tests/test_ci_workflows.py` — text inspection of the PR template |
