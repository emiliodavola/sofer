# Tasks: fix-schema-relation-map

**Change** `2026-10-15-fix-schema-relation-map` (GitHub **#304**) · branch
`fix/304-schema-relation-map` from `dev@fad1b00` · store **hybrid**.

**One-line outcome:** every planned remote gets a signature computed from its own
columns, one canonical `origin -> remote` relation drives grouping, `features`
and row counts identically, and a remote that could not be read never invents a
config group.

---

## TDD posture — stated honestly

`openspec/config.yaml` sets `strict_tdd: false`. The carrier is nevertheless a
real red-then-green, recorded before any source edit:

- **RED (measured):**
  `uv run pytest tests/test_repo_compliance.py -q -k "TestSchemaRelationMap or duplicate_name"`
  → **7 failed, 3 passed, 196 deselected**. The failures are the contract itself:
  `['data/first.csv'] != ['data/first.csv', 'other/second.csv']` (the global
  dedup), `plan == [persona_2010, hogar_2010, persona_2022]` where two configs are
  required, empty `features` per group, an invented group for an unreadable
  remote where no `configs` is required, one Data Fields block instead of three,
  and `Empty columns: VACIO, VACIO`.
- **GREEN (measured):** the three focused classes plus the whole module →
  **33 passed**; the full suite → **2144 passed, 9 skipped** in 84.12s
  (`uv run pytest tests/ -q`, run after `rm -f .coverage` — the stale local data
  file from 2026-10-09 is the subject of #305 and would have failed the
  coverage-contract guard for an unrelated reason).
- **REFACTOR:** no further target; the eligibility predicate, the classifier, the
  alias map and the features builder are each single shared helpers (AGENTS.md
  rule 4).

---

## Tasks

| # | Task | State | Evidence |
| --- | --- | --- | --- |
| T1 | RED: two same-schema tables + one different table → one entry per origin and **two** configs | done | `7 failed, 3 passed` (focused run) |
| T2 | RED: multi-group card on the CSV-fallback path carries non-empty per-group `features` | done | same RED run (`[] == ['PROV','ANO']`) |
| T3 | RED: an unreadable eligible remote makes the corpus ungroupable; a declared non-schema remote keeps its own group | done | same RED run + a green pin for the declared class |
| T4 | Per-`(origin, name)` collection; `_dup_map`/RC-R02 output preserved | done | `_note_column_origin`, three dedup `continue`s removed |
| T5 | Shared eligibility predicate + remote-class classifier in grouping | done | `_is_convertible_entry`, `_is_schema_eligible`, `_schema_eligible_remotes`, `group_remotes_by_schema` |
| T6 | `aliases` threaded into `_features_for_group` (name-deduped); Data Quality Notes dedup | done | `_features_for_group(..., aliases)`, `all_empty` dedup |
| T7 | Spec delta + canonical `repo-compliance` spec: RC-R05, § 3.3.6, RC-R06, RC-R21, RC-R23 | done | `openspec/specs/repo-compliance/spec.md` |
| T8 | Gates: focused tests, full suite, ruff/format/mypy/pyright, mapping checker, archive | done | see the verify evidence in `archive-report.md` |
| T9 | Commit the work units on the branch | done | see `archive-report.md` |
| T10 | Push + PR → `dev` (assignee `emiliodavola`), `Closes #304` | pending | user decision — not part of this branch's commits |

## Notes

- `tests/test_repo_compliance.py` pins the changed contract in three places that
  had asserted the old dedup (`test_duplicate_name_yields_one_entry_per_origin`,
  `TestDuplicateWarningRouting::test_one_duplicate_individual_warning`,
  `::test_four_duplicates_summary`) and in two earlier `assert names == ["value"]`
  sites; all five were updated in the same commit as the behaviour, with the
  RC-R02 warning-routing assertions left intact.
- The user-facing message `using first occurrence.` was replaced with
  `each file keeps its own schema entries.` because it no longer describes what
  the code does (AGENTS.md rule 7).
