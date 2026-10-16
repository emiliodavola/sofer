# Delta for repo-compliance

> **Change** `2026-10-15-fix-schema-relation-map` (issue **#304**) · branch
> `fix/304-schema-relation-map` from `dev@fad1b00` · store **hybrid**
> (`odd/tasks/schema-relation-map.md` + this folder).
>
> **Five modifications, no new requirement.** RC-R05 and RC-R06 stop mandating
> global first-occurrence-wins; § 3.3.6's superseded prefix example is re-stated
> in today's `origin` format; RC-R21 gains the per-table display clause; RC-R23
> gains the remote-class policy and the single origin relation.
>
> **Rule-6 resolution.** `repo-compliance` is a permanent declared-backlog spec
> (`openspec/test-mapping-registry.md`: "No `## Test Mapping` section — permanent
> declared backlog"), so the new scenarios are unmapped, the registry is not
> edited, and `scripts/check_test_mapping.py` still exits 0.

## MODIFIED Requirements

### 3.3.6 Schema from Parquet — column name disambiguation

The prefix format was already superseded by RC-R05/RC-R13; the block now reads
in the `origin` format and asserts two entries, as RC-R05 requires after this
change (verbatim, as it reads in the canonical spec after this change):

```
GIVEN two CSV files: "a.csv" and "b.csv"
  AND both have a column named "value"
  AND both are converted to Parquet
WHEN build_schema_report(cfg, staging_dir=tmpdir) is called
THEN the returned list SHALL contain two entries named "value"
  (one per source file, origin "a.parquet" and "b.parquet" — RC-R05)
```

### 4.6 Column origin attribution (RC-R05) — Modified 2026-10-15, fix-schema-relation-map

`ColumnSchema` SHALL keep its optional `origin: str = ""` field, now holding
the source file's **remote-relative POSIX path**: on the Parquet path, the
remote-derived `.parquet` key (e.g. `"data/survey.parquet"`); on the CSV
path, `entry.remote`. `build_schema_report()` SHALL populate `origin` for
every collected column, on both paths. Each file's columns SHALL yield their
**own** entries: the report SHALL carry one entry per `(origin, name)` pair, so
a column name appearing in several files yields one entry **per source file**,
each attributed to its own `origin`. The duplicate warnings of § 3.3.7 remain
unchanged and SHALL never remove an entry. This also supersedes RC-R07's clause
calling origin "basename-based": origin is display and grouping provenance only
and is never joined against row-count keys.

#### Scenario: Multi-file dataset exposes origin

- GIVEN a DatasetConfig with two CSV files, each contributing columns
- WHEN `build_schema_report()` runs
- THEN every returned ColumnSchema SHALL carry `origin` set to its source
      file's remote-relative path

#### Scenario: Duplicate name yields one entry per origin

- GIVEN two files that both contain a column "value"
- WHEN `build_schema_report()` runs
- THEN the returned list SHALL contain two "value" entries
- AND their `origin` values SHALL be the two declaring files, in declaration
      order

#### Scenario: Nested Parquet origins distinguish same-stem files

- GIVEN remotes `survey.csv` and `data/survey.csv`, both read from Parquet
- WHEN origins are assigned
- THEN they SHALL be `survey.parquet` and `data/survey.parquet` respectively

### 4.7 Data Fields renders per-file attribution (RC-R06) — Modified 2026-10-15, fix-schema-relation-map

The Dataset Card's "Data Fields" table SHALL include a **File** column whose cell
contains the column's `origin`. The card MUST NOT drop any included column, and
column names SHALL be displayed without the `file::` disambiguation prefix, since
attribution is now structural.

Design decision — one row per schema entry, File column carries attribution: the
schema report carries one entry per `(origin, name)` pair (RC-R05), so the Data
Fields section renders one row per entry — as the flat `### Data Fields` table in
a single-origin card, and as one `<details>` block per origin in a card with more
than one origin (RC-R21). A name declared by several files therefore appears once
per declaring file, each row naming its source in the File column; no table's
columns are dropped, and the section is exact about each table's own schema.

#### Scenario: Multi-file card shows file attribution

- GIVEN a schema built from two files
- WHEN `build_dataset_card(cfg, schema)` runs
- THEN every Data Fields row SHALL show its source file in the File column
- AND the number of rows SHALL equal the number of schema entries (no silent drops)

#### Scenario: Single-file card still attributes

- GIVEN a schema built from one file
- WHEN the card is rendered
- THEN the File column SHALL be present and populated for every row

#### Scenario: Repeated name appears once per declaring file

- GIVEN two files that both declare a column "PROV"
- WHEN the card is rendered
- THEN "PROV" SHALL appear in each declaring file's table
- AND no table SHALL lose its other columns

### Requirement: Collapsible Data Fields per sheet with threshold (RC-R21) — Modified 2026-10-15, fix-schema-relation-map

The requirement's grouping, threshold and title rules are unchanged. One clause
is added (verbatim):

- Grouping for display SHALL be by `origin` (one block per table), NEVER by
  config group: two origins that share one column signature still render one
  independent block each, so every table's own columns stay visible.

#### Scenario: RC-R21.09 same-schema tables keep one block each

- GIVEN two origins whose ordered column lists are identical
- WHEN the card is generated
- THEN both origins SHALL render their own `<details>` block
- AND each block SHALL list that origin's full column list

### Requirement: Mixed-schema config grouping (RC-R23) — Modified 2026-10-15, fix-schema-relation-map

- **Grouping (D2).** Group planned remotes by the ordered `(name, dtype)`
  signature of the entries attributed to them through the resolved origin of the
  group's remote (`_remote_origin_aliases`), so grouping, `dataset_info.features`
  and row counts all resolve the SAME `origin -> remote` relation; sheet origins
  group per sheet.
- **Remote classes (D1).** A planned remote whose declaring entry is not
  schema-eligible (recursive tree, non-convertible suffix, or
  `include_in_schema = false`) SHALL keep its own config group and stay listed in
  `configs.data_files` (RC-R03, RC-R12). A planned remote that IS schema-eligible
  but yielded no column — the file could not be read — SHALL be treated as
  *signature unknown*: it SHALL join the sole signature group when exactly one
  exists, and otherwise the corpus SHALL be ungroupable (neither `configs` nor
  `dataset_info`). An unknown signature SHALL NEVER invent a config group of its
  own.
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
  count **for that group only**. A group's `features` SHALL list the distinct
  column names attributed to that group's remotes through the same origin
  relation, once each — a name repeated across the group's files is one feature.
  The single-group dict shape is preserved; the multi-group shape is the HF list
  of `DatasetInfo` dicts.
- **Ungroupable guard (S2/D1).** When the schema report carries no column for
  any planned remote and more than one remote is planned, the card SHALL emit
  neither `configs` nor `dataset_info`.
- **Actionable warning (S4).** `validate_split_mapping(remotes)` SHALL warn, for
  a multi-file corpus with no split keywords, that the card groups those files by
  column schema — every file into one `train` split for a single-config card,
  and one table at a time via `load_dataset(repo, name=...)` for a multi-config
  card. The clause SHALL NOT claim a single merged split in general, because the
  card no longer emits one.

#### Scenario: Mixed-schema corpus is never one merged config — issue #292

- GIVEN two census tables with different columns declared without split keywords
- WHEN the card is generated
- THEN the two tables SHALL NOT share one `train` config
- AND each config's `data_files` SHALL contain only its own group's remotes

#### Scenario: Same-schema table pair shares one config — issue #304

- GIVEN three tables where two declare an identical ordered column list and the
  third differs
- WHEN the card is generated
- THEN `configs` SHALL contain exactly two entries
- AND the two identical-schema tables SHALL share one config's `data_files`

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

#### Scenario: Unknown-signature remote never invents a group

- GIVEN two known signatures and a planned remote whose file cannot be read
- WHEN the card is generated
- THEN `configs` SHALL be absent
- AND `dataset_info` SHALL be absent

#### Scenario: Unknown-signature remote joins the sole group

- GIVEN one known signature and a planned remote whose file cannot be read
- WHEN the card is generated
- THEN `configs` SHALL contain exactly one entry
- AND its `data_files` SHALL include the unreadable remote

#### Scenario: Declared non-schema remote keeps its own config

- GIVEN a `[[file]]` entry with `include_in_schema = false` beside two
  schema-assessed tables
- WHEN the card is generated
- THEN the opted-out file SHALL keep its own `configs` entry
- AND the file SHALL stay listed in `configs.data_files` (RC-R03)

#### Scenario: Per-group num_examples

- GIVEN two groups, one with exact row counts and one without
- WHEN the card is generated
- THEN each `dataset_info` block's `num_examples` SHALL use its own group's
  counts, or the per-file fallback for that group only
