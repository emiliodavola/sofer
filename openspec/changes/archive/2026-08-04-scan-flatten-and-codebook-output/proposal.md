# Proposal: Scan Flatten & Per-File Codebook Output

## Intent

`scan` copies `raw/sub/data.csv` → `data/raw/sub/data.csv`, preserving the full source directory and contradicting the flatten-first-level contract already specified in SCN-02/SCN-03. `codebook --all-files` collapses every file in a directory into a single `codebook_<fmt>.md`, silently overwriting same-format siblings, and only the single `cfg.codebook` file ever reaches HF. Fix: flatten scan output, give each file its own codebook under a dedicated `data/codebooks/` tree, and upload all codebooks to HF.

## Scope

### In Scope
- Scan flatten (first segment only): `raw/x.csv` → `data/x.csv`; `raw/Labels/y.csv` → `data/Labels/y.csv`; root files (`x.csv` → `data/x.csv`) unchanged. Remote mirrors data/: `raw/DPTO.csv` → `DPTO.csv`.
- Multi-source-dir collision (`A/x.csv` + `B/x.csv` → both `data/x.csv`): command fails with a clear error naming both sources. No dedup, no silent overwrite.
- `codebook --all-files`: per-file codebook under `data/codebooks/` mirroring data/ (e.g. `data/codebooks/DPTO.md`, `data/codebooks/Labels/etiquetas_a.md`); format suffix removed.
- Root index `codebook.md` preserved (CB-R04); per-file codebooks + root index uploaded to HF (uploader.py:984-988 currently uploads only `cfg.codebook`).
- README + CLI `help=` updated in the same commit (AGENTS.md rules 2, 7).

### Out of Scope
- Single-file `codebook <file>` (CB-R02) — unchanged.
- Configurable source-dir key (`source_dir`) — deferred.
- validate/quality/parquet-conversion behavior — untouched.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `scan`: SCN-02/SCN-03 flatten-first-level contract; SCN-06 new collision-failure requirement.
- `codebook`: CB-R03 per-file output layout (fixes the impossible "both → data/codebook.md" scenario); CB-R05 replaced by per-file-dir convention; CB-R04 index links updated.
- `repo-compliance`: upload() orchestration adds per-file codebooks + root index upload.

## Approach

1. Flatten helper `_flatten_first_level(relative)` in scanner.py; used by `merge_entries` (local + remote) and `copy_files`; `_cmd_scan` preview uses the same helper.
2. Collision pre-check: group discovered files by flattened destination; raise a clear error before any copy.
3. Rewrite `generate_all` (codebook.py:359-462): drop `dir_counts`/`fmt_label`; output = `data/codebooks/<data-rel-stem>.md`; root index links recomputed from actual outputs.
4. Upload: after data files, upload `data/codebooks/**` and root `codebook.md` (uploader.py ~984).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/scanner.py` | Modified | flatten helper; merge_entries/copy_files; collision error |
| `src/sofer/cli.py` | Modified | scan preview; codebook help= |
| `src/sofer/codebook.py` | Modified | generate_all layout; root index links |
| `src/sofer/uploader.py` | Modified | codebooks + index upload |
| `tests/test_scanner.py`, `tests/test_codebook.py` | Modified | 5 tests to new contracts |
| `openspec/specs/{scan,codebook,repo-compliance}/spec.md` | Modified | delta specs |
| `README.md` | Modified | CLI + codebook convention |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Remote paths change in already-published HF repos | High | Breaking change documented; only affects future scan/upload runs |
| 5 tests break (creates_subdirs_lazily, remote_uses_posix_separators, output_collision_uses_suffixes, generates_for_all_toml_entries, root_index_has_correct_links) | High | Update to new contracts in same change (strict TDD red→green) |
| Multi-folder flatten collision | Med | Explicit error listing conflicting sources |
| Stale index links after layout change | Low | Index regenerated from actual outputs |

## Rollback Plan

Revert the 4 modules + tests to HEAD~1; delete generated `data/codebooks/`; no migrations, no persistent state. For already-published HF repos, re-run upload after revert (additive file upload/delete only).

## Dependencies

None new — openpyxl/pyarrow already present.

## Success Criteria

- [ ] `raw/sub/data.csv` → `data/sub/data.csv`, remote `sub/data.csv`; root file `x.csv` → `data/x.csv`
- [ ] Colliding flatten sources fail with a clear error, exit 1
- [ ] `--all-files` writes one codebook per file under `data/codebooks/`; no `_csv` suffix
- [ ] Root index links to new paths; upload pushes per-file codebooks + index
- [ ] `uv run pytest tests/ -q` green (422+), ruff + mypy clean
