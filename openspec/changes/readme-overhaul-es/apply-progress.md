# Apply Progress — readme-overhaul-es

**Phase**: sdd-apply (PR1 + PR2 slices — bug fixes; restructure + extraction)
**Dates**: 2026-08-28 (PR1), 2026-08-28 (PR2)
**Branch**: `docs/readme-overhaul-es` (off `dev`)
**Mode**: Standard (strict TDD disabled — `openspec/config.yaml` `apply.tdd: false`)

## Scope of this batch (cumulative)

PR1 of the 4-PR feature-branch chain: bug fixes in `README.md` only (tasks
1.1–1.4). PR2 of the chain: restructure + extraction (tasks 2.1–2.7).
PR3/PR4 tasks intentionally untouched.

## Completed tasks

### Phase 1 (PR1) — bug fixes

- [x] **1.1** `README.md` `## Why`: L36 Spanish principle → English
  (`Automatizar observaciones; no inventar conocimiento semántico.` →
  `Automate observations; don't invent semantic knowledge.`), kept in the
  surrounding `- **Principle.** explanation` list style. Verify: rendered
  README shows English text. **Done** — line 36 now English.
- [x] **1.2** `README.md`: removed the duplicate "Release note" blockquote
  (was L279-282, second copy of the editable-install behavior note) and the
  second "Every value has a sensible default — the whole section is optional."
  line (was L284). Canonical copies retained in place (editable-install note at
  L224-228, sensible-default intro at L201-202); they move to
  `docs/configuration.md` in PR2 per design D-section "Moves out". Verify: no
  duplicated blocks remain. **Done** — diff shows both deletions, section
  flows TOML block → `## Command reference`.
- [x] **1.3** `README.md` `## Install`: rephrased the PyPI note to the
  rot-proof git-tag install path. Removed "It is not published on PyPI yet, so
  install it from the git tag of the release you want." → "Install it from the
  git tag of the release you want." No PyPI claim remains (nothing to rot);
  wording matches AGENTS.md rule 12 (tag-driven releases, no PyPI step). Verify:
  no negative/rot-prone PyPI wording. **Done**.
- [x] **1.4** Baseline: `uv run pytest tests/ -q`. Verify: 795 tests still pass
  (code untouched). **Done** — **886 passed, 2 skipped** in 20.59s (suite has
  grown past the 795 baseline noted in tasks.md; all green, no code touched).

### Phase 2 (PR2) — restructure + extraction

- [x] **2.1** `README.md`: add `## Table of Contents` (flat anchor bullets;
  top-level + `Flags at a glance`, `Parquet conversion limitations`, `Verify
  the built package` subsections). Verify: every TOC anchor resolves.
  **Done** — TOC added with flat bullets. **Sequencing decision**: the 3
  subsection bullets from the design's final-state TOC are NOT in PR2's TOC —
  those sections are PR3 content and their anchors cannot resolve yet, and
  task 2.1's own verify gate ("every TOC anchor resolves") wins over the
  design's final-state TOC. **CARRY-FORWARD (PR3)**: add the 3 subsection
  bullets to the TOC in the same commit as their sections. All 15 PR2 TOC
  anchors verified against the GitHub slug rule.
- [x] **2.2** `README.md`: reorder to the pinned spine (Install → Quick start →
  Why → Typical workflow → TOML reference → Directory layout → Profiling and
  rendering → Command reference → Data format support → Split detection →
  Validation and quality checks → Codebook generation → AI and MCP server →
  Configuration → Architecture summary → Related); add `## Quick start`
  (~6-line happy path init→scan→prepare→publish). Verify: section order
  matches design. **Done** — order verified heading-by-heading; Split
  detection is PR3 so absent in PR2 (spine otherwise matches). Quick start =
  5-command happy path (init→scan→prepare→publish) + pointer to Typical
  workflow.
