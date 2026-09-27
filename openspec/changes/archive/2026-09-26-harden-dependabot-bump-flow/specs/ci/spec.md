# Delta for ci

> **Change** `2026-09-26-harden-dependabot-bump-flow` (Dependabot CI breakage
> #251/#252/#253) · branch `ci/dependabot-bump-hardening` · store **hybrid**
> (this file + Engram mirror).
>
> **One addition, two requirements.** CI-13 makes the multi-home version
> declarations literal-free and consistency-guarded so a *consistent* bump
> needs no test edit and a *partial* bump fails with an actionable message.
> CI-14 configures the Dependabot update policy so the bumps the bot cannot
> complete atomically (the coordinated `ruff` pin, `fastmcp` majors) are not
> attempted, and majors stay individually reviewable.
>
> **Rule-6 resolution.** All six new scenarios map to static guards in
> `tests/test_ci_workflows.py`. The CI-12 S1 guard
> (`test_release_lint_job_runs_the_ci_lint_gates`) is amended to derive the
> setup-uv ref rather than name it, so it now also carries CI-13 S2; the
> scenario names are distinct so both map to exactly one row.

## ADDED Requirements

### Requirement: Literal-free, consistency-guarded version declarations (CI-13)

> Added by change `2026-09-26-harden-dependabot-bump-flow` (Dependabot CI
> breakage #251/#252/#253). Before this change a static guard hardcoded the
> `astral-sh/setup-uv` action ref (GitHub #251), so a consistent Dependabot
> action bump failed eleven test jobs until a human edited the literal; no
> guard asserted that an action ref is identical across workflows; and the
> `.python-version` ↔ gate-job interpreter equality of CI-07 was verify-phase
> only.

Every declaration that decides **which tooling runs** and appears in more than
one home SHALL be guarded by a static test that derives the expected value from
one declaration home and SHALL carry **no version or action-ref literal of its
own**, so a consistent bump or ref move edits declarations only and never a
test. Specifically:

- Every GitHub Action repository referenced under `.github/workflows/` SHALL
  use exactly one ref across all workflow files — the same `owner/repo@ref`
  value wherever that repository appears, in a step-level `uses` or a
  job-level reusable-workflow `uses` (so `github/codeql-action/init` and
  `github/codeql-action/analyze` move together) — so a partial bump fails
  loudly instead of drifting silently.
- The `lint` job of `.github/workflows/release.yml` SHALL use the same
  `astral-sh/setup-uv` ref as the `lint` job of `.github/workflows/ci.yml`, and
  the guard SHALL derive that ref from `ci.yml` rather than naming it.
- `.python-version` SHALL equal the `python-version` pin of the `lint` and
  `coverage` jobs of both `ci.yml` and `release.yml` — the CI-07 invariant,
  promoted from verify-phase evidence to a static guard. The `test` jobs'
  `${{ matrix.python-version }}` expression is excluded by design (it is the
  support matrix, not a gate pin).

These guards SHALL arm no new CI step: they run in the existing test/lint jobs
that already execute `tests/test_ci_workflows.py`. A bump that moves every
occurrence together SHALL leave them green with no test edit.

#### Scenario: Action refs are consistent across workflows

- GIVEN every workflow file under `.github/workflows/` (`.yml` or `.yaml`)
- WHEN `tests/test_ci_workflows.py::test_workflow_action_refs_are_consistent_across_workflows`
  groups every step-level and job-level `uses:` value by its action repository
  (`owner/repo`) and collects the distinct refs
- THEN each action repository SHALL map to exactly one ref, so a ref that moves
  in one workflow but not another fails with the repository and the competing
  refs

#### Scenario: Release setup-uv parity is derived from ci.yml

- GIVEN the `lint` job of `.github/workflows/ci.yml` and of `.github/workflows/release.yml`
- WHEN `tests/test_ci_workflows.py::test_release_lint_job_runs_the_ci_lint_gates`
  locates each job's `astral-sh/setup-uv` step by action name
- THEN the release ref SHALL equal the CI ref, and the guard SHALL hold no
  `setup-uv` version literal, so a consistent bump of both workflows needs no
  test edit (GitHub #251)

#### Scenario: Interpreter pin agrees across homes

- GIVEN `.python-version` and the `lint` and `coverage` jobs of both workflows
- WHEN `tests/test_ci_workflows.py::test_dev_interpreter_pin_matches_gate_jobs`
  reads each setup-uv step's `with.python-version`
- THEN every gate-job pin SHALL equal the `.python-version` value, so the local
  and CI gate interpreters cannot diverge silently

---

### Requirement: Dependabot update policy (CI-14)

> Added by change `2026-09-26-harden-dependabot-bump-flow`. Dependabot opened
> three consecutively red PRs (#251/#252/#253). Two of the three classes are
> bumps the bot cannot complete atomically: the coordinated `ruff` pin
> (#252 — its version is declared in `pyproject.toml` twice, in
> `.pre-commit-config.yaml`, and in `CONTRIBUTING.md`, and the `uv` ecosystem
> can move only the first) and a `fastmcp` major (#253 — a runtime dependency
> whose major changes the MCP SDK API, and whose declared `<4` cap Dependabot
> rewrote to `<5` itself).

`.github/dependabot.yml` SHALL declare an update policy that keeps automated
bumps compatible with the repository's coordinated declarations and its
review granularity:

- The `uv` update SHALL `ignore` the `ruff` dependency entirely, so Dependabot
  opens no `ruff` PR. The version is coordinated across the `pyproject.toml`
  dev pin and `[tool.ruff] required-version`, the
  `astral-sh/ruff-pre-commit` `rev` in `.pre-commit-config.yaml`, and the
  `CONTRIBUTING.md` Code style section, forced to agree by CI-08; the manual
  bump procedure SHALL be documented in `CONTRIBUTING.md`.
- The `uv` update SHALL `ignore` `fastmcp` **major** updates, so a major is
  only adopted by a deliberate, code-adapting change rather than a bot PR that
  widens the declared cap (GitHub #253).
- Every catch-all minor/patch group SHALL declare exactly
  `update-types: ["minor", "patch"]` and SHALL NOT declare `major`, so major
  updates stay out of the routine sweep and arrive individually for explicit
  review.

This requirement SHALL add no workflow step and SHALL NOT weaken any existing
gate: the full test matrix remains the code-level barrier that a major must
pass.

#### Scenario: uv updates ignore the coordinated ruff pin

- GIVEN `.github/dependabot.yml` parsed
- WHEN `tests/test_ci_workflows.py::test_dependabot_ignores_the_coordinated_ruff_pin`
  reads the `uv` update's `ignore` list
- THEN exactly one entry SHALL name `ruff` and SHALL NOT narrow the ignore with
  `update-types`, so Dependabot opens no `ruff` PR at any update type

#### Scenario: uv updates ignore fastmcp majors

- GIVEN `.github/dependabot.yml` parsed
- WHEN `tests/test_ci_workflows.py::test_dependabot_ignores_fastmcp_majors`
  reads the `uv` update's `ignore` list
- THEN exactly one entry SHALL name `fastmcp` and SHALL declare
  `update-types: ["version-update:semver-major"]`, so a major is never adopted
  automatically while minor/patch updates remain enabled

#### Scenario: minor/patch groups exclude majors

- GIVEN `.github/dependabot.yml` parsed
- WHEN `tests/test_ci_workflows.py::test_dependabot_groups_exclude_majors`
  reads every update's `groups`
- THEN every group SHALL declare `update-types` exactly
  `["minor", "patch"]`, so a major cannot be silently absorbed into the routine
  sweep and a group's scope cannot drift from the declared sweep
