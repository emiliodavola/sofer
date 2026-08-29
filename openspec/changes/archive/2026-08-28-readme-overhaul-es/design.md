# Design: README overhaul + README_ES.md (Spanish)

## Technical Approach

Docs-only change implementing the proposal's Approach 2 (locked): restructure `README.md` user-first with a TOC, extract the deep `[tool.sofer]` reference to a new `docs/configuration.md` and contributor content to `CONTRIBUTING.md`, document shipped-but-undocumented features (split detection, `prepare --verify`, flag semantics, `sofer-mcp` row, `prepare`/`publish` format columns, Parquet conversion limitations per parquet-conversion §7.2), and add a mirrored `README_ES.md` with English headings / Spanish prose under an enforced sync policy. Delivered as 4 chained PRs. All facts below were verified against `src/sofer/` (splits.py, verification.py, cli.py, mcp_server.py) and the spec delta (TC-09).

## Architecture Decisions

| # | Decision | Choice | Alternatives | Rationale |
|---|----------|--------|--------------|-----------|
| D1 | README_ES heading language | **English heading text, Spanish body prose** | Spanish headings | Identical headings make sync drift visible in review (a section added in one file but not the other jumps out); GitHub auto-anchors are then identical across files, so TOC anchors and cross-links can be copied verbatim between them |
| D2 | Heading punctuation | **Rename 3 headings** to drop `&`, `/`, `( )`: `Validation and quality checks`, `AI and MCP server`, `Profiling and rendering` | Keep existing text | GitHub anchors for `&`/`/`/parens produce ambiguous double-hyphen slugs (`validation--quality-checks`); clean headings give predictable pinned anchors (spec risk #3) |
| D3 | Non-spine section placement | Why, TOML reference, Directory layout, Profiling and rendering, Configuration, Split detection placed adjacently to their natural sibling in the mandated spine (see tree) | Drop them / fold into other sections | No-content-loss rule; each is user-facing and referenced by the workflow |
| D4 | `--verify` home | Subsection of `Validation and quality checks` | New top-level section / under Typical workflow | It is a validation-adjacent prepare feature; keeps the top-level spine unchanged |
| D5 | Sync policy | New AGENTS.md **rule 13** + one PR-template checklist item (exact text below) | Fold into rule 7 | Rule 7 is CLI/README-specific; the translation obligation is broader (any translated-section change) and needs its own discoverable rule |
| D6 | Parquet limitations | New subsection under `Data format support` | Ignore (was undocumented) | Required by parquet-conversion spec §7.2 ("SHALL be documented in the project README") |
| D7 | Badges | **Out of core scope**; if adopted, fixed position under tagline above TOC, mirrored in README_ES | — | Proposal lists badges as optional bonus; placement pinned so adoption is a no-brainer |

## README.md Target Structure (pinned anchors)

Switcher line (not a heading, placed immediately after the H1, identical in both files):
`**[English](README.md) | [Español](README_ES.md)**`

```markdown
# sofer                                          #sofer
[English](README.md) | [Español](README_ES.md)   ← switcher (not a heading)
<!-- badges: optional bonus, under tagline, above TOC, mirrored in ES -->
<tagline + one-paragraph description>            (existing L6-8, kept)

## Table of Contents                  #table-of-contents      NEW — flat bullets, top-level + 3 key subsections
## Install                            #install                FIXED PyPI note → git-tag path (no rot-prone negative)
## Quick start                        #quick-start            NEW — compact happy path (init→scan→prepare→publish), ~6 lines
## Why                                #why                    MOVED down; Key principles verbatim + L36 English fix
## Typical workflow                   #typical-workflow       existing annotated walkthrough (L59-88), kept
## TOML reference                     #toml-reference         existing dataset-config template (L156-197), KEPT (user-facing)
## Directory layout                   #directory-layout       existing 3-line block (L148-154), kept
## Profiling and rendering            #profiling-and-rendering   existing L90-146 (renamed from "& (metadata workflow)")
### Semantic types and PII detection  #semantic-types-and-pii-detection   (renamed from "&")
## Command reference                  #command-reference      existing table + sofer-mcp ROW (carry-forward #1) + upload-removal note kept
### Flags at a glance                 #flags-at-a-glance      NEW glossary table (carry-forward #2)
## Data format support                #data-format-support    + prepare/publish columns
### Parquet conversion limitations    #parquet-conversion-limitations   NEW — §7.2 content
## Split detection                    #split-detection        NEW — keyword rule, sources, precedence
## Validation and quality checks      #validation-and-quality-checks  existing (renamed)
### Verify the built package (prepare --verify)  #verify-the-built-package-prepare---verify  NEW
## Codebook generation                #codebook-generation    existing, kept
## AI and MCP server                  #ai-and-mcp-server      existing L378-458, kept VERBATIM (verified accurate)
## Configuration                      #configuration          NEW summary: what [tool.sofer] is, precedence one-liner, link → docs/configuration.md, one-line SOFER_VERBOSE pointer → docs/configuration.md#seeing-which-file-was-used (TC-09)
## Architecture summary               #architecture-summary    NEW 2-3 lines + link → CONTRIBUTING.md#architecture; contributor pointer → CONTRIBUTING.md
## Related                            #related                existing links
```

**TOC format**: flat bullet list, `- [Install](#install)` style, top-level `##` sections plus `### Flags at a glance`, `### Parquet conversion limitations`, `### Verify the built package (prepare --verify)`. README_ES.md carries the identical TOC (same anchors).

**Stays in README**: title/tagline, Why + Key principles (verbatim, one fix), Install, Typical workflow, TOML reference, Directory layout, Profiling and rendering, Command reference (+rows/glossary), Data format support (+columns/limitations), Split detection, Validation and quality checks (+verify), Codebook generation, AI and MCP server (verbatim), Configuration summary, Architecture summary, Related.

**Moves out**: `[tool.sofer]` deep reference (L199-284) → `docs/configuration.md`; Architecture tree (L460-488), Development setup (L50-57), Development commands (L490-496) → `CONTRIBUTING.md`. **Deduped**: second "Behavior change for editable installs" note (L279-282) and second "Every value has a sensible default" line (L284) — single canonical copies in `docs/configuration.md`.

## docs/configuration.md Structure (pinned anchors — README links here)

New file; `docs/` directory does not exist yet (create it). Content moved verbatim from README L199-284 with dedup; headings renamed to clean anchors:

```markdown
# Tool-wide configuration ([tool.sofer])          #tool-wide-configuration-toolsofer
  intro: what it is + single "Every value has a sensible default — the whole section is optional."
## Discovery and precedence                       #discovery-and-precedence   3-step walk (dataset dir → cwd → defaults), first-found-stops, editable-install note (single canonical copy)
## Bootstrap keys (cwd-only)                      #bootstrap-keys-cwd-only   default_config_name / output_dir pre-config window
## Seeing which file was used                     #seeing-which-file-was-used  SOFER_VERBOSE=1 full explanation + stderr example
## Metadata inference tuning                      #metadata-inference-tuning  semantic_priors, confirm/min/detect thresholds, profile_max_sample, confidence_round_digits
```

README `## Configuration` links: `docs/configuration.md#discovery-and-precedence` and `docs/configuration.md#seeing-which-file-was-used` (SOFER_VERBOSE one-liner). README_ES.md links to the same English file with a "technical docs are in English" note.

## CONTRIBUTING.md Structure

Existing 62 lines, extended (no rewrite of current content):

```markdown
# Contributing to sofer
## Getting started              existing, kept
## Development setup            NEW (merged from README L50-57 + existing env steps): uv sync, pre-commit install, .env + HF token
## Development commands         NEW (from README L490-496): uv run pytest / mypy src/ / ruff check src/ tests/
## Architecture                 NEW (from README L460-488): module tree verbatim + 2-line orientation
## Development conventions      existing (Code style / Type checking / Commit messages)
## Pull requests                existing + NEW bullet: "Changes touching a user-facing README section MUST update README_ES.md in the same commit"
## Testing                      existing (kept; pytest command lives in Development commands)
## Reporting bugs               existing
## Questions?                   existing
```

## README_ES.md Mirrored Structure

New file, same top-level heading tree and order as README.md (D1: **English headings, Spanish prose**). User-facing sections only. Translation scope: prose translated to neutral/professional Spanish; **everything inside code blocks and inline technical tokens stays English**: commands, flags (`--verify`, `--keep-csv`, …), TOML/YAML excerpts, CLI output (`SKIPPED`/`PASSED`/`FAILED`), filenames, URLs, tool names (`sofer-mcp`, `sofer_validate`), `pip install datasets`. Deep content links to the English `docs/configuration.md` and `CONTRIBUTING.md`. `README_ES.md` is NOT referenced by `pyproject.toml` (`readme = "README.md"` unchanged) — packaging untouched.

## Sync Policy Mechanism

**AGENTS.md — new rule 13** (exact text):

```markdown
### 13. README / README_ES sync
- `README_ES.md` mirrors the user-facing headings and section order of `README.md`.
  Any change to a translated README section MUST update the matching `README_ES.md`
  section in the same commit; section additions/removals MUST land in both files.
- Technical content (commands, flags, TOML/YAML excerpts, CLI output, filenames,
  URLs) stays in English in both files; only prose is translated.
```

**PR template checklist** — extend the existing list (exact addition, after "README updated if CLI surface changed"):

```markdown
- [ ] README_ES.md updated if a translated README section changed
```

## Delivery Slicing — 4 Chained PRs (boundaries only; chain strategy decided by orchestrator)

| PR | Unit | Start / End | Depends on | Out of scope | Est. lines |
|----|------|-------------|-----------|--------------|------------|
| 1 | Bug fixes | L36 → English; dedupe both duplicated notes; PyPI note → git-tag path | — | Restructure, feature docs | ~40 |
| 2 | Restructure + extraction | TOC; reorder; 3 heading renames; extract `[tool.sofer]` → `docs/configuration.md`; extract contributor content → `CONTRIBUTING.md`; add `## Configuration` + `## Architecture summary` summaries | PR1 | Feature documentation, README_ES, sync policy | ~550-650 ⚠️ |
| 3 | Feature docs | `sofer-mcp` row (carry-forward #1); `## Flags at a glance` (carry-forward #2); format-table `prepare`/`publish` columns; `## Split detection`; `### Parquet conversion limitations`; `### Verify the built package (prepare --verify)` | PR2 | README_ES, sync policy | ~150 |
| 4 | README_ES + sync policy | `README_ES.md` (full); switcher lines in both files; AGENTS.md rule 13; PR-template checklist item | PR3 | — | ~320 |

Dependency order: **PR1 → PR2 → PR3 → PR4** (each targets `docs/readme-overhaul-es` chain; sync policy lands last so rule 13 references the final section inventory). PR2 exceeds the 400-line review budget because moving sections reads as delete+add in a diff; mitigation: it is mechanical (reviewers verify no-content-loss + link integrity), and the orchestrator may accept a `size:exception` for PR2 or let `auto-chain` split it into 2a restructure / 2b extraction — either way it stays within the 4-step intent. Total ≈ 1100-1200 changed lines (within the user's 2000-line budget).

## Carry-Forward Commitments (spec risk #4 — cannot silently drop)

1. **`sofer-mcp` row** in `## Command reference` (PR3): `| sofer-mcp | Launch the MCP server over stdio (10 tools, 3 resources, 3 prompts). Requires the mcp extra — see AI and MCP server. |` — also in README_ES (PR4).
2. **Flags glossary** `### Flags at a glance` (PR3): table of `--keep-csv` (publish; hf only), `--no-checks` (prepare), `--force` (prepare/publish/scan), `--dry-run` (publish/scan), `--output DIR` (prepare/publish/profile/render) with per-command semantics — also in README_ES (PR4).

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `README.md` | Modify | Restructure, TOC, bug fixes, summaries, feature docs (PR1-3); switcher line (PR4) |
| `README_ES.md` | Create | Mirrored Spanish README, English headings (PR4) |
| `docs/configuration.md` | Create | `[tool.sofer]` deep reference, moved verbatim + deduped (PR2) |
| `CONTRIBUTING.md` | Modify | + Architecture, Development setup, Development commands, PR sync bullet (PR2) |
| `AGENTS.md` | Modify | + rule 13 README/README_ES sync (PR4) |
| `.github/PULL_REQUEST_TEMPLATE.md` | Modify | + README_ES checklist item (PR4) |

## Interfaces / Contracts

No code interfaces. Doc contracts: (1) pinned anchor pairs above (README ↔ docs/configuration.md, README ↔ README_ES); (2) switcher line byte-identical in both files; (3) heading text identical between README.md and README_ES.md for translated sections.

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Regression | 795 existing tests | `uv run pytest tests/ -q` — must stay green (code untouched) |
| Structural verification | Spec scenarios (TC-09, §7.2) | Manual/scripted checks for docs (AGENTS.md rule 6 maps to verification, not pytest): anchors resolve, deep reference absent from README, SOFER_VERBOSE pointer present, mirrored headings diff README.md ↔ README_ES.md, `sofer-mcp` + glossary present |
| Quality | Markdown validity | `pyproject.toml` declares `readme = "README.md"` — must remain valid markdown; link-check TOC anchors |

## Migration / Rollout

No migration required — docs-only. Rollback: revert per-PR commits; `README_ES.md` is deletable; moved content recoverable from git history.

## Open Questions

- [ ] Badges / live HF dataset link / rendered codebook example (proposal bonus items): adopt in PR3 or defer?
- [ ] Chain strategy for the 4 slices (stacked vs feature-branch chain) — orchestrator decision.
- [ ] PR2 size: accept `size:exception` for the mechanical restructure+extraction, or split into 2a/2b?