# Feature: agent-metadata-flow — issue #288

**Branch:** `feat/288-agent-metadata-flow` from `dev@6786ba1`. **Issue:** `emiliodavola/sofer#288`
**Delivery PR:** (this PR) → `dev`. **SDD change:** `openspec/changes/<date>-feat-agent-metadata-flow/`
(archived inside this PR, AGENTS.md rule 15). **Milestone:** v0.6.0.
**Risk:** low — the gate only adds warnings, and the chain edits are prose.

## Goal

`sofer init` writes a `[meta]` block of placeholders and nothing in the agent-facing surface said they
had to be replaced. They travelled through validate, prepare, codebook_all, profile_all and render_all
with every envelope reporting `ok: true`, and the only way to notice was to read the generated card.

## Specs

S1 (issue #288 §"Proposed solution" 1, verbatim): "**Say it in the flow the agent reads.** Mark the
metadata step as part of the canonical chain — e.g. `sofer_init`'s `next` pointing at a metadata step
before `validate`, and the prepare/validate descriptions carrying `Requires: [meta]
description/license/source/tags filled (no placeholders)`."

S2 (issue #288 §"Proposed solution" 2, verbatim): "**Make the gate notice.** `sofer_validate` (and the
pre-prepare quality run) should warn, or fail, when `[meta] description`, `license` or `source` still
look like template placeholders (prefix `TODO`, `YOUR_`, `example`, or an empty value). A warning is
enough to reach the agent; a failure would match how `sofer_init --user` already rejects `YOUR_USER`."

S3 (issue #288 §"Proposed solution" 4, verbatim): "**Document the ownership** in the agent-setup/README
section: on an MCP-driven run, the agent completes `[meta]`; the human only supplies what the data
cannot determine (license, source)."

**Not delivered, and recorded as such:** option 3 of the issue (`sofer_meta_set` / `sofer_meta_check`).
It is offered as one option among several, and a new tool changes the advertised tool inventory — its own
decision on its own schema and parity surface.

## Decisions not in the issue

| # | Decision | Rationale / evidence |
| --- | --- | --- |
| D1 | **Warn, never fail** (maintainer decision D3). | The issue leaves the force open and notes a failure would match `sofer_init --user`'s `YOUR_USER` rejection. A `fail` would break every existing config that still carries a placeholder, which is a contract change rather than a fix. `ValidationReport.passed` stays `True`, asserted. |
| D2 | The prefixes are `[tool.sofer] meta_placeholder_prefixes` = `["TODO", "YOUR_", "example"]`. | AGENTS.md rule 1, and the list is the issue's own wording. Validated as a non-empty list of non-empty strings. |
| D3 | Only a **prefix** matches, case-insensitively. | "An example-driven survey" is prose; "example.org" is a stand-in. Both are tested. |
| D4 | One call site: `DatasetValidator.run_all()`. | That covers the CLI `sofer validate`, the MCP `sofer_validate` tool and the pre-prepare run the issue names — three surfaces, one implementation. |
| D5 | An empty `tags` list does not warn, but an empty `description` does. | There is no value to replace in an empty list; warning there would be noise on every config that legitimately declares no tags. |

## Log

L1 (user request, verbatim): "revisá los issues pendientes, chequeá que sea correcto lo que reportan y
armá un roadmap de implementación"

L2 (user request, verbatim): "dale persistilo y convertilo en un milestone en github

arrancá la implementación, llevala hasta el final para cada issue pero no hagas push y PR, eso lo
hacemos mañana"

L3 (maintainer decision D3): warn, not fail.

L4 (verified against the code, confirming the issue): `grep -n "\[meta\]" src/sofer/mcp_server.py` on
`dev@6786ba1` hit only the confidential publish gate and the two CSV dialect overrides — never a
descriptive field — and neither `sofer_validate`'s `Requires:` nor the canonical chain mentioned
metadata. The issue's account holds.

L5 (measured, my own errors, recorded because it is what the runs showed): the first run of the new
tests was `5 failed, 17 passed`, and all five were wrong premises of mine rather than code defects — an
empty `tags` list is not a placeholder (3 warnings, not 4); a fixture using
`source = "Example Organisation"` as if it were a real value trips the `example` prefix, which is the
intended behaviour; `config` was not imported by the test module; and the `passed is True` assertion was
measuring a missing-file error, so its fixture now creates the file. Full table in `design.md` §5.

L6 (measured, a defect in the change itself, found by its own test): the first
`_PHASED_INSTRUCTIONS` edit listed the metadata step *after* `Phase 1 Build`, which teaches the wrong
order. The assertion is by index, not by presence, so the test caught it.

L7 (measured): `140 passed` on the five affected existing test files **before** the new tests existed —
no existing expectation changed, because the gate only adds warnings and the rest of the change is prose.
