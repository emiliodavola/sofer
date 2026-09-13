# Proposal: Raise per-file coverage to ≥90% (turn the coverage gate green)

> **Amendment 2026-09-13 (authoritative; supersedes the original handoff where
> conflicting).** Re-scoped per new user decisions: the CLI core
> (`cli.py`, `scanner.py`, `prepare.py`, `publish.py`) SHALL reach **100% line
> coverage with zero `# pragma: no cover`** ("No, 100% real"); the five-file ≥90
> floors reduce to **three** (`profile.py`, `mcp_registration.py`,
> `verification.py` — `cli.py`/`publish.py` are now governed by the 100%
> mandate); the adjacent cheapest-wins set (COV-04) is **DROPPED** (the core-100
> overshoot lands TOTAL ≈ 91% ≥ 90); **zero `src` edits** (Resolution A,
> parent-authorized 2026-09-13 — supersedes the earlier guard-removal text below):
> the dead `if __name__ == "__main__": main()` guard at `cli.py:1574-1575` is
> KEPT and becomes a covered line via an in-process
> `runpy.run_module("sofer.cli", run_name="__main__")` test under the coverage
> tracer (real execution, no pragma — `tests/conftest.py::run_cli` spawns
> `-m sofer.cli` as the PB-02 boundary, so removal breaks 14 tests, and the guard
> body provably executes in-process via runpy);
> enforcement adds **per-file scoped gates (COV-06)** — a NEW requirement, NOT a
> mutation of the config-owned TOTAL floor (CI-01). `specs/coverage/spec.md` is
> amended in lockstep (COV-01..COV-06).

## Intent

PR #172 (change `2026-09-13-ci-coverage-codeql`) armed a total-coverage gate at
`fail_under = 90` in `pyproject.toml` (`[tool.coverage.report]`, config-owned).
The baseline on `dev` measures **88%**, so the gate is red by design — it was
explicitly armed as a forcing function until coverage is raised. This change
pays that debt with a **stricter, re-scoped contract** (amendment 2026-09-13):

1. **CLI-core 100% mandate (COV-06)** — the four modules the user named as the
   riskiest dispatch surface (`src/sofer/cli.py`, `scanner.py`, `prepare.py`,
   `publish.py` — "cli.py + núcleo") SHALL each reach **100.00% line coverage**,
   with **zero `# pragma: no cover`** tokens anywhere in those files every line
   must actually execute under tests. Enforcement is per-file scoped
   `coverage report --include=src/sofer/<file>.py --fail-under=100 -m`
   invocations in the CI coverage job (COV-06) — additive, and never a
   workaround of the config-owned TOTAL gate.
2. **Three per-file ≥90 floors (COV-01, re-scoped)** — `profile.py`,
   `mcp_registration.py`, `verification.py` SHALL each measure ≥90% (the second
   tier of the original five; `cli.py`/`publish.py` moved to the 100% mandate).
   `verification.py` barely misses 90 (8 missed at baseline) and needs no
   adjacent help.
3. **Adjacent cheapest-wins set DROPPED (COV-04 retired)** — the core-100
   overshoot obviates it: the four core files carry ≈181 missed statements at
   ~88% (handoff working estimate; prior-capture rows: cli 84%/87 missed,
   prepare 88%/46 missed, publish 87%/36 missed, scanner ≈12 pinned fresh at
   design). Clearing ≈181 of ≈720 missed statements on a ≈6000-statement
   instrumented surface lands TOTAL ≈ **91%** ≥ 90 (the 90% floor needs only
   ≈120 more) — ≈60 statements of margin. No adjacent fills are needed; chasing
   them would be scope creep.
4. **Zero `src` edits (Resolution A, parent-owned 2026-09-13)** — the dead
   `if __name__ == "__main__": main()` guard at `cli.py:1574-1575` is KEPT and
   becomes a covered line through an in-process `runpy.run_module("sofer.cli",
   run_name="__main__")` test (real execution under the coverage tracer, no
   pragma). The removal plan rested on two false premises: "nothing references
   `python -m sofer.cli`" is false (`tests/conftest.py::run_cli` spawns it as
   the PB-02 boundary — 14 tests fail with the guard removed), and "cannot be
   driven without subprocess-coverage machinery" is false (probe executed
   `main()` through the guard in-process under coverage). Everything in this
   change is test-only; no `src/sofer/` path is touched.
5. **Mandatory repo policy** — a new AGENTS.md rule (14, after rule 13) makes
   the CLI-core 100% + no-pragma mandate binding repo policy, enforced by the
   scoped gates. Exact draft in the Amendment Appendix.

Delivery shape is unchanged from the handoff: a separate branch
(`test/raise-coverage-90`) + **single PR based on `dev`**, assigned to
emiliodavola. Size expectation grows to ≈1800–2600 changed lines (four modules
to 100% is a large test body) — single-PR intent is preserved, with
**ask-on-risk above 1500 changed lines** (see Decision Point 9).

