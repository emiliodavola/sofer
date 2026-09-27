# Verify Report: Harden the release/dependabot bump flow

**Change**: `2026-09-26-harden-dependabot-bump-flow`
**Branch**: `ci/dependabot-bump-hardening` (base `origin/dev` @ `1ac716d`, rebased
after the concurrent #251/#252 merges landed ruff 0.16.8 / setup-uv 10.2.0)
**Worktree**: `/workspace/sofer-worktrees/dependabot-bump-hardening` (isolated from
a concurrent agent mutating the primary checkout)

## Claim-by-claim verification

| # | Claim | Result | Evidence |
|---|-------|--------|----------|
| 1 | The setup-uv release-parity guard no longer holds a version literal and derives the ref from `ci.yml` | PASS | `git diff dev -- tests/test_ci_workflows.py` removes `uses="astral-sh/setup-uv@v10.1.0"`; the guard calls `_step_action_ref(ci_lint, _SETUP_UV_REPO)` and compares. `rg 'v10\.' tests/test_ci_workflows.py` has no hit. |
| 2 | A consistent setup-uv bump of both workflows needs no test edit | PASS | Negative control mutated `release.yml` only → guard fails; with both workflows aligned the guard passes. The guard compares `release_uv == ci_uv` (both derived) and the `python-version` axis against `.python-version` — no `setup-uv` or interpreter literal remains (raised by the adversarial verifier and fixed). |
| 3 | Action refs are one-per-repository across all workflows | PASS | `test_workflow_action_refs_are_consistent_across_workflows` groups by `owner/repo` (lower-cased), scans step-level AND job-level `uses`, and covers `.yml`/`.yaml`; passes on the committed tree and fails on the `codeql-action/init` v4→v5 probe. |
| 4 | `.python-version` equals every gate-job pin | PASS | `test_dev_interpreter_pin_matches_gate_jobs` collects 4 pins (lint+coverage × ci+release), all `3.13`; the `3.12` probe fails. |
| 5 | Dependabot opens no `ruff` PR | PASS | `.github/dependabot.yml` `uv.ignore` names `ruff`; `test_dependabot_ignores_the_coordinated_ruff_pin` passes and fails when the entry is removed. |
| 6 | Dependabot opens no `fastmcp` major PR, keeps minor/patch | PASS | `ignore` entry `fastmcp` with `update-types: ["version-update:semver-major"]`; guard passes and fails on the minor probe. |
| 7 | Every group declares exactly minor/patch, never a major | PASS | Both groups declare `update-types: ["minor", "patch"]`; the group guard asserts exact set equality (tightened after the adversarial verifier flagged the earlier subset check as weaker than the requirement) and fails when `major` is added. |
| 8 | The manual bump procedure is documented | PASS | `CONTRIBUTING.md` "Dependency updates" section + `AGENTS.md` rule 9 bullet; `test_contributing_names_the_declared_ruff_version` (unchanged) still passes. |
| 9 | Spec↔test mapping holds for the six new scenarios | PASS | `uv run python scripts/check_test_mapping.py` → `OK: test-mapping contract holds`. |
| 10 | No runtime regression, no coverage loss | PASS | Full suite 1987 passed / 2 skipped; four core modules 100%; TOTAL 94%. |

## Negative-control probes (guard efficacy)

Each probe mutates exactly one declaration, runs the owning guard, and restores
the original bytes. All six fail as expected:

```
[FAILS AS EXPECTED] CI-13 S1 action-ref consistency -> exit 1
[FAILS AS EXPECTED] CI-13 S2 setup-uv parity (release vs ci) -> exit 1
[FAILS AS EXPECTED] CI-13 S3 interpreter pin -> exit 1
[FAILS AS EXPECTED] CI-14 S1 ruff ignore -> exit 1
[FAILS AS EXPECTED] CI-14 S2 fastmcp major ignore -> exit 1
[FAILS AS EXPECTED] CI-14 S3 groups exclude majors -> exit 1
PROBE SUMMARY: ALL GUARDS FAIL ON DRIFT
```

Representative actionable messages:

```
AssertionError: the same GitHub Action repository is referenced at more than one
ref across .github/workflows/*.yml: {...} — a bump must move every occurrence
together (CI-13 S1, GitHub #251)
```

```
AssertionError: the release `lint` job must use the same astral-sh/setup-uv ref
as ci.yml (…), got … — derived, never a literal (CI-13 S2, GitHub #251)
```

The first probe round exposed a real gap (grouping by full action path treated
`github/codeql-action/init` and `/analyze` as separate repositories); `_action_repo`
now groups by `owner/repo`, matching Dependabot's bump granularity, and the probe
passes.

## Runtime gate evidence

```
$ uv run pytest tests/test_ci_workflows.py -q
45 passed

$ uv run pytest tests/ -q
1988 passed, 1 skipped

$ uv run ruff check tests/test_ci_workflows.py
All checks passed.

$ uv run ruff format --check tests/test_ci_workflows.py
1 file already formatted

$ uv run mypy src/ scripts/            # under the 3.13 gate interpreter
Success: no issues found

$ uv run pyright
0 errors, 1 warning, 0 informations    # pre-existing tomli reportMissingModuleSource

$ uv run coverage run -m pytest -q
1988 passed, 1 skipped

$ bash scripts/check_core_coverage.sh
src/sofer/cli.py      100%
src/sofer/scanner.py  100%
src/sofer/prepare.py  100%
src/sofer/publish.py  100%

$ uv run coverage report -m | tail -1
TOTAL   6222  325  2340  154  94%

$ uv run python scripts/check_test_mapping.py
OK: test-mapping contract holds
```

## Adversarial findings (independent subagent) and resolution

An independent adversarial verifier (read-only) adjudicated the six scenarios
and found three concrete weaknesses, all fixed before this report:

1. **Residual interpreter literal** in `test_release_lint_job_runs_the_ci_lint_gates`
   (`== "3.13"`) contradicted CI-13's own "no literal of its own" rule: a
   consistent interpreter bump would still need a test edit. **Fixed** — the
   guard now compares against `.python-version`.
2. **Group check weaker than the requirement** — the test asserted a subset of
   `{minor, patch}` while the requirement says *exactly*. **Fixed** — exact set
   equality, and the scenario wording aligned.
3. **Job-level reusable-workflow `uses:` unscanned** (and `.yaml` workflows /
   case-variant owners not covered). **Fixed** — job-level `uses` values are
   now scanned, `.yaml` workflows are enumerated, and the repository key is
   lower-cased.

## Notes

- One full-suite run hit `TestStdioFraming::test_initialize_list_call_clean_jsonrpc`
  (`unhandled errors in a TaskGroup`) under concurrent sandbox load from the
  other agent's `uv sync`/test processes. It passed in isolation and on the
  rerun; it is a timing-sensitive stdio subprocess test unrelated to this
  change, which touches no `src/sofer/` file.
- No `uv.lock`, workflow, or `pyproject.toml` change was needed; the guards
  read declarations, they do not move them.

## Verdict

PASS — all ten claims verified, six negative controls fail on drift, all gates
green. Independent read-only subagent verification is recorded separately.
