# Feature: mixed-schema-configs — issue #292

**Branch:** `fix/292-mixed-schema-configs` from `dev@4ca823e`. **Issue:** `emiliodavola/sofer#292`
**Delivery PR:** (this PR) → `dev`. **SDD change:** `openspec/changes/<date>-fix-mixed-schema-configs/`
(archived inside this PR, AGENTS.md rule 15). **Risk:** high — it changes the artifact users load with
`load_dataset()`; today's card ships an unloadable default config.

## Goal

`build_dataset_card()` emits **one** `configs` entry with **one** `train` split for every planned
remote, and derives `config_name` from `pretty_name` (a display string with spaces, commas, parens and
accents). For a corpus that mixes schemas (8 tables + 57 dictionaries) the published default config
fails with `CastError` / `DatasetGenerationError`, and `dataset_info` reports a merged row total for a
split that cannot be generated. Evidence map: `repo_compliance.py:1121-1138` (`configs`),
`:1139-1167` (`dataset_info`), `:497-845` (`_collect_columns` → per-file `ColumnSchema.origin` +
`row_counts`), `splits.py:335` (the dry-run warning), `prepare.py:585/595` (the call sites).

## Specs

S1 (issue §"Proposed solution" 1, verbatim): "**Group by compatible schema.** Emit one config per
schema group, named from the file stem (`persona`, `hogar`, `vivienda`, ...), each with its own
`dataset_info`. This is the standard multi-table HF pattern."
S2 (2, verbatim): "**Do not merge what cannot merge.** If files declare no split keyword and their
schemas differ, emit nothing rather than one wrong config, and let the Hub infer per-file."
S3 (3, verbatim): "**Never derive `config_name` from `pretty_name`.** Use a slug from `[dataset] name`
or the file stem; validate it as an identifier."
S4 (4, verbatim): "**Make the existing dry-run warning actionable** — it currently describes the
problem without preventing the artifact that causes it."
S5 (issue §Problem, verbatim): "For a corpus whose files do **not** share a schema — several tables
plus their dictionaries — the emitted `default: True` config is unloadable." and the two defects:
"1. **No schema grouping.** Files that differ in columns are merged into one split. 2. **`config_name`
derives from `pretty_name`**, a human display string."

## Decisions not in the issue

| # | Decision | Rationale / evidence |
| --- | --- | --- |
| D1 | S1 and S2 are read together: group remotes by column signature and emit one config per group (S1); S2's "emit nothing" is the guard for the **ungroupable** case (no schema available for the remotes, so every grouping would be a guess), never a rule that suppresses valid per-group configs. | S2's target is "one wrong config"; a per-group config is not that. Recorded because the two bullets can be read as alternatives — see L3. |
| D2 | Group identity = the ordered `(name, dtype)` signature of the `ColumnSchema` entries whose `origin` is that remote; sheet origins group per sheet. | `ColumnSchema.origin` (`repo_compliance.py:142`) + `_collect_columns` (`:497`) already carry exactly this; `row_counts` gives the per-remote count for `dataset_info`. |
| D3 | `config_name` is a slug (`[a-z0-9._-]`) derived from `[dataset] name` for a single group and from the remote's file stem for multiple groups, and is validated; `pretty_name` never reaches it. | S3; observed offender: `Censo Nacional de Población, Hogares y Viviendas 2010 (Argentina) - Microdatos`. |
| D4 | `default: True` **only when the card emits exactly one config**. With several schema groups no config carries `default`, so `load_dataset(repo)` cannot silently pick one table for the user. | Maintainer decision (L4): "Una config por grupo, sin default", chosen over defaulting the largest group. |
| D5 | The `dataset_info` block follows the same grouping (one per config, its own `num_examples`), and a group with no exact row count falls back to the existing conservative per-file product for that group only. | S1 ("each with its own `dataset_info`"); `RC-R12`'s undercount note stays true per group. |

## Tasks

| # | Task | Spec | State | Evidence |
| --- | --- | --- | --- | --- |
| T1 | RED: mixed-schema corpus produces one config per column signature, each with matching `dataset_info`; a single-signature corpus keeps exactly one config; `config_name` is a slug and never `pretty_name`; a multi-group card carries no `default` key | S1 S3 S5 D2 D4 D5 | pending | — |
| T2 | RED: the ungroupable case emits no `configs` / `dataset_info` instead of a merged one, and the dry-run warning names why | S2 S4 | pending | — |
| T3 | Grouping implementation over `schema` + `row_counts` (per-remote column signature) | S1 D2 | pending | — |
| T4 | `config_name` slug + identifier validation, applied to `configs` and `dataset_info` | S3 D3 | pending | — |
| T5 | D4 applied to `default` | S1 D4 | pending | — |
| T6 | Dry-run warning becomes actionable: it names the mixed schema groups and what the card will emit | S4 | pending | — |
| T7 | `repo-compliance` spec delta (the config generation clause) | S1 S2 S3 | pending | — |
| T8 | README + README_ES if the documented card structure changes | S4 | pending | — |
| T9 | Gates: full suite, coverage TOTAL ≥ 90, ruff/format/mypy/pyright, `check_test_mapping.py` | — | pending | — |
| T10 | Commit + push + PR (base `dev`, assignee `emiliodavola`), `Closes #292` | — | pending | — |

## Log

L1 (2026-10-13, user, verbatim): "revisá los issues tipo bug e implementalos, 1 rama y PR (asignado a
mi) por issue"
L2: parent-mapped the sites after the delegated explore stalled (`repo_compliance.py:1121-1167`,
`prepare.py:585/595`, `splits.py:335`).
L3 (resolved): S1 (one config per schema group) and S2 ("emit nothing … and let the Hub infer per-file")
can be read as alternatives for a mixed corpus, and neither bullet settles whether a multi-config card
carries a `default: True`. Asked to the maintainer as one question.
L4 (2026-10-13, maintainer answer, verbatim): "Una config por grupo, sin default" — D1's reading
(per-group configs, S2 as the ungroupable-case guard) is confirmed and D4 is settled: no `default` flag
in a multi-group card.
