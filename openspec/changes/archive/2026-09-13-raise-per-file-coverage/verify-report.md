# Verify Report — Raise per-file coverage to ≥90% (CLI-core 100% mandate)

Change: `2026-09-13-raise-per-file-coverage` · Branch: `test/raise-coverage-90` · Base: `dev`
Phase: verify · **Status: PASS** (implementation verification clean) — with recorded residuals at the parent-owned delivery gates and the CI-arbiter measurement pending the PR run.

## Structured status and actionContext findings

- **Native status** (authoritative, consumed as-is): `applyState: all_done`; `verify: ready`; `sync: blocked` (waits on clean verify); `archive: blocked`; `nextRecommended: sdd-verify`. `taskProgress`: 78 total / 78 complete / 0 remaining / `unchecked: []` (implementation tasks). `deferredParentActions`: 3 remaining — all parent-owned lifecycle gates (§14), none an implementation task.
- **actionContext**: `mode: repo-local`, `workspaceRoot: C:\Users\elaze\Desktop\sofer`, `allowedEditRoots: [repo]`, no warnings. No stop condition fired.
- **Strict TDD**: disabled — `openspec/config.yaml` `strict_tdd: false`; `apply-progress.md` carries the `TDD Cycle Evidence` section correctly marking "Not applicable". The strict-TDD verification checklist does not apply; standard rule-6 (scenario→test/evidence) verification was performed instead.
- **Verify report existence**: `verifyReport: missing` prior to this phase; this report is the authoritative rewrite (apply-progress facts preserved, consolidated below).

## Task completion

All **78/78 implementation tasks** are checked `[x]` in `tasks.md`. The only unchecked markers are the three **parent-owned** lifecycle gates (§14) — not implementation tasks, not archive blockers from the implementation side:

```text
159: - [ ] Ask-on-risk gate: when the measured `git diff origin/dev --stat` crosses 1500 changed lines, PAUSE and request the user decision — chain vs size-exception; never invent a chain strategy or an exception. Record the decision in the verify report. <!-- sdd-owner: parent -->
160: - [ ] Post-apply bounded review of the full PR diff (review lens): assertion quality per COV-05, no pragma relapse, **zero `src/sofer/` paths** (Resolution A), gate-shape correctness, floor margins recorded. <!-- sdd-owner: parent -->
161: - [ ] Delivery: open the single PR against `dev` from `test/raise-coverage-90`, assign emiliodavola, fill the PR template with the real verification output from V. <!-- sdd-owner: parent -->
```

**Ask-on-risk decision record (per §14 gate text):** measured `git diff origin/dev --stat` = **2770 changed lines**, crossing the 1500 ask-on-risk threshold. The apply-progress records a **user-authorized provisional single-PR size exception (≤ ~3000 changed lines)**; 2770 < 3000, so the measured size sits within the recorded exception. Chain strategy was never selected and is **not** invented here; the final chain-vs-exception confirmation stays at the parent-owned delivery gate. Archive readiness for the *implementation* is unaffected; the delivery decision is a parent action.

## Per-requirement verification (COV-01..COV-06)

Spec contains **16 scenarios** (15 top-level + 1 nested guard-execution scenario under COV-06). Every scenario maps to a green test or recorded verify-phase evidence (AGENTS.md rule 6) — none uncovered.

