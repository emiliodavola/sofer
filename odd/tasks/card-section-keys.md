# Feature: card-section-keys — issue #291

**Branch:** `feat/291-card-section-keys` from `dev@6786ba1`. **Issue:** `emiliodavola/sofer#291`
**Delivery PR:** (this PR) → `dev`. **SDD change:** `openspec/changes/<date>-feat-card-section-keys/`
(archived inside this PR, AGENTS.md rule 15). **Milestone:** v0.6.0.
**Risk:** low — additive fields; every config that does not declare them is unchanged.

## Goal

`build_dataset_card()` hardcoded five sections to a sentinel, and no TOML key or tool argument could
fill them. A config with every ROTW field filled still shipped `[More Information Needed]` ×4 and
`[Not specified]` ×2, with `ok: true` on every MCP call — so an agent following the advertised flow to
the letter produced a card that read as unfinished, and the only way to notice was to read the output.

## Specs

S1 (issue #291 §"Proposed solution" 2, verbatim): "**Add the keys** so the generator can fill them:
`repository`, `direct_use`, `out_of_scope_use`, `bias_risks_limitations`, `contact` (multi-line
strings), plus `study_design` promoted from the documented-but-obscure path to the obvious one."

S3 (issue #291 §"Proposed solution" 3, verbatim): "**Compose from what exists** where possible:
`- **Repository:**` could fall back to the `source` value or a new `source_url`, rather than a bare
sentinel."

S7 (issue #291 §"Evidence", verbatim): "Config with every ROTW field filled — description, license,
confidential, source, tags, language, pretty_name, task_categories, size_categories, collection_method,
citation — and a placeholder-free TOML. `grep -c 'TODO'` on the generated card: 0. `grep -c
'\[More Information Needed\]'`: 4. Plus 2 × `[Not specified]`."

**Not delivered, and recorded as such:** option 1 of the issue (omit the section entirely). See the
decision table.

## Decisions not in the issue

| # | Decision | Rationale / evidence |
| --- | --- | --- |
| D1 | **Add the keys** (the issue's option 2) plus its option 3 for `repository`, rather than the issue's preferred option 1. | Omission is not the cheaper option: `repo-compliance` §2.1.2 **requires** the placeholder and the *Minimal config* scenario requires it again, so omitting a section carries a spec delta and rewrites the tests that assert the sentinel — for a card that is shorter but no more informative. Adding the keys fixes the reported defect (a **fully-filled** config shipping placeholders) and leaves the rule that an unfilled config says so. Maintainer decision D1. |
| D2 | `_MORE_INFO` becomes one module constant instead of four inline literals. | AGENTS.md rule 4; and it makes the option-1 variant one edit rather than four if the maintainer ever switches. |
| D3 | A whitespace-only value behaves exactly like an unset one. | A value that is only whitespace is not content; `.strip()` before the fallback, pinned by a test. |
| D4 | `### Curation Rationale` keeps `study_design` as its only fill path. | The issue itself calls `study_design` the "fillable indirectly" path and asks for it to be *promoted*, not duplicated. A `curation_rationale` key would be new surface; recorded as a follow-up instead. |
| D5 | The README is not touched. | Its `[meta]` block enumerates only `description`, `license` and `tags`; the full key list lives in the spec. A second copy in the README would be duplicate surface, so rule 13 is not triggered. |

## Log

L1 (user request, verbatim): "revisá los issues pendientes, chequeá que sea correcto lo que reportan y
armá un roadmap de implementación"

L2 (user request, verbatim): "dale persistilo y convertilo en un milestone en github

arrancá la implementación, llevala hasta el final para cada issue pero no hagas push y PR, eso lo
hacemos mañana"

L3 (maintainer decision D1): add the `[meta]` keys, not omit the sections.

L4 (correction to the issue as written, verified against the code): the issue's line numbers are from
v0.5.0 and have drifted — the seven sites are at `repo_compliance.py:1522` (`_ns`), `1691`
(`- **Repository:**`), `1699`, `1703`, `1826`, `1853` and `1892` on `dev@6786ba1`. The substance of the
report holds exactly.

L5 (measured, my own error, recorded because it is what the run showed): three test fixtures had to be
corrected. The "fully filled config" fixture omitted `language`, `collection_method` and `citation` —
all keys that already existed — so the first version of the acceptance test failed against correct code
and looked like a defect in the change. And `build_dataset_card()` takes `study_design_content` as a
**parameter**; it never reads `cfg.study_design`. Full table in the change's `design.md` §3.3.

L6 (measured): no existing test changed expectation — `370 passed` on the four affected files before the
new tests existed, because the five new fields default to `""` and every pre-existing sentinel assertion
still holds. That is the evidence this change is additive.
