# Feature: schema-relation-map — issue #304

**Branch:** `fix/304-schema-relation-map` from `dev@fad1b00`. **Issue:** `emiliodavola/sofer#304`
**Delivery PR:** (pending — user decision) → `dev`. **SDD change:**
`openspec/changes/2026-10-15-fix-schema-relation-map/` (archived inside this branch, AGENTS.md rule 15).
**Risk:** high — it changes the card artifact users load with `load_dataset()`, and it modifies the
published `repo-compliance` clauses RC-R05 / RC-R06.

## Goal

`repo_compliance._build_schema_report_impl` dedups column names **globally** (`seen_names` / `_dup_map`,
`repo_compliance.py:532-533` and the `continue` at `:634`, `:688`, `:800`), so a table whose columns all
repeat an earlier table's contributes **no** `ColumnSchema` entry. Its signature is therefore unknown,
and `group_remotes_by_schema` (`:1123`) can only absorb it into a sole signature group; with several
signatures the table is split into its own `config_name` although its schema is identical to another
table's. The same missing per-origin attribution also empties `dataset_info.features` on the
CSV-fallback path, because `_features_for_group` (`:1262`) filters `col.origin in group_remotes` without
the `_remote_origin_aliases` resolution that grouping and row counts use.

Measured today (three CSVs, `persona_2010`[PROV,ANO] + `hogar_2010`[PROV,HOGAR] + `persona_2022`[PROV,ANO]):

```text
schema entries      : persona_2010 x2, hogar_2010 x1        (persona_2022: none)
configs emitted     : persona_2010 | hogar_2010 | persona_2022   (3, must be 2)
dataset_info.features per group: [] | [] | []
```

**One-line outcome:** every planned remote gets a signature computed from **its own** columns, one
canonical `origin -> remote` relation resolves grouping, features and row counts identically, and a
remote that cannot be assessed never invents a config group.

## Specs

S1 (user, verbatim): "revisá los issues tipo bug y armate un roadmap para implementar los cambios, el
issue #304 analizalo bien, puede haber columnas con nombres repetidos a lo largo de las diferentes
tablas y eso no es un problema, en todo caso tendria que haber un esquema de como se relacionan"

S2 (user, verbatim): "2. D2: data fields por tabla"

