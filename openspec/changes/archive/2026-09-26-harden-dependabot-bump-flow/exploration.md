# Exploration: Harden the release/dependabot bump flow

## Problem

Three consecutive Dependabot PRs against `main` opened with red CI, each for a
different class of reason. The signal only arrives late (after the bump PR is
open), and the remedy is a manual, easy-to-miss edit against a test literal.

Measured evidence, re-derived from the live PRs and their CI logs:

| PR | Bump | Files | Red jobs | Root cause (log evidence) |
|----|------|-------|----------|---------------------------|
| #251 | `astral-sh/setup-uv` 10.1.0 → 10.2.0 | `ci.yml`, `release.yml` | 11 `test` jobs | `tests/test_ci_workflows.py:934` hardcodes `uses="astral-sh/setup-uv@v10.1.0"`; the workflow moved to `v10.2.0`, so `test_release_lint_job_runs_the_ci_lint_gates` fails (`assert (None is not None)`). |
| #252 | python minor/patch group (7 updates) | `pyproject.toml`, `uv.lock` | `lint` + 11 `test` | Dependabot bumped the dev pin to `ruff==0.16.8`; `[tool.ruff] required-version = "==0.16.7"` still names the old version. Ruff aborts at config load: `Required version '==0.16.7' does not match the running version '0.16.8'` (exit 2). The pre-commit `rev` and `CONTRIBUTING.md` prose also still name `0.16.7`. |
| #253 | `fastmcp` 3.4.7 → 4.0.5 (major) | `pyproject.toml`, `uv.lock` | 11 `test` jobs | Dependabot **widened the declared cap itself** (`fastmcp>=3.4,<4` → `<5`). fastmcp 4 / MCP SDK v2 changed the API: `McpError` → `MCPError` (`ImportError: cannot import name 'McpError'`), `float + datetime.timedelta` in a test helper, and resource-URI resolution changed. |

## Findings that shape the design

1. **#251 is a test-literal problem, not a workflow problem.** `ci.yml` and
   `release.yml` were both bumped consistently; the only thing that broke is a
   static guard that hardcoded the action ref instead of deriving it. Removing
   the literal means a future bump needs **no test edit**.
2. **#252's multi-home drift is already mostly guarded** — CI-08 derives the
   ruff version from the dev pin and asserts `required-version`, the
   pre-commit `rev`, and `CONTRIBUTING.md` agree. The failure is that
   `required-version` makes ruff abort at config load *before* any guard runs,
   and Dependabot can only edit the `uv` ecosystem (it cannot move the
   pre-commit `rev` or the prose). A coordination the bot cannot perform is a
   coordination the bot should not attempt.
3. **#253 shows the `<4` cap is not a barrier.** Dependabot's `uv` ecosystem
   rewrote the upper bound to admit the major. The only effective barrier at
   the config level is `ignore`; the code-level barrier is the test suite,
   which is exactly what went red.
4. **Every GitHub Action ref is a multi-home declaration** (`actions/checkout`,
   `astral-sh/setup-uv`, `actions/upload-artifact`,
   `github/codeql-action/{init,analyze}`, `softprops/action-gh-release`). No
   guard currently asserts they agree across `ci.yml`, `release.yml`, and
   `codeql.yml`; a partial bump would drift silently.
5. **`.python-version` + the four gate-job pins** are another multi-home value
   (`.python-version`, `ci.yml`/`release.yml` `lint` and `coverage` jobs,
   `[tool.pyright] pythonVersion`). Today only the pyright half is a static
   guard; CI-07's job-pin equality is verify-phase-only.

## Candidate measures (from the request) and disposition

| # | Candidate | Disposition |
|---|-----------|-------------|
| 1 | Guards accompany the bump or fail actionably | **Implement.** The setup-uv guard derives its ref from `ci.yml` (no literal); a new action-ref consistency guard fails the first drift with an actionable message. The ruff guards already exist (CI-08) and are not duplicated. |
| 2 | One pin-consistency check across all multi-home versions | **Implement, generalized into static guards** rather than a new script. The existing CI-run guard home is `tests/test_ci_workflows.py`; a second script would duplicate collection/coverage/type infrastructure without detecting anything new. Add: action-ref consistency across workflows, and `.python-version` == every gate-job interpreter pin. |
| 3 | `dependabot.yml` rule for majors / `ignore` | **Implement the enforceable half.** `ignore` `ruff` (a coordinated multi-home pin Dependabot cannot move atomically) and `ignore` `fastmcp` majors (adaptation required; Dependabot otherwise rewrites the cap). Keep majors out of the minor/patch groups and pin that with a guard. **Reject** a bundled "majors group": grouping would collapse independent majors into one PR and does not enforce review — branch protection does that, and the group adds no gate. |
| 4 | Document the manual bump procedure | **Implement.** A `CONTRIBUTING.md` "Dependency updates" section plus an `AGENTS.md` rule-8 pointer. |

## Constraints

- Do not redesign versioning (hatch-vcs + tag) or touch the published release
  flow / `v0.4.0`.
- No new runtime code: this is a CI-policy change, so no `src/sofer/` edit and
  no coverage impact on the four core modules.
- Every new spec scenario must map to a collected test (AGENTS.md rule 6).
