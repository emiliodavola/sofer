# Apply Progress — readme-overhaul-es

**Phase**: sdd-apply (PR1 slice — bug fixes only)
**Date**: 2026-08-28
**Branch**: `docs/readme-overhaul-es` (off `dev`)
**Mode**: Standard (strict TDD disabled — `openspec/config.yaml` `apply.tdd: false`)

## Scope of this batch

PR1 of the 4-PR feature-branch chain: bug fixes in `README.md` only (tasks 1.1–1.4).
PR2/PR3/PR4 tasks intentionally untouched.

## Completed tasks

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

## Files changed

| File | Action | What Was Done |
|------|--------|---------------|
| `README.md` | Modified | 4 insertions / 11 deletions: English key principle, dedupe ×2 (release-note blockquote + duplicated sensible-default line), rot-proof git-tag install note |
| `openspec/changes/readme-overhaul-es/tasks.md` | Modified | Tasks 1.1–1.4 marked `[x]` |
| `openspec/changes/readme-overhaul-es/apply-progress.md` | Created | This artifact |

## Deviations from design

None — implementation matches design.md decisions (canonical editable-install
note is the L224-228 "Behavior change for editable installs" blockquote; the
second "Release note" blockquote and second sensible-default line removed;
PyPI note → git-tag path per design "no rot-prone negative" and proposal "Keep
git-tag wording (AGENTS.md rule 12)").

## Issues found

None. Note: tasks.md Review Workload Forecast risk note claims README is 388
lines; the file is 501 lines (494 after PR1) — the note is wrong, the file is
authoritative (per orchestrator briefing, matched).

## Workload / PR boundary

- Mode: chained PR slice (PR1 of 4), feature-branch-chain, tracker `docs/readme-overhaul-es`
- Current work unit: PR1 — README bug fixes (tasks 1.x)
- Boundary: start = README.md as committed on `dev` (501 lines); end = 494
  lines with the 4 fixes applied. PR2+ work NOT started.
- Review budget impact: 15 changed lines (4+/11-) — well under the ~40 estimate;
  entire PR1 diff is one file.

## Verification evidence

- `git diff README.md` = 4 insertions, 11 deletions, single file.
- `uv run pytest tests/ -q` → `886 passed, 2 skipped` (20.59s).
- Rendered README checked: all three fixes present; headings/links untouched.

## Status

4/4 PR1 tasks complete. Ready for `sdd-verify` (PR1 slice) or next `apply` batch (PR2).