## Scope

### In Scope

- **New/updated tests driving the four core modules to 100.00%** —
  `src/sofer/cli.py` → `tests/test_cli.py` (extend the existing ~1400-line
  module), `scanner.py` → `tests/test_scanner.py` (exists), `prepare.py` →
  `tests/test_prepare.py`, `publish.py` → `tests/test_publish.py`. Every missed
  statement gains a behavior-asserting test; `# pragma: no cover` is forbidden,
  so any line that cannot be reached is resolved by test strategy or design-doc
  escalation, never a pragma. The dead `__main__` guard at `cli.py:1574-1575` is
  covered by a dedicated in-process `runpy.run_module("sofer.cli",
  run_name="__main__")` test (`test_cli_main_guard_executed_via_runpy`) — the
  guard is KEPT (Resolution A) and executed under the tracer with argv at a
  harmless subcommand. Tests drive handlers in-process per existing
  precedent (`conftest.run_cli`, `test_main_help_prints(monkeypatch)`,
  `TestSubprocessBoundary`); subprocess execution would escape coverage and
  cannot be 100%-real.
- **New/updated tests for the three ≥90 floor modules** — `profile.py` →
  `tests/test_profile.py`, `mcp_registration.py` →
  `tests/test_mcp_registration.py`, `verification.py` → `tests/test_splits.py`
  (+ `tests/test_prepare.py` integration leg).
- **Fixtures** in `tests/conftest.py` only where reuse justifies them (values
  from `[tool.sofer]` / `DatasetConfig`, never hardcoded — AGENTS.md rules 1
  and 3).
- **Scoped CLI-core 100 gates (COV-06)** in the `ci.yml` coverage job: four
  per-file steps or one committed gate script under `scripts/` referenced from
  it (exact drafts in the Amendment Appendix). `release.yml` MAY mirror them
  (design choice; the CI-01 TOTAL gate already gates release).
- **AGENTS.md rule 14** — the mandatory CLI-core 100% policy with the
  no-pragma clause (exact text in the Amendment Appendix).
- **Zero `src` edits (Resolution A)** — nothing under `src/sofer/` is touched;
  the dead `__main__` guard at `cli.py:1574-1575` is kept and executed in-process
  via a `runpy.run_module("sofer.cli", run_name="__main__")` test (real
  execution, no pragma; justification in Decision Point 4). This change is
  strictly test-only.
- **Static contract tests** — NEW `tests/test_coverage_contract.py`
  (`# pragma: no cover` token scan of the four core modules; optional
  skip-if-absent floor guard reading a local `.coverage` file);
  `tests/test_ci_workflows.py` additions (scoped-gate presence; AGENTS.md
  rule-14 text) and ONE narrowing of CI-01 S2
  (`test_coverage_gate_is_config_driven_without_cli_floor`) so its
  `--fail-under` ban applies to the TOTAL gate only, permitting the per-file
  100 invocations.
- **Amended `coverage` spec domain** — COV-01..COV-06 in
  `openspec/changes/2026-09-13-raise-per-file-coverage/specs/coverage/spec.md`
  (COV-04 retired in Decision Point 2).
- **Verify-phase evidence** — `uv run coverage report -m` rows (four core rows
  100.00, three floor rows ≥90, TOTAL ≥90, rc 0) reproduced in the verify
  report; the four per-file gate rows from the CI log; `git diff` evidence of
  **zero `src/sofer/` paths** (test-only change) plus the green in-process
  runpy guard-execution test as part of the cli.py 100.00 row.

### Out of Scope

- **Any `src/sofer/` change at all (Resolution A: zero src touches)** — no
  refactor-for-testability, no behavior change, no new seams, no logic edits
  anywhere else; the `cli.py` `__main__` guard is kept and covered in-process.
- **`# pragma: no cover` in the four core modules — absolute, no exceptions**
  (including "genuinely untestable" lines; unresolvable lines escalate in the
  design doc instead).
- **Adjacent cheapest-wins set (COV-04)** — dropped; no coverage-raising tests
  for `_clean.py`, `_parquet_helpers.py`, `quality.py`, `codebook.py`,
  `render.py`, `repo_compliance.py`, `_converters.py`, or any module outside
  the four core + three floors; no per-file floor for non-target modules.
- **New gate machinery beyond COV-06's per-file scoped invocations** — no
  Codecov, badges, XML output, `pytest-cov`, new config keys.
- **Changing the gate value or re-architecting CI-01** — `fail_under = 90`
  stays config-owned and untouched; COV-06 gates are additive per-file 100%
  checks, never a workaround of the TOTAL floor.
- **Docs beyond AGENTS.md rule 14** — CONTRIBUTING / README / README_ES / PR
  template already describe the 90% gate (PR #172); unchanged (rule 13
  untouched).
