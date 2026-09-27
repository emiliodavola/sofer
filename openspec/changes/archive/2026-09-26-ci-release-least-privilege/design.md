# Design: scope release.yml write access to the release job (GitHub #261)

## Technical Approach

Move the release workflow's write permission from the workflow root to the one job
that needs it, and make the workflow-level token explicitly read-only. Pin the
contract with a static guard, add `ci` requirement CI-15, and compose it into the
canonical spec.

## Architecture Decisions

### Decision: workflow-level `contents: read`, job-level `contents: write`

**Choice**:
```yaml
permissions:
  contents: read
...
  release:
    permissions:
      contents: write
```
**Alternatives considered**: omit the workflow-level block and only grant the
`release` job.

**Rationale**: an omitted workflow-level table lets the other jobs inherit the
repository/org default token permissions, which could be broader than read. The
explicit `contents: read` guarantees the least-privilege floor. Only the `release`
job (which calls `softprops/action-gh-release`) overrides it. This mirrors
`codeql.yml`'s explicit workflow-level table.

### Decision: one guard, two scenarios

**Choice**: a single `test_release_workflow_permissions_are_least_privilege`
function asserts both clauses (workflow-level read-only; only the `release` job
writes), and both CI-15 scenarios map to it.

**Rationale**: the guard compares two facets of one contract; splitting it would
duplicate the parse. Multiple Test Mapping rows may name the same test (the repo
already does this for CI-09/CI-13).

## Data Flow

    release.yml workflow-level permissions ──► contents: read
              │
              ├── lint / test / coverage / build / citation-check  (inherit read)
              └── release ──► contents: write  (softprops/action-gh-release)

    guard ──► tests/test_ci_workflows.py::test_release_workflow_permissions_are_least_privilege

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `.github/workflows/release.yml` | Modify | Workflow read-only; `release` job `contents: write` |
| `tests/test_ci_workflows.py` | Modify | CI-15 guard; docstring range CI-01..CI-15 |
| `openspec/specs/ci/spec.md` | Modify | CI-15 added; two Test Mapping rows |
| `openspec/changes/2026-09-26-ci-release-least-privilege/` | Create | SDD artifacts |

## Interfaces / Contracts

```yaml
# release.yml
permissions: { contents: read }          # workflow
jobs.release.permissions: { contents: write }
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|--------------|----------|
| Unit | Workflow-level grants no write; `contents: read` | YAML inspection |
| Unit | Only `release` grants `contents: write` | YAML inspection of every job |
| Contract | Spec↔test mapping bijection | `scripts/check_test_mapping.py` |

## Threat Matrix

N/A — no routing, application shell/subprocess, VCS/PR automation, executable-file
classification, or process-integration boundary changes. The change reduces the
token's authority.

## Migration / Rollout

No migration. The release job keeps the scope it needs; the other jobs become
read-only on the next tag push.

## Open Questions

None.
