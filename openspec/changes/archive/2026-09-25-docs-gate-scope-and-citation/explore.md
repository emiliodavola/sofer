# Exploration: Documented gate-command scope and CITATION.cff on `dev` (#212, #191)

## Current State

**#212 — documented commands are narrower than CI.** The CI and pre-commit gates run `ruff check`
and `mypy` over `src/ tests/ scripts/` / `src/ scripts/`, but several developer-facing documents
still document the narrower `src/ tests/` / `src/`:

| File | Documented command | Enforced scope |
|------|--------------------|----------------|
| `AGENTS.md:39` (rule 5) | `uv run mypy src/` | `uv run mypy src/ scripts/` |
| `CONTRIBUTING.md` Development commands | `uv run mypy src/` | `uv run mypy src/ scripts/` |
| `CONTRIBUTING.md` Development commands | `uv run ruff check src/ tests/` | `uv run ruff check src/ tests/ scripts/` |
| `.github/PULL_REQUEST_TEMPLATE.md` Verification block + Checklist | `uv run ruff check src/ tests/`, `uv run mypy src/` | `src/ tests/ scripts/`, `src/ scripts/` |

A contributor who follows these exactly can be green locally and fail CI.

**#191 — `CITATION.cff` on `dev` is stale.** `dev` declares `version: 0.2.2` / `date-released:
2026-08-27`; the newest tag is `v0.3.12` and `main`'s CFF declares `0.3.12` / `2026-09-13`. The
tag-time `citation-check` guard reads the tagged commit (never `dev`), so the staleness has no
mechanical impact — but `dev` is the integration branch, and AGENTS.md rule 12's branch-flow rule
("`main` receives changes only via merges from `dev`") is false for the CFF bump, which has landed
directly on `main` for 11 consecutive releases. The maintainer recorded option (a): move the bump
onto `dev` before the merge to `main`.

## Affected Areas

- `AGENTS.md` — rule 5 line 39 (mypy scope); rule 12 "Cutting a release" step order; the
  branch-flow bullet.
- `CONTRIBUTING.md` — Development commands block (mypy + ruff check scope).
- `.github/PULL_REQUEST_TEMPLATE.md` — Verification block and Checklist (mypy + ruff check scope).
- `CITATION.cff` — version + date-released synced to the latest release.

## Approaches

1. **Align the four documented sites to CI scope, and apply option (a)** (recommended) — the
   minimal, faithful fix for both issues; no spec-level behavior changes, so no delta spec.
2. **Align CI down to the narrower documented scope** — rejected by #212's second option; it
   would stop linting/type-checking `scripts/`, which contains live code.
3. **Document `main` as the authoritative CFF home (option b)** — rejected by the maintainer's
   recorded decision; it legalizes the rule-12 violation and risks a stale public citation.

## Recommendation

Approach 1. Fix the two command scopes in the three docs, reorder AGENTS.md rule 12 so the CFF
bump is a `dev` commit before the merge, add the branch-flow sentence, and sync `dev`'s CFF to
`v0.3.12` with the existing script (the only writer of the field).

## Risks

- `test_mypy_and_pyright_exclude_tests` reads CONTRIBUTING's **type-checking** section (unchanged)
  and the PR template Checklist's `pyright` item (kept) — the edits stay outside those assertions.
- The branch-flow sentence and release-step reorder must not weaken AGENTS.md rule 12's
  latent-issue note, which CI-07 scenario 4 pins.
- The CFF edit must go through `scripts/update_citation.py` (AC), preserving every other byte.

## Ready for Proposal

Yes.