- **Mutation testing, branch-coverage-per-file floors above 100, or any floor
  for non-target modules.**

## Capabilities

### New Capabilities

- **CLI-core 100% mandate (COV-06)** — `cli.py`, `scanner.py`, `prepare.py`,
  `publish.py` each at 100.00% line coverage with zero `# pragma: no cover`
  tokens anywhere in the four files; enforced by per-file scoped gates
  (`--fail-under=100` per `--include=src/sofer/<file>.py`) in the CI coverage
  job; AGENTS.md rule 14 makes it mandatory repo policy.
- **Per-file coverage floor ≥90% for the three second-tier modules** —
  `profile.py`, `mcp_registration.py`, `verification.py` (COV-01, re-scoped)
  — with verify-phase runtime evidence for each row.
- **Green TOTAL gate** — the PR #172 `fail_under = 90` gate passes on local
  verify and in the CI coverage job, closing the forcing-function loop
  deliberately armed in the previous change.
- **Amended `coverage` spec domain** (COV-01..COV-06) documenting the 100%
  mandate, the three floors, the no-pragma rule, the retired adjacent set, and
  the evidence shape, cross-referencing `ci` CI-01 and `process-boundary`
  PB-05.

### Modified Capabilities

- `tests/test_cli.py`, `tests/test_scanner.py`, `tests/test_prepare.py`,
  `tests/test_publish.py`: extended to execute every line of the four core
  modules (no pragmas).
- `tests/test_profile.py`, `tests/test_mcp_registration.py`,
  `tests/test_splits.py` (+ `tests/test_prepare.py` leg): extended to ≥90 for
  the three floor modules.
- `tests/test_ci_workflows.py`: NEW scoped-gate + AGENTS-rule static tests;
  CI-01 S2 (`test_coverage_gate_is_config_driven_without_cli_floor`) NARROWED
  so its `--fail-under` ban applies to the TOTAL gate only, permitting the
  COV-06 per-file 100 gates.
- NEW `tests/test_coverage_contract.py`: static pragma-token scan of the four
  core modules and the optional skip-if-absent `.coverage`-based floor guard
  (the guard-absence scan is REPLACED by the in-process guard-EXECUTION test
  `test_cli_main_guard_executed_via_runpy` in `tests/test_cli.py` — Resolution A).
- `src/sofer/cli.py`: UNTOUCHED under Resolution A — the dead `__main__` guard
  (1574-1575) is kept and covered by a new in-process
  `runpy.run_module("sofer.cli", run_name="__main__")` test in `tests/test_cli.py`
  (`test_cli_main_guard_executed_via_runpy`); zero `src/sofer/` paths in the diff.
- `.github/workflows/ci.yml`: coverage job gains the COV-06 per-file 100 gate
  step(s) (or references a `scripts/` gate script); `release.yml` MAY mirror.
- `AGENTS.md`: rule 14 added (mandatory CLI-core 100% + no-pragma policy).
- `tests/conftest.py`: fixtures only if reuse is justified.

## Approach

1. **Repin the baseline on the branch.** Regenerate `coverage run -m pytest` →
   `coverage report -m` on `test/raise-coverage-90`; record per-file rows for
   the four core modules (target 100.00), the three floors (≥90), and TOTAL
   (≈91 expected). Statement counts in this proposal are ≈ and superseded by
   the fresh run (blocking design step A-0).
2. **Classify every missed statement in the seven target files.** For each
   module, map each missed line/branch arc to the behavior it implements (CLI
   subcommand, error path, argument combination, scanner flatten/collision/move
   paths, MCP tool registration, publish destination/format, verification
   skip/fail paths…). The design doc pins the classified table.
3. **Write behavior-asserting tests to 100% for the four core modules.** Each
   new/updated test SHALL assert observable behavior with config/fixture values
   (AGENTS.md rules 1/3/6); in-process invocation per existing `test_cli.py` /
   `conftest` patterns — subprocess-driven execution would escape coverage and
   is not 100%-real. Zero pragmas: a line that cannot be reached is a defect in
   the test strategy or an escalation, never a pragma.
4. **Write tests to ≥90 for the three floor modules** (profile,
   mcp_registration, verification).
5. **Cover the kept `__main__` guard (zero `src` edits, Resolution A)**: add the
   in-process runpy test `test_cli_main_guard_executed_via_runpy`
   (`runpy.run_module("sofer.cli", run_name="__main__")` with argv at a harmless
   subcommand; asserts rc/exit-call under the tracer) so the guard lines are
   covered by real execution; `uv run sofer --help` and the full suite stay green
   as-is.
6. **Land the enforcement**: AGENTS.md rule 14; the COV-06 gate step(s) in the
   `ci.yml` coverage job (inline four-step form recommended — exact YAML in the
   Amendment Appendix); narrow CI-01 S2; add the static contract tests.
