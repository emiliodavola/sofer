# Archive Report — readme-overhaul-es

**Change**: readme-overhaul-es
**Branch**: `docs/readme-overhaul-es` @ `8453a37` (commits `5923838` PR1, `1f81040`+`d434b05` PR2, `1c28dc9`+`e3d1ddf`+`adb3f67` PR3, `d39cc1e`+`65ad281`+`8453a37` PR4 — 9 commits, feature-branch chain off `dev`)
**Archived to**: `openspec/changes/archive/2026-08-28-readme-overhaul-es/`
**Archive date**: 2026-08-28
**Verdict**: ✅ ARCHIVED — **PASS** (0 blockers, 0 critical findings)

> NOTE: the change is **not yet merged to dev** — the user merges manually and
> opens the PR(s), which carry these archived artifacts as-is.

## Verification Source

Engram verify-report for this change (observation #645, topic key
`sdd/readme-overhaul-es/verify-report`, project sofer) — FINAL verdict **PASS**,
0 blockers, 0 critical. 1/1 requirement (TC-09), 3/3 TC-09 scenarios compliant,
parquet-conversion §7.2 carried compliant, 24/24 tasks complete. The report is
the merged 4-slice audit (PR1 bug fixes, PR2 restructure + extraction, PR3
feature docs, PR4 README_ES + sync policy).

Gate outputs (from verify-report #645, FINAL slice):

- `uv run pytest tests/ -q` → 886 passed, 2 skipped, 13 warnings (exit 0) — unchanged across all 4 slices
- `uv run mypy src/` → Success, 26 source files (exit 0) — output byte-identical to baseline (`394f9a8f…`), zero code touched
- `uv run ruff check src/ tests/` → All checks passed (exit 0)
- Docs-only change: no code, CLI surface, dependency, or test changes (886/2 identical on every slice)

### SDD artifact traceability (Engram observation IDs)

| Artifact | Topic key | Observation ID |
|----------|-----------|----------------|
| exploration | `sdd/readme-overhaul-es/explore` | #639 |
| proposal | `sdd/readme-overhaul-es/proposal` | #640 |
| spec (delta) | `sdd/readme-overhaul-es/spec` | #641 |
| design | `sdd/readme-overhaul-es/design` | #642 |
| tasks | `sdd/readme-overhaul-es/tasks` | #643 |
| apply-progress | `sdd/readme-overhaul-es/apply-progress` | #644 |
| verify-report | `sdd/readme-overhaul-es/verify-report` | #645 |
| archive-report | `sdd/readme-overhaul-es/archive-report` | (this save) |

## Task Completion Gate

`tasks.md`: **24/24 tasks checked** across 4 phases (PR1 1.1–1.4, PR2 2.1–2.7,
PR3 3.1–3.7, PR4 4.1–4.6). No stale unchecked implementation tasks;
apply-progress and the FINAL verify-report independently confirm all phases
complete. Gate PASSED — spec sync and archive move proceeded normally.

## Spec Sync Summary

Delta spec synced to the live source of truth. The `tool-config` domain already
exists under `openspec/specs/`, and the delta is a **MODIFIED requirement**
(TC-09 re-scope) — merged by replacing the old TC-09 block:

| Domain | Action | Details |
|--------|--------|---------|
| tool-config | Updated | **TC-09** MODIFIED: deep `[tool.sofer]` reference relocated to `docs/configuration.md` (authoritative), README keeps a short summary + link + one-line `SOFER_VERBOSE` pointer and MUST NOT duplicate the deep reference. Scenario "Docs cover precedence and maintainer shift" re-scoped to `docs/configuration.md`; 2 scenarios added ("README points to the authoritative reference", "SOFER_VERBOSE pointer survives extraction") — 3 scenarios total. Previous state recorded via the delta's `(Previously: …)` note. TC-01..TC-08 untouched. |

Each modified requirement carries a provenance note
(`> Added by change \`readme-overhaul-es\` (archived 2026-08-28).`) matching the
repo's established archive convention (same as `sofer-mcp-server`,
`installable-cli-pypi`, `staged-parquet-*`, etc.).

Per `openspec/config.yaml` `rules.archive` ("Warn before merging destructive
deltas"): the merge was **non-destructive** (single MODIFIED requirement,
deliberately re-scoped by this change and documented with the previous text;
no large sections removed, no other requirements touched) — no warning
required.

## Archive Contents

- exploration.md ✅ (issue #69 validation, approach lock, refinements)
- proposal.md ✅ (intent, scope in/out, 4-step approach, rollback, success criteria)
- specs/tool-config/spec.md ✅ (delta spec — MODIFIED TC-09)
- design.md ✅ (7 architecture decisions D1–D7, pinned anchor trees, 4-PR delivery slicing, carry-forward commitments)
- tasks.md ✅ (24/24 complete)
- apply-progress.md ✅ (merged PR1–PR4, 7 deviations recorded)
- verify-report.md ✅ (4-slice audit; FINAL verdict PASS, 0 critical)
- archive-report.md ✅ (this file)

No `state.yaml` / `change.md` status file exists in this repo's change folders;
the archive folder + this report is the status record (matches prior archives).

## Non-blocking verify suggestions (carried forward)

1. Missing trailing newline at EOF in `README.md`, `README_ES.md`,
   `docs/configuration.md`, `CONTRIBUTING.md` — POSIX text-file convention,
   cosmetic; nothing enforces it for `.md`.
2. `tasks.md` cites stale line counts (388/501) and a 795-test baseline —
   authoritative numbers are 495-line README / 536-line README_ES / 886 passed;
   cosmetic.
3. `prepare.py` L324 prints uploader-era phrasing ("conversion failed —
   uploading as CSV") while the README correctly documents "stages the original
   CSV" — flag for a future code-message cleanup (out of scope, docs-only
   change).

## Source of Truth Updated

- `openspec/specs/tool-config/spec.md` (TC-09 MODIFIED — re-scoped to
  `docs/configuration.md`, 3 scenarios)

## SDD Cycle Complete

The change has been fully planned, implemented, verified, and archived.
The user opens the PR(s) from `docs/readme-overhaul-es` (which carries these
archived artifacts) and merges to `dev` manually.