# Exploration: README overhaul + README_ES.md (Spanish)

> Change: `readme-overhaul-es` — GitHub issue #69.
> Exploration performed against `dev` HEAD (branch `docs/readme-overhaul-es`), 2026-08-28.
> Artifact mode: hybrid (OpenSpec + Engram).

## Purpose

Validate and refine GitHub issue #69 ("docs: overhaul README.md and add README_ES.md (Spanish)") against the current on-disk README (501 lines) and the actual source code, then recommend a concrete change scope. The change has locked decisions (language switcher, neutral Spanish with English technical content, sync policy, mirrored structure, user-docs-only translation scope) that the recommendation must honor.

## Current State

`README.md` (501 lines) is a single-file, single-audience document that actually serves three audiences — end users, config power-users, and contributors — with no navigation. Verified facts:

**Confirmed content bugs (issue was accurate):**

1. **Spanish principle in the English README** — L36 in the "Key principles" list: `**Automatizar observaciones; no inventar conocimiento semántico.**`. Must be "Automate observations; don't invent semantic knowledge."
2. **Duplicated "Behavior change for editable installs"** — L224–228 and L279–282 carry the same note with slightly different wording (both confirmed on disk).
3. **Duplicated "Every value has a sensible default — the whole section is optional."** — L201–202 and L284 (confirmed).
4. **"It is not published on PyPI yet" (L12–13)** — ACCURATE TODAY: the release workflow (`.github/workflows/release.yml`, AGENTS.md rule 12) explicitly has no PyPI publishing, and the archived change `2026-08-26-installable-cli-pypi` was about `--version` resolution and console-script installability, not PyPI publication. Still a forward-staleness risk the moment PyPI publication is added — the note needs a formulation that documents the git-tag install path without asserting a negative that can rot.

**Confirmed structural problems:**

- **No TOC** in a 501-line file.
- **Audience mixing**: "Development setup" (L50–57, contributor concern) sits before "Typical workflow" (L59–88, user concern).
- **Deep config reference in the main README**: the `[tool.sofer]` section (L199–284, ~86 lines) covers discovery & precedence, bootstrap keys, `SOFER_VERBOSE`, and inference tuning — power-user reference material.
- **Contributor content in the user README**: Architecture (L460–488) and Development (L490–496). `CONTRIBUTING.md` already exists (62 lines: getting started, conventions, PRs, testing) but has NO architecture section — it is the natural home.
- **"Data format support" table (L306–312)** covers only `scan`/`codebook`/`profile` — no `prepare`/`publish` columns (confirmed gap).

**Confirmed undocumented features (all verified in source via codegraph):**

1. **Split detection** — `src/sofer/splits.py`. `detect_split_keyword` enforces the HF delimiting rule: `test-file.csv` matches, `testfile.csv` does not (splits on non-word chars). Detection sources: filenames, directory names, shard names (`train-00001-of-00005.parquet`). Directory detection wins over filename; shard detection requires ≥2 splits to fire. Canonical names: `train`/`validation`/`test`. `detect_splits` has 21 callers across `prepare.py`, `publish.py`, `verification.py`. README mentions it only as one line in the architecture tree (L485).
2. **`--verify` on `prepare`** — `src/sofer/verification.py` + `cli.py:523-529`. Runs `datasets.load_dataset()` against the generated package and prints PASSED/FAILED (non-blocking, exit code unaffected). The `datasets` dependency is optional via an `ImportError` guard (verification.py:65-75) that returns a SKIPPED report with an informational message. **Refinement found**: `datasets` is NOT declared as an optional-dependency extra in `pyproject.toml` (only `mcp = ["fastmcp>=3.4,<4"]` exists) — "optional" means "guarded import, not a dependency". The README must tell users `pip install datasets` to enable `--verify` (verification.py:73 literally prints this instruction).
3. **Flag semantics** — all confirmed against argparse help in `cli.py`:
   - `--no-checks` (prepare): skip the structural + quality validation report (checks run by default and are non-blocking).
   - `--force`: prepare → overwrite existing generated artifacts; publish → skip overwrite protection on the remote; scan → overwrite existing cache files.
   - `--keep-csv` (publish): upload the original CSV alongside the converted Parquet (hf target only; documented in code as having no effect on the local target, publish.py:630).
   - `--dry-run`: publish → print repo diff + split report without preparing, copying, or touching the network; scan → report what would be done without modifying disk or TOML.
   - `--output`: prepare/publish/profile/render (defaults: `[dataset] build_dir` / dataset dir).

