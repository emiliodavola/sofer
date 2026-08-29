# Apply Progress — readme-overhaul-es

**Phase**: sdd-apply (PR1 + PR2 + PR3 + PR4 slices — bug fixes; restructure + extraction; feature docs; README_ES.md + sync policy)
**Dates**: 2026-08-28 (PR1), 2026-08-28 (PR2), 2026-08-28 (PR3), 2026-08-28 (PR4)
**Branch**: `docs/readme-overhaul-es` (off `dev`)
**Mode**: Standard (strict TDD disabled — `openspec/config.yaml` `apply.tdd: false`)

## Scope of this batch (cumulative)

All four PRs of the feature-branch chain: PR1 bug fixes (tasks 1.1–1.4),
PR2 restructure + extraction (tasks 2.1–2.7), PR3 feature documentation
(tasks 3.1–3.7), PR4 README_ES.md + sync policy (tasks 4.1–4.6). This is
the FINAL slice — the change is complete (24/24 tasks).

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
  anchors verified against the GitHub slug rule. **RESOLVED in PR3** — all 3
  subsection bullets landed in the same commits as their sections.
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

### Phase 3 (PR3) — feature documentation

- [x] **3.1** `README.md` `## Command reference`: add `sofer-mcp` row
  (carry-forward #1, exact text from design; `sofer upload` removal note
  kept). Verify: row matches design verbatim. **Done** — row added verbatim
  (README L250). Formatted as a separate console-script entry point
  (`pyproject.toml` `[project.scripts] sofer-mcp = "sofer.mcp_server:main"`),
  no `<args>`; `upload`-removal note kept.
- [x] **3.2** `README.md`: add `### Flags at a glance` glossary
  (carry-forward #2 — `--keep-csv`, `--no-checks`, `--force`, `--dry-run`,
  `--output` with per-command semantics). Verify: semantics match `cli.py`.
  **Done** — all 5 rows verified against cli.py: `--keep-csv` publish / HF
  target only (no effect with `--target local`, PUB-07); `--no-checks`
  prepare (`run_checks=not args.no_checks`); `--force` prepare/publish/scan
  (overwrite existing artifacts/destination files + skip the confirmation
  prompt); `--dry-run` publish/scan (no network, no copies, no TOML writes);
  `--output DIR` prepare/publish/profile/render. Command list follows the
  design's carry-forward text verbatim (`codebook` also accepts `--output`,
  kept out of the glossary per design — noted, not a deviation).
- [x] **3.3** `README.md` `## Data format support`: add prepare/publish
  columns to the format table. Verify: columns match `_formats.py`. **Done** —
  format rows unchanged (CSV/TSV/Parquet/Excel/JSONL = `SUPPORTED_FORMATS`
  keys exactly); `prepare`/`publish` columns + footnote added — CSV is
  converted to Parquet during prepare (unless `upload_as_csv = true`), every
  other format is staged as-is, publish delivers the package unchanged
  (verified against the prepare.py conversion loop, L660-711).
- [x] **3.4** `README.md`: add `### Parquet conversion limitations` (spec
  parquet-conversion §7.2 content). Verify: §7.2 limitations documented.
  **Done** — the three §7.2 gaps (comma-as-decimal, mixed-type >50 %, >2 GB
  strings) in a pattern/workaround table. Fallback wording modernized to the
  current prepare flow (warning + stage the original CSV as-is in the
  package), replacing the old uploader-era "upload as CSV" phrasing.
- [x] **3.5** `README.md`: add `## Split detection` (keyword delimiting rule,
  filename/directory/shard sources, precedence). Verify: matches `splits.py`.
  **Done** — keywords (train/training, validation/valid/val/dev,
  test/testing/eval/evaluation), delimiting rule (`test-file.csv` ✅ /
  `testfile.csv` ❌, `-`/`_`/`.`/whitespace delimit), cascade directory →
  filename → shard (`-NNNNN-of-NNNNN`, needs ≥2 distinct splits) → single-train
  fallback, exclusions (README.md/LICENSE/.gitattributes/.gitignore), and the
  HF-viewer `train`-split note — all from splits.py.
