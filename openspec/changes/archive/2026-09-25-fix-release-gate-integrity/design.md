# Design: Release gate integrity (CI-03/CI-10 contradiction + #233 lint parity)

## Technical Approach

Two coupled edits that restore truth to the `ci` specification and to the release workflow:

1. **Spec truth.** Amend CI-10 so it stops claiming the COV-06 gate is pending under issue #185,
   and delete the scenario that pinned that false claim. Add CI-12 for the release `lint` job.
2. **Workflow truth.** Add the three missing gates to `release.yml`'s `lint` job, mirroring
   `ci.yml` exactly, and correct the header comment.

The canonical spec is updated with `gentle-ai sdd-archive-compose` (requirement blocks) plus a
direct edit of the `## Test Mapping` table (the compose tool merges requirements only).

## Architecture Decisions

### Decision: Amend CI-10 and add CI-12 instead of broadening CI-10

**Choice**: Keep CI-10 scoped to the release `test` job (drop the stale #185 statements and S3);
introduce CI-12 for the release `lint` job.
**Alternatives considered**: Rename CI-10 to "Release job parity with CI" and fold lint parity in.
**Rationale**: CI-10's name says "test job"; folding lint into it would make the name false and
require a RENAMED heading plus a full replacement. A new CI-12 keeps one requirement per release
job and mirrors how CI-11 was added for the format gate.

### Decision: Mirror `ci.yml` invocations verbatim

**Choice**: The three new steps use exactly `uv run ruff format --check src/ tests/`, `uv run
pyright`, and `uv run python scripts/check_test_mapping.py` — the same strings and order as
`ci.yml`.
**Alternatives considered**: Parameterize with a shared reusable workflow.
**Rationale**: The repository already duplicates the coverage job shape across both workflows and
pins it with tests; a reusable workflow is a larger structural change out of scope here. Verbatim
mirroring lets a single guard compare the two ordered step lists.

### Decision: Archive via compose + direct Test Mapping edit

**Choice**: `gentle-ai sdd-archive-compose` replaces CI-10 and appends CI-12; the Test Mapping
table is edited directly in the canonical file.
**Alternatives considered**: Model-driven merge of the whole canonical spec.
**Rationale**: The mechanical compose contract forbids model-driven requirement merges; the
compose tool does not merge the Test Mapping table, so that table is a bounded, reviewable edit.

## Data Flow

    ci.yml lint job ──(gate command list)──┐
                                           ├── compared by test_release_lint_job_mirrors_ci_lint_invocations
    release.yml lint job ──(same list)─────┘

    spec delta ──compose──→ canonical ci spec ──check_test_mapping.py──→ bijection check
                   └──(Test Mapping rows edited directly)──┘

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `.github/workflows/release.yml` | Modify | Header comment corrected; `lint` job gains format, pyright, test-mapping steps |
| `tests/test_ci_workflows.py` | Modify | CI-10 guard drops the #185 assertion; three CI-12 guards added; docstring range |
| `openspec/specs/ci/spec.md` | Modify | CI-10 amended, CI-12 added via compose; Test Mapping row removed/added |
| `openspec/changes/fix-release-gate-integrity/` | Create | SDD artifacts (explore, proposal, specs, design, tasks, apply-progress, verify-report) |

## Interfaces / Contracts

The `lint` job's gate invocation contract, shared by both workflows:

```
uv run ruff check src/ tests/ scripts/
uv run ruff format --check src/ tests/
uv run mypy src/ scripts/
uv run pyright
uv run python scripts/check_test_mapping.py
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Release `lint` steps present and exact | `test_release_lint_job_runs_the_ci_lint_gates` (YAML inspection) |
| Unit | Both `lint` jobs carry the same ordered gates | `test_release_lint_job_mirrors_ci_lint_invocations` (YAML inspection) |
| Unit | Header states lint parity, no stale #185 claim | `test_release_header_states_lint_parity_without_the_stale_cov06_claim` (text scan) |
| Unit | CI-10 guard no longer asserts #185 | `test_release_test_job_mirrors_ci_os_axis_and_cli_smoke` (updated) |
| Contract | Spec↔test mapping bijection | `uv run python scripts/check_test_mapping.py` |
| Runtime | The added commands are already green on the tree | `uv run ruff format --check src/ tests/`, `uv run pyright`, `uv run python scripts/check_test_mapping.py` (verify-phase evidence) |

## Threat Matrix

N/A — no routing, application shell/subprocess, VCS/PR automation, executable-file
classification, or process-integration boundary changes. The change adds GitHub Actions steps
that invoke the same commands the CI `lint` job already runs; no new runtime code path is
introduced.

## Migration / Rollout

No migration required. The change takes effect for future tag pushes.

## Open Questions

None.
