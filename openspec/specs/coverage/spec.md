# coverage Specification

## Purpose

Contracts for sofer's per-file and total coverage policy: the **CLI-core 100%
mandate** — `cli.py`, `scanner.py`, `prepare.py`, `publish.py` each at 100.00%
with zero `# pragma: no cover` tokens, enforced by per-file scoped CI gates
(COV-06) — plus a ≥90% per-file floor for the three second-tier modules
`profile.py`, `mcp_registration.py`, `verification.py` (COV-01), the
interaction with the config-owned TOTAL gate (COV-02, cross-referencing `ci`
CI-01), the delivery constraint that bounds the diff to **zero `src/sofer/`
paths** and forbids pragmas in the core modules (COV-03 — the `cli.py`
`__main__` guard is kept and executed in-process via runpy), and the
behavior-asserting test discipline that makes coverage gain a side effect of
real assertions, never a line-touching exercise (COV-05).

The `ci` spec pins the pipeline mechanics and the config gate for TOTAL
coverage (CI-01..CI-03), and `process-boundary` pins the complete-suite
invariant (PB-05) that every coverage measurement re-runs. This domain
cross-references both and SHALL NOT re-specify the TOTAL gate: the TOTAL floor
stays config-owned (`[tool.coverage.report] fail_under = 90`, CI-01), while the
per-file 100% mandate — which coverage.py cannot express in config — is
enforced by per-file scoped invocations (`coverage report --include=src/sofer/
<file>.py --fail-under=100 -m`) in the CI coverage job (COV-06): additive,
scoped per file, hardcoding 100 only because 100 is a fixed policy constant,
never a tunable floor, and never a workaround of CI-01. The three ≥90 floors
are verified by verify-phase runtime evidence and optionally guarded by a
skip-if-absent contract test. TOTAL ≥90 SHALL NOT substitute for any single
row, and no single row SHALL substitute for the others.

> Amendments 2026-09-13 (scoped pass): COV-01 re-scoped from five ≥90 modules
> to three (cli/publish moved to the COV-06 100% mandate); COV-03 amended to
> "**zero `src/sofer/` paths**" with an absolute no-pragma rule for the core four;
> COV-04 (cheapest-wins adjacent set) **retired** — the core-100 overshoot
> (≈181 statements from ~88%) lands TOTAL ≈ 91% ≥ 90, so no adjacent fills are
> needed (proposal Decision Point 2); COV-06 added.
>
> Amendment 2026-09-13b (Resolution A, parent-authorized — supersedes the
> interim "exactly one justified `cli.py` guard removal" text): the `cli.py`
> `__main__` guard is KEPT (not removed) and becomes a covered line via an
> in-process `runpy.run_module("sofer.cli", run_name="__main__")` test executing
> `main()` through the guard under the coverage tracer — real execution, no
> pragma, zero `src` edits. Rationale: `tests/conftest.py::run_cli` spawns
> `-m sofer.cli` as the PB-02 subprocess boundary (14 tests fail with the guard
> removed), and the guard body provably executes in-process under coverage.
> This domain is written canonical-first under the change
> `2026-09-13-raise-per-file-coverage`; it is a new domain with no prior
> canonical `openspec/specs/coverage/`, so it is unaffected by the pending sync
> of archived delta specs referenced in the proposal.

> Introduced by change `2026-09-13-raise-per-file-coverage` (archived 2026-09-13).
## Requirements

### Requirement: Per-file coverage floor for the three second-tier modules (COV-01)

