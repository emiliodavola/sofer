# Design: Harden the release/dependabot bump flow

## Technical Approach

Three coupled layers, all CI-policy, no runtime code:

1. **Literal-free guards.** The release-parity guard derives the setup-uv ref
   from `ci.yml` instead of naming it. A consistent action bump then flows
   through with no test edit.
2. **Consistency guards.** One guard asserts every GitHub Action ref is
   identical across every workflow; one asserts `.python-version` equals every
   gate-job interpreter pin. Together with the existing CI-08 (ruff) and CI-09
   (mypy/pyright) guards, every version declared in more than one home is
   guarded.
3. **Dependabot policy.** `ignore` the two bumps the bot cannot complete: the
   coordinated `ruff` pin and `fastmcp` majors. Keep majors out of the
   minor/patch groups and pin that with a guard. Document the manual procedure.

## Architecture Decisions

### Decision: Extend `tests/test_ci_workflows.py`, do not add a scripts/ checker

**Choice**: Add the consistency guards to the existing static guard module.
**Alternatives considered**: A new `scripts/check_pin_consistency.py` invoked
as a lint step.
**Rationale**: `tests/test_ci_workflows.py` already parses the workflows,
`pyproject.toml`, `.pre-commit-config.yaml`, and `openspec/config.yaml`, and
already runs in every `test`/`lint`/`coverage` job (and the release job). A new
script would duplicate YAML/TOML parsing and impose collection, typing, and
coverage obligations on a second artifact without detecting anything the
extended guards miss. The request's "one check" is satisfied by one cohesive
guard family in the one CI-run home.

### Decision: Derive the action ref, do not bump the literal

**Choice**: Replace `_find_step(lint, uses="astral-sh/setup-uv@v10.2.0")` with
a comparison of `release.yml`'s setup-uv ref against `ci.yml`'s, both located
by action name.
**Alternatives considered**: Keep the literal and bump it in every Dependabot
PR (status quo), or read the ref from `dependabot.yml`.
**Rationale**: The literal is the defect (#251). Deriving from `ci.yml` makes
the guard assert the *property* that matters (release parity with CI) rather
than an incidental value, and needs no maintenance.

### Decision: `ignore` ruff fully, `ignore` fastmcp majors only

**Choice**: A bare `ignore: ruff` (all updates) and
`ignore: fastmcp` with `update-types: ["version-update:semver-major"]`.
**Alternatives considered**: Ignore all majors for all dependencies; ignore
nothing and rely on the suite.

- `ruff` is a single authoritative version spread over four homes
  (`pyproject.toml` dev pin **and** `required-version`,
  `.pre-commit-config.yaml` rev, and `CONTRIBUTING.md` prose) enforced by CI-08.
  Dependabot's `uv` ecosystem can only touch the first; the others are a
  `pre-commit`/docs ecosystem and a TOML key it will not move. Any PR it opens
  is guaranteed red, so ignoring is correct and the manual procedure is
  documented.
- `fastmcp` is a **runtime** dependency whose major requires code adaptation
  (#253: MCP SDK v2 renames), and Dependabot escalated it by rewriting the
  declared `<4` cap itself. Ignoring majors keeps the cap as a real boundary;
  a human opens the adaptation deliberately.
- Other majors arrive as individual, ungrouped PRs and are fine to review
  case by case; ignoring them all would lose signal.

### Decision: Reject a bundled "majors group"

**Choice**: No group for majors; instead a guard pins that the catch-all
groups declare only `minor`/`patch`.
**Alternatives considered**: A `majors` group with `update-types: ["major"]`.
**Rationale**: A Dependabot group collapses every matching update into one PR;
grouping majors would make one giant, hard-to-attribute PR and still not
*enforce* review (only branch protection does). The separation that matters —
majors stay out of the routine minor/patch sweep — already holds because the
groups filter on `update-types`; the guard makes that property durable against
a future edit that silently adds `major`.

## Data Flow

    ci.yml lint ── setup-uv ref ──┐
                                   ├── compared by test_release_lint_job_runs_the_ci_lint_gates
    release.yml lint ── same ref ──┘

    all workflows ── uses: owner/action@ref (step + job level) ── group by owner/repo ── assert one ref  (CI-13 S1)

    .python-version ─┐
    ci.yml lint/coverage ─┼── assert equal  (CI-13 S3)
    release.yml lint/coverage ─┘

    dependabot.yml uv.ignore ── assert ruff + fastmcp-major present  (CI-14)
    dependabot.yml groups[*].update-types ── assert no "major"        (CI-14 S3)

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `tests/test_ci_workflows.py` | Modify | Derived setup-uv parity; two consistency guards; three Dependabot policy guards; docstring range CI-01..CI-14 |
| `.github/dependabot.yml` | Modify | `ignore` ruff + fastmcp-major, with comments |
| `CONTRIBUTING.md` | Modify | "Dependency updates" subsection |
| `AGENTS.md` | Modify | Rule 8 bullet pointing at the procedure |
| `openspec/specs/ci/spec.md` | Modify | CI-13 + CI-14 via compose; Test Mapping rows |
| `openspec/changes/2026-09-26-harden-dependabot-bump-flow/` | Create | SDD artifacts |

## Interfaces / Contracts

Verification-cell prefixes for the new scenarios (AGENTS.md rule 6): all six
are `test:` references into `tests/test_ci_workflows.py`.

```
CI-13 S1  test:tests/test_ci_workflows.py::test_workflow_action_refs_are_consistent_across_workflows
CI-13 S2  test:tests/test_ci_workflows.py::test_release_lint_job_runs_the_ci_lint_gates
CI-13 S3  test:tests/test_ci_workflows.py::test_dev_interpreter_pin_matches_gate_jobs
CI-14 S1  test:tests/test_ci_workflows.py::test_dependabot_ignores_the_coordinated_ruff_pin
CI-14 S2  test:tests/test_ci_workflows.py::test_dependabot_ignores_fastmcp_majors
CI-14 S3  test:tests/test_ci_workflows.py::test_dependabot_groups_exclude_majors
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Action refs one-per-action | `test_workflow_action_refs_are_consistent_across_workflows` (YAML parse of every workflow) |
| Unit | Release setup-uv parity, derived | `test_release_lint_job_runs_the_ci_lint_gates` (rewritten) |
| Unit | Interpreter pin equality across homes | `test_dev_interpreter_pin_matches_gate_jobs` |
| Unit | Dependabot `ignore` + group bounds | three Dependabot guards (YAML parse) |
| Contract | Spec↔test mapping bijection | `uv run python scripts/check_test_mapping.py` |
| Runtime | Guards are green on the tree | `uv run pytest tests/test_ci_workflows.py -q`; full suite; ruff/mypy/pyright |

## Threat Matrix

N/A — no routing, application shell/subprocess, VCS/PR automation,
executable-file classification, or process-integration boundary change. The
change edits test guards, one YAML config file consumed by GitHub's Dependabot
service, and documentation; it adds no runtime code path.

## Migration / Rollout

No migration. The guards take effect for the next PR; the Dependabot policy
takes effect on the next scheduled run.

## Open Questions

None.