S3 (issue #304 §Problem, verbatim): "- is absorbed into the sole signature group when the corpus has
exactly one signature (correct for a `train`/`test` pair of the same table), but - becomes its own group
when several signatures exist — so the second table of an otherwise identical schema lands in a
**different** `config_name` than the first. That second case is the defect: `configs` no longer means
"one config per schema", and a user loading the two halves of the same table must pick two configs
instead of one."

S4 (issue #304 §Proposed solution, verbatim): "1. Have `build_schema_report_with_rows()` /
`_collect_columns()` return a per-origin column map (or extend `ColumnSchema` with a per-origin list) so
a signature can be computed for **every** planned remote, not only for the first file that declared each
name. 2. Treat "no schema entries for a remote" as *signature unknown* rather than as an empty
signature, so an unknown-signature remote never invents a group on its own (it should join the sole
group, or make the corpus ungroupable — which already emits no `configs` at all, per S2)."

S5 (user, verbatim): "4. arrancá"

S6 (this triage, man-in-the-loop finding; output observed verbatim on the S1 corpus above):

```text
--- dataset_info.features per group ---
  persona_2010  -> []
  hogar_2010    -> []
  persona_2022  -> []
```

`_features_for_group` is called with `group_remotes` (planned `.parquet` remotes) while
`ColumnSchema.origin` on the CSV-fallback path is the declared `.csv` remote (RC-R05), so no column
matches and every multi-group card emitted from that path carries empty features.

S7 (AGENTS.md rule 6 and rule 15, verbatim): "Every SDD spec scenario maps to a repository test
(`test:`) or to declared verify-phase evidence (`verify:`)." / "A completed SDD change SHALL be archived
**inside the pull request that delivers it**".

## Decisions not in the issue

| # | Decision | Rationale / evidence |
| --- | --- | --- |
| D1 | **Three classes of planned remote, not two.** (a) *assessed*: schema-eligible and read → groups by its own signature; (b) *declared non-schema*: recursive tree, non-convertible suffix, or `include_in_schema = false` → keeps its own group, exactly as today; (c) *eligible but unassessed*: the file could not be read (or a sheet failed) → signature **unknown**, never invents a group: it joins the sole signature group, or the corpus is **ungroupable** (no `configs`/`dataset_info`). | Class (b) may not be folded into (c): RC-R03 and RC-R12 require `include_in_schema = false` files to stay in `configs`/`data_files`, and a recursive tree or a `.zip` can never be schema-assessed. Treating all unresolved remotes as unknown would make any corpus with a label file or a recursive directory ungroupable — a regression, not a fix. The common *train*/*test* case disappears from (c) once T1 lands, so (c) is genuinely "we could not read it". |
| D2 | Data Fields stays **one block per origin** (per table), the RC-R21 contract, and does **not** collapse to one block per config group. | S2, verbatim. Keeps RC-R21.01–.08 and `TestCardCollapsible` intact; the alternative (per config group) would rewrite two published scenarios for a display preference. |
| D3 | `build_schema_report()` / `build_schema_report_with_rows()` keep their `(list[ColumnSchema], dict[str, int])` return shape; the per-origin map is derived from the returned entries, which T1 makes complete. | S4 offers both shapes ("a per-origin column map (or extend `ColumnSchema` with a per-origin list)"); keeping the tuple confines the change to `repo_compliance` + `prepare`'s existing call, and the flat list with per-`(origin, name)` entries *is* the per-origin map. |
| D4 | The schema-eligibility predicate lives in one pair of helpers used by **both** the collection loop and the class classifier. | AGENTS.md rule 4: the classifier must not re-implement "recursive / convertible suffix / `include_in_schema`". Without one shared definition the two would drift and class (c) would mis-fire. |
| D5 | The single `origin -> [keys]` resolution (`_remote_origin_aliases`) is passed into `_features_for_group` so grouping, features and row counts resolve identically. | S1's "un esquema de como se relacionan": today the three consumers each resolve differently, which is what produces S6. |
| D6 | The `RC-R02` duplicate-name warning keeps reporting every repeated name (`_dup_map` is display-only data and is not affected by T1). | Its contract (individual `[!]` warnings under the threshold, one `[i]` summary above it) is published and unrelated to grouping; the repetition it reports is now *accurate* rather than a reason to drop the column. |

## Tasks

| # | Task | Spec | Route | State | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | RED: two same-schema tables plus one different table yield entries for **all three** origins, and the same-schema pair lands in **one** config | S1 S3 S4 | inline | done | `7 failed, 3 passed, 196 deselected` (focused RED run) |
| T2 | RED: a multi-group card built on the CSV-fallback path carries non-empty `dataset_info.features` per group | S6 D5 | inline | done | same RED run (`[] == ['PROV', 'ANO']`) |
| T3 | RED: an eligible-but-unreadable remote never invents a group (joins the sole group / ungroupable), while a declared non-schema remote keeps its own group | S4 D1 | inline | done | same RED run; the declared class passes as a pin |
| T4 | Per-`(origin, name)` collection: drop the three global-dedup `continue`s, keep `_dup_map` and the RC-R02 output | S1 D6 | inline | done | `03eb052` (`_note_column_origin`) |
| T5 | One shared eligibility predicate + the class classifier; `group_remotes_by_schema` honours the unknown policy | S4 D1 D4 | inline | done | `03eb052` (`_is_convertible_entry`, `_is_schema_eligible`, `_schema_eligible_remotes`) |
| T6 | Thread `aliases` into `_features_for_group`; dedup the Data Quality Notes empty-column list | S2 S6 D2 D5 | inline | done | `03eb052` |
| T7 | `repo-compliance` spec delta + canonical spec: RC-R05, §3.3.6, RC-R06, RC-R21 note, RC-R23 | S7 | inline | done | `openspec/specs/repo-compliance/spec.md` + the delta in the archived change folder |
| T8 | Gates + archive: focused tests, full suite, ruff/format/mypy/pyright, `check_test_mapping.py`, archive report inside the branch | S7 | inline | done | `2144 passed, 9 skipped`; ruff/format/mypy/pyright/mapping green; `archive-report.md` |

## Log

L1 (2026-10-15, user, verbatim): "revisá los issues tipo bug y armate un roadmap para implementar los
cambios, el issue #304 analizalo bien, puede haber columnas con nombres repetidos a lo largo de las
diferentes tablas y eso no es un problema, en todo caso tendria que haber un esquema de como se
relacionan"

L2 (2026-10-15, this session, read-only triage): reproduced #304 and #305, found S6, and corrected two
claims in #304's own report — the schema report is consumed only by `repo_compliance` and `prepare`
(`codebook.py` streams its own readers; `quality.py` never sees it), and the proposed "environment
marker" for #305 is a trap (`coverage run` erases the data file at start and flushes it at exit, so a
guard that *required* the marker could never assert). Roadmap: three separate SDD changes
(`fix/304-schema-relation-map`, `fix/305-coverage-guard-freshness`, then #303 on top of the plan).

L3 (2026-10-15, user, verbatim): "1. D1: explicamelo en facil / 2. D2: data fields por tabla / 3. opcion
1 / 4. arrancá"

L4 (2026-10-15, parent, D1 resolution): #304's own proposal ("it should join the sole group, or make the
corpus ungroupable") plus RC-R03/RC-R12 settle class (c) without a new product decision, so D1 is
applied as written above and no question is left open; user-facing explanation delivered with this
change.

L5 (2026-10-15, implementation evidence): RED measured before the first source edit (`7 failed, 3
passed`); behaviour work unit committed as `03eb052` (`fix(schema): keep one column entry per origin so
same-schema tables share a config`), pre-commit green (ruff/format/mypy/pyright); full suite `2144
passed, 9 skipped`; `check_test_mapping.py` OK. End-to-end card check over a three-table corpus: 2
configs (`persona_2010` + `persona_2022` sharing one, `hogar_2010` alone), per-group `features`
without duplicates, one Data Fields block per table. Pending: push + PR (user decision).