**MCP section quality (NEW since issue creation — PR #71):**

- The "AI / MCP server" section (L378–458) is **accurate against code**: `mcp` extra + `sofer-mcp` script entry confirmed in `pyproject.toml` (`[project.scripts] sofer-mcp = "sofer.mcp_server:main"`); 10 tools / 3 resources / 3 prompts match `mcp_server.py`; path containment, fail-closed publish authorization, and approval-phrase hardening match the archived `2026-08-28-sofer-mcp-server` spec. Content quality is good — no rewrite needed.
- **Confirmed gap**: the command reference table (L286–299) does NOT list `sofer-mcp`. A CLI-surface table that omits a shipped console script is incomplete.

**What the issue missed or underweighted (refinements):**

1. `datasets` is not an extra — document `pip install datasets`; don't let "optional dependency" be read as "declared extra".
2. `SOFER_VERBOSE` (L245–253) is documented only inside the deep config section; when that section moves to `docs/`, the README should keep a one-line troubleshooting pointer.
3. The "Key principles" block (L34–48) is high-quality and must survive the restructure verbatim (with the L36 translation fix).
4. The "`sofer upload` was removed" note (L301–302) is a useful historical pointer for users of older versions — keep it near the command reference.
5. `pyproject.toml` declares `readme = "README.md"` — the overhaul must keep README.md valid markdown; `README_ES.md` is not referenced by packaging.
6. Sync-policy insertion points exist and are cheap: AGENTS.md rule 7 (L48, "README must reflect the current CLI interface") and the PR template checklist item "README updated if CLI surface changed" — both get a README_ES companion.
7. Review-budget risk: a 501-line restructure plus a new ~300-line `README_ES.md` far exceeds the 400-line review budget; the issue's 4-step execution order maps naturally to chained PRs.

## What Was Explored

- `README.md` (501 lines) — full read, line-level confirmation of every issue claim.
- `gh issue view 69` — full plan, locked decisions, alternatives considered.
- `src/sofer/splits.py` — split detection algorithm, keyword delimiting rule, detection precedence (via codegraph).
- `src/sofer/verification.py` — `verify_load_dataset`, optional-`datasets` guard, pass/skip/fail reporting (via codegraph).
- `src/sofer/cli.py` — `_cmd_prepare`, `_cmd_publish`, `_build_parser` argparse help for every flag in scope (via codegraph).
- `src/sofer/prepare.py` / `publish.py` — verify wiring (`prepare`→`verify_load_dataset` call path), `--keep-csv` local-target no-op.
- `src/sofer/mcp_server.py` + archived `2026-08-28-sofer-mcp-server` spec — MCP section accuracy audit.
- `pyproject.toml` — extras, scripts, dependencies.
- `CONTRIBUTING.md` (62 lines) — exists, no architecture section; natural home for contributor content.
- `openspec/` — hybrid mode initialized (config.yaml, 20 archived changes); `openspec/changes/readme-overhaul-es/` created by this phase.
- Archived `2026-08-26-installable-cli-pypi` change — PyPI status context.

## Approaches

1. **Full 1:1 translation (all sections, including deep config and architecture)**
   - Pros: maximal Spanish coverage.
   - Cons: doubles maintenance cost; the two files desynchronize quickly; deep config/architecture content is rarely read in Spanish; violates the locked decision.
   - Effort: High. **Rejected (locked decision).**

2. **User-docs-only translation, mirrored structure (recommended, locked)**
   - Pros: covers ~90% of value for Spanish-speaking users; mirrored headings keep sync cost bounded (a section updated in one file is easy to spot as missing in the other); GitHub auto-generates anchors from headings so TOC links work in both files without manual anchor maintenance.
   - Cons: Spanish users who need the deep `[tool.sofer]` reference must read English docs (mitigated by linking `docs/configuration.md` from both READMEs).
   - Effort: Medium.

3. **Single English source of truth in `docs/` + generated translations**
   - Pros: one source of truth, no manual sync.
   - Cons: i18n build machinery (translation tooling, generation step) is heavier than warranted for a two-language repo; breaks the "README is the entry point" convention.
   - Effort: High. **Rejected (locked decision).**

4. **English restructure only, no `README_ES.md`**
   - Pros: smallest change; zero translation risk.
   - Cons: Spanish-speaking users are a stated project audience; the issue explicitly rejected this.
   - Effort: Low. **Rejected (locked decision).**

## Recommendation (change scope)

Proceed with Approach 2, structured as the issue's 4 execution steps. The change WILL:

- **Fix content bugs**: translate the L36 principle to English; deduplicate the "Behavior change for editable installs" note and the "Every value has a sensible default" line (keep one canonical copy each); rephrase the PyPI note to document the git-tag install path without a rot-prone negative (e.g. "Install from the release tag — see Releases") — accurate today (no PyPI publishing in the release workflow) and stable if PyPI arrives.
- **Restructure `README.md` user-first**: add a TOC (manual anchor links); reorder Install → Quick start → Typical workflow → Command reference → Data formats → Checks → Codebooks → AI/MCP → References; preserve the "Key principles" block verbatim (with fix).
- **Extract deep reference**: move the `[tool.sofer]` reference (~L199–284) to a new `docs/configuration.md`, link from both READMEs; keep a one-line `SOFER_VERBOSE` troubleshooting pointer in the README.
- **Extract contributor content**: move Architecture + Development setup + Development commands into `CONTRIBUTING.md` (which exists); leave a short contributor pointer in the README.
- **Document real features**: add a Split detection section (keyword delimiting rule, filename/directory/shard sources, precedence); explain `--verify` on `prepare` including the `pip install datasets` opt-in and SKIPPED/PASSED/FAILED output; add a flags glossary covering `--keep-csv`, `--no-checks`, `--force`, `--dry-run`, `--output`.
- **Close the CLI-surface gap**: add `sofer-mcp` to the command reference table (and keep the `sofer upload` removal note).
- **Extend the Data format support table** with `prepare`/`publish` columns.
- **Create `README_ES.md`**: language switcher at the top of BOTH files (`[English](README.md) | [Español](README_ES.md)`); neutral Spanish prose with English technical content (commands, flags, TOML/YAML excerpts, CLI output, filenames never translated); mirrored headings/structure for user-facing sections only; links to the English `docs/configuration.md` and `CONTRIBUTING.md` for deep content.
- **Enforce sync**: add an AGENTS.md rule (extend rule 7 or a new rule: any README change touching a translated section MUST update `README_ES.md` in the same commit) and a matching PR template checklist item.

The change WILL NOT:

- Translate deep config reference, architecture, or contributor content into Spanish (stays English in `docs/` / `CONTRIBUTING.md`).
- Add i18n/generation machinery.
- Change any code, CLI surface, `pyproject.toml` dependencies, or tests (this is a docs-only change; no new `verify`/`datasets` extra is introduced — `pip install datasets` is documented instead).
- Include the non-blocking bonus items by default (badges, quick-start with expected output, rendered `codebook.md` example, live HF dataset link) — they are cheap and can be folded in at proposal/design if the orchestrator wants them, but they are not part of the core scope.

## Risks

- **Sync drift between README.md and README_ES.md over time** — the main risk; mitigated by the locked sync policy (AGENTS.md rule + PR template checklist item) and by mirrored structure making drift visible in review.
- **Review budget**: restructure (~501 lines rewritten) + new `README_ES.md` (~300 lines) exceeds the 400-line review budget. The 4-step execution order should be delivered as chained PRs (bug fixes → restructure → feature docs → README_ES). Flag for `sdd-tasks` forecast.
- **Anchor fragility**: TOC links depend on GitHub's auto-generated heading anchors; headings must be mirrored exactly between files and the language-switcher line must not break anchor generation (it won't — it is not a heading).
- **Content loss during extraction**: moving `[tool.sofer]` and contributor content risks losing visibility; mitigated by explicit links from both READMEs.
- **PyPI note rephrase**: must stay truthful with the current tag-driven release flow (AGENTS.md rule 12 — no PyPI publishing; don't imply PyPI exists).
- **CLI/README drift (doubled surface)**: AGENTS.md rule 7 already requires README sync with the CLI; with two READMEs the sync surface doubles — the AGENTS.md rule must explicitly cover both files.
- **Translation quality**: neutral Spanish with English technical terms requires care to avoid invented terminology drift; technical terms stay English by policy.

## Ready for Proposal

Yes. The issue's plan is validated against the current file and code; refinements (datasets-not-an-extra, SOFER_VERBOSE pointer, `sofer-mcp` table gap, CONTRIBUTING.md as contributor home, chained-PR delivery) are captured above. The orchestrator should proceed to `sdd-propose` with the WILL/WON'T scope and the locked decisions as-is.