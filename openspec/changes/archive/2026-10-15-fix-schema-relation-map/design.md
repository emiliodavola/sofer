# Design — `2026-10-15-fix-schema-relation-map`

> **Change** `2026-10-15-fix-schema-relation-map` (issue **#304**) · branch
> `fix/304-schema-relation-map` from `dev@fad1b00` · store **hybrid**.

---

## 1. The defect, precisely

`_build_schema_report_impl` keeps one global `seen_names` map and, for every
column whose name was already collected from any earlier file, **skips the column
entirely** (three `continue` sites: the XLSX per-sheet branch, the staged-Parquet
branch, the CSV/JSONL branch). One structure was answering two different
questions:

1. *display*: do not repeat a name in the card's flat Data Fields table;
2. *attribution*: which table is this column's source — what `_origin_signatures`
   reads to compute a remote's schema signature, what `group_remotes_by_schema`
   groups by, and what `_group_by_origin` splits the Data Fields section by.

Because the whole `ColumnSchema` was dropped rather than only its display row, a
table whose columns **all** repeat an earlier table's ends up with **no entries
of its own**. Its signature is therefore `None` (not "empty"), and the grouping
can only absorb it into a sole signature group (the `train`/`test` case, where the
result is accidentally right) or give it a group of its own (the defect).

The second effect is the same root: `_features_for_group` filtered
`col.origin in group_remotes` with no alias resolution, while grouping
(`group_remotes_by_schema`) and row counts (`_row_count_for_remote`) both resolve
`origin` through `_remote_origin_aliases`. On the CSV-fallback path an origin is
the declared `.csv` remote and a planned remote is the normalized `.parquet` one,
so no column matched and every multi-group card from that path shipped empty
`features`. There was no single relation; there were three, and only two agreed.

## 2. Measured evidence

Reproduced read-only against the unmodified code (three CSVs, temporary corpus
removed after the run):

```text
schema entries      : persona_2010.csv x2, hogar_2010.csv x1   (persona_2022.csv: none)
_origin_signatures  : {persona_2010.csv: [PROV, ANO], hogar_2010.csv: [PROV, HOGAR]}   (persona_2022.csv absent)
configs emitted     : persona_2010 | hogar_2010 | persona_2022        (3, must be 2)
dataset_info.features per group: [] | [] | []
```

RED of the new tests, focused on the new class plus the inverted unit test:

```
$ uv run pytest tests/test_repo_compliance.py -q -k "TestSchemaRelationMap or duplicate_name"
7 failed, 3 passed, 196 deselected
```

The three that pass are deliberate pins of unchanged behaviour: an unreadable
remote joining a **sole** group, a declared `include_in_schema = false` remote
keeping its own config, and a single-config card listing a shared column once.

GREEN after the change: **33 passed** on the focused selection, **2144 passed, 9
skipped** on the full suite (`uv run pytest tests/ -q`, 84.12s).

## 3. The edits

### 3.1 `src/sofer/repo_compliance.py`

| Site | Change |
| --- | --- |
| module imports | `FileEntry` added to the `.model` import (ruff F821: the new helpers annotate it). |
| `_is_convertible_entry` (new) | The single "is this a table we can read" predicate: not recursive, convertible suffix. Consumed by the loop and by `_is_schema_eligible` (D4). |
| `_is_schema_eligible` (new) | `_is_convertible_entry` and `include_in_schema`. Defines the eligibility the classifier needs. |
| `_note_column_origin` (new) | Replaces the three duplicated dedup/`_dup_map` blocks: records the origin for the RC-R02 warning and never suppresses the column. The unused positional index in the old `seen_names` values is gone with it (it was written and never read). |
| `_build_schema_report_impl` | Loop now calls `_is_convertible_entry`; every branch always appends its `ColumnSchema` with its own `origin`. `seen_names: dict[str, str]`. |
| duplicate warning text | `using first occurrence.` → `each file keeps its own schema entries.` (the old text no longer described the code). |
| `build_schema_report` docstring | Returns section states one entry per `(origin, name)` and that the warnings never remove an entry. |
| `_schema_eligible_remotes` (new) | Classifies the planned remotes the schema report attempts to read, reusing `_remote_origin_aliases` for the remote↔entry matching (no second matching rule). |
| `group_remotes_by_schema` | New `schema_eligible` parameter and the D1 policy: `unknown` (eligible but unresolved) makes a multi-signature corpus ungroupable and never invents a group; `declared` (everything else unresolved) keeps its own group; a sole signature group absorbs both; the "signatures exist but fit no remote" fixture case keeps returning one group for everything, as before. |
| `schema_config_plan` | Passes `_schema_eligible_remotes(cfg, remotes, aliases)`. |
| `_features_for_group` | Takes `aliases`, resolves each group remote to its origin keys (D5), and lists each distinct column name once. The single-group path keeps every entry as before, deduped by name. |
| `_build_dataset_info` | Forwards `aliases` to `_features_for_group`. |
| Data Quality Notes | The empty-column list is deduped while preserving order. |

### 3.2 `openspec/specs/repo-compliance/spec.md`

Modified: § 3.3.6 (block re-stated in the `origin` format and asserting two
entries), RC-R05 (one entry per `(origin, name)` — the first-occurrence-wins
clause is replaced), RC-R06 (rationale rewritten; one row per entry; new
scenario), RC-R21 (per-origin display clause + RC-R21.09), RC-R23 (Grouping
resolves through the alias map; new **Remote classes (D1)** clause; `features`
dedup clause; four new scenarios). No requirement added or removed. The delta
lives at `specs/repo-compliance/spec.md` inside this change folder.

### 3.3 `tests/test_repo_compliance.py`

New `TestSchemaRelationMap` (8 tests) covering SC-1..SC-6; the inverted
`test_duplicate_name_yields_one_entry_per_origin`; five assertions that pinned the
old dedup updated (`TestDuplicateWarningRouting` ×2 and two earlier
`assert names == ["value"]` sites). The RC-R02 warning-routing assertions
themselves are untouched.

## 4. TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`. The carrier is nevertheless a
real red-then-green (§2): RED measured before the first source edit, GREEN after.

## 5. Risks

See `proposal.md` §5. The two that need the reviewer's attention: the Data Fields
shape change for multi-file corpora (R1) and the ungroupable outcome for a corpus
with an unreadable file (R3) — both deliberate, both pinned by tests, both named
in the spec delta.

## 6. Rollback

Revert-only; no state, no migration (§6 of the proposal).

## 7. Success criteria

SC-1..SC-7 of `proposal.md` §7.
