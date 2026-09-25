# Proposal: Align documented gate-command scope and sync CITATION.cff on `dev` (#212, #191)

## Intent

Two documentation/process defects make the repository's own guidance false:

1. **#212** — every developer-facing gate command is documented with a narrower path than CI and
   the pre-commit hook enforce. A contributor (or an agent) who follows `AGENTS.md`,
   `CONTRIBUTING.md`, and the PR template exactly can be fully green locally and still fail CI.
2. **#191** — `CITATION.cff` on `dev` declares `0.2.2` while the latest tag is `v0.3.12`, because
   the release-time bump has always been committed directly on `main`. AGENTS.md rule 12's
   branch-flow rule says `main` receives changes only via merges from `dev`; the CFF bump is the
   one artifact that never obeyed it.

The maintainer recorded option (a) for #191: move the CFF bump onto `dev` before the merge, so the
merge carries it to `main`.

## Scope

### In Scope

- Align the four tracked command sites in `AGENTS.md`, `CONTRIBUTING.md`, and
  `.github/PULL_REQUEST_TEMPLATE.md` to the CI-enforced scope (`src/ tests/ scripts/` for
  `ruff check`; `src/ scripts/` for `mypy`; pyright stays bare).
- Reorder AGENTS.md rule 12 "Cutting a release" so the `CITATION.cff` sync is a `dev` commit made
  before the merge to `main`; add the branch-flow sentence recording it.
- Sync `dev`'s `CITATION.cff` to `v0.3.12` / `2026-09-13` using `scripts/update_citation.py`
  (the only writer of the field).

### Out of Scope

- `openspec/config.yaml` and `openspec/project.md` command/tally staleness (issues #184, #236 —
  the docs sweep).
- Any change to CI workflows, `pyproject.toml`, or `scripts/`.
- #233 (release lint parity), handled by its own change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None.

The change edits documentation and release process prose only. It does not alter any spec-governed
behavior: CI-06's asserted facts (the 90% floor, the coverage commands, the PR-template coverage
item) are untouched, and CI-07's rule-12 latent-issue note is untouched. The CFF change is a data
sync via the existing script; the tag-time guard still reads the tagged commit.

## Approach

Edit the three documents in place, changing only the two command scopes; reorder rule 12's numbered
steps and append one sentence to the branch-flow bullet; run
`python scripts/update_citation.py --version 0.3.12 --date 2026-09-13` against the repo-root CFF.
No spec delta and no new canonical spec.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `AGENTS.md` | Modified | Rule 5 mypy scope; rule 12 step order; branch-flow sentence |
| `CONTRIBUTING.md` | Modified | Development commands: mypy and ruff check scope |
| `.github/PULL_REQUEST_TEMPLATE.md` | Modified | Verification block and Checklist: mypy and ruff check scope |
| `CITATION.cff` | Modified | `version` + `date-released` synced to `v0.3.12` / `2026-09-13` |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| CONTRIBUTING/PR-template edits break CI-09's assertions | Low | Edits stay in the Development-commands block / command lines; the type-checking section and the `pyright` checklist item are untouched |
| Rule-12 reorder weakens the CI-07 latent-issue note | Low | The note is a separate `Rules` bullet, left byte-identical; the reorder only swaps steps 1-2 |
| CFF sync lands a not-yet-released version on `dev` | Low | `v0.3.12` is already released; the tag-time guard is tag-scoped and `sofer --version` resolves from installed metadata |

## Rollback Plan

Revert the four-file diff: restore `AGENTS.md`, `CONTRIBUTING.md`,
`.github/PULL_REQUEST_TEMPLATE.md`, and `CITATION.cff` from the merge base. No code, dependency, or
workflow state is touched; the release guard is unaffected either way.

## Dependencies

None.

## Success Criteria

- [ ] The four sites name the CI-enforced scope.
- [ ] AGENTS.md rule 12 sets the CFF bump on `dev` before the merge, and the branch-flow rule says
      so.
- [ ] `CITATION.cff` on the branch declares `0.3.12` / `2026-09-13`, edited only by the script.
- [ ] `uv run python scripts/update_citation.py --check --version 0.3.12` exits 0 on the branch.
- [ ] `uv run pytest tests/ -q` green; ruff/mypy/pyright clean.
