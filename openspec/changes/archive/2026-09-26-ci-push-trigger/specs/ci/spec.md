# Delta for ci

> **Change** `2026-09-26-ci-push-trigger` (GitHub #262) · branch `ci/262-ci-push-trigger` ·
> store **hybrid** (this file + Engram mirror).
>
> **One addition.** `.github/workflows/ci.yml` triggered only on `pull_request` targeting
> `[main, dev]`, so a direct push to `dev`/`main` — or any non-PR path — ran no
> lint/test/coverage gate. `.github/workflows/codeql.yml` already declares `push` alongside
> `pull_request`; CI-16 brings `ci.yml` to that trigger contract, mirroring CI-04's CodeQL
> trigger requirement. The delta adds CI-16 with two scenarios and two Test Mapping rows.
>
> **Sequencing note.** This requirement is numbered **CI-16** because the sibling release-
> permissions change (#261 / PR #268) adds CI-15 and is intended to land first; on `dev`
> alone the canonical spec's last requirement is CI-14, and this delta appends CI-16.

## ADDED Requirements

### Requirement: CI workflow gates push and pull requests on long-lived branches (CI-16)

> Added by change `2026-09-26-ci-push-trigger` (GitHub #262). Before this change `ci.yml`
> contained no `push` trigger, so a direct push to `dev` or `main` bypassed the
> lint/test/coverage gates the PR pipeline enforces.

`.github/workflows/ci.yml` SHALL trigger on `push` to `main` and `dev` and on `pull_request`
targeting `main` and `dev`, mirroring `.github/workflows/codeql.yml`'s branch list. Every
commit that lands on a long-lived branch SHALL therefore be gated by the `lint`, `test`, and
`coverage` jobs, not only commits that arrive through a pull request. A static guard in
`tests/test_ci_workflows.py` SHALL assert the trigger contract so it cannot silently regress.

#### Scenario: Push trigger targets main and dev

- GIVEN `.github/workflows/ci.yml` parsed
- WHEN its `push` trigger is inspected
- THEN `push.branches` SHALL be `[main, dev]`, so a direct push to either long-lived branch
  is gated

#### Scenario: Pull request trigger still targets main and dev

- GIVEN `.github/workflows/ci.yml` parsed
- WHEN its `pull_request` trigger is inspected
- THEN `pull_request.branches` SHALL be `[main, dev]`
