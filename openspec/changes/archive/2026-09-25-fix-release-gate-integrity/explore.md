# Exploration: Release gate integrity (CI-03/CI-10 contradiction + #233 lint parity)

## Current State

The `ci` specification carries two requirements about the release workflow's parity with CI:

- **CI-03** ("Release gated on the coverage job") is shipped: `.github/workflows/release.yml`'s
  `coverage` job runs `bash scripts/check_core_coverage.sh` (`release.yml:89-93`), GitHub #185 is
  closed, and the CI-03 scenario "Release coverage job runs the core 100% gates" is green.
- **CI-10** ("Release test job parity with CI") was added by change
  `2026-09-24-fix-release-test-parity` (GitHub #209). Its note still says the COV-06 core-coverage
  gate "is deliberately separate and tracked as issue #185", and its third scenario
  ("COV-06 stays cross-referenced as issue #185") requires the release header comment to name
  issue #185 as the change that *adds* that gate.

Both statements are false on the current tree: #185 is closed and the gate is present. CI-10
therefore contradicts shipped CI-03, and it pins a false header claim via
`tests/test_ci_workflows.py::test_release_test_job_mirrors_ci_os_axis_and_cli_smoke`, which
asserts `"185" in header` (`tests/test_ci_workflows.py:879-883`).

Independently, the release `lint` job is narrower than the CI `lint` job:

| ci.yml lint step | release.yml lint job |
|---|---|
| `uv run ruff check src/ tests/ scripts/` | present (`release.yml:31-32`) |
| `uv run ruff format --check src/ tests/` | **missing** |
| `uv run mypy src/ scripts/` | present (`release.yml:34-35`) |
| `uv run pyright` | **missing** |
| `uv run python scripts/check_test_mapping.py` | **missing** |

So a formatting regression, a pyright error, or a broken spec↔test mapping cannot block a tag even
though each blocks a PR (GitHub #233).

## Affected Areas

- `openspec/specs/ci/spec.md` — CI-10 note + scenario S3 + its Test Mapping row; new CI-12
  requirement and rows (lines ~522-551, ~592-640).
- `.github/workflows/release.yml` — header comment (lines 3-8) and `lint` job (lines 18-35).
- `tests/test_ci_workflows.py` — `test_release_test_job_mirrors_ci_os_axis_and_cli_smoke`
  (~842-883) drops the #185 header assertion; new CI-12 guards; module docstring range.

## Approaches

1. **Minimal CI-10 modification + new CI-12 requirement (recommended)** — CI-10 stays scoped to
   the test job and loses its stale #185 claim/scenario; a new CI-12 owns lint parity. Pros:
   requirement names stay honest, the delta is additive except for one requirement replacement,
   each scenario maps to one guard. Cons: one requirement replacement (compose handles it).
2. **Broaden CI-10 into "Release job parity with CI"** — rename it and fold lint parity in. Pros:
   one requirement. Cons: a RENAMED heading plus a full replacement, and CI-10's name (test job)
   would no longer describe its content.

## Recommendation

Approach 1. Keep CI-10 about the test job; remove only its two stale statements (note sentence +
S3 + the S3 Test Mapping row) and add CI-12 for the lint job with three scenarios. Update the
release header to state both parities accurately, and re-point the guard.

## Risks

- The test-mapping gate requires an exact scenario↔row bijection; removing S3 and adding CI-12
  scenarios must adjust the table in the same change.
- Existing guards that read release.yml text (`test_coverage_job_gates_core_modules_at_100`,
  `test_coverage_gate_is_config_driven_without_cli_floor`,
  `test_workflows_do_not_declare_a_ruff_version`,
  `test_no_xml_codecov_or_badge_references_in_workflows`) must stay green — the new steps add no
  floor literal, version literal, badge, or XML marker.
- The literal token `185` currently asserted in the header must be removed from the guard, or the
  guard will fail on the corrected header.

## Ready for Proposal

Yes.