- [x] **2.3** `README.md`: rename 3 headings for clean anchors — `Profiling
  and rendering`, `Semantic types and PII detection`, `Validation and quality
  checks` (drop `&`/`/`/parens). Verify: no ambiguous double-hyphen slugs.
  **Done** — 4 renames applied (incl. `AI and MCP server` per design tree);
  anchors re-derived programmatically with the GitHub slug rule and checked
  against the TOC (no `--` slugs remain).
- [x] **2.4** Create `docs/` + `docs/configuration.md`: move `[tool.sofer]`
  deep reference verbatim with pinned anchors (Discovery and precedence;
  Bootstrap keys (cwd-only); Seeing which file was used; Metadata inference
  tuning) + single canonical editable-install/sensible-default copies. Verify:
  content matches README pre-move (no content loss). **Done** — new
  `docs/configuration.md` with `# Tool-wide configuration ([tool.sofer])` H1 +
  the 4 pinned `##` headings; **all 80 deep-ref lines verified present (0
  missing)**; dedup held from PR1 (single canonical copies).
- [x] **2.5** `README.md`: remove deep reference; add `## Configuration`
  summary (precedence one-liner, link →
  `docs/configuration.md#discovery-and-precedence`, one-line `SOFER_VERBOSE`
  pointer → `#seeing-which-file-was-used`). Verify: TC-09 scenarios —
  authoritative link, no deep ref in README, verbosity pointer survives.
  **Done** — TC-09 scenarios 1–3 satisfied: (1) docs/configuration.md covers
  3-step precedence + bootstrap-key caveat + editable-install note; (2) README
  links to the authoritative doc and carries no deep ref (leftover check
  empty); (3) one-line `SOFER_VERBOSE=1` pointer with destination anchor.
- [x] **2.6** `CONTRIBUTING.md`: add `Development setup`, `Development
  commands`, `Architecture` (module tree verbatim + 2-line orientation).
  Verify: sections present, tree verbatim. **Done** — 25-line tree, 3-line
  commands block, and the dev-setup block (uv sync / cp .env.template /
  HF-token blockquote) verified verbatim; all 33 non-env lines of the existing
  62-line CONTRIBUTING preserved (0 missing). Getting-started step 3 now
  points to Development setup (design says Development setup is "merged from
  ... existing env steps" — the env commands moved, so no duplication).
- [x] **2.7** `README.md`: remove Architecture tree + Development
  setup/commands; add `## Architecture summary` (2–3 lines) + contributor
  pointer → `CONTRIBUTING.md#architecture`. Verify: moved content exists in
  CONTRIBUTING.md and links resolve. **Done** — contributor sections removed
  from README (leftover check empty); `## Architecture summary` links to
  `CONTRIBUTING.md#architecture` and `CONTRIBUTING.md`.

## Files changed

| File | Action | What Was Done |
|------|--------|---------------|
| `README.md` | Modified (PR1 + PR2) | PR1: 4+/11- bug fixes. PR2: TOC, Quick start, reorder to pinned spine, 4 heading renames, badges placeholder, deep `[tool.sofer]` ref removed, `## Configuration` + `## Architecture summary` added. |
| `docs/configuration.md` | Created (PR2) | `[tool.sofer]` deep reference, moved verbatim (80 lines verified), 4 pinned headings + H1, deduped canonical copies. |
| `CONTRIBUTING.md` | Modified (PR2) | + Development setup, Development commands, Architecture (tree verbatim + 2-line orientation); Getting-started step 3 → pointer to Development setup; existing content preserved. |
| `openspec/changes/readme-overhaul-es/tasks.md` | Modified | Tasks 1.1–1.4 (PR1) and 2.1–2.7 (PR2) marked `[x]`. |
| `openspec/changes/readme-overhaul-es/apply-progress.md` | Modified | This artifact (merged PR1 + PR2). |

## Deviations from design

1. **TOC subsection bullets deferred to PR3.** Design's final-state TOC lists
   `### Flags at a glance`, `### Parquet conversion limitations`, `### Verify
   the built package (prepare --verify)`; those sections are PR3 tasks and
   their anchors cannot resolve in PR2. PR2 TOC carries top-level bullets
   only — task 2.1's "every TOC anchor resolves" gate satisfied (verified
   programmatically). PR3 MUST add the 3 bullets with their sections.