7. **Iterate locally to green with margin**: `coverage run -m pytest` →
   `coverage report -m` (plus the four scoped gate invocations) per batch; stop
   when the four core rows read 100.00, the three floor rows ≥90, TOTAL ≥90
   (≈91), and every gate exits 0.
8. **Evidence in the verify-report**: `coverage report -m` rows (four core +
   three floors + TOTAL + rc 0), the four per-file gate rows from the CI
   coverage job log, the suite count, and `git diff origin/dev --stat` showing
   **zero `src/sofer/` paths** (test-only change) — real command output, never
   placeholders (PR template rule).

## Decision Points

| # | Decision | Recommendation | Tradeoff | Status |
| --- | ---------- | ---------------- | ---------- | -------- |
| 1 | Scope definition | **CLI-core 100% (cli/scanner/prepare/publish) + three ≥90 floors (profile/mcp_registration/verification) + TOTAL ≥90** | The original five ≥90 floors left cli (84%) and publish (87%) — the riskiest dispatch surface — short of the coverage that matters most. The user's mandate ("cli.py + núcleo", "100% real") upgrades exactly those four to absolute 100% with zero pragmas; per-file ≥90 is the deliberate second tier for the remaining three. Cost: a much larger test body (≈1800–2600 changed lines) | **Locked** (user decisions; supersede the handoff) |
| 2 | Adjacent cheapest-wins set (COV-04) | **DROPPED** | The core-100 overshoot (≈181 statements from ~88%) lands TOTAL ≈91% ≥ 90 with ≈60 statements of margin over the ≈120 needed for 90% — adjacent fills are unnecessary. Keeping them adds out-of-focus tests and review load. COV-04 is retired; no adjacent module is chased to a floor | **Closed** (superseded by decision 1; see Scope Out) |
| 3 | Pragma policy in the four core modules | **Absolute ban — zero `# pragma: no cover` tokens anywhere in the four files** | "No, 100% real": every line must actually execute. The old "a genuinely untestable line MAY earn one" escape hatch is revoked for the core four; an unreachable line is fixed by test strategy (or escalated in the design doc), never a pragma. Pragmas elsewhere in the diff remain governed by the pre-existing absent/justified rule | **Locked** (user decision) |
| 4 | The dead `__main__` guard — remove vs keep (Resolution A, parent-authorized 2026-09-13) | **KEEP the guard at cli.py:1574-1575; cover it in-process via `runpy.run_module("sofer.cli", run_name="__main__")`; zero `src` edits in this change** | The earlier removal argument rested on two false premises: (a) "nothing references `python -m sofer.cli`" — false: `tests/conftest.py::run_cli` spawns exactly that as the PB-02 subprocess boundary and 14 tests fail with the guard removed; (b) "cannot be driven without subprocess-coverage machinery" — false: an in-process runpy probe executed `main()` through the guard under the coverage tracer (full `--help` emitted; guard lines traced). Real execution reaches 100% with the guard kept — no pragma, no src edit, `python -m sofer.cli` keeps working. The planned static absence test is REPLACED by the guard-EXECUTION test `test_cli_main_guard_executed_via_runpy` (tests/test_cli.py) | **Locked** (parent-owned decision, recorded in this proposal) |
| 5 | Enforcement mechanism | **Per-file scoped gates = NEW COV-06, additive; TOTAL floor untouched (CI-01)** | coverage.py has no per-file floor in config; the scoped invocations `coverage report --include=src/sofer/<file>.py --fail-under=100 -m` express the 100% mandate without touching `[tool.coverage.report]` or the config-owned TOTAL gate. The ci-domain static test CI-01 S2 is narrowed so its `--fail-under` ban covers the TOTAL gate only (the per-file 100 invocations are the documented exception); a one-line carve-out note in the `ci` canonical text is a recorded follow-up, not edited in this scoped pass | **Locked** (user decision) |
| 6 | Enforcement of the three ≥90 floors | **Verify-phase runtime evidence + optional skip-if-absent contract test** | Same precedent as the original COV-01/DP6: percentages are not pytest-assertable as a matter of course; a skip-if-absent guard (local `.coverage`) makes the floors a regression guard without failing a clean checkout. The core four no longer rely on this — the COV-06 CI gates are their durable enforcement | **This proposal** (unchanged for the three floors) |
| 7 | Measurement environment | **Verify on the CI interpreter (ubuntu, Python 3.13) — binary for the core four** | The 100% rows have no margin: the CI gate itself is the arbiter and any 3.13-specific uncovered branch fails the PR there. The three floor rows and TOTAL keep the ≥90-with-margin strategy | **Locked** (as before) |
| 8 | Docs | **AGENTS.md rule 14 ONLY** | The 100% mandate is mandatory repo policy (rule 14, after rule 13); README/README_ES/CONTRIBUTING/PR-template stay as PR #172 left them (rule 13 applies to translated README sections, not AGENTS.md) | **Locked** (user decision) |
| 9 | Delivery shape and size | **Single PR, base `dev`, branch `test/raise-coverage-90`, assigned to emiliodavola; size expectation ≈1800–2600 changed lines; ask-on-risk above 1500** | The 100%-core scope roughly doubles the earlier five-90 test estimate (four modules to 100% yields a large test body — `test_cli.py` alone grows by a third or more). Single-PR intent is preserved, but the 1500-line review budget is an ask-on-risk gate: when the branch crosses it, delivery pauses for a user decision (chain vs exception), never silently | **Locked** (user size expectation; ask-on-risk above 1500) |

