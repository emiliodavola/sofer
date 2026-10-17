# Design — `2026-10-17-fix-scan-move-raw-mandatory`

> **Change** `2026-10-17-fix-scan-move-raw-mandatory` (issue **#339**) · branch
> `fix/339-scan-move-raw-mandatory` from `dev@ec511e7` · store **hybrid**.

---

## 1. The defect, precisely

`sofer_scan_apply` (`mcp_server.py`) wrapped the whole Phase 1 in

```python
moved: list[tuple[Path, Path]] = []
if move_loose:                      # move_loose: bool = False
    loose = discover_files(base_dir, ext_set, exclude_dirs=exclude_move)
    ...
    moved = move_to_raw(loose, base_dir, raw_dir, dry_run=False)
```

and the CLI never had that gate — `cli.py:550-593` has always run Phase 1
unconditionally. The default MCP run therefore copied loose files straight into
`cache/` and registered `local = "cache/<file>"` with no tracked source.

The second half was the key. `merge_entries` registered
`flatten_first_level(src.relative_to(base_dir))`, which drops a **fixed** first
path segment. That is only correct while discovery happens to be `raw/`-rooted:

| discovered as | registered key | cache destination |
| --- | --- | --- |
| loose `Labels/x.csv` (pre-move) | `x.csv` | `cache/x.csv` |
| `raw/Labels/x.csv` (post-move) | `Labels/x.csv` | `cache/Labels/x.csv` |

Two keys, one file. Reproduced with the real helpers:
`3 entries for 2 files`, and the stale `cache/x.csv` entry is never removed.

## 2. The rule that replaces it

`registration_path(src, base_dir, raw_dir)` returns `src.relative_to(raw_dir)`
when the file lives under `raw/`, and `src.relative_to(base_dir)` otherwise. The
key is therefore a property of the file's own root, so a loose file and the same
file after the move produce **the same** key, and `scan → move → scan` registers
nothing new. For a `raw/`-rooted file the result is identical to the old rule
(the segment dropped is literally `raw`), which is why the spec's SCN-02
"Flattened paths" scenario still holds.

`check_flatten_collisions`, `merge_entries` and `copy_files` share it, so the
destination, the collision guard and the registration cannot disagree.

## 3. The tracked-source gate

`cache/` is disposable and shared. `raw_source_for_local(local, …)` maps a
declared `cache/<key>` back to `raw/<key>`; when that source is missing the entry
has no tracked copy. `DatasetValidator._check_cache_only_registrations` makes it
an **error** (so `validate` and `prepare` refuse, exit 1) naming the missing
`raw/` path and the repair; both scan adapters print the same finding as a
warning bounded by `report_max_items`. `raw_source_for_local` is the single home
(rule 4) of that mapping for both consumers.

## 4. Decisions

- **D1 — `move_loose` is removed, not defaulted to `true`.** A parameter that
  must always be `true` is a lie in the schema, and leaving it accepts
  `move_loose=false` as a silent route back to the reported state. Documented as
  a breaking change (rule 12, pre-1.0).
- **D2 — previewable, never promptable, on the MCP channel.** `sofer_scan_dry_run`
  keeps previewing the move; the CLI keeps its `[y/N]` gate or `--force`.
- **D3 — raw/-relative key, not "drop the first segment".** See §2.
- **D4 — the gate refuses; it does not rewrite the TOML.** A silent rewrite hides
  a state the operator must see, and the repository has no format-preserving
  array-of-tables writer outside `meta_edit.py`.
- **D5 — legacy duplicates are reported, not mutated.** The fix stops creating
  them; a repair command is a separate change.

## 5. Invariants the change must preserve

- `sofer scan` (CLI) behaviour is unchanged: same Phase 1, same prompt/`--force`
  gate, same collision abort, same preview text.
- `raw/DPTO.csv` → `cache/DPTO.csv`, `remote = "DPTO.csv"` (SCN-02 unchanged).
- A re-scan of an unchanged tree is byte-identical and registers nothing
  (SCN-05, SCN-08).
- `convert_to_parquet`, `--ext`, `--dry-run` and the symlink guard are untouched.

## 6. Residual risks

- The gate is fail-closed on configs a pre-fix scan produced: a dataset whose
  entries point into `cache/` with no `raw/` source now fails `validate` until it
  is re-scanned. That is the requested behaviour, and the message names the
  repair, but it is a behaviour change for existing users and belongs in the
  release notes.
- `check_flatten_collisions` can no longer fire in the scan flow (two distinct
  sources cannot share a key once the move has run); it keeps its force for a
  caller that passes mixed roots, and the reachable collision is the `raw/` one
  Phase 1 aborts on. Covered by a unit test with a mixed-root input.
