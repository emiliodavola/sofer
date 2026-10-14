# Delta for repo-compliance

> **Change** `2026-10-13-fix-mixed-schema-configs` (issue **#292**) · branch
> `fix/292-mixed-schema-configs` from `dev@4ca823e` · store **hybrid**.
>
> **One modification + one new requirement.** RC-Universal-Card gains the
> mixed-schema grouping clause; a new RC-R23 declares the whole config plan
> (grouping, slug, `default`, ungroupable guard, per-group `dataset_info`).
>
> **Rule-6 resolution.** `repo-compliance` is a permanent declared-backlog spec
> (`openspec/test-mapping-registry.md`), so the new scenarios are unmapped and
> the registry is not edited; `scripts/check_test_mapping.py` still exits 0.

## MODIFIED Requirements

### 4.20 Card data_files reflect universal normalized remotes (RC-Universal-Card) — Modified 2026-10-13, fix-mixed-schema-configs

The existing clause is unchanged: `build_dataset_card` lists
`configs.data_files` and `Dataset Structure` via `expanded_planned_remotes`
when a staging directory is available, otherwise via `planned_remotes`;
TSV/XLSX/JSONL appear as normalized `.parquet` remotes; a multi-sheet
`report.xlsx` appears as N `stem__sheet.parquet` entries; no local-disk path
leaks.

**Added clause (verbatim, as it reads in the canonical spec after this change):**

`build_dataset_card` SHALL NOT merge remotes whose column signatures differ
into one `configs` entry. It SHALL group the planned remotes by the ordered
`(name, dtype)` signature of their `ColumnSchema` entries and emit **one**
`configs` entry per group, each with its own `dataset_info` (RC-R23). When the
schema report carries no column for any planned remote and more than one remote
is planned, the card is **ungroupable** and SHALL emit neither `configs` nor
`dataset_info`, leaving the Hub to infer per file.

**Added scenarios (verbatim):**

#### Scenario: Mixed-schema corpus emits one config per signature

- GIVEN two remotes whose `ColumnSchema` origins carry different ordered
  `(name, dtype)` signatures
- WHEN the card is generated
- THEN `configs` SHALL contain two entries, one per group
- AND `dataset_info` SHALL contain one block per config, each with its own
  `num_examples`

#### Scenario: Same-signature corpus stays one config

- GIVEN remotes that share one column signature
- WHEN the card is generated
- THEN `configs` SHALL contain exactly one entry carrying `default: True`

## ADDED Requirements

### Requirement: Mixed-schema config grouping (RC-R23)

`build_dataset_card` SHALL derive its `configs` and `dataset_info` from a
schema-grouping plan, never from a single unconditional merged config:

- **Grouping (D2).** Group planned remotes by the ordered `(name, dtype)`
  signature of the `ColumnSchema` entries attributed to them via
  `ColumnSchema.origin`; sheet origins group per sheet.
- **`config_name` (D3).** Each `config_name` SHALL be a slug matching
  `[a-z0-9._-]`, derived from `[dataset] name` (or `cfg.config_names[0]`) for a
  single group and from the remote's file stem for multiple groups. The slug
  rule (invalid-character pattern, separator, maximum length, empty fallback)
  SHALL be config-owned (`config.CARD_CONFIG_*`, `[tool.sofer]`), never a
  literal in the function body. `pretty_name` SHALL NEVER be passed to the slug
  builder.
- **`default` (D4).** `default: True` SHALL appear on the config **only** when
  the card emits exactly one config. A multi-group card SHALL carry no
  `default` key on any config.
- **`dataset_info` (D5).** One block per config, each with the group's
  `features` and a `train` split whose `num_examples` sums the group's exact
  row counts, falling back to `card_fallback_rows_per_file` × group remote
  count **for that group only**. The single-group dict shape is preserved; the
  multi-group shape is the HF list of `DatasetInfo` dicts.
- **Ungroupable guard (S2/D1).** When the schema report carries no column for
  any planned remote and more than one remote is planned, the card SHALL emit
  neither `configs` nor `dataset_info`.
- **Actionable warning (S4).** `validate_split_mapping(remotes,
  config_names=None)` SHALL keep its historical default-load warning when the
  config names are unknown, and SHALL name the configs and the
  `load_dataset(repo, name=...)` call when they are supplied, listing at most
  `config.CARD_CONFIG_GROUP_WARN_LIMIT` names before an ellipsis.

#### Scenario: Mixed-schema corpus is never one merged config — issue #292

- GIVEN two census tables with different columns declared without split keywords
- WHEN the card is generated
- THEN the two tables SHALL NOT share one `train` config
- AND each config's `data_files` SHALL contain only its own group's remotes

#### Scenario: config_name is a validated slug

- GIVEN `[dataset] name = "Censo Nacional de Población, Hogares y Viviendas 2010 (Argentina) - Microdatos"`
- WHEN the card is generated
- THEN `config_name` SHALL match `[a-z0-9._-]+`
- AND it SHALL NOT equal `pretty_name`

#### Scenario: Multi-group card carries no default key

- GIVEN remotes that fall into two or more schema groups
- WHEN the card is generated
- THEN no `configs` entry SHALL contain a `default` key

#### Scenario: Ungroupable corpus emits neither block

- GIVEN more than one planned remote and a schema report with no columns
- WHEN the card is generated
- THEN `configs` SHALL be absent
- AND `dataset_info` SHALL be absent

#### Scenario: Per-group num_examples

- GIVEN two groups, one with exact row counts and one without
- WHEN the card is generated
- THEN each `dataset_info` block's `num_examples` SHALL use its own group's
  counts, or the per-file fallback for that group only

#### Scenario: Dry-run warning names the configs

- GIVEN multiple files without split keywords and the card's config names
- WHEN `validate_split_mapping(remotes, config_names=[...])` runs
- THEN the warning SHALL name the configs and the `load_dataset(repo, name=...)`
  call
- AND with `config_names=None` it SHALL keep the historical default-load warning

## Non-goals recorded by this change

No `publish.py` or `prepare.py` change; no version bump; no Test Mapping row;
no registry edit.
