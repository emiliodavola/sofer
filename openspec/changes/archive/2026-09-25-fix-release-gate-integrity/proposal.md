# Proposal: Release gate integrity — fix the CI-03/CI-10 contradiction and complete release lint-job parity

## Intent

The release workflow's own header claims it "Runs the same quality gates as CI first", but two
things are untrue on the current tree:

1. The `ci` spec's CI-10 still claims the COV-06 coverage gate is "deliberately separate and
   tracked as issue #185", and its third scenario requires the release header to cross-reference
   that pending issue. GitHub #185 is closed and `release.yml` already runs the gate (shipped as
   CI-03), so CI-10 contradicts shipped CI-03 and pins a false comment.
2. The release `lint` job omits the `ruff format --check`, `uv run pyright`, and
   `scripts/check_test_mapping.py` steps that the CI `lint` job runs, so a formatting regression,
   a pyright error, or a broken spec↔test mapping cannot block a tag (GitHub #233).

## Scope

### In Scope

- Remove the stale #185 statements from CI-10 (note sentence, scenario S3, and its Test Mapping
  row) so the requirement agrees with shipped CI-03.
- Add CI-12: the release `lint` job runs the same gates as the CI `lint` job, with scenarios and
  Test Mapping rows.
- Add the three missing steps to `release.yml`'s `lint` job, mirroring `ci.yml` exactly.
- Correct the `release.yml` header comment to state both parities and the shipped COV-06 gate.
- Update `tests/test_ci_workflows.py`: drop the stale #185 assertion and pin the new lint steps
  and the corrected header.

### Out of Scope

- The release `test` job parity (CI-10's surviving scenarios) — already shipped by #209.
- The COV-06 gate itself and the `release.yml` `needs` graph — already shipped by #185 / CI-03.
- Any change to `ci.yml`, the coverage floor, the ruff/type-gate configuration, or CodeQL.
- Issues #212 (documented command scope) and #191 (CITATION.cff on `dev`); each gets its own
  change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ci`: CI-10 is amended to drop the stale #185 claim; a new requirement CI-12 is added for
  release lint-job parity.

## Approach

Keep CI-10 scoped to the release `test` job and delete only its two false statements. Introduce
CI-12 for the release `lint` job, whose scenarios assert the presence and exact shape of the three
added steps and the corrected header. Implement the workflow edit and the guards; archive-compose
the delta into `openspec/specs/ci/spec.md` (replacing CI-10 in full, appending CI-12 and its rows).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `openspec/specs/ci/spec.md` | Modified | CI-10 loses the #185 note + S3 + row; CI-12 added with scenarios and rows |
| `.github/workflows/release.yml` | Modified | `lint` job gains format, pyright, and test-mapping steps; header comment corrected |
| `tests/test_ci_workflows.py` | Modified | CI-10 guard drops the #185 assertion; new CI-12 guards; docstring range |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Test-mapping bijection breaks when S3 is removed / CI-12 added | Medium | Update the canonical Test Mapping in the same archive composition; run the checker |
| New steps trip existing workflow-text guards | Low | Steps mirror `ci.yml` exactly; no floor/version/badge/XML tokens added |
| Duplicate-step drift between `ci.yml` and `release.yml` | Low | A guard compares the ordered gate invocations of both `lint` jobs |

## Rollback Plan

Revert the three-file diff and re-run the suite: `git revert` the commit, or restore
`release.yml`, `tests/test_ci_workflows.py`, and `openspec/specs/ci/spec.md` from the merge base.
No data, dependency, or release state is touched.

## Dependencies

None.

## Success Criteria

- [ ] `release.yml`'s `lint` job runs the five CI lint-gate invocations in CI order.
- [ ] CI-10 no longer mentions the COV-06 gate as pending/separate; CI-12 exists with rows.
- [ ] `uv run python scripts/check_test_mapping.py` exits 0.
- [ ] `uv run pytest tests/ -q` green; `ruff check`, `ruff format --check`, `mypy`, `pyright` clean.
