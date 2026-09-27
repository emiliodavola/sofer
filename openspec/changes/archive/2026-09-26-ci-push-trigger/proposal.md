# Proposal: add a push trigger to ci.yml (GitHub #262)

**Change:** `2026-09-26-ci-push-trigger` · **Issue:** #262 `ci` ·
**Branch:** `ci/262-ci-push-trigger` (base `dev`, PR-only)

## Intent

`.github/workflows/ci.yml` triggers only on `pull_request`, so a direct push to
`dev` or `main` runs no lint/test/coverage gate. Add a `push` trigger for the two
long-lived branches, mirroring `codeql.yml`, so every landed commit is gated, and
pin the trigger contract with a static guard.

## Scope

### In Scope

- `.github/workflows/ci.yml`: add `push: branches: [main, dev]` alongside the
  existing `pull_request` trigger.
- `tests/test_ci_workflows.py`: `test_ci_has_push_and_pr_triggers_targeting_main_and_dev`;
  module docstring range CI-01..CI-16.
- Specs: a new `ci` requirement CI-16 with two scenarios and two Test Mapping rows.

### Out of Scope

- Branch protection settings (out-of-repo configuration).
- `release.yml`'s tag trigger (unchanged).
- Any change to the `lint`/`test`/`coverage` jobs or their steps.

## Capabilities

### Modified Capabilities

- `ci`: CI-16 ("CI workflow gates push and pull requests on long-lived branches")
  is added.

## Approach

Add the `push` block, mirroring `codeql.yml`'s branch list exactly. Add the guard,
compose the delta into the canonical `ci` spec, and append its two Test Mapping
rows. The requirement is numbered CI-16 because the sibling release-permissions
change (#261 / PR #268) adds CI-15 and lands first.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `.github/workflows/ci.yml` | Modified | `push` trigger added; jobs unchanged |
| `tests/test_ci_workflows.py` | Modified | CI-16 guard; docstring range |
| `openspec/specs/ci/spec.md` | Modified | CI-16 added; two rows appended |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Trigger drift (`dev`/`main` diverges from codeql.yml) | Low | Guard asserts both lists; mirrors CI-04's contract |
| Test-mapping bijection breaks | Low | Two CI-16 rows added with the requirement; checker run |
| Duplicate runs on PR branches | Medium | Same as codeql.yml; accepted (the branch state is the point) |

## Rollback Plan

Revert the three-file diff. No state is touched.

## Dependencies

None. Sequencing: intended to land after PR #268 (CI-15).

## Success Criteria

- [ ] `ci.yml` triggers on push and pull_request targeting `[main, dev]`.
- [ ] `uv run pytest tests/ -q` green; ruff/mypy/pyright clean; checker exit 0.
