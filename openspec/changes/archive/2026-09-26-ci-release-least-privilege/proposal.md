# Proposal: scope release.yml write access to the release job (GitHub #261)

**Change:** `2026-09-26-ci-release-least-privilege` · **Issue:** #261
`ci(release)` · **Branch:** `ci/261-release-permissions` (base `dev`, PR-only)

## Intent

`.github/workflows/release.yml` grants `contents: write` at the workflow root, so
every job (`lint`, `test`, `coverage`, `build`, `citation-check`) runs with write
access even though only the `release` job needs it. Move the write scope to that
job and make the workflow-level token read-only.

## Scope

### In Scope

- `.github/workflows/release.yml`: workflow-level `permissions: contents: read`;
  the `release` job declares `permissions: contents: write`.
- `tests/test_ci_workflows.py`: `test_release_workflow_permissions_are_least_privilege`
  pinning the contract; module docstring range CI-01..CI-15.
- Specs: a new `ci` requirement CI-15 with two scenarios and two Test Mapping rows.

### Out of Scope

- CodeQL's workflow-level permission table (CI-04 owns it).
- `ci.yml` permissions (issue #262 covers its trigger contract).
- Any change to the release flow, jobs, `needs` graph, or gate commands.

## Capabilities

### Modified Capabilities

- `ci`: CI-15 ("Least-privilege permissions in the release workflow") is added.

## Approach

Keep the `release` job's behaviour identical by granting it the exact scope it
needs; make every other job read-only by construction. Add the guard, compose the
delta into the canonical `ci` spec, and append its two Test Mapping rows.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `.github/workflows/release.yml` | Modified | Workflow-level read-only; `release` job write |
| `tests/test_ci_workflows.py` | Modified | CI-15 guard; docstring range |
| `openspec/specs/ci/spec.md` | Modified | CI-15 added; two rows appended |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| A non-release job silently needs write | Low | Guard fails if any job grants write; release flow unchanged |
| Test-mapping bijection breaks | Low | Two CI-15 rows added with the requirement; checker run |
| Workflow text guards trip | Low | No floor/version/badge/XML token added |

## Rollback Plan

Revert the three-file diff and re-run the suite. No state is touched.

## Dependencies

None.

## Success Criteria

- [ ] Workflow-level permissions grant no write; `contents: read`.
- [ ] Only the `release` job declares `contents: write`.
- [ ] `uv run pytest tests/ -q` green; ruff/mypy/pyright clean; checker exit 0.