`src/sofer/profile.py`, `src/sofer/mcp_registration.py`, and
`src/sofer/verification.py` SHALL each measure ≥90% coverage under
`coverage report -m` on the regenerated baseline, using the same
`[tool.coverage.run]` configuration the CI coverage job uses (`branch = true`,
`source = ["src/sofer"]`) over the complete suite (PB-05). Each of the three
rows SHALL be individually binding; TOTAL ≥90 (COV-02) SHALL NOT substitute for
any single row. The floor SHALL be verified as verify-phase runtime evidence on
the CI interpreter (ubuntu / Python 3.13), which is the arbiter because
statement counts and branch arcs vary across Python versions; the measured rows
SHALL be recorded with an observed margin above the floor. The change MAY
additionally guard the floors with a skip-if-absent `tests/test_coverage_contract.py`
regression guard that asserts the three rows and TOTAL from a local `.coverage`
data file when one is present, and SHALL skip on a clean checkout (the data
file is gitignored local state — a clean checkout SHALL never fail on its
absence). The top-tier CLI-core modules (`cli.py`, `scanner.py`, `prepare.py`,
`publish.py`) are NOT governed by this ≥90 floor: they carry an absolute 100%
mandate under COV-06, enforced by the scoped CI gates.

#### Scenario: Three second-tier rows meet the floor on the regenerated baseline

- GIVEN the `[tool.coverage.run]` configuration exactly as CI uses it and a fresh `coverage run -m pytest` (complete suite, PB-05) on `test/raise-coverage-90`
- WHEN `coverage report -m` runs
- THEN the rows for `src/sofer/profile.py`, `src/sofer/mcp_registration.py`, and `src/sofer/verification.py` SHALL each be at or above 90 (the `cli.py`/`publish.py` rows are governed by COV-06 at 100.00, not this floor)

#### Scenario: The CI interpreter is the arbiter

- GIVEN the CI reproduction environment (ubuntu, Python 3.13 — the interpreter the gate measures on)
- WHEN `coverage run -m pytest` then `coverage report -m` run there
- THEN each of the three rows SHALL be ≥90 with an observed margin above the floor recorded in the verify report and the CI coverage job log (a file at 90.1 locally can land at 89.8 on 3.13; the CI gate is the arbiter); the four core rows are binary gates under COV-06 with no margin by design

#### Scenario: Optional contract guard skips on a clean checkout

- GIVEN `tests/test_coverage_contract.py` present and a checkout with no local `.coverage` data file
- WHEN the suite runs
- THEN the contract test SHALL skip, and the suite SHALL pass without it — the three floors remain verify-phase evidence (COV-01), never a hard test dependency on absent local state

---

### Requirement: TOTAL ≥90 and the CI-01 gate green (COV-02)

TOTAL coverage SHALL be ≥90% on the regenerated baseline so the config-owned
`ci` CI-01 gate (`fail_under = 90` in `pyproject.toml` `[tool.coverage.report]`,
next to `show_missing = true`) passes — locally and in the CI coverage job on
the PR (ubuntu, Python 3.13). `coverage report -m` SHALL exit 0 on the
measurement. The gate value SHALL NOT be lowered, raised, or re-declared: the
gate SHALL stay exactly as PR #172 (`2026-09-13-ci-coverage-codeql`) left it.
This requirement SHALL hold the PB-05 complete-suite invariant: TOTAL is
measured over the same complete suite CI gates today.

#### Scenario: TOTAL meets the floor and the gate exits 0

- GIVEN the complete-suite measurement (PB-05) and `[tool.coverage.report] fail_under = 90` unchanged (CI-01)
- WHEN `coverage report -m` runs
- THEN the TOTAL row SHALL be at or above 90 and the process SHALL exit 0

#### Scenario: CI coverage job turns green on the PR

- GIVEN the PR branch based on `dev` and the `ci.yml`/`release.yml` coverage jobs on ubuntu / Python 3.13 with the config-owned gate untouched (and, per COV-06, the four per-file 100 gates additionally present in the `ci.yml` coverage job)
- WHEN the jobs run
- THEN they SHALL pass — closing the forcing-function loop deliberately armed by PR #172

#### Scenario: Gate value untouched

- GIVEN `pyproject.toml` parsed with `tomllib`
- WHEN the `[tool.coverage.report]` table is inspected
- THEN `fail_under` SHALL equal 90 exactly as CI-01 declares, with no value change and no duplicated threshold elsewhere

