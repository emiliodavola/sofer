# Proposal — `2026-10-17-fix-scan-move-raw-mandatory`

> **Change** `2026-10-17-fix-scan-move-raw-mandatory` · issue **#339** · branch
> `fix/339-scan-move-raw-mandatory` from `dev@ec511e7` · store **hybrid**
> (this folder + Engram mirror).
>
> **Status:** implementation complete; archived inside the delivering PR
> (AGENTS.md rule 15).

---

## 1. Intent

The documented MCP chain (`sofer_init` → `sofer_scan_apply`) did not move loose
source files into `raw/`: the Phase-1 move was gated behind `move_loose`, which
defaulted to `false`. The default run therefore reproduced exactly the state
#152 was filed about — `raw/` empty, sources left loose next to the TOML, and
every `[[file]]` entry pointing at `cache/`, the tool-wide, sibling-shared
staging directory that `sofer publish --clean --clean-cache` deletes. The
registered sources were one authorized cleanup away from being the only copy.

On top of that, registering a nested loose file flattened it one segment
(`Labels/x.csv` → `cache/x.csv`) while the same file after the move registered as
`cache/Labels/x.csv`, so a second scan added a second entry for one source and
never removed the stale one: one file, two remotes, delivered twice.

The CLI already did the right thing (`sofer scan` runs Phase 1 unconditionally),
so the defect is precisely the CLI/MCP parity #152 accepted as its own criterion.

## 2. Scope

**In:** the mandatory move in both MCP scan tools; `move_loose` removed from the
tool schema; the registration key computed relative to the root that owns the
file; the `validate`/`prepare` gate that refuses a `cache/`-only registration
with no `raw/` source; the scan report naming such entries; the `scan` spec, both
READMEs, the CLI help and the phased instructions.

**Out:** a migration or repair command for configs a pre-fix scan already
doubled (the fix stops creating them and reports them; rewriting a generated
config is its own change with its own risk); any change to `sofer init`'s
`--move-existing` convenience; the `cache/` → `raw/` copy semantics of
`copy_files`.

## 3. Approach

1. `sofer_scan_apply` and `sofer_scan_dry_run` run Phase 1 unconditionally —
   `check_raw_collisions` abort before any move, then `move_to_raw` — matching the
   CLI. The move is never silent (the dry run previews it) and never optional.
2. `scanner.registration_path` keys each discovered file relative to the root
   that owns it: `raw/` for a file under `raw/`, the dataset root otherwise.
   `check_flatten_collisions`, `merge_entries` and `copy_files` all use it, so
   the key is a property of the file, not of where a scan found it.
3. `scanner.raw_source_for_local` is the single home for the `cache/` →
   `raw/` mapping; `DatasetValidator` refuses a `cache/`-only entry whose source
   is missing, and both scan adapters report those entries (bounded by
   `[tool.sofer] report_max_items`) without rewriting the TOML.

## 4. Affected specs

- `scan` — SCN-01 (discovery/keying), SCN-02 (TOML merge/key), SCN-07 (mandatory
  move in both surfaces) modified; three scenarios added. `scan` is a permanent
  declared-backlog spec, so no `## Test Mapping` row is owed and the registry is
  not edited.

## 5. Delivery

One branch, one delivery PR against `dev`, assigned to `@emiliodavola` with
`Closes #339`, archived inside that PR. Work-unit commits: the mandatory move and
the key rule; the enforcement gate and the stale-entry report.