| Req | Scenario | Evidence (exact) | Result |
| --- | --- | --- | --- |
| COV-01 | Three second-tier rows meet the floor on the regenerated baseline | Verify-phase runtime evidence, complete suite (`coverage run -m pytest tests/ -q`, PB-05): `profile.py 253 8 96 7 **96%**`, `mcp_registration.py 235 1 106 1 **99%**`, `verification.py 60 0 22 0 **100%**` — each ≥90, individually binding | ✅ PASS |
| COV-01 | The CI interpreter is the arbiter | Reproduced locally (measured rows above; margins recorded: +6 / +9 / +10 pp over the 90 floor). CI (ubuntu / Python 3.13) measurement pending the PR run — binary gates have no margin by design; floors carry recorded margin | ✅ PASS (local) / residual: CI run pending |
| COV-01 | Optional contract guard skips on a clean checkout | `tests/test_coverage_contract.py::test_three_floor_modules_and_total_meet_90_when_data_file_present` — `@pytest.mark.skipif(not (.coverage).exists())`, lazy `import coverage`, read-only API, empty/partial DB treated as absent. Verified with `.coverage` removed: `2 passed, 1 skipped` | ✅ PASS |
| COV-02 | TOTAL meets the floor and the gate exits 0 | `uv run coverage report -m` → `TOTAL 5995 365 2318 166 **93%**`, exit **0** | ✅ PASS |
| COV-02 | CI coverage job turns green on the PR | Local reproduction green: config-owned TOTAL gate (`uv run coverage report -m` rc 0) + all four COV-06 per-file gates rc 0; `fail_under = 90` untouched. CI job result pending PR opening (parent delivery gate) | ✅ PASS (local reproduction) / residual: CI run pending |
| COV-02 | Gate value untouched | `tests/test_ci_workflows.py::test_pyproject_declares_coverage_fail_under_90` (existing, unchanged) — `fail_under == 90`; `pyproject.toml` absent from the diff (`git diff origin/dev --name-only` grep count 0) | ✅ PASS |
| COV-03 | The diff contains zero src changes | `git diff origin/dev --stat` = 11 files, **2770 insertions(+), 8 deletions(-), ZERO `src/sofer/` paths** (Resolution A: guard kept, not removed) | ✅ PASS |
| COV-03 | Core modules are pragma-free (full-text scan) | `tests/test_coverage_contract.py::test_core_modules_contain_no_pragma_tokens` green (regex covers `# pragma:` and `#pragma:` spellings) + independent `grep -rn "pragma: no cover" src/sofer/{cli,scanner,prepare,publish}.py` → zero matches (rc 1) | ✅ PASS |
| COV-03 | Gate machinery in the diff is bounded | Verify-phase static evidence + `test_gate_machinery_bounded`: `pyproject.toml` absent from diff; the only gate invocations are the COV-06 scoped `--include=src/sofer/<file>.py --fail-under=100 -m` calls inside `scripts/check_core_coverage.sh` (invoked by one ci.yml step); no `pytest-cov`, no `coverage xml`, no Codecov/Coveralls tokens in ci.yml/release.yml | ✅ PASS |
| COV-04 | (Retired — no scenarios) | Recorded retired in proposal DP2 / spec text; not enforced; nothing references the superseded cheapest-wins set | ✅ (informational) |
| COV-05 | Each new test asserts an observable outcome | Review-lens audit (verify) + apply V-5: behavior tests assert rc / stdout+stderr text / written artifact content / exception; sampled directly (see Assertion-quality findings); full suite green | ✅ PASS |
| COV-05 | No test asserts measured percentages | Test-diff scan: zero coverage-measurement percentage assertions; the single `.coverage` read is the sanctioned skip-if-absent floor guard (COV-01-S3 carve-out). Percentages live in verify-phase evidence + CI gate exit codes only | ✅ PASS |
| COV-06 | Scoped gates are declared for all four core files | `tests/test_ci_workflows.py::test_coverage_job_gates_core_modules_at_100` green: script roster `for f in cli scanner prepare publish`, invocation shape `--include="src/sofer/${f}.py" --fail-under=100 -m`, script referenced by ci.yml step, no `--fail-under` value other than 100, no config-key spelling `fail_under` in script/workflows. Script run: rc 0, four 100.00 rows | ✅ PASS |
| COV-06 | No pragma tokens anywhere in the four core modules | Same shared scan as COV-03 row (`test_core_modules_contain_no_pragma_tokens` green + independent grep, zero matches) | ✅ PASS |
| COV-06 | AGENTS.md carries the mandatory rule | `tests/test_ci_workflows.py::test_agents_md_declares_core_100_mandate` green + text inspection: rule 14 (`### 14. CLI-core coverage: 100% mandate, zero pragmas`, AGENTS.md:100) names the four modules, declares 100.00%, forbids `# pragma: no cover`, references `scripts/check_core_coverage.sh` | ✅ PASS |
| COV-06 | The cli.py `__main__` guard is executed under the coverage tracer | `tests/test_cli.py::test_cli_main_guard_executed_via_runpy` (line 1443) green standalone (`1 passed`) and in-suite: `runpy.run_module("sofer.cli", run_name="__main__")` with `argv = ["sofer", "--help"]`, asserts `SystemExit.code == 0`; guard **kept** at `cli.py:1574-1575`; cli.py row 100.00 including the guard (zero missed) | ✅ PASS |
| COV-06 | TOTAL stays config-owned at 90 | `test_pyproject_declares_coverage_fail_under_90` green (`fail_under == 90`); verify-phase gate runs: four per-file invocations each rc 0, TOTAL gate rc 0; no coverage threshold added or re-declared; `release.yml` deliberately not mirrored (COV-03 bounded machinery) | ✅ PASS |

## Exact validation-command output

### Full suite (task V-1 / verify contract)
```text
$ uv run pytest tests/ -q
1745 passed, 6 skipped, 14 warnings in 45.01s
```
Complete-suite coverage pass (PB-05; same run regenerates `.coverage`):
```text
$ uv run coverage run -m pytest tests/ -q
1745 passed, 6 skipped, 14 warnings in 60.49s
```

