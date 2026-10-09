# Delta for ci

> **Change** `2026-10-09-fix-dependabot-multi-home-pins` (GitHub **#275**) · branch
> `ci/275-dependabot-multi-home-pins` · store **hybrid** (this file + Engram mirror).
>
> **One modification, no new requirement.** CI-14 gains a third ignored dependency class — the
> `mypy`/`pyright` analyzer pins — which is the same class as the coordinated `ruff` pin already
> handled by CI-14 S1: an exact version declared in three text homes, of which Dependabot's `uv`
> ecosystem can move only the first. PR #271 (open, red since 2026-10-05) is the measured instance:
> `mypy 2.3.1 → 2.4.0` was grouped with three single-home bumps, and the group's one poisoned member
> withheld all four.
>
> **Rule-6 resolution.** The one new scenario maps to one new static guard,
> `tests/test_ci_workflows.py::test_dependabot_ignores_the_coordinated_analyzer_pins`, in the row
> appended to the `## Test Mapping` table. The guard carries no version literal, deriving nothing
> from a declaration it does not read (CI-08 S1/S3 discipline).
>
> **Not weakened.** `test_openspec_context_declares_the_enforced_tool_versions` (issue #258) and its
> helpers are byte-identical after this change: it removes a bump the bot cannot complete, never the
> check that catches the drift when a human moves one home and not the others.

## MODIFIED Requirements

### Requirement: Dependabot update policy (CI-14)

> Added by change `2026-09-26-harden-dependabot-bump-flow`. Dependabot opened
> three consecutively red PRs (#251/#252/#253). Two of the three classes are
> bumps the bot cannot complete atomically: the coordinated `ruff` pin
> (#252 — its version is declared in `pyproject.toml` twice, in
> `.pre-commit-config.yaml`, and in `CONTRIBUTING.md`, and the `uv` ecosystem
> can move only the first) and a `fastmcp` major (#253 — a runtime dependency
> whose major changes the MCP SDK API, and whose declared `<4` cap Dependabot
> rewrote to `<5` itself).
>
> Extended by change `2026-10-09-fix-dependabot-multi-home-pins` (GitHub #275):
> the `mypy` and `pyright` analyzer pins are the same class as the coordinated
> `ruff` pin — three text homes, of which the `uv` ecosystem can move only the
> first — so they are ignored too.

`.github/dependabot.yml` SHALL declare an update policy that keeps automated
bumps compatible with the repository's coordinated declarations and its
review granularity:

- The `uv` update SHALL `ignore` the `ruff` dependency entirely, so Dependabot
  opens no `ruff` PR. The version is coordinated across the `pyproject.toml`
  dev pin and `[tool.ruff] required-version`, the
  `astral-sh/ruff-pre-commit` `rev` in `.pre-commit-config.yaml`, and the
  `CONTRIBUTING.md` Code style section, forced to agree by CI-08; the manual
  bump procedure SHALL be documented in `CONTRIBUTING.md`.
- The `uv` update SHALL `ignore` `mypy` and `pyright` entirely, so Dependabot
  opens no analyzer PR. Each exact version is declared in the `pyproject.toml`
  dev pin and named in `openspec/project.md` and `openspec/config.yaml`, forced
  to agree by the tool-version guard; the `uv` ecosystem can move only the first
  (GitHub #275). The manual bump procedure SHALL be documented in
  `CONTRIBUTING.md`.
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

#### Scenario: uv updates ignore the coordinated analyzer pins

- GIVEN `.github/dependabot.yml` parsed
- WHEN `tests/test_ci_workflows.py::test_dependabot_ignores_the_coordinated_analyzer_pins`
  reads the `uv` update's `ignore` list
- THEN exactly one entry SHALL name `mypy` and exactly one SHALL name `pyright`,
  and neither SHALL narrow the ignore with `update-types`, so Dependabot opens
  no analyzer PR at any update type

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

---

## Test Mapping row appended by this change

| Req | Scenario | Verification |
| --- | -------- | ------------ |
| CI-14 | uv updates ignore the coordinated analyzer pins | test:tests/test_ci_workflows.py — `test_dependabot_ignores_the_coordinated_analyzer_pins`: YAML inspection of the `uv` update's `ignore` list |

## Non-goals recorded by this change

No version bump (`pyproject.toml`, `uv.lock`, `openspec/project.md` and `openspec/config.yaml` are
untouched); no amendment or weakening of the #258 tool-version guard; no new `ci` requirement; no
change to the `ruff` or `fastmcp` ignore entries; no workflow, `release.yml`, CI-matrix or
coverage-floor change; no README change; no `src/` change; no commit/push/PR from SDD phases.