---

### Requirement: Bounded diff — zero src touches, no pragmas in the core modules (COV-03)

The change SHALL be strictly test-only: **no path under `src/sofer/` SHALL be
modified** (Resolution A, parent-owned 2026-09-13 — recorded in the proposal
Decision Point 4). In particular the dead `if __name__ == "__main__": main()`
guard at `cli.py:1574-1575` SHALL be KEPT and SHALL become a covered line via an
in-process `runpy.run_module("sofer.cli", run_name="__main__")` test that
executes `main()` through the guard under the coverage tracer (real execution,
no pragma — the earlier removal plan is superseded: `tests/conftest.py::run_cli`
spawns `python -m sofer.cli` as the PB-02 subprocess boundary and 14 tests fail
with the guard removed, while the guard body provably executes in-process via
runpy). No refactor-for-testability, no behavior change, no new seams, no logic
edits of any kind. `# pragma: no cover` SHALL be absent from the entire filesystem image
of the four core modules (`cli.py`, `scanner.py`, `prepare.py`, `publish.py`):
zero tokens anywhere in those files (absolute ban, static full-text scan —
baseline has none). Elsewhere in the diff (tests, workflow, gate script),
pragmas SHALL be absent unless a design-doc justification entry names each line
and reason (1:1). `pyproject.toml` SHALL be untouched. Coverage-gate machinery
in the diff SHALL be limited to the COV-06 per-file scoped invocations (inline
steps or one `scripts/` gate script): no Codecov, no `pytest-cov`, no XML
output, no new config keys.

#### Scenario: The diff contains zero src changes
    
- GIVEN the change branch based on `dev`
- WHEN `git diff origin/dev --stat` is inspected
- THEN **zero** paths under `src/sofer/` SHALL appear (the change is strictly test-only; the `cli.py` `__main__` guard is kept, not removed)

#### Scenario: Core modules are pragma-free (full-text scan)

- GIVEN the current source of `cli.py`, `scanner.py`, `prepare.py`, `publish.py`
- WHEN each file's full text is scanned for the token `# pragma: no cover`
- THEN zero matches SHALL be found in each of the four files

#### Scenario: Gate machinery in the diff is bounded

- GIVEN the change diff
- WHEN it is scanned for coverage-gate machinery
- THEN `pyproject.toml` SHALL NOT appear, and the only gate invocations SHALL be the COV-06 per-file scoped `coverage report --include=src/sofer/<file>.py --fail-under=100 -m` steps/script — no `pytest-cov`, no `coverage xml`, no Codecov references

---

### Requirement: Cheapest-wins adjacent set (COV-04) — RETIRED in this change

(Reason: superseded by the amendment 2026-09-13 re-scope, recorded in the
proposal Decision Point 2 and Out-of-Scope list. The original strategy closed
the TOTAL gap with a ranked cheapest-wins adjacent set (near-90 modules plus
the `_converters.py` reservoir) because five ≥90 files alone left a ≈30–45
statement hole. The four core modules reaching 100.00% from the ~88% baseline
(~181 missed statements) overshoots the TOTAL floor — TOTAL ≈ 91% ≥ 90 with
≈60 statements of margin — so adjacent fills are unnecessary. COV-04 has no
scenarios and SHALL NOT be enforced.)

(Migration: no module outside the four core + three floors is chased to any
coverage floor; earlier design notes/tasks from the superseded handoff that pin
a cheapest-wins set SHALL NOT be applied — the design phase re-syncs on COV-01,
COV-03, and COV-06 as amended. Nothing else in this change's artifacts is
affected.)

---

### Requirement: Behavior-asserting tests only (COV-05)

