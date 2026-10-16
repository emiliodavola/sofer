# Feature: card-config-group-warning — issue #303

**Branch:** `fix/303-card-config-group-warning` from `dev@6786ba1`. **Issue:** `emiliodavola/sofer#303`
**Delivery PR:** (this PR) → `dev`. **SDD change:** `openspec/changes/<date>-fix-card-config-group-warning/`
(archived inside this PR, AGENTS.md rule 15). **Milestone:** v0.6.0 — agent surface & card completeness.
**Risk:** low — the warning text changes; nothing else observes it.

## Goal

`sofer publish --dry-run` warns that a multi-table corpus without split keywords is loaded one table at
a time with `load_dataset(repo, name='<config>')` — true, but not actionable: the names are known
exactly when the card is built, and the caller that prints the warning never sees the card.

## Specs

S (issue #303 §"Proposed solution" 1 and 2, verbatim): "**Emit the group-aware warning from the card
builder.** `build_dataset_card()` already holds the plan; have it return the plan (or a warning list)
so `prepare`/`publish` can print it where the user reads it. No new parsing, and the truth lives in one
place." / "**Read the built card in the dry-run path.** When `<build_dir>/README.md` exists (the
auto-prepare path guarantees it in most runs), extract `configs[].config_name` and pass them to
`validate_split_mapping(remotes, config_names=...)`. This needs a frontmatter reader — `sofer/_yaml.py`
already loads YAML mappings for the MCP registration paths — and a fallback to today's two-shape
message when the card is absent."

**Delivered: option 2**, with the reason recorded in the change's `proposal.md` §3 — the issue's option
1 assumed one process, but `prepare` and `publish --dry-run` are separate, so a plan held in
`prepare`'s memory cannot reach the caller that prints the warning.

## Decisions not in the issue

| # | Decision | Rationale / evidence |
| --- | --- | --- |
| D1 | `card_config_group_warn_limit` (`[tool.sofer]`, default 5) caps the named list with `... and N more`. | A 65-table corpus would otherwise print 65 names in the one message that tells the user how to load the repo. This is the default PR #301 removed as callerless; it now has a production caller. |
| D2 | Any unreadable or partially-readable card yields `[]` for the whole card, never a partial list. | Naming some configs and hiding others looks complete while being wrong; the placeholder at least does not. |
| D3 | The names come from the artifact, never a re-derivation in `publish`. | The reader returns what shipped, so the warning cannot disagree with the card. |
| D4 | `_config_name_hint()` returns the bare list and the caller supplies the prose. | Makes the elision rule testable on its own, without asserting on a whole paragraph. |

## Log

L1 (user request, verbatim): "revisá los issues pendientes, chequeá que sea correcto lo que reportan y
armá un roadmap de implementación"

L2 (user request, verbatim): "dale persistilo y convertilo en un milestone en github

arrancá la implementación, llevala hasta el final para cada issue pero no hagas push y PR, eso lo
hacemos mañana"

L3 (issue #303 §"Related", verbatim): "- PR #301 (merged as `69678c6`) — the delivered behaviour and the
removed draft surface." The removed `config_names` keyword and `card_config_group_warn_limit` default
are restored here, now with a production caller on both `publish` paths — the condition PR #301's review
found missing.

L4 (measured, this change): `validate_split_mapping` returns **three** warnings for two keyword-less
files, not one — the per-split keyword-consistency check adds its own. Recorded because two new tests
had to be narrowed to select the `Default-load warning` entry rather than index `warnings[0]`, and that
is a fact about the existing function, not a convenience.
