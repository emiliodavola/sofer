# Archive report: 2026-09-25-csv-dialect-override

**Archived to:** `openspec/changes/archive/2026-09-25-csv-dialect-override/`
**Issue:** #204 · **Branch:** `feat/204-csv-dialect-override` (base `dev@e9d5101`)

## Preserved artifacts

```
proposal.md          intent, scope (in/out), approach, risks, success criteria
explore.md           the CSV-reading surface survey; why `scan` is inert
design.md            D1–D8 decisions (None sentinel, tiers, .tsv, echo, schema)
tasks.md             all phases checked, with verification evidence
apply-progress.md    what changed, per file, and the apply-time decisions
verify-report.md     test/quality/coverage output + independent verification
sync-report.md       canonical spec sync (CB-R12/PRF-07/CLI-R12/MSP-R18)
specs/
  codebook/spec.md   ADDED CB-R12
  profile/spec.md    ADDED PRF-07
  cli/spec.md        ADDED CLI-R12
  mcp-server/spec.md ADDED MSP-R18
```

## State at archive

- Canonical specs synced; `check_test_mapping.py` green.
- Full suite: **1913 passed, 2 skipped**; core coverage 4×100%; profile floor 96%;
  TOTAL 93%; ruff/mypy/pyright green.
- Independent adversarial review: 12/12 claims PASS, 0 falsified.
- No destructive delta: four ADDED requirements only; no existing requirement
  rewritten and no default removed.

## Follow-up

Open the PR against `dev` (assigned `emiliodavola`, `Refs #204`); the issue stays
open until the maintainer merges.
