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

> Introduced by change `2026-09-13-ci-coverage-codeql` (archived 2026-09-13).

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

> COV-06 (spec `coverage`) is the documented, additive exception: per-file
> scoped `--fail-under=100` gates exist only as the four invocations in
> `scripts/check_core_coverage.sh` referenced by the `ci.yml` coverage job, and
> SHALL NOT weaken or re-declare the config-owned TOTAL floor.

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

### Requirement: Dev interpreter pin matches the gate interpreter (CI-07)

> Added by change `2026-09-14-chore-python-version-313` (GitHub #178). Every scenario below is evidenced by verify-phase static or runtime gate evidence rather than by a pytest assertion — the framing this capability's own Test Mapping already uses for gate exit codes.

The repository's local development interpreter pin — the single-version `.python-version` file at the repository root, which uv resolves for every documented `uv run …` invocation — SHALL name the same Python version the gate-bearing CI jobs run on. `.python-version` SHALL contain exactly `3.13` and SHALL equal both gate pins declared in `.github/workflows/ci.yml`: the `lint` job's `python-version` (which runs `uv run mypy src/ scripts/`) and the `coverage` job's `python-version` (which runs the complete-suite coverage gate plus the four COV-06 per-file scoped gates). The pin SHALL be the single local source of the gate interpreter, so that a clean checkout needs no `--python` flag to run the gates.

The pin SHALL make the documented, flag-free gate commands satisfiable on a clean checkout. `uv run mypy src/` and `uv run mypy src/ scripts/` SHALL exit 0 with zero errors — in particular zero `[no-redef]` errors at the five interpreter-selection fallback sites (`cli.py`, `config.py`, `mcp_registration.py`, `mcp_server.py`, `model.py`). `uv run coverage run -m pytest` followed by `bash scripts/check_core_coverage.sh` SHALL exit 0 with each of the four core rows (`cli.py`, `scanner.py`, `prepare.py`, `publish.py`) at 100.00% and an empty `Missing` column, and the script SHALL reach its last gate (a first-file failure aborts it under `set -euo pipefail`, leaving the remaining gates unverified). A `3.10` pin could satisfy neither gate, because `3.10` installs the conditional `tomli` backport, which makes one arm of every fallback dead and therefore makes the four-module 100.00% mandate unsatisfiable by construction rather than by test quality.

`.python-version` selects the interpreter a developer's tools run under; it SHALL NOT be read as a support declaration. This requirement SHALL NOT change user-facing Python support: `pyproject.toml` `[project] requires-python` SHALL remain `>=3.10`, `[tool.mypy] python_version` SHALL remain `"3.10"` (it declares the minimum language/typing level, tied to `requires-python`, not the developer interpreter), the CI test matrix SHALL keep exercising `3.10`–`3.14`, the TOTAL coverage floor SHALL remain the config-owned `fail_under = 90` (CI-01), and the diff SHALL contain zero `pyproject.toml` paths and zero `.github/workflows/` paths.

`AGENTS.md` rule 12's latent-issue note SHALL be accurate and SHALL record the consequence for a contributor on an older interpreter: it SHALL name all five fallback modules, quote the real fallback form (`import tomli as _tomli` / `import tomllib as _tomli`), record that the pin is `3.13` because a `3.10` development environment installs the `tomli` backport and thereby makes the local `mypy` and COV-06 gates unsatisfiable by construction, keep the existing "do not add mypy to the version matrix" instruction, and state that a contributor on an older interpreter must pass `--python 3.13` explicitly for those two gates. The note SHALL stay where it is and SHALL NOT weaken any other rule-12 bullet.

#### Scenario: Dev pin equals both gate-job pins

- GIVEN `.python-version` at the repository root and `.github/workflows/ci.yml`
- WHEN the pin is read and compared against the `python-version` declared for the
  `lint` job and for the `coverage` job
- THEN `.python-version` SHALL contain exactly `3.13` and no other content
- AND it SHALL equal both job pins, so the local gate interpreter and the CI gate
  interpreter are the same value

#### Scenario: Flag-free mypy gates are green on the pinned interpreter

- GIVEN a clean checkout whose only interpreter selection is `.python-version` (no
  `--python` flag on any command)
- WHEN `uv run mypy src/` and `uv run mypy src/ scripts/` run — the latter being the
  exact entry of the local pre-commit mypy hook
- THEN each SHALL exit 0 with zero errors
- AND in particular no `[no-redef]` error SHALL be reported at any of the five
  interpreter-selection fallback sites, which the `3.10` pin produced

#### Scenario: The COV-06 gate script runs all four scoped gates to completion on the pin

- GIVEN a clean checkout whose only interpreter selection is `.python-version`
- WHEN `uv run coverage run -m pytest` runs and is followed by
  `bash scripts/check_core_coverage.sh`
- THEN the script SHALL exit 0
- AND each of the four core rows SHALL be 100.00% with an empty `Missing` column
- AND the script SHALL NOT abort before its last gate has run, so all four scoped
  gates are verified in the same pass (the pin that made the first row fail left the
  remaining three unverified)

#### Scenario: The latent-issue note states the rationale and the escape hatch

- GIVEN `AGENTS.md` rule 12's latent-issue note
- WHEN the note is read
- THEN it SHALL name all five fallback modules and quote the real fallback form
  (`import tomli as _tomli` / `import tomllib as _tomli`)
- AND it SHALL record that the pin is `3.13` because a `3.10` development environment
  installs the `tomli` backport and makes the local `mypy` and COV-06 gates
  unsatisfiable by construction
- AND it SHALL keep the "do not add mypy to the version matrix" instruction
- AND it SHALL state that a contributor on an older interpreter must pass
  `--python 3.13` explicitly for those two gates

#### Scenario: User-facing support is unchanged

- GIVEN `pyproject.toml`, `.github/workflows/ci.yml`, and this change's diff
- WHEN the support declarations, the coverage floor, and the diff are inspected
- THEN `requires-python` SHALL still be `>=3.10` and `[tool.mypy] python_version`
  SHALL still be `"3.10"`
- AND the CI test matrix SHALL still exercise `3.10`, `3.11`, `3.12`, `3.13`, and
  `3.14`
- AND the TOTAL coverage floor SHALL still be the config-owned `fail_under = 90`
  (CI-01), with no threshold added or re-declared
- AND the diff SHALL contain zero `pyproject.toml` paths and zero
  `.github/workflows/` paths

---

### Requirement: Single authoritative ruff version (CI-08)

> Added by change `2026-09-15-chore-ruff-single-authority` (GitHub #195). Scenarios 1–3 are
> asserted by three static guard tests in `tests/test_ci_workflows.py`; scenario 4 is
> verify-phase runtime evidence — the framing this capability's own Test Mapping already
> uses for gate exit codes.

The repository SHALL declare exactly one authoritative ruff version, and the three
declarations that decide which ruff runs SHALL name that same version: the `pyproject.toml`
dev-group pin (an exact `==X.Y.Z` specifier, never a floor), `[tool.ruff] required-version`
in `pyproject.toml`, and the `astral-sh/ruff-pre-commit` entry's `rev` in
`.pre-commit-config.yaml` (`vX.Y.Z`). The dev pin SHALL be the single source of the value —
`required-version` and the hook `rev` SHALL be derived from it — so a future bump edits
declarations only and SHALL NOT have to edit a test literal.

`[tool.ruff] required-version` SHALL be the enforcing declaration: a binary whose version
does not satisfy it SHALL fail when configuration is loaded, so a drifted environment
errors instead of silently formatting or linting under a version the repository did not
declare. The declarations SHALL be statically guarded in `tests/test_ci_workflows.py`,
extending that module's existing `_read_text` / `_load_toml` / `_load_yaml` helpers: the dev
pin's exact specifier, the `required-version` value, and the hook `rev` SHALL be asserted
equal; no file under `.github/workflows/` SHALL declare a ruff version literal (the version
reaches CI through `uv.lock`, not through a workflow); and the extracted `X.Y.Z` SHALL
appear in `CONTRIBUTING.md`'s Code style section. Each guard SHALL derive the version from
the dev pin and SHALL NOT hardcode a version literal.

This requirement SHALL arm no CI step and SHALL add no workflow file: it SHALL NOT
introduce a `ruff format --check` invocation under `.github/workflows/**`, enforcement of
the staged-file formatter SHALL remain the local pre-commit `ruff-format` hook, and issue
#194 SHALL retain the un-staged-file gap (`process-boundary` PB-10). A change that moves
the pin SHALL refresh `uv.lock` in the same change, confined to the ruff package
block and the dev specifier. `packaging` PKG-06 states the same regeneration class for its own
`fastmcp` declaration and SHALL NOT be read as owning this one: its `uv.lock` clause is scoped to that
declaration, so the obligation for a ruff pin move is stated here, in CI-08.

#### Scenario: Dev pin, required-version, and hook rev agree

- GIVEN the three ruff version declarations — the `[dependency-groups] dev` pin in
  `pyproject.toml`, `[tool.ruff] required-version`, and the `astral-sh/ruff-pre-commit`
  entry in `.pre-commit-config.yaml`
- WHEN `tests/test_ci_workflows.py::test_ruff_pin_hook_rev_and_required_version_agree`
  extracts `X.Y.Z` from the dev pin and compares the other two declarations against it
- THEN the dev specifier SHALL be exact (`==X.Y.Z`, so a `>=` floor SHALL fail the guard)
- AND `[tool.ruff] required-version` SHALL equal `"==" + X.Y.Z`
- AND the hook entry's `rev` SHALL equal `"v" + X.Y.Z`

#### Scenario: No workflow declares a ruff version

- GIVEN every file under `.github/workflows/`
- WHEN `tests/test_ci_workflows.py::test_workflows_do_not_declare_a_ruff_version` scans
  them for a ruff version literal
- THEN zero matches SHALL exist, so the authority stays in the three declarations and CI
  receives the version through `uv.lock`

#### Scenario: CONTRIBUTING names the declared version

- GIVEN `CONTRIBUTING.md`'s Code style section
- WHEN `tests/test_ci_workflows.py::test_contributing_names_the_declared_ruff_version`
  looks for the `X.Y.Z` extracted from the dev pin
- THEN that value SHALL appear
- AND the guard SHALL hold no version literal of its own, so a bump cannot leave the
  documentation silently stale

#### Scenario: required-version rejects a mismatched binary

- GIVEN the repository's declared `[tool.ruff] required-version` and a mismatch probe that
  declares a different required version
- WHEN `uv run ruff check src/ tests/ scripts/` and
  `uv run ruff format --check src/ tests/ scripts/` run under the probe, and both run again
  under the declared value
- THEN each probe run SHALL exit non-zero and SHALL report both the required and the
  running version
- AND each declared-value run SHALL exit 0, so the mismatch fails loudly instead of
  disagreeing quietly
- AND this evidence is **verify-phase runtime evidence** — the commands above, pasted with
  their exit codes into the verify report (CI-01 gate-exit-code precedent)

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
| CI-07 | Dev pin equals both gate-job pins | Verify-phase static evidence — `.python-version` read against the `lint` and `coverage` job pins in `ci.yml` |
| CI-07 | Flag-free mypy gates are green on the pinned interpreter | Verify-phase runtime evidence — `uv run mypy src/` and `uv run mypy src/ scripts/` exit codes (CI-01 gate-exit-code precedent) |
| CI-07 | The COV-06 gate script runs all four scoped gates to completion on the pin | Verify-phase runtime evidence — `bash scripts/check_core_coverage.sh` exit code with four 100.00% rows (COV-06 precedent) |
| CI-07 | The latent-issue note states the rationale and the escape hatch | Verify-phase static evidence — `AGENTS.md` rule 12 text inspection |
| CI-07 | User-facing support is unchanged | Verify-phase static evidence — diff and config inspection (zero `pyproject.toml` / `.github/workflows/` paths, `fail_under = 90` intact) |
| CI-08 | Dev pin, required-version, and hook rev agree | `tests/test_ci_workflows.py` — `test_ruff_pin_hook_rev_and_required_version_agree`: tomllib + YAML declaration equality, with `X.Y.Z` extracted from the dev pin |
| CI-08 | No workflow declares a ruff version | `tests/test_ci_workflows.py` — `test_workflows_do_not_declare_a_ruff_version`: YAML/full-text scan of `.github/workflows/*.yml` |
| CI-08 | CONTRIBUTING names the declared version | `tests/test_ci_workflows.py` — `test_contributing_names_the_declared_ruff_version`: text inspection of `CONTRIBUTING.md` |
| CI-08 | required-version rejects a mismatched binary | Verify-phase runtime evidence — `uv run ruff check src/ tests/ scripts/` and `uv run ruff format --check src/ tests/ scripts/` exit codes under a mismatched `required-version` probe and under the declared value (CI-01 gate-exit-code precedent) |
