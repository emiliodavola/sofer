# Feature: curation-rationale-key — issue #324

- **Issue:** [#324](https://github.com/emiliodavola/sofer/issues/324) — `feat(card): Curation Rationale needs a file - give it a free-text [meta] key`
- **Branch:** `feat/324-curation-rationale-key` from `dev@5249be6` · **Change:** `openspec/changes/archive/2026-10-16-feat-curation-rationale-key/`
- **Spec of record:** `openspec/specs/repo-compliance/spec.md` §2.1.1 / §2.1.2. This file is the working plan behind it.

## Goal

`### Curation Rationale` was the only Dataset Card section whose sole fill path was `[meta] study_design`
— a *path* to a markdown file whose content the caller resolves — while every neighbouring narrative
section takes a plain multi-line string. A user with three paragraphs of rationale and nothing else to
say had to author a file. This change adds the free-text key the issue asks for, in front of that
existing path.

The issue is the follow-up its own predecessor recorded: `odd/tasks/card-section-keys.md` D4 and
`2026-10-16-feat-card-section-keys/archive-report.md` §6.

## Specs

S1 (issue #324 §"Proposed solution" 1, verbatim): "**A `curation_rationale` free-text `[meta]` key**, used when set and falling back to `study_design_content` and then to the sentinel. One field, one site, and the existing path keeps working — no migration, and a config that declares neither is unchanged."

S2 (issue #324 §"Proposed solution" 1, verbatim): "If option 1 lands, the sentinel constant (`_MORE_INFO`) and the \"one sentinel site\" test in `tests/test_repo_compliance.py` both need updating, which is exactly what that test exists to force."

S3 (issue #324 §"Problem", verbatim): "`study_design` is a **path**, not a value: the user must author a markdown file and point `[meta]` at it before this one section fills. Every neighbouring section takes a plain multi-line string."

S4 (issue #324 §"Proposed solution" 2, verbatim — **rejected**): "**Or drop the indirection** and let `study_design` accept inline text as well as a path — rejected as a first option because it makes one key mean two things."

S5 (issue #324 §"Proposed solution" 3, verbatim): "**Or keep it and say so** in the spec and README: \"Curation Rationale is filled by `[meta] study_design`, a file\". Cheapest, and honest — the current text is in the spec but nowhere a user writing a TOML would look."

S6 (the clause this change replaces — `openspec/specs/repo-compliance/spec.md` §2.1.2 before the change, verbatim): "`### Curation Rationale` SHALL continue to be filled by `[meta] study_design`, whose content the caller resolves; it has no free-text key of its own."

S7 (the clause as amended, verbatim): "`### Curation Rationale` SHALL be filled by `[meta] curation_rationale` when that key holds non-whitespace content, otherwise by the resolved content of the file `[meta] study_design` points at, otherwise by that section's placeholder. The key SHALL win over the file, so declaring both is unambiguous. When `curation_rationale` is absent the branch taken SHALL be the pre-#324 one unchanged."

## Decisions not in the issue

| # | Decision | Rationale / evidence |
| --- | --- | --- |
| D1 | Option 1 — the free-text key, with the file kept as the fallback. | S1's own text. Option 2 (S4) makes one key mean two things; option 3 (S5) is delivered as a by-product, because the amended clause and §2.1.1 now say it where a TOML author looks. |
| D2 | The key wins over the file when both are declared. | S1 says "used when set and falling back to" — a defined order, not a merge. Pinned by `test_the_key_wins_over_the_study_design_file`. |
| D3 | A whitespace-only `study_design` file keeps its pre-#324 outcome — an empty section, not the sentinel. | The issue asks for one new key, not for a change to the file path's existing edge. `.strip()` decides *which source wins*; a resolved file's content is appended exactly as before. No existing test pinned this edge; the new one documents the choice. |
| D4 | No `sofer init` template change, no README change. | The five #291 keys are not in the template either, and `README.md:194` delegates the full key set to §2.1.1, which this change updates. Rule 13 is therefore not triggered — no README section changed. |
| D5 | This change is **not** ad-hoc: it carries an `openspec/changes/` folder. | The test in `odd/tasks/bug-chore-followups.md` D1 is "does the change touch a spec'd clause?". It does — S6 — and #291's own D4 was recorded against that clause. Same shape as `2026-10-16-feat-card-section-keys`. |
| D6 | The feature document was written **after** the first source edit. | A deviation from `odd/README.md` ("written before the first source edit"), caused by a stalled reconnaissance subagent (L5). The code was RED→GREEN before this file existed; nothing in it claims otherwise. |

## Tasks

| ID | Task | Spec | Route | State | Commit |
| --- | --- | --- | --- | --- | --- |
| T1 | Branch `feat/324-curation-rationale-key` off `dev@5249be6` | — | git | done | — |
| T2 | RED: 7 tests for the key, the precedence, the whitespace edges and the TOML round trip | S1 S2 S3 | inline, test-first | done | `3b90af3` |
| T3 | `model.py`: the `curation_rationale` field + its `from_toml` read | S1 | inline | done | `3b90af3` |
| T4 | `repo_compliance.py`: the three-arm chain; `_MORE_INFO` stays at four sites | S1 S2 S7 | inline | done | `3b90af3` |
| T5 | Canonical §2.1.1/§2.1.2 + this change's delta, removing the clause sentence that asserted the opposite | S6 S7 | inline | done | `3b90af3` |
| T6 | Gates: full suite, collection delta, ruff/format/mypy/pyright, test-mapping checker | — | inline | done | `3b90af3` |
| T7 | Archive inside the delivery branch (rule 15) | — | inline | done | `3b90af3`, this folder |
| T8 | Push the branch; assign the issue; leave the PR to the maintainer's authorization | — | git/gh | done | `origin/feat/324-curation-rationale-key` == `3b90af3`; #324 assigned to `emiliodavola` |

## Close-out

| Gate | Result |
| --- | --- |
| Full suite | **2247 passed, 9 skipped** (86.44 s) |
| Collection delta vs `dev@5249be6` | 2249 → 2256 collected (**+7** = the 7 new tests) |
| ruff check / format (`src/ tests/`) | `All checks passed!` / `75 files already formatted` |
| mypy (`src/ scripts/`, py3.13) / pyright | 0 errors / 0 errors (1 pre-existing `tomli` warning) |
| Test-mapping contract | `OK` |
| rule-14 per-file 100.00% gates | **not run** — no edit to `cli.py`/`scanner.py`/`prepare.py`/`publish.py`, and no test here executes their lines |
| `ruff format --check .` (bare) | red **before and after** on `README.md`/`README_ES.md` (pre-existing drift CI never sees). Out of scope |

## Log

L1 (user, verbatim, 2026-10-16): "buenas\n\n- usá ODD\n- revisá los issues pendientes, chequeá que lo propuesto tenga sentido y no haya sido implementado\n- armá un roadmap de implementación\n- definí prioridades\n- comentame cuán costoso es el proceso de implementación"

L2 (user, verbatim): "1. Arrancá con #324\n2. arreglalo antes de comenzar si corresponde"

L3 (evidence, recon): the four open issues (#320, #322, #323, #324) were each checked against the code and **none** was implemented. For #324: no `curation_rationale` token anywhere under `src/`, `repo_compliance.py:1835` branching on `study_design_content` alone, and S6 still live in the spec.

L4 (evidence, repo state): the fast-forward the roadmap note asked for had already happened — `dev` == `origin/dev` == `5249be6`, worktree clean, no open PRs, no open `openspec/changes/`. L2's second item had nothing to repair.

L5 (incident): a `gentle-ai-explore` subagent tasked with mapping all four issues' change surface **stalled 30 minutes inside `codegraph`** and was killed by its timeout. The mapping was done inline instead. Consequence: this file was written after the first source edit (D6).

L6 (evidence, RED→GREEN): with the tests written and the source untouched, `pytest -q -k "CurationRationale or CardSectionKeys"` → **7 failed, 11 passed**, every failure an `AttributeError`/`TypeError` on the missing field. After T3+T4: **21 passed**.

L7 (decision): S6 could not be extended in place — it asserted the opposite of the new behaviour. The #291 paragraph now keeps its five keys and delegates Curation Rationale to a new clause owning both fill paths. Leaving both sentences would have put a false statement in the spec of record.

L8 (finding, pre-existing, out of scope): `uv run ruff format --check .` fails on `README.md:166` and `README_ES.md:174` — comment alignment in the MCP example block — on `dev` before and after this change. CI's gate is scoped to `src/ tests/`, which is why it is green.

L9 (evidence, delivery): committed as **`3b90af3`** — `11 files changed, 652 insertions(+), 12 deletions(-)` — with all four pre-commit hooks `Passed` (`ruff`, `ruff-format`, `mypy`, `pyright`). Pushed to `origin/feat/324-curation-rationale-key` (remote SHA verified equal to local). Issue #324 assigned to `emiliodavola`. **The pull request was deliberately not opened**: publishing is the maintainer's call, and it stays pending.`
