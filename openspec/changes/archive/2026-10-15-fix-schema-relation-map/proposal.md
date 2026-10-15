# Proposal — `2026-10-15-fix-schema-relation-map`

> **Change** `2026-10-15-fix-schema-relation-map` · issue **#304** · branch
> `fix/304-schema-relation-map` from `dev@fad1b00` · store **hybrid**
> (`odd/tasks/schema-relation-map.md` + this folder).
>
> **Status:** implementation complete; archived inside the delivering branch
> (AGENTS.md rule 15).

---

## 1. Intent

`repo_compliance._build_schema_report_impl` dedups column names **globally**: a
name already collected from any earlier file is skipped entirely, so a table
whose columns all repeat an earlier table's contributes **no** `ColumnSchema`
entry. The grouping added by #292 keys on the emitted column signature of each
planned remote, so that table has no signature and — when the corpus carries more
than one signature — lands in a `config_name` of its own although its schema is
identical to another table's. `configs` therefore stops meaning "one config per
schema", and a user loading the two halves of the same table must pick two
configs.

The same missing per-origin attribution has a second, unreported effect: on the
CSV-fallback path `ColumnSchema.origin` is the declared `.csv` remote while
`_features_for_group` compares it against the planned `.parquet` remotes with no
alias resolution, so every multi-group card emitted from that path carries empty
`dataset_info.features`.

Measured before the change (three CSVs, `persona_2010`[PROV,ANO] +
`hogar_2010`[PROV,HOGAR] + `persona_2022`[PROV,ANO]):

```text
schema entries      : persona_2010 x2, hogar_2010 x1        (persona_2022: none)
configs emitted     : persona_2010 | hogar_2010 | persona_2022   (3, must be 2)
dataset_info.features per group: [] | [] | []
```

## 2. Scope

### In scope

- `_build_schema_report_impl`: one `ColumnSchema` entry per `(origin, name)`;
  the RC-R02 duplicate warning becomes purely informational and never removes an
  entry.
- One shared schema-eligibility predicate (`_is_convertible_entry`,
  `_is_schema_eligible`) and one planned-remote classifier
  (`_schema_eligible_remotes`).
- `group_remotes_by_schema`: the remote-class policy — an eligible remote that
  yielded no column is *signature unknown* and never invents a group; a declared
  non-schema remote keeps its own group (RC-R03/RC-R12).
- `_features_for_group`: resolve the group's remotes through
  `_remote_origin_aliases` and list each distinct name once.
- Data Quality Notes: dedup the empty-column list.
- The `repo-compliance` spec (RC-R05, § 3.3.6, RC-R06, RC-R21, RC-R23), the
  tests, and this change folder.

### Out of scope (non-goals)

- **No return-shape change.** `build_schema_report()` /
  `build_schema_report_with_rows()` keep `(list[ColumnSchema], dict[str, int])`;
  with T1 the flat list *is* the per-origin map, so `prepare.py` and every
  existing caller are untouched (D3).
- **No `pretty_name`/slug change, no `default` rule change, no ungroupable-guard
  change** — all #292 contracts stay exactly as they are.
- **No Data Fields reshape.** Display stays one block per origin (RC-R21), the
  user's `D2` answer; the alternative (per config group) was rejected.
- No change to `codebook.py`, `quality.py`, `publish.py`, `splits.py`.
- No version bump; no new dependency.

## 3. Settled decisions

Quoted from `odd/tasks/schema-relation-map.md` (the spec of record):

| # | Decision |
| --- | --- |
| D1 | Three classes of planned remote: *assessed* (groups by its own signature), *declared non-schema* (recursive / non-convertible / `include_in_schema = false` → own group), *eligible but unassessed* (could not be read → signature unknown, joins the sole group or makes the corpus ungroupable). Only the third is "unknown"; folding the second into it would make any corpus with a label file or a recursive directory ungroupable. |
| D2 | Data Fields stays one block per origin (user answer, verbatim: "data fields por tabla"). |
| D3 | Keep the existing return shape; derive the per-origin map from the entries. |
| D4 | One shared eligibility predicate for the collection loop and the classifier. |
| D5 | One `origin -> [keys]` resolution shared by grouping, features and row counts. |
| D6 | The RC-R02 duplicate warning output is unchanged in shape and now truthful. |

## 4. Affected specs

`repo-compliance`: RC-R05 and RC-R06 (Modified), § 3.3.6 block, RC-R21 (Modified,
one display clause + scenario), RC-R23 (Modified, remote-class policy, single
origin relation, features dedup + four scenarios). No requirement added, none
removed. `openspec/specs/repo-compliance/spec.md` is a permanent
declared-backlog spec, so no `## Test Mapping` row is added and
`scripts/check_test_mapping.py` is unchanged.

## 5. Risks

| # | Risk | Severity | Disposition |
| --- | --- | --- | --- |
| R1 | The card's Data Fields shape changes for multi-file corpora (per-table blocks, one row per entry). | Med | Intended: the flat table with a File column was ambiguous about repeated names, and a name already appeared once per file there. RC-R06's rationale is rewritten in the same change; RC-R21.09 pins the new behaviour. |
| R2 | RC-R05/RC-R06 are published clauses of a delivered capability (#292). | Med | Explicit spec modification, archived with this change and cross-referenced to #292's R1 in the archive report. |
| R3 | An eligible-but-unreadable remote now makes a multi-signature corpus ungroupable (no `configs` at all) instead of emitting a bogus group. | Med | Named in RC-R23's Remote classes clause and pinned by two scenarios. It is the conservative reading of #304's proposal ("never invents a group on its own") and it is loud: the user sees no `configs` rather than a silent split. |
| R4 | A repeated name in one config's `features` could double a column. | Low | `_features_for_group` lists each distinct name once; a group's entries share a signature by construction, so the dedup is lossless. Pinned by two tests. |
| R5 | Larger schema reports (one entry per file) inflate the Data Fields section on wide corpora. | Low | `CARD_COLLAPSE_THRESHOLD` already wraps multi-origin cards (RC-R21). |

## 6. Rollback

Revert-only. Restoring the three global-dedup `continue`s, the previous
`group_remotes_by_schema` tail, the previous `_features_for_group`, the two test
edits and the five spec sections restores the previous behaviour exactly. No
state, no migration, no artifact on disk to clean up.

## 7. Success criteria

SC-1 The same-schema table pair shares one config (the #304 reproduction).
SC-2 Every planned origin contributes its own schema entries.
SC-3 A multi-group card built on the CSV-fallback path carries non-empty,
per-group, name-deduplicated `features`.
SC-4 An unknown-signature remote never invents a config group.
SC-5 A declared non-schema remote keeps its own group and stays in `data_files`.
SC-6 Data Fields lists every declaring table with its own columns.
SC-7 Existing behaviour (slug, `default`, ungroupable guard, RC-R02 warning
     routing, row counts) is unchanged: full suite green.