Every test added or meaningfully extended by this change SHALL assert
observable behavior — return value, output text, exit code, side effect, or
raised exception — built on fixtures / `tests/conftest.py` helpers and
config-sourced values from `[tool.sofer]` / `DatasetConfig` (AGENTS.md rules 1
and 3), following the existing per-module style. Measured coverage gain SHALL
be a side effect of behavior tests, SHALL NOT be the assertion of any test:
the per-file and TOTAL percentages are verify-phase evidence, not pytest
assertions (CI-01-S2 precedent), and no new test SHALL invoke coverage
measurement APIs to assert percentages. (The COV-06 100% rows are enforced by
the CI gate invocations' exit codes — runtime gate evidence, the same
precedent — not by pytest percentage assertions.)

#### Scenario: Each new test asserts an observable outcome

- GIVEN any test added or meaningfully extended by this change
- WHEN its body is inspected
- THEN it SHALL assert at least one observable outcome (return, output text, exit code, side effect, or exception) with values from configuration or fixtures — never merely executing a line to touch it

#### Scenario: No test asserts measured percentages

- GIVEN the full test diff
- WHEN it is scanned for coverage-measurement assertions
- THEN zero new tests SHALL assert measured coverage percentages — the floors live in verify-phase evidence (COV-01, COV-02) and CI gate exit codes (COV-06), not in pytest

---

### Requirement: CLI-core 100% mandate with scoped gates (COV-06)

`src/sofer/cli.py`, `src/sofer/scanner.py`, `src/sofer/prepare.py`, and
`src/sofer/publish.py` SHALL each measure **100.00%** line coverage under
`coverage report -m` on the regenerated baseline (same `[tool.coverage.run]`
configuration, complete suite, PB-05) — every line and every branch arc
executes under tests. `# pragma: no cover` SHALL NOT appear anywhere in those
four files — no exception, including "genuinely untestable" lines; an
unreachable line is a defect in the test strategy or a design-doc escalation,
never a pragma. AGENTS.md SHALL carry rule 14 declaring this mandate and the
pragma ban as mandatory repo policy. The dead `if __name__ == "__main__":
main()` guard in `cli.py` SHALL be KEPT and SHALL be executed under the
coverage tracer via an in-process `runpy.run_module("sofer.cli",
run_name="__main__")` test (with argv pointing at a harmless subcommand) —
real execution of the guard lines is a mandatory part of the 100.00% row, not a
pragma, not a src edit (Resolution A; see COV-03).

The mandate SHALL be enforced by per-file scoped gate invocations in the CI
coverage job on the PR (`.github/workflows/ci.yml`): for each of the four core
module paths, a `coverage report --include=src/sofer/<file>.py
--fail-under=100 -m` invocation SHALL run within the job — expressed either as
four inline steps or as one committed `scripts/` gate script that lists all
four files and is referenced by the job. These gates are NEW machinery, scoped
per file, and SHALL NOT alter the config-owned TOTAL gate: `pyproject.toml`
`[tool.coverage.report]` `fail_under = 90` (CI-01 / COV-02) SHALL stay
untouched, the scoped invocations SHALL NOT pass any floor other than 100, and
no config key SHALL be added. CI-01's flag ban applies to the TOTAL gate; the
per-file 100 invocations are its documented, additive exception — the ci-domain
static test CI-01 S2 is narrowed accordingly in this change, and a one-line
carve-out note in the `ci` canonical spec text is a recorded follow-up, not
edited in this scoped pass.

#### Scenario: Scoped gates are declared for all four core files

- GIVEN `.github/workflows/ci.yml` (and, if the script shape is chosen, the referenced `scripts/` gate script)
- WHEN the coverage job's steps are parsed (YAML) and the gate script's text is inspected
- THEN each of `src/sofer/cli.py`, `src/sofer/scanner.py`, `src/sofer/prepare.py`, and `src/sofer/publish.py` SHALL appear in a `coverage report --include=src/sofer/<file>.py --fail-under=100 -m` invocation within the job — inline or via the gate script — and no `--fail-under` value other than 100 SHALL appear in the workflow or script (the config-key spelling `fail_under` SHALL still be absent, CI-01)

#### Scenario: No pragma tokens anywhere in the four core modules

