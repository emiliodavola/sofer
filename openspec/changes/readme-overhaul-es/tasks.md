# Tasks: README overhaul + README_ES.md (Spanish)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1100–1200 total (PR1 ~40; PR2 ~550–650; PR3 ~150; PR4 ~320) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR1 → PR2 → PR3 → PR4 (feature-branch chain) |
| Delivery strategy | auto-forecast (resolved by forecast) |
| Chain strategy | feature-branch-chain (tracker: `docs/readme-overhaul-es`) |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

PR2 exceeds the 400-line default (mechanical move, reads as delete+add); accepted under the user's 2000-line ceiling — fallback: split into 2a restructure / 2b extraction.

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Bug fixes (L36, dedupe ×2, PyPI note) | PR1 | base `docs/readme-overhaul-es`; pytest stays green |
| 2 | Restructure + extraction (TOC, reorder, renames, `docs/configuration.md`, CONTRIBUTING) | PR2 | base = PR1 branch; no-content-loss + link review |
| 3 | Feature docs (sofer-mcp row, flags glossary, format columns, split detection, Parquet limits, `--verify`) | PR3 | base = PR2 branch; verify against `src/sofer/` |
| 4 | README_ES.md + switcher + AGENTS.md rule 13 + PR-template item | PR4 | base = PR3 branch; mirrored-heading diff review |

## Phase 1 (PR1): Bug fixes

- [x] 1.1 `README.md` `## Why`: fix L36 Spanish principle → English (Key principles kept verbatim). verify: rendered README shows English text.
- [x] 1.2 `README.md`: delete duplicate "Behavior change for editable installs" note and second "Every value has a sensible default" line (canonical copies move in PR2). verify: no duplicated blocks remain.
- [x] 1.3 `README.md` `## Install`: rephrase PyPI note to the git-tag install path (AGENTS.md rule 12, rot-proof). verify: no negative/rot-prone PyPI wording.
- [x] 1.4 Baseline: run `uv run pytest tests/ -q`. verify: 795 tests still pass (code untouched).

## Phase 2 (PR2): Restructure + extraction

- [ ] 2.1 `README.md`: add `## Table of Contents` (flat anchor bullets; top-level + `Flags at a glance`, `Parquet conversion limitations`, `Verify the built package` subsections). verify: every TOC anchor resolves.
- [ ] 2.2 `README.md`: reorder to the pinned spine (Install → Quick start → Why → Typical workflow → TOML reference → Directory layout → Profiling and rendering → Command reference → Data format support → Split detection → Validation and quality checks → Codebook generation → AI and MCP server → Configuration → Architecture summary → Related); add `## Quick start` (~6-line happy path init→scan→prepare→publish). verify: section order matches design.
- [ ] 2.3 `README.md`: rename 3 headings for clean anchors — `Profiling and rendering`, `Semantic types and PII detection`, `Validation and quality checks` (drop `&`/`/`/parens). verify: no ambiguous double-hyphen slugs.
- [ ] 2.4 Create `docs/` + `docs/configuration.md`: move `[tool.sofer]` deep reference verbatim with pinned anchors (Discovery and precedence; Bootstrap keys (cwd-only); Seeing which file was used; Metadata inference tuning) + single canonical editable-install/sensible-default copies. verify: content matches README pre-move (no content loss).
- [ ] 2.5 `README.md`: remove deep reference; add `## Configuration` summary (precedence one-liner, link → `docs/configuration.md#discovery-and-precedence`, one-line `SOFER_VERBOSE` pointer → `#seeing-which-file-was-used`). verify: TC-09 scenarios — authoritative link, no deep ref in README, verbosity pointer survives.
- [ ] 2.6 `CONTRIBUTING.md`: add `Development setup`, `Development commands`, `Architecture` (module tree verbatim + 2-line orientation). verify: sections present, tree verbatim.
- [ ] 2.7 `README.md`: remove Architecture tree + Development setup/commands; add `## Architecture summary` (2–3 lines) + contributor pointer → `CONTRIBUTING.md#architecture`. verify: moved content exists in CONTRIBUTING.md and links resolve.

## Phase 3 (PR3): Feature documentation

- [ ] 3.1 `README.md` `## Command reference`: add `sofer-mcp` row (carry-forward #1, exact text from design; `sofer upload` removal note kept). verify: row matches design verbatim.
- [ ] 3.2 `README.md`: add `### Flags at a glance` glossary (carry-forward #2 — `--keep-csv`, `--no-checks`, `--force`, `--dry-run`, `--output` with per-command semantics). verify: semantics match `cli.py`.
- [ ] 3.3 `README.md` `## Data format support`: add prepare/publish columns to the format table. verify: columns match `_formats.py`.
- [ ] 3.4 `README.md`: add `### Parquet conversion limitations` (spec parquet-conversion §7.2 content). verify: §7.2 limitations documented.
- [ ] 3.5 `README.md`: add `## Split detection` (keyword delimiting rule, filename/directory/shard sources, precedence). verify: matches `splits.py`.
- [ ] 3.6 `README.md` under `Validation and quality checks`: add `### Verify the built package (prepare --verify)` (SKIPPED/PASSED/FAILED, `pip install datasets` opt-in). verify: matches `verification.py`/`cli.py`.
- [ ] 3.7 Optional bonus (badges under tagline above TOC, live HF dataset link, rendered codebook example): adopt or defer. verify: if adopted, placement per design D7 and mirrored in ES (PR4).

## Phase 4 (PR4): README_ES.md + sync policy

- [ ] 4.1 Create `README_ES.md`: mirrored user-facing headings + TOC (English headings, neutral Spanish prose; commands, flags, TOML/YAML, CLI output, filenames, URLs stay English); links to English `docs/configuration.md` + `CONTRIBUTING.md` with "technical docs are in English" note. verify: heading tree identical to README.md.
- [ ] 4.2 Both files: add switcher line byte-identical after H1 — `**[English](README.md) | [Español](README_ES.md)**`. verify: line identical in README.md and README_ES.md.
- [ ] 4.3 `README_ES.md`: carry `sofer-mcp` row + flags glossary (English). verify: rows match README.md.
- [ ] 4.4 `AGENTS.md`: add rule 13 (README/README_ES sync) with exact text from design. verify: rule 13 present verbatim.
- [ ] 4.5 `.github/PULL_REQUEST_TEMPLATE.md` `## Checklist`: add `- [ ] README_ES.md updated if a translated README section changed` after "README updated if CLI surface changed". verify: item present.
- [ ] 4.6 Final: mirrored-heading diff README.md ↔ README_ES.md; confirm `pyproject.toml` `readme = "README.md"` unchanged. verify: translated-section heading diff empty; packaging untouched.