## Affected Areas

| Area | Impact | Description |
| ------ | -------- | ------------- |
| `tests/test_cli.py` | Modified | Behavior tests to 100.00% for `cli.py` (extend existing ~1400-line module) |
| `tests/test_scanner.py` | Modified | Behavior tests to 100.00% for `scanner.py` (exists) |
| `tests/test_prepare.py` | Modified | 100.00% for `prepare.py` (+ verification integration leg, unchanged from original) |
| `tests/test_publish.py` | Modified | 100.00% for `publish.py` |
| `tests/test_profile.py` | Modified | ≥90 for `profile.py` |
| `tests/test_mcp_registration.py` | Modified | ≥90 for `mcp_registration.py` |
| `tests/test_splits.py` | Modified | ≥90 for `verification.py` |
| `tests/test_ci_workflows.py` | Modified | NEW scoped-gate + AGENTS rule-14 static tests; NARROWED CI-01 S2 (`test_coverage_gate_is_config_driven_without_cli_floor`) to permit the COV-06 per-file 100 gates |
| `tests/test_coverage_contract.py` | New | Static pragma-token scan (four core modules), optional skip-if-absent `.coverage` floor guard (the `__main__`-guard execution assertion lives in `tests/test_cli.py::test_cli_main_guard_executed_via_runpy` — Resolution A) |
| `tests/conftest.py` | Modified (as needed) | Reusable fixtures only where justified; values from config, never hardcoded |
| `src/sofer/cli.py` | **Untouched** (Resolution A) | `__main__` guard kept; covered by the new in-process runpy test `test_cli_main_guard_executed_via_runpy` in `tests/test_cli.py` (parent decision 4) — zero `src/sofer/` paths in the diff |
| `.github/workflows/ci.yml` | Modified | Coverage job gains COV-06 per-file 100 gate step(s) or references the `scripts/` gate script |
| `scripts/` | New (if script shape chosen) | `check_cli_core_coverage.sh` listing the four files with `--fail-under=100` (permitted alternative to inline steps) |
| `AGENTS.md` | Modified | Rule 14 added (mandatory CLI-core 100% + no-pragma policy) |
| `openspec/changes/2026-09-13-raise-per-file-coverage/` | Modified | Amended proposal + `specs/coverage/spec.md` (COV-01..COV-06; COV-04 retired) |
| `pyproject.toml`, other workflows, other `src/sofer/` files, docs | None | Untouched — TOTAL gate stays config-owned exactly as PR #172 left it |

## Affected Specs

**Recommendation stands: the `coverage` spec domain**
(`openspec/changes/2026-09-13-raise-per-file-coverage/specs/coverage/spec.md`)
rather than extending `ci` or `process-boundary`.

- `ci` pins the pipeline mechanics for the TOTAL gate (CI-01: config-owned
  `fail_under = 90`; CI-02 evidence; CI-03 release gating). The **per-file
  coverage contract** — which modules must hold which floor, the no-pragma
  rule, the single justified `src` touch, the scoped gates — is a
  coverage-policy concern that also binds local test-writing, not the CI
  pipeline. The `ci` proposal itself set the precedent: don't shoehorn a
  distinct concern into an existing domain's audit trail.
- COV-06 intentionally adds per-file scoped gates (a new-machinery exception to
  the original "no gates" stance) but SHALL NOT re-specify or alter CI-01: the
  TOTAL floor stays config-owned, and the scoped invocations' `--fail-under=100`
  is a fixed policy constant, not a tunable floor. The `ci` canonical spec's
  blanket "no `--fail-under`" clause needs a one-line carve-out; that `ci` text
  is NOT edited in this scoped pass (recorded follow-up), while the ci-domain
  static test CI-01 S2 IS narrowed here so the PR gate stays green.
- `process-boundary` PB-05 (complete-suite gate) stays unchanged; the `coverage`
  spec SHALL cross-reference CI-01 for the TOTAL floor and PB-05 for the
  complete-suite-run invariant that every measurement requires.
