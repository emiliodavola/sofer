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

- [x] 2.1 `README.md`: add `## Table of Contents` (flat anchor bullets; top-level + `Flags at a glance`, `Parquet conversion limitations`, `Verify the built package` subsections). verify: every TOC anchor resolves. **Done** — TOC added; top-level bullets only (the 3 subsection bullets land with PR3 when those sections exist; task 2.1's "every anchor resolves" gate is what matters in PR2).
- [x] 2.2 `README.md`: reorder to the pinned spine (Install → Quick start → Why → Typical workflow → TOML reference → Directory layout → Profiling and rendering → Command reference → Data format support → Split detection → Validation and quality checks → Codebook generation → AI and MCP server → Configuration → Architecture summary → Related); add `## Quick start` (~6-line happy path init→scan→prepare→publish). verify: section order matches design. **Done** — spine matches design (Split detection is PR3); Quick start = init→scan→prepare→publish.
- [x] 2.3 `README.md`: rename 3 headings for clean anchors — `Profiling and rendering`, `Semantic types and PII detection`, `Validation and quality checks` (drop `&`/`/`/parens). verify: no ambiguous double-hyphen slugs. **Done** — 4 renames incl. `AI and MCP server`; anchors verified against the GitHub slug rule (no double-hyphen slugs).
- [x] 2.4 Create `docs/` + `docs/configuration.md`: move `[tool.sofer]` deep reference verbatim with pinned anchors (Discovery and precedence; Bootstrap keys (cwd-only); Seeing which file was used; Metadata inference tuning) + single canonical editable-install/sensible-default copies. verify: content matches README pre-move (no content loss). **Done** — all 80 deep-ref lines verified present (0 missing); canonical copies single (PR1 dedup held).
- [x] 2.5 `README.md`: remove deep reference; add `## Configuration` summary (precedence one-liner, link → `docs/configuration.md#discovery-and-precedence`, one-line `SOFER_VERBOSE` pointer → `#seeing-which-file-was-used`). verify: TC-09 scenarios — authoritative link, no deep ref in README, verbosity pointer survives. **Done** — TC-09 scenarios 1–3 satisfied (verified programmatically + rendered).
- [x] 2.6 `CONTRIBUTING.md`: add `Development setup`, `Development commands`, `Architecture` (module tree verbatim + 2-line orientation). verify: sections present, tree verbatim. **Done** — tree (25 lines) + commands (3) + setup block verified verbatim; existing 62-line content preserved.
- [x] 2.7 `README.md`: remove Architecture tree + Development setup/commands; add `## Architecture summary` (2–3 lines) + contributor pointer → `CONTRIBUTING.md#architecture`. verify: moved content exists in CONTRIBUTING.md and links resolve. **Done** — sections removed from README (leftover check empty), links to CONTRIBUTING.md#architecture + CONTRIBUTING.md resolve.

## Phase 3 (PR3): Feature documentation

- [x] 3.1 `README.md` `## Command reference`: add `sofer-mcp` row (carry-forward #1, exact text from design; `sofer upload` removal note kept). verify: row matches design verbatim. **Done** — row added verbatim (README L250); formatted as a separate console-script entry point (`pyproject.toml` `[project.scripts] sofer-mcp = "sofer.mcp_server:main"`), no `<args>`; `upload`-removal note kept.
- [x] 3.2 `README.md`: add `### Flags at a glance` glossary (carry-forward #2 — `--keep-csv`, `--no-checks`, `--force`, `--dry-run`, `--output` with per-command semantics). verify: semantics match `cli.py`. **Done** — all 5 rows verified against cli.py: `--keep-csv` publish/hf-only (no effect with `--target local`, PUB-07); `--no-checks` prepare (`run_checks=not args.no_checks`); `--force` prepare/publish/scan (overwrite + skip confirmation); `--dry-run` publish/scan (no network/copy/TOML write); `--output DIR` prepare/publish/profile/render (design's list; `codebook` also accepts `--output` — noted, kept out of the carry-forward list).
- [x] 3.3 `README.md` `## Data format support`: add prepare/publish columns to the format table. verify: columns match `_formats.py`. **Done** — rows unchanged (CSV/TSV/Parquet/Excel/JSONL = `SUPPORTED_FORMATS` keys); `prepare`/`publish` columns + footnote (CSV→Parquet unless `upload_as_csv`; other formats staged as-is; publish delivers unchanged) verified against prepare.py conversion loop.
- [x] 3.4 `README.md`: add `### Parquet conversion limitations` (spec parquet-conversion §7.2 content). verify: §7.2 limitations documented. **Done** — three §7.2 gaps (comma-as-decimal, mixed-type >50 %, >2 GB strings) in a pattern/workaround table; fallback wording updated to the current prepare flow (warning + stage CSV as-is).
- [x] 3.5 `README.md`: add `## Split detection` (keyword delimiting rule, filename/directory/shard sources, precedence). verify: matches `splits.py`. **Done** — keywords, delimiting rule (`test-file.csv` vs `testfile.csv`), directory → filename → shard (`-NNNNN-of-NNNNN`, ≥2 buckets) → single-train fallback cascade, exclusions (README.md/LICENSE/.gitattributes/.gitignore), HF-viewer `train` note.
- [x] 3.6 `README.md` under `Validation and quality checks`: add `### Verify the built package (prepare --verify)` (SKIPPED/PASSED/FAILED, `pip install datasets` opt-in). verify: matches `verification.py`/`cli.py`. **Done** — end-to-end `load_dataset()` on the build dir, SKIPPED when optional `datasets` is absent (install hint), PASSED/FAILED + split comparison, non-blocking (prepare.py step 10, PRP-08).
- [x] 3.7 Optional bonus (badges under tagline above TOC, live HF dataset link, rendered codebook example): adopt or defer. verify: if adopted, placement per design D7 and mirrored in ES (PR4). **Done — badges ADOPTED** (CI: `ci.yml` exists; License: LICENSE + `license = "MIT"`; Python: `requires-python = ">=3.10"` static badge — no PyPI dynamic badge since sofer is unpublished). Live-HF-link + rendered-codebook bonuses DEFERRED (not determinable without inventing). PR4 MUST mirror the badge block into README_ES.md.

## Phase 4 (PR4): README_ES.md + sync policy

- [x] 4.1 Create `README_ES.md`: mirrored user-facing headings + TOC (English headings, neutral Spanish prose; commands, flags, TOML/YAML, CLI output, filenames, URLs stay English); links to English `docs/configuration.md` + `CONTRIBUTING.md` with "technical docs are in English" note. verify: heading tree identical to README.md. **Done** — heading tree 32/32 identical (fence-aware compare), TOC 19/19 byte-identical, badge block verbatim; prose in neutral professional Spanish; technical tokens + all code blocks (incl. comments) English; Configuration + Architecture summary link to English docs with the note.
- [x] 4.2 Both files: add switcher line byte-identical after H1 — `**[English](README.md) | [Español](README_ES.md)**`. verify: line identical in README.md and README_ES.md. **Done** — present exactly once in each file, byte-identical, immediately after the H1 (before the tagline, per design tree).
- [x] 4.3 `README_ES.md`: carry `sofer-mcp` row + flags glossary (English). verify: rows match README.md. **Done** — `sofer-mcp` row verbatim vs README L250; Flags at a glance table 10/10 lines byte-identical (programmatic Compare-Object).
- [x] 4.4 `AGENTS.md`: add rule 13 (README/README_ES sync) with exact text from design. verify: rule 13 present verbatim. **Done** — rule 13 verbatim vs design.md L99-106 (header + 2 bullets, byte-compared).
- [x] 4.5 `.github/PULL_REQUEST_TEMPLATE.md` `## Checklist`: add `- [ ] README_ES.md updated if a translated README section changed` after "README updated if CLI surface changed". verify: item present. **Done** — item inserted directly after the README item, before "Related issues linked".
- [x] 4.6 Final: mirrored-heading diff README.md ↔ README_ES.md; confirm `pyproject.toml` `readme = "README.md"` unchanged. verify: translated-section heading diff empty; packaging untouched. **Done** — heading diff EMPTY (32/32, same order, same level); `pyproject.toml` L5 `readme = "README.md"` unchanged; `uv run pytest tests/ -q` → **886 passed, 2 skipped** (docs-only, no code touched).