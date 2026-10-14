# Proposal — `2026-10-14-fix-bounded-quality-scan`

> **Change** `2026-10-14-fix-bounded-quality-scan` · issue **#290** · branch
> `fix/290-bounded-quality-scan` from `dev@4ca823e` · store **hybrid** (this file + the Engram
> mirror).
>
> **Status:** delivered in one PR and archived in the same branch (AGENTS.md rule 15).

---

## 1. Intent

`sofer validate` / `sofer prepare` cannot run on the reported 3.2 GB / 66.2 M-row corpus: a
`fail`-severity quality check forces a full **unsampled** pass over every row, and two per-row
accumulators grow without bound (16.1 GB RSS, killed at the OOM limit).

The fix has two halves, and both are needed:

1. **Bound every per-row accumulator.** The `empty_columns` bookkeeping becomes a per-column
   "seen non-empty" boolean (it was a distinct-value set — the largest accumulator); the
   `duplicates` hash table gets a config-owned cap; and the three finding lists stop growing at the
   report limits they are printed at.
2. **Make the full-scan decision explicit and config-owned.** Today it is a side effect of
   severity: *any* `fail` check — including the 8 KB `encoding_validation` probe — turns the single
   pass into an unsampled one. The scan becomes a tri-state policy (`auto` / `always` / `never`)
   that consults a config-declared set of checks which genuinely need every row.

## 2. Scope

### In scope

- `src/sofer/quality.py`: boolean `_col_nonempty`; capped `_dup_hashes`; capped finding lists;
  `_needs_full_scan()` predicate; tri-state full-scan policy; `partial` semantics for capped and
  sampled evidence.
- `src/sofer/config.py`: `quality_max_dup_tracking`, `quality_full_scan`,
  `quality_row_requiring_checks` as `[tool.sofer]` defaults; `QUALITY_FULL_SCAN_MODES` policy
  vocabulary; removal of the now-readerless `quality_value_preview_len`.
- `src/sofer/model.py`: optional per-dataset `[quality]` policy table (`full_scan`, `max_sample`)
  and the `QualityConfig.full_scan` field, which wins over the tool-wide default when set.
- `pyproject.toml`, `docs/configuration.md`: the three new keys; removal of `quality_value_preview_len`.
- `README.md` / `README_ES.md`: the bounded strategy, the new knobs and what `partial` means.
- `tests/test_quality.py`, `tests/test_config.py`: the bounded-accumulator, cap, policy and config
  tests.
- The `data-quality` spec delta for the sampling/full-scan clause and the `partial` contract.

### Out of scope (non-goals)

- **No per-check multi-pass scan.** The validator stays deliberately single-pass
  (`openspec/project.md`); rescanning a multi-GB file once per check is the rejected alternative
  recorded in `design.md` §4.
- **No eviction from the duplicate table.** The cap stops inserting new hashes; it never drops the
  first-seen row number a `Row a = Row b` message needs (D2).
- **No change to the duplicate finding shape** — the file-scoped pair emission owned by the merged
  #293 change is left intact; #290 only caps how many entries can accumulate (see the rebase note in
  `tasks.md`).
- No version bump, no new dependency, no CLI flag, no Test Mapping row (`data-quality` is a permanent
  declared-backlog spec), no registry edit.

## 3. Settled decisions

The five decisions D1–D5 pre-date implementation and live in `odd/tasks/bounded-quality-scan.md`;
`design.md` records them with their rationale, plus the two config-surface decisions taken during
implementation (the removal of `quality_value_preview_len` and the `cap` arithmetic).

## 4. Success criteria

| ID | Criterion |
| --- | --- |
| SC-1 | RED before the fix, GREEN after: the focused selection goes from **24 failed / 5 passed** to **all passed** |
| SC-2 | Per-row memory is provably independent of dataset size: the three finding lists and the hash table stay at their caps on a large synthetic stream (`test_accumulator_sizes_do_not_grow_with_dataset_size`) |
| SC-3 | `quality_full_scan = never` keeps `max_sample` with a `fail` check active and marks the affected finding `partial`; `always` scans everything; an `encoding_validation`-only `fail` never forces the full pass |
| SC-4 | The full suite is green with the expected delta and no other test changes status |
| SC-5 | `cli.py` / `scanner.py` / `prepare.py` / `publish.py` stay at **100.00%**, no `# pragma: no cover` is added, and coverage TOTAL does not drop below the base |
| SC-6 | `scripts/check_test_mapping.py` exits 0 and the registry is untouched (`data-quality` stays a permanent declared-backlog spec) |
