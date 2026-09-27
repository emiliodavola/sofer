# Exploration: scope release.yml write access to the release job (GitHub #261)

## Current State

`.github/workflows/release.yml` declares `permissions: contents: write` at the
**workflow** root (lines 16-17). Declaring any permissions block resets every
unlisted scope to `none` (the codeql.yml comment states this), so every job —
`lint`, `test`, `coverage`, `build`, `citation-check`, `release` — runs with
`contents: write`, even though only the `release` job needs it (its
`softprops/action-gh-release@v3` step creates the release).

`codeql.yml` already demonstrates the least-privilege shape: a workflow-level
`permissions` table scoped to what that workflow needs.

## Affected Areas

- `.github/workflows/release.yml` — workflow-level `permissions` and the
  `release` job.
- `tests/test_ci_workflows.py` — a static guard pinning the contract.
- `openspec/specs/ci/spec.md` — a new requirement CI-15 with two scenarios.

## Approaches

1. **Workflow-level `contents: read` + job-level `contents: write` on `release`
   (recommended).** Every job inherits a read-only token; the one job that needs
   write declares it. Explicit, self-documenting, and guard-assertable.
2. **Drop the workflow-level block; only the `release` job declares
   `contents: write`.** Smaller diff, but the other jobs then inherit the
   repository/org default token permissions, which may be broader than read.

## Recommendation

Approach 1. It is the strongest least-privilege posture and matches codeql.yml's
explicit style. The write scope shrinks from "every job" to "the `release` job".

## Risks

- `actions/upload-artifact` in the `coverage` job uses the Actions runtime token,
  not `GITHUB_TOKEN`, so it keeps working under a read-only workflow token
  (the current `contents: write` block already leaves `actions: none`).
- No behaviour change to the release flow; the `release` job keeps
  `contents: write`.

## Ready for Proposal

Yes.
