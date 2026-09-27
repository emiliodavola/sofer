# Exploration: add a push trigger to ci.yml (GitHub #262)

## Current State

`.github/workflows/ci.yml` triggers only on `pull_request` targeting
`[main, dev]`:

```yaml
on:
  pull_request:
    branches: [main, dev]
```

There is no `push` trigger. A direct push to `dev` or `main` — or any path that
does not open a PR — runs no lint/test/coverage gate. `.github/workflows/codeql.yml`
already declares:

```yaml
on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main, dev]
  schedule:
    - cron: "0 3 * * 1"
```

`release.yml` re-runs the gates on a `v*` tag, so a released tag is verified; the
gap is the in-between state on `dev`/`main`, where an unverified commit can sit.

## Affected Areas

- `.github/workflows/ci.yml` — the `on:` trigger map.
- `tests/test_ci_workflows.py` — a static guard pinning the trigger contract.
- `openspec/specs/ci/spec.md` — a new requirement CI-16 with two scenarios.

## Approaches

1. **Add `push` mirroring `codeql.yml` (recommended).** `push` and `pull_request`
   both target `[main, dev]`. Every landed commit on a long-lived branch is
   gated, and the trigger set matches the one CI-04 already pins for CodeQL.
2. **Document + branch protection only.** Rejected by the issue's own wording:
   it leaves the guarantee outside the repository and un-guardable.

## Recommendation

Approach 1. It closes the bypass window with one workflow edit, mirrors an
existing, spec-owned trigger contract, and is assertable by a static guard.

## Risks

- Duplicate gate runs on PR branches: a branch push and its PR both trigger CI.
  This is the same behaviour `codeql.yml` already has; the extra run is cheap and
  the branch-blessed state is the point.
- `ci.yml`'s jobs are unchanged, so coverage/type/format gates are unaffected.

## Ready for Proposal

Yes.
