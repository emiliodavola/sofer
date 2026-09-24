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
> `scripts/check_core_coverage.sh` referenced by the `ci.yml` and `release.yml`
> coverage jobs, and SHALL NOT weaken or re-declare the config-owned TOTAL floor.

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
publish path that skips the gate. The release `coverage` job SHALL additionally
invoke the COV-06 per-file 100% gates via `bash scripts/check_core_coverage.sh`
— the same script the `ci.yml` coverage job runs, not a re-implementation — so
a tag cannot publish while a core module (`cli.py`, `scanner.py`, `prepare.py`,
`publish.py`) sits below the AGENTS.md rule-14 mandate the PR pipeline enforces.

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

#### Scenario: Release coverage job runs the core 100% gates

- GIVEN `.github/workflows/release.yml`
- WHEN the `coverage` job steps are inspected
- THEN one step SHALL run exactly `bash scripts/check_core_coverage.sh` — the
  same COV-06 gate script the `ci.yml` coverage job runs — so a core module
  below 100% fails the job before `build`/`citation-check`/`release` run

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
verify phase enforces the same floor CI-01 does. `openspec/config.yaml` is a
committed project artifact (issue #210, decision a): it SHALL NOT be gitignored,
so the S1 guard asserts on it unconditionally in every checkout. CONTRIBUTING.md SHALL document
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
>
> Modified by `2026-09-15-chore-type-gate-policy` (GitHub #201) — the `[tool.mypy] python_version` declaration
> moved to `"3.11"` by maintainer decision; the `.python-version` pin, its equality with both gate-job pins, and
> every other clause are unchanged.

The repository's local development interpreter pin — the single-version `.python-version` file at the repository root, which uv resolves for every documented `uv run …` invocation — SHALL name the same Python version the gate-bearing CI jobs run on. `.python-version` SHALL contain exactly `3.13` and SHALL equal both gate pins declared in `.github/workflows/ci.yml`: the `lint` job's `python-version` (which runs `uv run mypy src/ scripts/`) and the `coverage` job's `python-version` (which runs the complete-suite coverage gate plus the four COV-06 per-file scoped gates). The pin SHALL be the single local source of the gate interpreter, so that a clean checkout needs no `--python` flag to run the gates.

The pin SHALL make the documented, flag-free gate commands satisfiable on a clean checkout. `uv run mypy src/` and `uv run mypy src/ scripts/` SHALL exit 0 with zero errors — in particular zero `[no-redef]` errors at the five interpreter-selection fallback sites (`cli.py`, `config.py`, `mcp_registration.py`, `mcp_server.py`, `model.py`). `uv run coverage run -m pytest` followed by `bash scripts/check_core_coverage.sh` SHALL exit 0 with each of the four core rows (`cli.py`, `scanner.py`, `prepare.py`, `publish.py`) at 100.00% and an empty `Missing` column, and the script SHALL reach its last gate (a first-file failure aborts it under `set -euo pipefail`, leaving the remaining gates unverified). A `3.10` pin could satisfy neither gate, because `3.10` installs the conditional `tomli` backport, which makes one arm of every fallback dead and therefore makes the four-module 100.00% mandate unsatisfiable by construction rather than by test quality.

`.python-version` selects the interpreter a developer's tools run under; it SHALL NOT be read as a support declaration. This requirement SHALL NOT change user-facing Python support: `pyproject.toml` `[project] requires-python` SHALL remain `>=3.10`, `[tool.mypy] python_version` SHALL be `"3.11"` — the language level mypy analyses against, declared independently of both `requires-python` (`>=3.10`, the support floor) and `.python-version` (`3.13`, the gate interpreter). At `3.11` the `import tomllib as _tomli` arm of the interpreter-selection fallbacks is a resolvable stdlib module for mypy, while the marker-only `tomli` arm is covered by the global `ignore_missing_imports = true`. It SHALL NOT be read as a support declaration: `requires-python` SHALL remain `>=3.10`. A change that moves this value SHALL amend this clause in the same change. The CI test matrix SHALL keep exercising `3.10`–`3.14`, the TOTAL coverage floor SHALL remain the config-owned `fail_under = 90` (CI-01), and the diff SHALL contain zero `pyproject.toml` paths and zero `.github/workflows/` paths.

(Previously: this clause required `[tool.mypy] python_version` to remain `3.10` and described it as the
minimum language level tied to `requires-python`; the maintainer declared `"3.11"` as the analysis level and
change `2026-09-15-chore-type-gate-policy` (GitHub #201) amends the clause to match the committed
configuration.)

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
  SHALL be `"3.11"` — the declared analysis level, amended by change
  `2026-09-15-chore-type-gate-policy` (GitHub #201) to match the committed configuration
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
the staged-file formatter SHALL remain the local pre-commit `ruff-format` hook, and the
un-staged-file gap (`process-boundary` PB-10) SHALL be closed by CI-11, which arms
`ruff format --check src/ tests/` in the `lint` job (GitHub #194). A change that moves
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

### Requirement: Type-gate posture — `tests/` excluded from both type gates and pyright adopted as a real gate (CI-09)

> Added by change `2026-09-15-chore-type-gate-policy` (GitHub #201). Scenarios 1–4 are asserted
> by static guard tests in `tests/test_ci_workflows.py`; scenario 5's mypy-exit-zero half is
> verify-phase runtime evidence — the framing this capability's Test Mapping already uses for gate
> exit codes.

**Clause group Q1 — the `tests/` exclusion (the durable record of decision (a)).**

The repository SHALL keep `tests/` out of **every** enforced type gate. `[tool.mypy] exclude` SHALL contain
`tests/`; every mypy invocation in `.github/workflows/ci.yml` and `.pre-commit-config.yaml` SHALL name
`src`/`scripts` and SHALL NOT name `tests`; and `[tool.pyright] exclude` SHALL contain `tests`, so the
exclusion is declared once in configuration and the pyright gate SHALL be invoked **bare** (no path
arguments) for that declaration to be the single authority. The posture SHALL be documented in
`CONTRIBUTING.md`'s type-checking section, and this requirement SHALL NOT be read as relaxing
`process-boundary` PB-07: new test helpers SHALL still be type-annotated by convention even though neither
gate analyses them.

**Clause group Q2 — the pyright gate (the durable record of decision (c)).**

pyright SHALL be a **real** gate, not an advisory analyzer. `pyproject.toml` SHALL declare exactly one
`[tool.pyright]` table — the single configuration authority; no `pyrightconfig.json` SHALL exist anywhere in
the tree, because pyright silently prefers it over the table. That table SHALL declare
`typeCheckingMode = "standard"`, `include` covering `src` and `scripts` (the enforced mypy scope),
`exclude` containing `tests`, `pythonVersion` equal to the gate interpreter that `.python-version` pins,
`stubPath` naming the committed `tomli` stub directory, and SHALL NOT globally disable
`reportMissingImports`. One step in the `lint` job of `.github/workflows/ci.yml` SHALL run the gate, and one
local pre-commit hook SHALL run it locally, mirroring the `mypy` hook's shape (`pass_filenames: false`).

pyright SHALL be pinned by an exact `pyright==X.Y.Z` entry in `[dependency-groups] dev`, and the version
SHALL reach CI through `uv.lock`: **no file under `.github/workflows/` SHALL declare a pyright version
literal**. pyright has no `required-version` analogue, so the enforcement SHALL be a runtime equality proof
— `uv run pyright --version` SHALL equal the dev pin — recorded as verify-phase evidence.

The gate's exit contract SHALL be **errors only**: no invocation SHALL pass `--warnings`, and any rule the
repository wants to bind SHALL be declared at `error` severity in `[tool.pyright]` rather than left at
warning severity and hoped for. The measured `"N errors, M warnings"` summary SHALL be recorded as
verify-phase evidence so a warning-count jump is visible without failing the build.

The four `tomli` fallback sites that still select the parser behind `try:` / `except ImportError:`
(`cli.py`, `config.py`, `mcp_registration.py`, `model.py`) SHALL be resolved by the committed stub under
`stubPath`; `mcp_server.py`'s fallback is version-gated (`sys.version_info >= (3, 11)`), so a static checker
prunes its `tomli` arm and it needs no stub. `tomli` SHALL NOT be added to any dependency group, which would
make the fallback arm dead on the pinned interpreter and break the `cli.py` COV-06 row (AGENTS.md rule 12). The gate SHALL be invoked as `uv run pyright`, so
third-party imports resolve against the project environment.

**Clause group S — no weakening.** Adopting the new posture SHALL NOT weaken what already holds: under the
committed `[tool.mypy] strict = true`, `uv run mypy src/ scripts/` SHALL exit 0; the `[tool.coverage.report]`
TOTAL floor, the four COV-06 per-file gates, the CI test matrix and the `release.yml` `needs` graph SHALL be
unchanged; and no resolution of a type diagnostic SHALL add a `# pragma: no cover` anywhere.

#### Scenario: `tests/` stays out of both type gates

- GIVEN `pyproject.toml`'s `[tool.mypy]` and `[tool.pyright]` blocks, every mypy invocation in
  `.github/workflows/ci.yml` and `.pre-commit-config.yaml`, and `CONTRIBUTING.md`'s type-checking section
- WHEN `tests/test_ci_workflows.py::test_mypy_and_pyright_exclude_tests` inspects them
- THEN `[tool.mypy] exclude` SHALL contain `tests/` and `[tool.pyright] exclude` SHALL contain `tests`
- AND every mypy invocation SHALL name `src`/`scripts` and SHALL NOT name `tests`
- AND the type-checking section SHALL name both gate commands and state that `tests/` is excluded from
  both gates, so Q1's answer is documented where a contributor reads it
- AND the PR template's Checklist SHALL carry the pyright item (the CI-06 S4 shape), and
  `process-boundary` PB-07 SHALL be cross-referenced, not edited — its "test helpers are still
  annotated by convention" clause stays in force

#### Scenario: `[tool.pyright]` declares the decided posture and the gate runs

- GIVEN `pyproject.toml`, `.github/workflows/ci.yml`, and `.pre-commit-config.yaml`
- WHEN `tests/test_ci_workflows.py::test_pyright_config_declares_the_decided_posture` and
  `::test_ci_lint_job_runs_the_pyright_gate` inspect them
- THEN `[tool.pyright]` SHALL declare `typeCheckingMode = "standard"`, an `include` covering both
  `src` and `scripts`, an `exclude` containing `tests`, a `pythonVersion` equal to the value
  `.python-version` pins, and a `stubPath` naming the committed `tomli` stub directory
- AND `reportMissingImports` SHALL NOT be globally disabled
- AND the `lint` job SHALL contain exactly the bare gate invocation `uv run pyright`, and no file
  under `.github/workflows/` SHALL declare a pyright version literal
- AND the committed invocation SHALL exit 0 on the committed tree, with the measured
  `"N errors, 0 warnings"` summary recorded as verify-phase runtime evidence

#### Scenario: Exactly one pyright config home exists

- GIVEN the repository tree, excluding the virtual environment and other machine-local directories
- WHEN `tests/test_ci_workflows.py::test_pyright_has_exactly_one_config_home` searches it
- THEN zero `pyrightconfig.json` files SHALL exist, so `[tool.pyright]` stays the single
  configuration authority — the analogue of CI-08's single-declaration rule, which a stray JSON
  file would silently defeat because pyright prefers it over the table

#### Scenario: The pin is exact, reaches CI through the lock, and matches the running binary

- GIVEN `pyproject.toml`'s `[dependency-groups] dev` list and `uv.lock`
- WHEN `tests/test_ci_workflows.py::test_analyzer_dev_pins_are_exact_and_match_the_lock` derives
  `X.Y.Z` from the dev pin and compares the lock's resolved entry against it, and when
  `uv run pyright --version` runs
- THEN exactly one pyright dev entry SHALL exist and its specifier SHALL be the exact
  `==X.Y.Z`, so a `>=` floor SHALL fail the guard
- AND `uv.lock`'s resolved pyright package SHALL carry that same version
- AND the guard SHALL hold no version literal of its own, so a bump edits declarations only
- AND `uv run pyright --version` SHALL equal that version — the enforcement pyright itself lacks
  (it has no `required-version` analogue) — recorded as verify-phase runtime evidence

#### Scenario: Adopting the gate leaves every existing gate declaration intact

- GIVEN `.github/workflows/ci.yml`, `.github/workflows/release.yml`,
  `.pre-commit-config.yaml`, and `pyproject.toml`
- WHEN `tests/test_ci_workflows.py::test_type_gate_invocations_and_pins_are_unchanged_for_existing_gates`
  inspects them, and when `uv run mypy src/ scripts/` runs under the committed `strict = true`
- THEN the mypy invocations SHALL still be exactly `uv run mypy src/ scripts/` on both surfaces
  (the `lint` job step and the local `mypy` hook entry)
- AND no workflow SHALL declare a coverage floor literal or a `--fail-under` flag in its raw text,
  and exactly one `ruff-format` hook entry SHALL remain (PB-14)
- AND `uv run mypy src/ scripts/` SHALL exit 0 with zero errors, and the CI test matrix,
  `release.yml`'s `needs` graph, the TOTAL floor and the four COV-06 rows SHALL be unchanged —
  recorded as verify-phase runtime evidence (CI-01 gate-exit-code precedent)

---

### Requirement: Release test job parity with CI (CI-10)

> Added by change `2026-09-24-fix-release-test-parity` (GitHub #209). The release workflow's
> header claims to run the same quality gates as CI, so its `test` job SHALL mirror the CI
> `test` job's OS axis (`ubuntu-latest` + `windows-latest`, driven by
> `runs-on: ${{ matrix.os }}`) and SHALL run the same CLI help smoke test
> (`uv run sofer --help`) after the full-suite step. The COV-06 core-coverage gate in the
> release `coverage` job is deliberately separate and tracked as issue #185 — this requirement
> SHALL NOT re-implement it, and the release header comment SHALL keep cross-referencing it.

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

#### Scenario: COV-06 stays cross-referenced as issue #185

- GIVEN the release workflow header comment
- WHEN it is read for the parity claim
- THEN it SHALL name issue #185 as the deliberately separate change that adds the
  COV-06 core-coverage gate to the release `coverage` job

---

### Requirement: Format gate in the lint job (CI-11)

> Added by change `2026-09-24-fix-194-ruff-format-gate` (GitHub #194). Closes the
> un-staged-file drift class that PB-10 deliberately left open: the local pre-commit
> `ruff-format` hook sees staged files only, so a formatting regression on files nobody
> edits is invisible to CI. CI-08's "SHALL arm no CI step" clause stays scoped to that
> requirement; this one is the deliberate exception that arms the gate.

The `lint` job of `.github/workflows/ci.yml` SHALL run the formatter as a gate: a step
named `Check formatting with ruff` SHALL run exactly `uv run ruff format --check src/
tests/`, placed after the `Lint with ruff` step so it shares the already-installed
environment. The invocation SHALL mirror the PB-10 clean-checkout scope (`src/ tests/`),
SHALL name no other path, and SHALL NOT carry a `--diff` flag, a version literal, or a
floor value — the version reaches the step through `uv.lock` and the pin under CI-08. The
gate SHALL exit non-zero when any file under `src/` or `tests/` would be reformatted, so
the drift class is closed for the enforced scope. A contributor who does not install the
pre-commit hooks SHALL still be blocked by CI on an unformatted PR.

#### Scenario: Lint job runs the format gate

- GIVEN `.github/workflows/ci.yml`
- WHEN the `lint` job steps are inspected
- THEN a step named `Check formatting with ruff` SHALL run exactly
  `uv run ruff format --check src/ tests/`
- AND it SHALL appear after the `Lint with ruff` step in the same job
- AND the invocation SHALL name no other path, SHALL carry no `--diff` flag, no version
  literal, and no floor value

#### Scenario: Format gate is green on a clean checkout

- GIVEN a clean checkout of `dev` with this change applied
- WHEN `uv run ruff format --check src/ tests/` runs
- THEN it SHALL exit 0 and report zero files to reformat (verify-phase runtime evidence,
  CI-01 gate-exit-code precedent)

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
| CI-03 | Release coverage job runs the core 100% gates | `tests/test_ci_workflows.py` — `test_release_coverage_job_runs_core_100_gates`: YAML inspection of the release.yml `coverage` job steps |
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
| CI-09 | `tests/` stays out of both type gates | `tests/test_ci_workflows.py` — `test_mypy_and_pyright_exclude_tests`: tomllib parse of both type-checker blocks + text inspection of every mypy invocation and of `CONTRIBUTING.md`'s type-checking section and the PR template |
| CI-09 | `[tool.pyright]` declares the decided posture and the gate runs | `tests/test_ci_workflows.py` — `test_pyright_config_declares_the_decided_posture` and `test_ci_lint_job_runs_the_pyright_gate`: tomllib + YAML inspection; local gate run `uv run pyright` exit code with the measured summary line (verify-phase runtime evidence) |
| CI-09 | Exactly one pyright config home exists | `tests/test_ci_workflows.py` — `test_pyright_has_exactly_one_config_home`: tree walk for `pyrightconfig.json` |
| CI-09 | The pin is exact, reaches CI through the lock, and matches the running binary | `tests/test_ci_workflows.py` — `test_analyzer_dev_pins_are_exact_and_match_the_lock`: dev-pin derivation + `uv.lock` resolution equality; `uv run pyright --version` equality (verify-phase runtime evidence) |
| CI-09 | Adopting the gate leaves every existing gate declaration intact | `tests/test_ci_workflows.py` — `test_type_gate_invocations_and_pins_are_unchanged_for_existing_gates`: YAML/tomllib inspection; `uv run mypy src/ scripts/` exit code (CI-01 gate-exit-code precedent) |
| CI-10 | Test job OS axis matches CI | `tests/test_ci_workflows.py` — `test_release_test_job_mirrors_ci_os_axis_and_cli_smoke`: YAML inspection of both `test` job matrices |
| CI-10 | CLI help smoke test runs at tag time | `tests/test_ci_workflows.py` — `test_release_test_job_mirrors_ci_os_axis_and_cli_smoke`: YAML inspection of the release `test` job steps |
| CI-10 | COV-06 stays cross-referenced as issue #185 | `tests/test_ci_workflows.py` — `test_release_test_job_mirrors_ci_os_axis_and_cli_smoke`: full-text scan of the release header comment |
| CI-11 | Lint job runs the format gate | `tests/test_ci_workflows.py` — `test_ci_lint_job_runs_the_ruff_format_gate`: YAML inspection of the ci.yml `lint` job steps |
| CI-11 | Format gate is green on a clean checkout | Verify-phase runtime evidence — `uv run ruff format --check src/ tests/` exit code on `dev` (CI-01 gate-exit-code precedent) |
