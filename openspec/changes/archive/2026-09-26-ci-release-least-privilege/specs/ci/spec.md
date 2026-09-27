# Delta for ci

> **Change** `2026-09-26-ci-release-least-privilege` (GitHub #261) · branch
> `ci/261-release-permissions` · store **hybrid** (this file + Engram mirror).
>
> **One addition.** `.github/workflows/release.yml` declared `permissions: contents: write` at the
> workflow root, granting every job write access to the repository. Only the `release` job needs it
> (`softprops/action-gh-release`). GitHub #261 scopes the permission to that job and makes the
> workflow-level token read-only. CI-04 already owns CodeQL's workflow-level permission shape; CI-15
> adds the release-workflow least-privilege contract, with two scenarios and two Test Mapping rows.

## ADDED Requirements

### Requirement: Least-privilege permissions in the release workflow (CI-15)

> Added by change `2026-09-26-ci-release-least-privilege` (GitHub #261). The release workflow
> declared `permissions: contents: write` at the **workflow** root, so every job — `lint`, `test`,
> `coverage`, `build`, `citation-check` — ran with write access to the repository even though only
> the `release` job needs it.

`.github/workflows/release.yml` SHALL scope write access to the job that needs it: the workflow-level
`permissions` table SHALL NOT grant any `write` scope and SHALL be the read-only `contents: read`, so
every gate/build job runs least-privilege. Only the `release` job — the one calling
`softprops/action-gh-release` — SHALL declare `contents: write`, and SHALL NOT grant any other write
scope. Every other job SHALL NOT declare a `write` grant. A static guard in
`tests/test_ci_workflows.py` SHALL assert this contract, mirroring the per-workflow permission checks
CI-04 uses.

#### Scenario: Workflow-level permissions grant no write access

- GIVEN `.github/workflows/release.yml` parsed
- WHEN its workflow-level `permissions` table is inspected
- THEN no scope SHALL be `write`
- AND `contents` SHALL be `read`, so `lint`, `test`, `coverage`, `build`, and `citation-check`
  all run read-only

#### Scenario: Only the release job declares contents write

- GIVEN `.github/workflows/release.yml`
- WHEN every job's `permissions` table is inspected
- THEN the `release` job SHALL declare `contents: write` (the scope `softprops/action-gh-release`
  needs) and no other write scope
- AND no other job SHALL declare any `write` grant