- GIVEN the current source of `cli.py`, `scanner.py`, `prepare.py`, `publish.py`
- WHEN each file's full text is scanned for the token `# pragma: no cover`
- THEN zero matches SHALL be found (static full-text scan; spans the whole file, not just the diff)

#### Scenario: AGENTS.md carries the mandatory rule

- GIVEN `AGENTS.md`
- WHEN rule 14's text is inspected
- THEN it SHALL name the four modules, declare the 100.00% mandate, and forbid `# pragma: no cover` in them (no-pragma clause)

    #### Scenario: The cli.py __main__ guard is executed under the coverage tracer
    
    - GIVEN the kept `if __name__ == "__main__": main()` guard at `cli.py:1574-1575`
      and a test invoking `runpy.run_module("sofer.cli", run_name="__main__")`
      in-process with argv pointing at a harmless subcommand (e.g. `--help`)
    - WHEN the suite runs under `coverage run -m pytest`
    - THEN `main()` SHALL execute through the guard under the tracer (the guard lines
      count as covered — real execution, mandatory part of the cli.py 100.00 row),
      the invocation SHALL exit rc 0 (or the expected exit-call fires), and no
      `src/sofer/` path SHALL appear in the change diff

#### Scenario: TOTAL stays config-owned at 90

- GIVEN `pyproject.toml` parsed with `tomllib`
- WHEN the `[tool.coverage.report]` table is inspected and the COV-06 gates are compared against it
- THEN `fail_under` SHALL equal 90 (CI-01 / COV-02), no coverage threshold SHALL be added or re-declared by COV-06, and the per-file 100 gates SHALL remain scoped per file (they SHALL NOT change the TOTAL gate's behavior)

---

## Test Mapping

Every scenario SHALL map to a green test or to verify-phase static/runtime
evidence (AGENTS.md rule 6; rules.specs; PB-05/MSP-R12/CI-01-S2 precedent).
Actual measured percentages are NOT pytest-assertable (the CI-01-S2 precedent):
the three ≥90 floors and TOTAL are verified through `coverage report -m` rows,
gate exit codes, and the CI coverage job result reproduced in the verify
report. The COV-06 100% rows are enforced by the per-file gate invocations'
exit codes in CI — runtime gate evidence, same precedent. The COV-06 static
contracts (gate declaration shape, pragma-token absence, guard EXECUTION via the in-process runpy test, AGENTS
rule text, config threshold) ARE pytest-assertable via token/shape/text scans
and live in the added/modified static tests below.

Coverage-raising tests SHALL live in the existing per-module test files —
`tests/test_cli.py` (cli), `tests/test_scanner.py` (scanner),
`tests/test_prepare.py` (prepare), `tests/test_publish.py` (publish) for the
100% mandate, and `tests/test_profile.py` (profile),
`tests/test_mcp_registration.py` (mcp_registration), `tests/test_splits.py` (+
a `tests/test_prepare.py` integration leg) (verification) for the three ≥90
floors — with fixtures added to `tests/conftest.py` only where reuse justifies
them. Static contract assertions live in NEW `tests/test_coverage_contract.py`
and `tests/test_ci_workflows.py` additions/modifications as mapped below.

| Req | Scenario | Verification |
| --- | -------- | ------------ |
| COV-01 | Three second-tier rows meet the floor on the regenerated baseline | Verify-phase runtime evidence — `uv run coverage report -m` rows for `profile.py`/`mcp_registration.py`/`verification.py`, each ≥90 (CI-01-S2 precedent; percentages not pytest-assertable); optionally pinned by **new** `tests/test_coverage_contract.py` (skip-if-absent, asserts the three rows + TOTAL from a local `.coverage` file when present) |
| COV-01 | The CI interpreter is the arbiter | Verify-phase runtime evidence — per-file rows reproduced on ubuntu/Python 3.13 in the CI coverage job log and the verify report, with the observed margin recorded |
| COV-01 | Optional contract guard skips on a clean checkout | **new** `tests/test_coverage_contract.py` (skip-if-absent semantics) runs green with `.coverage` absent |
| COV-02 | TOTAL meets the floor and the gate exits 0 | Verify-phase runtime evidence — TOTAL row ≥90 and `coverage report -m` exit code 0 on the CI interpreter (CI-01-S2 precedent; percentage not pytest-assertable) |
| COV-02 | CI coverage job turns green on the PR | Verify-phase evidence — CI coverage job result on the PR (ubuntu, Python 3.13) with `fail_under = 90` untouched and the four COV-06 gates additionally green |
| COV-02 | Gate value untouched | `tests/test_ci_workflows.py::test_pyproject_declares_coverage_fail_under_90` (existing, unchanged) |
| COV-03 | The diff contains zero src changes | Verify-phase static evidence — `git diff origin/dev --stat` shows **zero** `src/sofer/` paths (test-only change); full suite green |
| COV-03 | Core modules are pragma-free (full-text scan) | **new** `tests/test_coverage_contract.py::test_core_modules_contain_no_pragma_tokens` — full-text token scan of `cli.py`/`scanner.py`/`prepare.py`/`publish.py`: zero `# pragma: no cover` matches |
| COV-03 | Gate machinery in the diff is bounded | Verify-phase static evidence — `pyproject.toml` absent from the diff; only COV-06 per-file scoped invocations appear; no `pytest-cov`/XML/Codecov |
| COV-04 | (Retired — no scenarios) | Recorded in proposal Decision Point 2 / Scope Out; kept as a retired marker only; not enforced |
| COV-05 | Each new test asserts an observable outcome | Review lens at verify + full-suite green — assertion-quality check per new test (return/output/exit-code/side-effect/exception, config-derived values); rule 6 |
| COV-05 | No test asserts measured percentages | Verify-phase static evidence — scan of the test diff for coverage-measurement assertions: zero; percentages stay in verify evidence (CI-01-S2 precedent) and CI gate exit codes (COV-06) |
| COV-06 | Scoped gates are declared for all four core files | **new** `tests/test_ci_workflows.py::test_coverage_job_gates_core_modules_at_100` — parse the `ci.yml` coverage job (and the referenced `scripts/` gate script, if the script shape is chosen); each of the four `src/sofer/<file>.py` paths SHALL be paired with `--fail-under=100 -m`; no other `--fail-under` value SHALL appear; **modified** `tests/test_ci_workflows.py::test_coverage_gate_is_config_driven_without_cli_floor` (CI-01 S2) — flag/floor ban scoped to the TOTAL gate, explicitly permitting the COV-06 per-file 100 invocations while keeping `fail_under` (config-key spelling) and any non-100 floor value out of the workflows |
| COV-06 | No pragma tokens anywhere in the four core modules | **new** `tests/test_coverage_contract.py::test_core_modules_contain_no_pragma_tokens` — same full-text scan as the COV-03 row; shared assertion |
| COV-06 | AGENTS.md carries the mandatory rule | **new** `tests/test_ci_workflows.py::test_agents_md_declares_core_100_mandate` — text inspection of AGENTS.md rule 14: names the four modules, declares 100.00%, forbids `# pragma: no cover` |
| COV-06 | The cli.py __main__ guard is executed under the coverage tracer | **new** `tests/test_cli.py::test_cli_main_guard_executed_via_runpy` — in-process `runpy.run_module("sofer.cli", run_name="__main__")` with argv at a harmless subcommand; asserts rc/exit-call; runs under the coverage tracer so the guard lines count as covered (mandatory part of the cli.py 100.00 row; REPLACES the planned `test_cli_has_no_main_guard` guard-absence scan) |
| COV-06 | TOTAL stays config-owned at 90 | `tests/test_ci_workflows.py::test_pyproject_declares_coverage_fail_under_90` (existing, unchanged) + verify-phase run of the four per-file gate invocations (each rc 0) and the TOTAL gate (rc 0) |