---
name: Release
about: Track cutting a tagged release (preparation PR, preflight, tag, verification)
title: "chore(release): v"
labels: ["type:chore"]
assignees: []
---

## Version

`X.Y.Z` — semver; pre-1.0 minor bumps may carry breaking changes (AGENTS.md rule 12).

## Why this bump

<!-- What changed since the previous tag: git log --oneline vPREV..main -->
<!-- A `feat` moves the minor; fixes only move the patch; breaking changes are documented in the notes. -->

## Procedure

1. Prepare `CITATION.cff` on a short-lived branch from updated `main`:
   `uv run --python 3.13 python scripts/update_citation.py --version X.Y.Z`
2. Merge the preparation PR. Record the merged `main` commit as `RELEASE_SHA` — after a squash or
   rebase merge that is the merged commit, never the preparation branch head.
3. Run the preflight on that exact commit. It is read-only and fails closed: no tag command is printed
   unless every check passes.

```bash
git fetch origin --prune --tags
uv run --python 3.13 python scripts/release_preflight.py --version X.Y.Z --sha <RELEASE_SHA>
```

4. Only with explicit release authorization, run the two commands the preflight prints (annotated tag
   on `RELEASE_SHA`, then a single-tag push with `--no-follow-tags`).
5. Track the `release.yml` run for that exact tag/SHA — not an arbitrary latest run.

## Checklist

- [ ] `CITATION.cff` prepared in a PR and merged
- [ ] `RELEASE_SHA` recorded (the merged `main` commit)
- [ ] Preflight passed on that exact SHA
- [ ] Tag created on `RELEASE_SHA` and pushed alone, with release authorization
- [ ] `release.yml` green for that tag/SHA: lint, full test matrix, coverage, wheel validation, citation check
- [ ] GitHub Release generated with notes since the previous tag
- [ ] No published tag moved or deleted; a failed release is repaired with a new patch version