- Cross-domain note (non-blocking, unchanged): PR #172 archived 6 changes whose
  delta specs were not yet absorbed into canonical `cli`/`mcp-registration`/
  `mcp-server`/`codebook` domains (memory-recorded follow-up). The `coverage`
  domain is written canonical-first, so it is not affected by that pending
  sync.

Planned requirements (RFC 2119, Given/When/Then per rules.specs; every
scenario maps to a test or verify-phase evidence per rule 6):

| Req | Requirement | Scenarios | Maps to |
| ----- | ------------- | ----------- | --------- |
| COV-01 (amended) | `profile.py`, `mcp_registration.py`, `verification.py` SHALL each measure ≥90% under `coverage report -m` (branch coverage, `[tool.coverage.run]` config); `cli.py`/`publish.py` top-tier floors superseded by the COV-06 100% mandate | three rows ≥90 on the regenerated baseline; CI interpreter arbiter; optional contract-guard skip | Verify-phase runtime evidence (`coverage report -m` rows, CI-01-S2 precedent); optional NEW `tests/test_coverage_contract.py` (skip-if-absent; three rows + TOTAL) |
| COV-02 | TOTAL ≥90 so the CI-01 gate passes (`fail_under = 90` untouched) — unchanged | TOTAL row ≥90 + rc 0; CI job green; gate value untouched | Verify-phase evidence + existing `tests/test_ci_workflows.py::test_pyproject_declares_coverage_fail_under_90` (unchanged) |
| COV-03 (amended) | **Zero `src/sofer/` paths in the diff** (Resolution A — the `cli.py` `__main__` guard is kept and executed in-process via runpy, never removed); zero `# pragma: no cover` tokens in the four core modules; pragmas elsewhere absent/justified; `pyproject.toml` untouched; workflow/script machinery limited to the COV-06 gates | zero-src diff; core modules pragma-free (full-text scan); guard-execution test green; gate scope bounded | Verify-phase static evidence (`git diff origin/dev --stat`: no `src/sofer/` path); NEW `tests/test_coverage_contract.py` pragma scan; NEW `tests/test_cli.py::test_cli_main_guard_executed_via_runpy`; diff scan |
| COV-04 | RETIRED in this amendment (Decision Point 2) — no scenarios | — | Recorded in proposal DP2 / Scope Out; kept as a retired marker in the change spec, not archived as a requirement |
| COV-05 | Behavior-asserting tests only — unchanged | observable outcome per new test; no measured-percentage assertions | Review + full-suite green at verify (rule 6) |
| COV-06 (NEW) | The four core modules SHALL each measure 100.00% under the per-file scoped gates (no-config-key, `fail-under=100` per `--include=src/sofer/<file>.py`); zero pragma tokens in the four modules; AGENTS.md rule 14 present; the `cli.py` `__main__` guard is EXECUTED under the coverage tracer via an in-process runpy test (mandatory part of the 100.00 row — Resolution A); TOTAL stays config-owned | (a) scoped gates declared for the four files (workflow or script); (b) no pragma token anywhere in the four modules (full-text scan); (c) AGENTS.md carries the rule; (d) `__main__` guard executed under the tracer (runpy test green); (e) TOTAL `fail_under = 90` untouched | NEW static tests in `tests/test_ci_workflows.py` + `tests/test_coverage_contract.py`; NEW `tests/test_cli.py::test_cli_main_guard_executed_via_runpy`; CI gate exit codes (rc 0) reproduced in verify |

## Impact and Risks

| Impact | Severity | Mitigation |
| -------- | ---------- | ------------ |
| Suite grows (baseline 1567 → ≈1700-1800 tests) and the full run gets slower | Low | Additions are unit-level, following existing per-module fixtures; suites of this shape already run ~1–2 min on CI |
| **PR size ≈1800–2600 changed lines exceeds the 1500 review budget** | **Medium** | Delivery decision 9: single-PR intent but **ask-on-risk** — when the branch crosses 1500 changed lines, pause for a user decision (chain vs exception), never silently expand |
| **Python-version coverage variance**: a floor file at ≥90.1 locally dips to 89.8 on 3.13 | Medium | Decision 7: verify on ubuntu/Python 3.13 with an observed margin above 90; the CI gate is the arbiter |
| **100% with zero pragmas** tempts line-toucher tests or a pragma relapse to game the row | **Medium** | Rule 6 (observable-behavior assertions) + the static pragma-token scan test + AGENTS.md rule 14; review lens checks assertion quality; an unreachable line escalates in the design doc, never a pragma |
| **CI-01 S2 static test conflict** — the new `--fail-under=100` invocations trip the existing workflow-scan test | Medium | Deliberate narrowing of `test_coverage_gate_is_config_driven_without_cli_floor`: the flag ban scopes to the TOTAL gate (per-file 100 invocations are the documented COV-06 exception); the `ci` canonical spec's blanket clause gets a one-line carve-out as a recorded follow-up (not edited in this pass) |
| Coverage-chasing tests with weak assertions creep in under rule 6 | Low | Every new test asserts observable behavior; verify-report records the suite count and an assertion-quality audit |
| Guard-removal premise contradicts the repo (PB-02 subprocess boundary) | **Resolved (Resolution A)** | Blocked at apply (14 tests failed with the guard removed); parent authorized keeping the guard and covering it in-process via runpy — zero `src` edits, `python -m sofer.cli` keeps working |
| Stale `design.md` pins the superseded five-90/cheapest-wins scope | **Medium** | Design phase re-syncs on the amended proposal/spec before apply; the old pinned set is explicitly superseded (DP2); tasks/verify must not reuse it |
| Per-file ≥90 floors (three modules) drift after merge | Low | Verify-phase evidence this change; optional skip-if-absent contract guard; the core four are durably CI-gated by COV-06 |