### Coverage rows (COV-01/02/06; `uv run coverage report -m`, exit 0)
```text
src\sofer\cli.py                   564      0    162      0   100%
src\sofer\mcp_registration.py      235      1    106      1    99%   424
src\sofer\prepare.py               432      0    226      0   100%
src\sofer\profile.py               253      8     96      7    96%   196->198, 325, 355, 358, 387, 411, 417, 451-452
src\sofer\publish.py               326      0    138      0   100%
src\sofer\scanner.py               159      0     76      0   100%
src\sofer\verification.py           60      0     22      0   100%
TOTAL                             5995    365   2318    166    93%
```
Four core rows **100.00 / zero missed**; floors **96 / 99 / 100** (≥90); **TOTAL 93%** (≥90); rc **0**.

### COV-06 gate script (COV-06; `bash scripts/check_core_coverage.sh`, exit 0)
```text
src\sofer\cli.py     564      0    162      0   100%   (TOTAL 564 0 162 0 100%)
src\sofer\scanner.py     159      0     76      0   100%  (TOTAL 159 0 76 0 100%)
src\sofer\prepare.py     432      0    226      0   100%  (TOTAL 432 0 226 0 100%)
src\sofer\publish.py     326      0    138      0   100%  (TOTAL 326 0 138 0 100%)
gate script exit code: 0
```

### Negative TOTAL probe (gate-enforcement proof, verify-only)
```text
$ uv run coverage report --fail-under=95 > /dev/null 2>&1; echo $?
2   (gate enforced — TOTAL 93 < 95)
```

### Quality gates
```text
$ uv run ruff check src/ tests/ scripts/
All checks passed!          (rc 0)
$ uv run mypy src/ scripts/
Success: no issues found in 33 source files   (rc 0)
$ git diff --check          → rc 0 (clean; CRLF-normalization warnings only, benign)
```

### Static contracts
```text
$ grep -rn "pragma: no cover" src/sofer/cli.py src/sofer/scanner.py src/sofer/prepare.py src/sofer/publish.py
(no output — zero tokens; rc 1)
$ grep -n "fail_under\|--fail-under\|fail-under" .github/workflows/ci.yml .github/workflows/release.yml
(no output — rc 1; floors live only in scripts/check_core_coverage.sh)
$ uv run pytest tests/test_cli.py::test_cli_main_guard_executed_via_runpy -q
1 passed
$ uv run pytest tests/test_coverage_contract.py -q        # with .coverage removed
2 passed, 1 skipped                                       # floor guard skips on clean checkout
```

### Runpy guard evidence (COV-06 scenario d)
`cli.py:1574-1575` keeps `if __name__ == "__main__":` + `main()`. The in-process test sets `sys.argv = ["sofer", "--help"]`, calls `runpy.run_module("sofer.cli", run_name="__main__")`, and asserts `SystemExit.code == 0` — `main()` executes **through the guard under the coverage tracer** (guard lines counted covered; cli.py row 100.00 with zero missed). No pragma, no `src/sofer/` edit; `python -m sofer.cli` remains a working entry point and `tests/conftest.py::run_cli` keeps its PB-02 subprocess boundary.

### Diff / scope-drift evidence (COV-03)
```text
$ git diff origin/dev --stat
 .github/workflows/ci.yml       |   7 +
 AGENTS.md                      |  28 ++
 openspec/specs/ci/spec.md      |   5 +
 tests/test_ci_workflows.py     |  72 +++-
 tests/test_cli.py              | 739 ++++++++....
 tests/test_mcp_registration.py | 280 ++++++++
 tests/test_prepare.py          | 631 +++++++++++...
 tests/test_profile.py          | 294 ++++++++-
 tests/test_publish.py          | 404 ++++++++
 tests/test_scanner.py          | 222 +++++++
 tests/test_splits.py           |  96 +++++
 11 files changed, 2770 insertions(+), 8 deletions(-)
```
**Zero `src/sofer/` paths** (Resolution A). Suite grows 1567 → **1745 passed** (+178), 6 skipped unchanged. No scope drift beyond the assigned slice (tests + gate script + ci.yml step + AGENTS.md rule 14 + canonical `ci` carve-out + change artifacts).

## Accepted deviations and reconciliations (recorded in apply-progress, preserved here)