- [x] **3.6** `README.md` under `Validation and quality checks`: add
  `### Verify the built package (prepare --verify)` (SKIPPED/PASSED/FAILED,
  `pip install datasets` opt-in). Verify: matches `verification.py`/`cli.py`.
  **Done** — end-to-end `datasets.load_dataset()` on the build directory (the
  same call a user makes with `load_dataset("user/repo")`); **SKIPPED** when
  the optional `datasets` package is not installed (install hint `pip install
  datasets`); **PASSED**/**FAILED** with split comparison; informational and
  non-blocking (prepare.py step 10, PRP-08).
- [x] **3.7** Optional bonus (badges under tagline above TOC, live HF dataset
  link, rendered codebook example): adopt or defer. Verify: if adopted,
  placement per design D7 and mirrored in ES (PR4). **Done — badges ADOPTED**
  at the D7 position (under tagline, above TOC), replacing the PR2
  placeholder: CI (`https://github.com/emiliodavola/sofer/actions/workflows/ci.yml/badge.svg`
  — `.github/workflows/ci.yml` verified to exist), License (LICENSE file +
  `license = "MIT"` → shields GitHub-license badge), Python (`requires-python
  = ">=3.10"` → static shields badge; no PyPI dynamic badge because sofer is
  not published). Live-HF-dataset-link + rendered-codebook-example bonuses
  **DEFERRED** (not determinable without inventing). **PR4 MUST mirror the
  badge block verbatim into README_ES.md.**

### Phase 4 (PR4) — README_ES.md + sync policy

- [x] **4.1** Created `README_ES.md` (new, 536 lines): mirror of README.md per
  the D1 contract — **identical English heading tree (32/32**, fence-aware
  compare), identical TOC (19/19 byte-identical), badge block verbatim,
  all code blocks verbatim (comments included), technical tokens in English,
  prose in neutral professional Spanish (no voseo; "tú" forms). Command
  reference descriptions translated; `sofer-mcp` row + Flags at a glance
  table kept verbatim English (carry-forwards 1+2). Configuration and
  Architecture summary link to the English `docs/configuration.md` /
  `CONTRIBUTING.md` with a "technical docs are in English" note. Deep config
  reference and architecture stay English in docs/ per design.
- [x] **4.2** Switcher `**[English](README.md) | [Español](README_ES.md)**`
  added to BOTH files, byte-identical, immediately after the H1 (before the
  tagline, per design tree); exactly 1 occurrence per file.
- [x] **4.3** `sofer-mcp` row verbatim vs README (Compare-Object equal);
  Flags at a glance table 10/10 lines byte-identical to README.
- [x] **4.4** `AGENTS.md` rule 13 added — **verbatim** vs design.md L99-106
  (header + both bullets byte-compared).
- [x] **4.5** `.github/PULL_REQUEST_TEMPLATE.md` `## Checklist`:
  `- [ ] README_ES.md updated if a translated README section changed`
  inserted directly after "README updated if CLI surface changed".
- [x] **4.6** Mirror verification: heading diff README.md ↔ README_ES.md
  **EMPTY** (32/32, same order, same level); `pyproject.toml` L5
  `readme = "README.md"` unchanged (packaging untouched); pytest still
  **886 passed, 2 skipped**. Also added the deferred CONTRIBUTING.md PR sync
  bullet ("Changes touching a user-facing README section MUST update
  README_ES.md in the same commit") — design D5 item, PR2 deviation #3
  RESOLVED.

## Files changed

| File | Action | What Was Done |
|------|--------|---------------|
| `README.md` | Modified (PR1 + PR2 + PR3 + PR4) | PR1: 4+/11- bug fixes. PR2: TOC, Quick start, reorder to pinned spine, 4 heading renames, badges placeholder, deep `[tool.sofer]` ref removed, `## Configuration` + `## Architecture summary` added. PR3: `sofer-mcp` row, `### Flags at a glance`, prepare/publish format columns, `### Parquet conversion limitations`, `## Split detection`, `### Verify the built package (prepare --verify)`, 4 TOC bullets, real CI/license/Python badges. PR4: language switcher line after H1 (+2 lines, nothing else). |
| `README_ES.md` | Created (PR4) | 536-line mirrored Spanish README: identical 32-heading tree, identical TOC, badge block + code blocks verbatim, Spanish prose, English technical tokens; links to English docs with note. |
| `docs/configuration.md` | Created (PR2) | `[tool.sofer]` deep reference, moved verbatim (80 lines verified), 4 pinned headings + H1, deduped canonical copies. |
| `CONTRIBUTING.md` | Modified (PR2 + PR4) | PR2: + Development setup, Development commands, Architecture (tree verbatim + 2-line orientation); Getting-started step 3 → pointer to Development setup; existing content preserved. PR4: + PR sync bullet ("Changes touching a user-facing README section MUST update README_ES.md in the same commit") under `## Pull requests`. |
| `AGENTS.md` | Modified (PR4) | + rule 13 README/README_ES sync (verbatim per design D5). |
| `.github/PULL_REQUEST_TEMPLATE.md` | Modified (PR4) | + `- [ ] README_ES.md updated if a translated README section changed` after the README checklist item. |
| `openspec/changes/readme-overhaul-es/tasks.md` | Modified | Tasks 1.1–1.4 (PR1), 2.1–2.7 (PR2), 3.1–3.7 (PR3), 4.1–4.6 (PR4) marked `[x]` — 24/24. |
| `openspec/changes/readme-overhaul-es/apply-progress.md` | Modified | This artifact (merged PR1 + PR2 + PR3 + PR4). |

## Deviations from design

1. **TOC subsection bullets deferred to PR3** (PR2). Design's final-state TOC
   lists `### Flags at a glance`, `### Parquet conversion limitations`,
   `### Verify the built package (prepare --verify)`; those sections are PR3
   tasks and their anchors could not resolve in PR2. **RESOLVED in PR3** —
   all 3 subsection bullets added in the same commits as their sections
   (mandatory carry-forward honored; 19/19 TOC anchors resolve).
2. **Badges = placeholder marker, not links** (PR2). No badge URLs were
   determinable in PR2 without inventing them. **RESOLVED in PR3** — 3 real
   badges adopted (task 3.7) at the D7 pinned position.
3. **CONTRIBUTING PR sync bullet deferred to PR4** (design D5 sync policy).
   Design's File-Changes table tags it "(PR2)" but the delivery table puts
   "sync policy" out of PR2 scope, no 2.x task exists for it, and
   `README_ES.md` does not exist until PR4. **RESOLVED in PR4** — the bullet
   landed in the sync-policy work unit with AGENTS.md rule 13 + PR-template
   item.
4. **Getting-started step 3 pointer** (PR2). Design says Development setup is
   "merged from README L50-57 + existing env steps" — the env commands moved
   into Development setup, so Getting started step 3 now points there instead
   of repeating them (no duplicated env setup).
5. **NEW (PR3)**: §7.2 fallback wording modernized — the parquet-conversion
   spec's "upload as CSV" language predates the prepare/publish split; the
   README documents the current behavior (conversion failure → warning + the
   original CSV is staged into the package as-is). Content (the three §7.2
   gaps) is verbatim-in-spirit.
6. **NEW (PR3), noted not a deviation**: `--output` glossary row follows the
   design carry-forward command list (prepare/publish/profile/render);
   `codebook --output` exists in cli.py but is outside the design's list.
   Reviewer may extend the row if desired.
7. **NEW (PR4), interpretation note**: README_ES translation scope — reference
   tables whose cells are technical facts (format table, integrity/quality
   check tables) keep their technical tokens English while descriptive prose
   cells are translated; the mandated verbatim items (badges, `sofer-mcp`
   row, Flags at a glance) are untouched per carry-forward commitments.
   Command-reference descriptions are translated (prose) with commands and
   flags kept English.

## Issues found

None blocking. Notes: tasks.md cites stale README line counts (388/501) and a
795-test baseline; the file (494 → 535 → 462 → 493 → 495 lines across PR1/PR2a/
PR2b/PR3/PR4 — PR4 adds the 2-line switcher) and the suite (886 passed, 2
skipped) are authoritative. README_ES.md is 536 lines (mirror; longer than the
English file because Spanish prose wraps slightly longer).

## Workload / PR boundary

- Mode: chained PR slice (PR4 of 4 — FINAL), feature-branch-chain, tracker `docs/readme-overhaul-es`
- Current work unit: PR4 — README_ES.md + sync policy, three commits:
  - `d39cc1e` `docs(readme): add Spanish README_ES.md mirror and language switcher` — README_ES.md (new, 536 lines) + README.md (+2)
  - `65ad281` `docs: add README/README_ES sync policy (AGENTS rule 13, PR template, contributing)` — AGENTS.md (+7), PULL_REQUEST_TEMPLATE.md (+1), CONTRIBUTING.md (+1)
  - (this batch) `docs(openspec): mark PR4 tasks complete and merge apply-progress` — tasks.md + apply-progress.md
- Boundary: start = README after PR3 (`adb3f67`, 493 lines, no README_ES.md);
  end = README 495 lines with switcher, README_ES.md (536 lines) with
  identical 32-heading tree, sync policy in AGENTS/template/CONTRIBUTING.
  Change COMPLETE — nothing pending.
- Review budget impact: PR4 combined ≈ 547 insertions / 0 deletions on docs
  (README_ES.md dominates — new file), + 9 on policy files, + process
  artifacts. Above the 400-line default ONLY because README_ES.md is a new
  mirror file (one indivisible unit); cumulative chain total ≈ 1280 changed
  lines, within the user's 2000-line ceiling.

## Verification evidence

- TOC anchors: **19/19 resolve** (fence-aware GitHub slug rule, programmatic
  check; 0 unresolved).
- New headings present with pinned anchors: `flags-at-a-glance`,
  `parquet-conversion-limitations`, `split-detection`,
  `verify-the-built-package-prepare---verify` (triple-hyphen anchor verified).
- `sofer-mcp` row verbatim vs design carry-forward #1; entry point confirmed
  in `pyproject.toml` `[project.scripts]` (`sofer-mcp = "sofer.mcp_server:main"`).
- Flags glossary semantics verified against `cli.py` (all 5 rows).
- Format rows match `_formats.py` exactly; prepare/publish columns verified
  against the prepare.py conversion loop.
- Split detection verified against `splits.py` (keywords, delimiters,
  cascade, exclusions, fallback).
- Verify subsection verified against `verification.py` + prepare.py step 10
  (optional-dependency guard, load_dataset on staging dir, split comparison,
  non-blocking).
- §7.2 three limitations documented (parquet-conversion spec).
- Badges: `.github/workflows/ci.yml` exists (Get-ChildItem), LICENSE exists,
  `license = "MIT"`, `requires-python = ">=3.10"`.
- **PR4 mirror checks** (programmatic, PowerShell): heading tree README.md ↔
  README_ES.md **identical 32/32** (fence-aware, same order/level); switcher
  line byte-identical, exactly 1 occurrence per file; TOC **19/19
  byte-identical**; badge block **byte-identical**; Flags at a glance table
  **10/10 lines identical**; `sofer-mcp` row verbatim; AGENTS.md rule 13
  verbatim vs design.md L99-106; `pyproject.toml` `readme = "README.md"`
  unchanged.
- `uv run pytest tests/ -q` → **886 passed, 2 skipped** (14.31s) — unchanged
  from baseline, code untouched.

## Status

24/24 tasks complete (PR1: 1.1–1.4; PR2: 2.1–2.7; PR3: 3.1–3.7; PR4:
4.1–4.6). Change COMPLETE — ready for `sdd-verify` (full change), then
`sdd-archive`.