## Rollback Plan

- **Test + static changes**: revert the touched `tests/` files and `tests/test_coverage_contract.py` — plain-text, additive edits with no migration.
- **Guard handling (Resolution A)**: the `__main__` guard is KEPT — nothing to restore; the runpy guard-execution test in `tests/test_cli.py` is reverted like any test change.
- **Enforcement additions**: revert AGENTS.md rule 14, the gate step(s) in `ci.yml`, and (if used) the `scripts/` gate script.
- **Gate state after rollback**: TOTAL drops back below 90 and the PR #172 gate returns to red — expected, since the gate was deliberately armed as a forcing function awaiting this change.
- **Spec domain**: the `coverage` change spec stays in the change dir / archived change; specs are documentation, no runtime effect.

## Non-Goals

- Any `src/sofer/` change at all — Resolution A mandates zero src touches (no refactor-for-testability, no behavior change, no new seams; the `cli.py` `__main__` guard is kept and covered in-process).
- `# pragma: no cover` anywhere in the four core modules — no exceptions, including "genuinely untestable" lines.
- Adjacent cheapest-wins set (COV-04); coverage-raising on modules outside the four core + three floors; no per-file floor for non-target modules.
- New gate machinery beyond COV-06's per-file scoped invocations (no Codecov, badges, XML, `pytest-cov`, new config keys).
- Changing the gate value (`fail_under = 90` stays; lowering it is a spec change per CI-01); mutating CI-01's config-owned TOTAL design.
- Documentation changes beyond AGENTS.md rule 14 (including README/README_ES — rule 13 untouched).
- Mutation testing or per-file branch floors above 100.

## Success Criteria

1. `uv run coverage report -m` on `test/raise-coverage-90`: `cli.py`,
   `scanner.py`, `prepare.py`, `publish.py` each **100.00** (zero missed
   lines); `profile.py`, `mcp_registration.py`, `verification.py` each **≥90**;
   **TOTAL ≥90** (expected ≈91); process exit rc 0.
2. CI coverage job green on the PR (ubuntu, Python 3.13): the four COV-06
   per-file gates exit 0 AND the config-owned `fail_under = 90` TOTAL gate
   passes — CI-01 untouched.
3. **AGENTS.md rule 14** present with the 100% mandate and the no-pragma clause
   (static test green).
4. **Zero `# pragma: no cover` tokens** in the four core modules (static
   full-text scan test green).
5. `cli.py` `__main__` guard KEPT and executed under the coverage tracer via the
   in-process runpy test `test_cli_main_guard_executed_via_runpy` (green —
   mandatory part of the cli.py 100.00 row); `git diff origin/dev --stat`
   contains **zero** `src/sofer/` paths — the change is strictly test-only.
6. Full suite green (`uv run pytest tests/ -q`); no test-count regression
   (baseline 1567 passed / 6 skipped + new tests); `uv run ruff check src/ tests/`
   and `uv run mypy src/` clean; `git diff --check` clean (test-only change —
   no src edits to trip mypy/ruff).
7. Amended `coverage` spec domain COV-01..COV-06 present, every scenario mapped
   to a test or verify-phase evidence (rule 6); cross-references `ci` CI-01 and
   `process-boundary` PB-05.
8. Single PR against `dev`, PR template filled with real verification output
   (coverage rows + suite + ruff/mypy), assigned to emiliodavola; **ask-on-risk**
   when the changed-line count crosses 1500 — a user decision (chain vs
   exception) is requested, never assumed.

## Amendment Appendix — exact drafts for apply

### A. AGENTS.md rule 14 (English; inserted after rule 13)