- **Resolution A (parent-authorized 2026-09-13)**: the `cli.py` `__main__` guard is KEPT (not removed) and covered in-process via the runpy test — the earlier removal plan rested on two false premises (PB-02 subprocess boundary uses `-m sofer.cli`; the guard body executes in-process under the tracer). Amendment recorded in proposal DP4, spec COV-03/COV-06, design §1/§3.1, tasks A-1, AGENTS rule 14 clause.
- **Seam-driven tests for provably-unreachable/defensive branches** (design-doc reconciliations, not pragmas): scanner parent-guard loop natural exit and link-skip/TOML-name-skip continues driven via FS-walk/`_is_link` seams; prepare parity-fail + the "No `[[file]]` entries" validator-reachable branch driven via direct-converter/validator seams; profile's remaining 8 lines/arcs (`196->198` gaps-empty, `out_path is None` guards, `base_rel` fallback) documented provably-defensive; mcp_registration line 424 (post-loop `return False`) documented provably dead (loop body always returns); publish NOT-FOUND advisory (830) requires a built package with the source then deleted (manifest gate precedes). Each is a recorded reconciliation in apply-progress units B–H.
- **COV-06 shape**: `scripts/check_core_coverage.sh` script form (proposal appendix C) chosen over inline steps — keeps CI-01 S2's workflow-text force literally true; `release.yml` deliberately NOT mirrored (COV-03 bounded machinery). The one-line `ci` canonical carve-out clause was appended to `openspec/specs/ci/spec.md` (line 30) as the recorded follow-up.
- **CI-01 S2 narrowing**: `test_coverage_gate_is_config_driven_without_cli_floor` re-scoped to the TOTAL gate only, with an added pinned assertion that the TOTAL report step stays the flag-free `uv run coverage report -m`.
- **Pre-existing pragma**: `mcp_registration.py::atomic_write` tomli-w import guard is untouched and out of scope (not a core module; COV-03/06 ban covers the four core files only).

## Assertion-quality findings (COV-05 audit, verify)

- Sampled behavior tests assert real observable outcomes: runpy guard test asserts `SystemExit.code == 0`; `TestNoChecksPath` asserts rc 0 + `build/` artifact contents; scan dry-run/EOf tests assert printed messages ("OK  Aborted.", "Nothing to copy — all files already present") and TOML byte-identity; publish tests assert rc, capsys "NOT FOUND"/warning text, `protected_out` side-channel growth. Values come from config/fixtures (AGENTS rules 1/3).
- Static contract tests are shape/text assertions, not tautologies: pragma-token regex scans, script-roster + invocation-shape checks, rule-14 text checks, `fail_under == 90` tomllib check, flag-absence scans.
- No ghost loops, type-only assertions, or smoke-only tests found in the changed set; the only measured-percentage read is the sanctioned skip-if-absent local `.coverage` guard (COV-01/02 evidence carve-out per spec Test Mapping).

## Review workload / PR boundary (ask-on-risk)

- **Review Workload Forecast**: chained PRs recommended; `Chain strategy: pending`; delivery strategy `ask-on-risk`; estimated ≈1800–2900.
- **Measured**: 2770 changed lines in one branch intended as a single PR vs `dev` — matches the forecast range; **zero `src/sofer/` paths**; one slice only (no chained-PR slices were split, consistent with a chain strategy still pending). Recorded user provisional single-PR exception ≤ ~3000 covers 2770 (apply-progress). No `size:exception` was silently adopted — the ask-on-risk decision is recorded above and remains open at the parent delivery gate.
- **Scope-creep check**: assignments 78/78 all within the changed-file set; nothing outside the mandated slice (no adjacent cheapest-wins, no non-target floors, no new gate machinery beyond the COV-06 script+step).

## Residuals / risks

1. **CI-arbiter measurement pending** (ubuntu / Python 3.13): the four 100.00 rows are binary with no margin; a 3.13-specific uncovered branch would fail the PR coverage job. Floors carry margin (+6/+9/+10 over 90; TOTAL +3 over 90). Design risk register §6.3 note: the win32 `sys.platform` reconfigure guards in prepare.py/publish.py are covered via patched-platform tests precisely because the CI gate is ubuntu — no relapse observed.
2. **Delivery gate open (parent-owned)**: no commits were made (parent hard constraint #1); the delivery phase must land the work-unit commits (messages recorded in apply-progress §6.1) and open the single PR vs `dev` from `test/raise-coverage-90` (assignee emiliodavola, PR template filled with the real output in this report). Chain-vs-exception confirmation also lives here.
3. **Post-apply bounded review (parent-owned)**: listed as a deferred parent action; the verify-side audit above covers assertion quality, pragma absence, zero-src, gate-shape, and floor margins, but the parent may wish to re-run the review lens on the full PR diff.
4. **Non-critical residuals within floors**: `mcp_registration.py` 99% (1 missed statement + 1 partial arc, provably-dead post-loop return) and `profile.py` 96% (8 provably-defensive/dead lines) — documented reconciliations, within floor with margin; `verification.py` at 100% overshoots its floor.
5. Parent input summary said "12 scenarios" — the authoritative spec count is **16** (15 top-level + 1 nested guard-execution scenario); all 16 mapped above.

## Blockers

None for implementation verification. Archive/sync remain `blocked` only by the pipeline order (sync waits on clean verify — now available; archive waits on sync + delivery).