2. **Badges = placeholder marker, not links.** Design D7 places badges under
   the tagline above the TOC (optional bonus). No real badge URLs are
   determinable without inventing them, so PR2 leaves the marked placeholder
   `<!-- BADGES ... -->` at the pinned position. **Decision for reviewer**:
   adopt real CI/license/Python badge links in PR3 (task 3.7) or keep the
   placeholder.
3. **CONTRIBUTING PR sync bullet deferred to PR4.** Design's CONTRIBUTING
   structure lists a NEW "Pull requests" bullet ("Changes touching a
   user-facing README section MUST update README_ES.md in the same commit")
   and the File-Changes table tags it "(PR2)", but the delivery table puts
   "sync policy" out of PR2 scope, tasks.md has no 2.x task for it, and
   `README_ES.md` does not exist until PR4. Deferred to PR4 with AGENTS.md
   rule 13 + PR-template item (design D5 sync policy). Flagged for reviewer.
4. **Getting-started step 3 pointer.** Design says Development setup is
   "merged from README L50-57 + existing env steps" — the env commands
   (uv sync / pre-commit install) moved into Development setup, so Getting
   started step 3 now points there instead of repeating them (no duplicated
   env setup).

## Issues found

None blocking. Notes: tasks.md cites stale README line counts (388/501) and a
795-test baseline; the file (494 → 535 → 462 lines across PR1/PR2a/PR2b) and
the suite (886 passed, 2 skipped) are authoritative.

## Workload / PR boundary

- Mode: chained PR slice (PR2 of 4), feature-branch-chain, tracker `docs/readme-overhaul-es`
- Current work unit: PR2 — restructure + extraction, split into two commits:
  - 2a `1f81040` `docs(readme): restructure README into user-first sections with TOC` — 119 insertions / 78 deletions (README only)
  - 2b (this batch) `docs(readme): extract tool config and contributor guides` — README extraction + docs/configuration.md + CONTRIBUTING.md + process artifacts
- Boundary: start = README.md after PR1 (`5923838`, 494 lines); end = final
  README (462 lines) + docs/configuration.md + CONTRIBUTING.md (all links
  resolve, zero content loss). PR3+ work NOT started.
- Review budget impact: combined PR2 diff ≈ 300 insertions / 200 deletions
  (within the ~550–650 forecast; mechanical move reads as delete+add).

## Verification evidence

- PR2a: every one of the 494 pre-PR2 lines present in the restructured README
  after the 4 D2 heading renames (programmatic line-set check).
- PR2b: deep-ref body (80 lines) → docs/configuration.md, architecture tree
  (25 lines), development commands (3 lines), dev-setup block (4 lines) →
  CONTRIBUTING.md, and 33 existing CONTRIBUTING lines — all 0 missing
  (programmatic checks). README leftovers scan: no `## Development setup`,
  `## Architecture`, `## Development`, `### Tool-wide configuration`, or
  `####` deep-ref headings remain. TOC anchors match the GitHub slug rule
  exactly (15/15). New markers present: `## Configuration`, `## Architecture
  summary`, both `docs/configuration.md#…` links, `CONTRIBUTING.md#architecture`
  link, `SOFER_VERBOSE=1` pointer.
- `uv run pytest tests/ -q` → `886 passed, 2 skipped` (16.94s) — unchanged
  from baseline, code untouched.
- Rendered heading order (README): Install → Quick start → Why → Typical
  workflow → TOML reference → Directory layout → Profiling and rendering →
  Command reference → Data format support → Validation and quality checks →
  Codebook generation → AI and MCP server → Configuration → Architecture
  summary → Related — matches design spine.

## Status

11/11 tasks complete (PR1: 1.1–1.4; PR2: 2.1–2.7). Ready for `sdd-verify`
(PR2 slice) or the next `apply` batch (PR3 — feature docs).