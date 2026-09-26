# Proposal: Harden the release/dependabot bump flow

## Intent

Dependabot bumped a dependency and CI went red three releases in a row
(#251, #252, #253), each time for a reason a static guard could have caught
*at the bump* instead of *after a maintainer notices*. This change makes the
guards derive from declarations (so a consistent bump needs no test edit),
adds the missing multi-home consistency guards, and configures Dependabot so
the bumps it cannot complete atomically are not attempted.

Evidence (details in `exploration.md`):

- **#251**: `tests/test_ci_workflows.py:934` hardcoded
  `uses="astral-sh/setup-uv@v10.1.0"`, so the consistent 10.2.0 bump failed 11
  test jobs until a human edited the literal.
- **#252**: Dependabot bumped the `ruff` dev pin to `0.16.8`, but
  `[tool.ruff] required-version`, the pre-commit `rev`, and `CONTRIBUTING.md`
  still named `0.16.7`. Ruff aborts at config load. Dependabot's `uv`
  ecosystem cannot move the pre-commit rev or the prose.
- **#253**: Dependabot rewrote `fastmcp>=3.4,<4` to `<5`; fastmcp 4 / MCP SDK
  v2 changed the API and 11 test jobs failed.

## Scope

### In Scope

- Remove the hardcoded setup-uv ref from the CI-12 release-parity guard; derive
  it from `ci.yml` so a consistent action bump requires no test edit.
- Add a guard that every GitHub Action ref is identical across all
  `.github/workflows/*.yml` occurrences.
- Add a guard that `.python-version` equals the `python-version` pin of the
  `lint` and `coverage` jobs in both workflows (strengthens CI-07 to
  test-backed).
- Harden `.github/dependabot.yml`: `ignore` `ruff` (all updates) and
  `fastmcp` major updates; keep majors out of the minor/patch groups and pin
  that with a guard.
- Document the bump procedure in `CONTRIBUTING.md`, with an `AGENTS.md`
  pointer.
- Add `ci` requirements CI-13 and CI-14 with scenarios and Test Mapping rows.

### Out of Scope

- Versioning (hatch-vcs + tag) and the published release flow / `v0.4.0`.
- Any `src/sofer/` change — this is a CI-policy change.
- Adapting fastmcp 4 (#253's code work) — that is the bump PR's own work.
- A new standalone consistency script — the existing CI-run guard module is
  the home; a second script adds infrastructure without new detection.
- A bundled Dependabot "majors group" — rejected; see `design.md`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ci`: two requirements are added — **CI-13** (literal-free, consistency-guarded
  version declarations) and **CI-14** (Dependabot update policy).

## Approach

1. Rewrite the setup-uv half of `test_release_lint_job_runs_the_ci_lint_gates`
   to derive the expected `uses` from `ci.yml`'s `lint` job.
2. Add `test_workflow_action_refs_are_consistent_across_workflows` and
   `test_dev_interpreter_pin_matches_gate_jobs`.
3. Add `ignore` entries and explanatory comments to `.github/dependabot.yml`,
   then guard them with three tests.
4. Add the `CONTRIBUTING.md` "Dependency updates" section and the `AGENTS.md`
   pointer.
5. Write the CI-13/CI-14 delta, archive it into `openspec/specs/ci/spec.md`,
   and add the Test Mapping rows.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `tests/test_ci_workflows.py` | Modified | Derived setup-uv parity; action-ref consistency guard; interpreter-pin guard; Dependabot policy guards; docstring range |
| `.github/dependabot.yml` | Modified | `ignore` ruff + fastmcp-major; explanatory comments |
| `CONTRIBUTING.md` | Modified | New "Dependency updates" subsection |
| `AGENTS.md` | Modified | Rule 8 pointer to the bump procedure |
| `openspec/specs/ci/spec.md` | Modified | CI-13 + CI-14 requirements, scenarios, Test Mapping rows |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Action-ref consistency guard trips on a legitimate intentional divergence | Low | Every action currently has one ref per repo; the guard's failure message names the action and the refs |
| Dependabot `ignore` on `ruff` hides a needed bump | Low | The rule is documented; a human bumps all homes together (CONTRIBUTING) |
| Test-mapping bijection breaks when CI-13/CI-14 rows are added | Medium | Add rows and run `check_test_mapping.py` in the same change |
| New guards conflict with existing workflow-text guards | Low | No workflow file is edited; guards read only |

## Rollback Plan

Revert the five-file diff (`tests/test_ci_workflows.py`,
`.github/dependabot.yml`, `CONTRIBUTING.md`, `AGENTS.md`,
`openspec/specs/ci/spec.md`) and re-run the suite. No dependency, release, or
runtime state is touched.

## Dependencies

None.

## Success Criteria

- [ ] A consistent setup-uv bump no longer requires editing a test literal.
- [ ] A partial action bump or an interpreter-pin drift fails a static guard.
- [ ] Dependabot cannot open a `ruff` PR or a `fastmcp` major PR.
- [ ] `uv run python scripts/check_test_mapping.py` exits 0.
- [ ] `uv run pytest tests/ -q` green; ruff check/format, mypy, pyright clean.
