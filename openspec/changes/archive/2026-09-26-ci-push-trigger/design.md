# Design: add a push trigger to ci.yml (GitHub #262)

## Technical Approach

Add a `push` trigger to `.github/workflows/ci.yml` for `[main, dev]`, mirroring
`.github/workflows/codeql.yml`. Jobs and steps are untouched. Pin the contract
with a static guard; add CI-16 to the canonical `ci` spec.

## Architecture Decisions

### Decision: mirror codeql.yml's branch list exactly

**Choice**:
```yaml
on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main, dev]
```
**Alternatives considered**: a reusable workflow or a branch-protection-only fix.

**Rationale**: CI-04 already owns CodeQL's `push`/`pull_request` branch contract;
using the same list keeps the two workflows consistent and lets the guard assert a
single known shape. Branch protection is repository configuration, outside the
tree, so it cannot be guard-tested in-repo.

### Decision: number the requirement CI-16

**Choice**: the new `ci` requirement is CI-16, not CI-15.

**Rationale**: the sibling release-permissions change (#261 / PR #268) adds CI-15
and is intended to land first. Numbering CI-16 keeps the two deltas from colliding;
on `dev` alone this delta appends CI-16 after CI-14, and after PR #268 merges the
sequence is contiguous. The delta's header records the sequencing.

### Decision: one guard, two scenarios

**Choice**: `test_ci_has_push_and_pr_triggers_targeting_main_and_dev` asserts both
the `push` and `pull_request` branch lists; both CI-16 scenarios map to it.

**Rationale**: one parse, one contract; multiple mapping rows may name the same
test (CI-09/CI-13 precedent).

## Data Flow

    push to dev|main ──► ci.yml: lint + test + coverage   (new)
    PR to dev|main ─────► ci.yml: lint + test + coverage   (existing)

    guard ──► tests/test_ci_workflows.py::test_ci_has_push_and_pr_triggers_targeting_main_and_dev

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `.github/workflows/ci.yml` | Modify | `push` trigger added; jobs unchanged |
| `tests/test_ci_workflows.py` | Modify | CI-16 guard; docstring range CI-01..CI-16 |
| `openspec/specs/ci/spec.md` | Modify | CI-16 added; two Test Mapping rows |
| `openspec/changes/2026-09-26-ci-push-trigger/` | Create | SDD artifacts |

## Interfaces / Contracts

```yaml
# ci.yml
on:
  push:        { branches: [main, dev] }
  pull_request:{ branches: [main, dev] }
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|--------------|----------|
| Unit | `push.branches == [main, dev]` | YAML inspection |
| Unit | `pull_request.branches == [main, dev]` | YAML inspection |
| Contract | Spec↔test mapping bijection | `scripts/check_test_mapping.py` |

## Threat Matrix

N/A — no routing, application shell/subprocess, VCS/PR automation, executable-file
classification, or process-integration boundary changes. The change only adds a
trigger; it introduces no new code path.

## Migration / Rollout

No migration. The trigger takes effect on the next push to `dev`/`main`.

## Open Questions

None.