```markdown
### 14. CLI-core coverage: 100% mandate, zero pragmas
- `src/sofer/cli.py`, `src/sofer/scanner.py`, `src/sofer/prepare.py`, and
  `src/sofer/publish.py` MUST each measure **100.00% line coverage** under
  `uv run coverage report -m` (the `[tool.coverage.run]` configuration:
  `branch = true`, `source = ["src/sofer"]`), over the complete suite
  (`coverage run -m pytest`). The scoped per-file gates in the CI coverage job
  (`coverage report --include=src/sofer/<file>.py --fail-under=100 -m`) are the
  enforcement; a drop below 100.00% in any of the four files fails CI.
- `# pragma: no cover` is **FORBIDDEN** in those four modules — no exception,
  including "genuinely untestable" lines. Every line must actually execute in
  tests; a line that cannot be reached from a test is a defect in the test
  strategy or a design-doc escalation, never a pragma.
- The TOTAL gate stays config-owned (`[tool.coverage.report] fail_under = 90`,
  spec `ci` CI-01) and is never weakened, bypassed, or re-declared by the
  per-file mandate. The per-file 100% gates are additive and scoped per file;
  they hardcode 100 only because 100 is a fixed policy constant, not a tunable
  floor.
- This rule does NOT justify any `src/sofer/` edit: the dead
  `if __name__ == "__main__": main()` guard in `cli.py` is kept and is exercised
  in-process (`runpy.run_module("sofer.cli", run_name="__main__")` with argv at a
  harmless subcommand) as part of the 100.00% row — `python -m sofer.cli` remains
  a working entry point exercised by the PB-02 subprocess boundary.
- This rule's 100% mandate covers exactly those four modules. Other modules are
  governed by their own per-file floors (spec `coverage` COV-01) or have no
  floor.
```

### B. COV-06 gate steps — recommended shape (inline, in the `ci.yml` coverage job, after the existing `Report coverage with missing lines (the gate)` step)

```yaml
          # ── CLI-core 100% gates (COV-06, AGENTS.md rule 14) ──────────────
          # The four core modules carry an absolute 100% line mandate with zero
          # `# pragma: no cover`. coverage.py cannot express a per-file floor in
          # config, so each file gets its own scoped invocation. `--fail-under=100`
          # is a fixed policy constant, never a tunable floor — the config-owned
          # TOTAL gate (CI-01) is untouched and stays the same `coverage report -m`
          # step above.
          - name: Gate core coverage: cli.py (COV-06)
            run: uv run coverage report --include=src/sofer/cli.py --fail-under=100 -m
          - name: Gate core coverage: scanner.py (COV-06)
            run: uv run coverage report --include=src/sofer/scanner.py --fail-under=100 -m
          - name: Gate core coverage: prepare.py (COV-06)
            run: uv run coverage report --include=src/sofer/prepare.py --fail-under=100 -m
          - name: Gate core coverage: publish.py (COV-06)
            run: uv run coverage report --include=src/sofer/publish.py --fail-under=100 -m
```

(The YAML above is shown at the same indentation as the existing job steps;
apply-phase positions it inside `steps:`.)

### C. COV-06 gate — permitted alternative (one committed script under `scripts/`, referenced by the coverage job)

```bash
# scripts/check_cli_core_coverage.sh  (invoked from the coverage job)
#!/usr/bin/env bash
set -euo pipefail
for f in cli scanner prepare publish; do
  uv run coverage report --include="src/sofer/${f}.py" --fail-under=100 -m
done
```

```yaml
          # Replaces the four inline steps of shape B:
          - name: Gate core module coverage (COV-06)
            run: bash scripts/check_cli_core_coverage.sh
```

## Assumptions (recorded from the amendment handoff — no interview run)

1. **Binding contract** = four core modules at 100.00% (zero pragmas in the
   four files) + `profile.py`/`mcp_registration.py`/`verification.py` at ≥90%
   each + TOTAL ≥90% (CI gate green). No other module is floor-bound (adjacent
   set dropped).
2. **AGENTS.md rule 14** is mandatory repo policy, enforced by the COV-06
   scoped gates.
3. **Zero `src/sofer/` changes (Resolution A, parent-owned 2026-09-13, recorded
   in Decision Point 4)**: the `cli.py` `__main__` guard is KEPT and covered by
   the in-process runpy test `test_cli_main_guard_executed_via_runpy` — the guard
   body executes under the coverage tracer, so cli.py reaches 100.00% by real
   execution with no src edit and `python -m sofer.cli` keeps working.
4. **Scoped gates live in the `ci.yml` coverage job** (inline steps
   recommended in Appendix B; a `scripts/` gate script is the permitted
   alternative in Appendix C); `release.yml` MAY mirror.
5. **Single PR, base `dev`, branch `test/raise-coverage-90`, assignee
   emiliodavola**; size expectation ≈1800–2600 changed lines; ask-on-risk above
   1500 (Decision Point 9) — no chain strategy or size exception is invented.
6. **Baseline figures are the handoff's** (≈181 core statements from ~88%,
   TOTAL ≈91%); exact counts are re-pinned at design with a fresh `coverage
   run`, but the structural conclusion (core-100 overshoot closes TOTAL without
   adjacent fills) is invariant.