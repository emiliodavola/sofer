# Proposal: README overhaul + README_ES.md (Spanish)

## Intent

README.md (501 lines) mixes three audiences (users, config power-users, contributors) with no navigation, carries confirmed content bugs, and under-documents shipped features (split detection, `--verify`, flag semantics). Spanish-speaking users are a stated audience with no localized entry point. This change makes the README user-first, moves deep reference to `docs/`, moves contributor content to `CONTRIBUTING.md`, documents real features, and adds a mirrored Spanish README under a bounded, enforced sync policy. Docs-only — no code, CLI, dependency, or test changes.

## Scope

### In Scope
- Fix bugs: L36 Spanish principle → English; dedupe "Behavior change" note and "Every value has a sensible default"; rephrase PyPI note to the git-tag install path (rot-proof).
- Restructure user-first: TOC (anchor links), order Install → Quick start → Typical workflow → Command reference → Data formats → Checks → Codebooks → AI/MCP → References; preserve Key principles verbatim.
- Extract `[tool.sofer]` deep reference (~L199–284) → new `docs/configuration.md`; README keeps short summary + link + one-line `SOFER_VERBOSE` troubleshooting pointer.
- Extract Architecture + Development into `CONTRIBUTING.md`; README keeps a short contributor pointer.
- Document: split detection (`splits.py` rules: keyword delimiting, filename/directory/shard sources, precedence); `--verify` on `prepare` (incl. `pip install datasets` opt-in, SKIPPED/PASSED/FAILED); flags glossary (`--keep-csv`, `--no-checks`, `--force`, `--dry-run`, `--output`); add `sofer-mcp` to the command reference; add prepare/publish columns to the format table; add Parquet type-conversion limitations (spec §7.2 — required by spec, currently undocumented).
- Create `README_ES.md`: language switcher in both files; neutral Spanish prose, technical content (commands, flags, TOML/YAML, CLI output, filenames, URIs) stays English; mirrored headings for user-facing sections; links to English `docs/configuration.md` and `CONTRIBUTING.md`.
- Sync policy: AGENTS.md rule + PR template checklist item (any change to a translated section updates `README_ES.md` in the same commit).

### Out of Scope
- Translating deep config/architecture (stays English in `docs/` / `CONTRIBUTING.md`).
- i18n/generation machinery; any code, CLI surface, dependency, or test change (no `datasets` extra — `pip install datasets` is documented only).
- Fixing pre-existing PKG-05 drift (spec wants `pip install sofer`; README truthfully documents git-tag installs — address when PyPI publishing lands).
- Bonus items: badges, live HF dataset link, rendered `codebook.md` example (cheap; fold in at design if wanted).

## Capabilities

### New Capabilities
None — no new product behavior; documentation and repo-process files only.

### Modified Capabilities
- `tool-config` (TC-09 "README documents discovery rules"): MODIFIED — the deep `[tool.sofer]` section relocates to `docs/configuration.md`; the requirement re-scopes to that file as the authoritative location, with the README linking to it. Delta spec required.

Notes: `parquet-conversion` §7.2 is fulfilled (not modified) by the new limitations section. `mcp-server`, `cli`, `packaging`, `tool-config` README-documentation requirements remain otherwise satisfied — content preserved or extended.

## Approach

Follow exploration Approach 2 (locked). Execute in 4 steps (one chained PR each): (1) bug fixes, (2) restructure + extraction, (3) feature documentation, (4) `README_ES.md` + sync policy. Preserve Key principles verbatim; keep the MCP section (verified accurate) and the `sofer upload` removal note. GitHub auto-generates anchors from mirrored headings, so TOC links work in both files.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `README.md` | Modified | Restructure, bug fixes, TOC, feature docs, format-table columns |
| `README_ES.md` | New | Mirrored Spanish translation, user-facing sections |
| `docs/configuration.md` | New | `[tool.sofer]` deep reference, moved verbatim |
| `CONTRIBUTING.md` | Modified | + Architecture, dev setup/commands |
| `AGENTS.md` | Modified | + README_ES sync rule |
| `.github/PULL_REQUEST_TEMPLATE.md` | Modified | + README_ES checklist item |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| README/README_ES sync drift | Med | Sync rule + PR checklist; mirrored headings expose drift in review |
| Review budget ~1450–1500 changed lines (vs 400 default) | High | Within user's 2000-line budget; still ship as 4 chained PRs |
| Content loss on extraction | Low | Explicit links from both READMEs; sections moved verbatim |
| PyPI note untruthful | Low | Keep git-tag wording (AGENTS.md rule 12) |
| Translation drift | Low | English technical terms by policy; neutral professional Spanish |

## Rollback Plan

Revert per-step commits; docs-only — no schema or data migration. `README_ES.md` is deletable, and moved content remains recoverable from git history (sections preserved verbatim in `docs/` / `CONTRIBUTING.md`).

## Dependencies

None (no code or dependency changes). `pip install datasets` is documented as a user opt-in for `--verify`, not a declared extra.

## Success Criteria

- [ ] All 4 bug fixes present; no duplicated blocks remain; PyPI note stays truthful.
- [ ] TOC links resolve; `[tool.sofer]` and contributor content removed from README and present in `docs/configuration.md` / `CONTRIBUTING.md` with links from both READMEs.
- [ ] Split detection, `--verify`, flags glossary, `sofer-mcp` row, format-table columns match source (`splits.py`, `verification.py`, `cli.py`).
- [ ] `README_ES.md` mirrors user-facing headings; switcher in both files; technical content in English.
- [ ] AGENTS.md rule + PR checklist item present; TC-09 delta spec drafted; 795 tests still pass (code untouched).