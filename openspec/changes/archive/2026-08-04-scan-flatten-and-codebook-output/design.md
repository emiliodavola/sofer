# Design: Scan Flatten & Per-File Codebook Output

## Technical Approach

Three coordinated changes: (1) `scanner.py` gains a first-segment flatten helper shared by `merge_entries`, `copy_files` and the CLI preview, plus a collision pre-check that fails before any copy; (2) `generate_all` in `codebook.py` writes one codebook per file under `data/codebooks/<rel-stem>.md`, writing codebooks for all non-colliding files and failing at the END (exit 1, colliding sources listed) when files resolve to the same output path; (3) `uploader.py` replaces the legacy `cfg.codebook` upload with an orchestrated upload of the root index + per-file codebooks, ordered after the data files. No hardcoded path literals — the codebooks directory name is a `[tool.sofer]` key. Maps to SCN-02/SCN-03/SCN-06, CB-R03/CB-R04, RC-C01.

## Architecture Decisions

| Decision | Options | Choice | Rationale |
|----------|---------|--------|-----------|
| Flatten helper location | (A) new shared `_paths.py`, (B) `scanner.py` public fn | **B** — `flatten_first_level(relative)` in `scanner.py` | Only `scan` flattens (one-module-per-concern, AGENTS.md 10). Shared by `merge_entries` + `copy_files`; `cli.py` imports it for the preview, so it is public (docstring mandate) to avoid cross-module private imports. |
| Flatten semantics | drop first segment vs. string strip | **Drop first segment**: `Path(*parts[1:])`; `len(parts) <= 1` → unchanged | Matches SCN-02 verbatim: `raw/DPTO.csv` → `DPTO.csv`, `raw/sub/data.csv` → `sub/data.csv`, root `x.csv` → `x.csv`. Nested segments preserved. |
| Scan collision gate | (A) inside `copy_files`, (B) standalone `check_flatten_collisions()` called in `_cmd_scan` | **B** — run right after discovery, before merge/prompt | Must fail before ANY copy and before TOML mutation; raises `ValueError` listing every colliding destination with all sources; CLI catches → stderr → exit 1 (existing error boundary). Runs for `--dry-run` too, so the preview reports the failure. |
| Codebook rel-stem derivation | (A) only files under `data/`, (B) under `data/` → rel to data dir, else rel to config dir | **B** | Spec examples cover `data/` only, but `[[file]]` entries may point outside it. Fallback to `relative_to(base_dir)` keeps deterministic names (`a.csv` → `data/codebooks/a.md`). `with_suffix(".md")` replaces only the last suffix (multi-suffix → `PROV.csv.md`). |
| Codebook collision | (A) partial write: non-colliding codebooks written, then fail at end (exit 1) listing colliding sources; (B) atomic abort, no writes | **A** (closed decision) | CB-R03's minimum IS this behavior: colliding files MUST get no codebook, error names sources, exit 1 — the spec constrains only colliding files, not non-colliding ones. Atomic abort rejected by user decision. Scan's SCN-06 atomic gate (fail before ANY copy) is UNCHANGED and applies only to scan's multi-folder flatten collision — deliberately different policies. Partial `codebooks/` tree is overwritten by the next successful run. |
| Upload orchestration | legacy `cfg.codebook → codebook/{name}` vs. RC-C01 | **RC-C01** | Delta supersedes legacy. Model field kept for TOML parse compatibility; uploader ignores it. Remote = path relative to data dir (espejo local): `data/codebooks/DPTO.md` → `codebooks/DPTO.md`; root index → `codebook.md`. Missing artifacts skipped silently. |
| Codebooks dir name | hardcoded `"codebooks"` vs. config key | **`[tool.sofer] codebooks_dir`** (default `"codebooks"`) | AGENTS.md rule 1 — no hardcoded literals. `config.py` exposes `CODEBOOKS_DIR`; `codebook.py` and `uploader.py` both read it. Remote prefix is derived from the local layout, not configurable. |

## Data Flow

```
scan:         discover_files → check_flatten_collisions (fail BEFORE any copy → exit 1)
              → merge_entries (local="data/<flat>", remote=flat posix)
              → copy_files (dest = data_dir/<flat>) → write_toml

codebook --all-files:  collect valid entries → pre-compute output paths
              → partition colliding vs non-colliding
              → write data/codebooks/<rel-stem>.md for non-colliding files
              → collisions? → error naming colliding sources → exit 1 (no index)
              → else → write root codebook.md index (links recomputed from outputs)

upload:       data files loop → walk data/codebooks/**/*.md (sorted)
              → upload each as rel-to-data-dir → upload codebook.md
              (missing dir/index → skipped silently, exit unaffected)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/scanner.py` | Modify | Add `flatten_first_level` + `check_flatten_collisions`; `merge_entries`/`copy_files` use the helper |
| `src/sofer/cli.py` | Modify | `_cmd_scan`: collision gate + flattened preview + `help=`; `_cmd_codebook`: catch `ValueError` → exit 1; codebook `help=` |
| `src/sofer/codebook.py` | Modify | Rewrite `generate_all`: drop `dir_counts`/`fmt_label`, per-file layout, partition colliding/non-colliding, write non-colliding codebooks then fail at end listing colliding sources, index links from actual outputs |
| `src/sofer/uploader.py` | Modify | Remove legacy `cfg.codebook` upload; add RC-C01 codebook upload after data loop; `_repo_diff_summary` lists codebook remotes; docstring |
| `src/sofer/config.py` | Modify | `CODEBOOKS_DIR` constant + default |
| `pyproject.toml` | Modify | `[tool.sofer] codebooks_dir = "codebooks"` |
| `tests/test_scanner.py` | Modify | 2 tests to flattened contract + new collision/flatten tests |
| `tests/test_codebook.py` | Modify | 3 tests to new layout + new rel-stem/collision tests |
| `tests/test_uploader.py` | Modify | 2 codebook tests → RC-C01 scenarios |
| `README.md` | Modify | Command table, scan description, batch-generation section |

## Interfaces / Contracts

```python
# scanner.py
def flatten_first_level(relative: Path) -> Path:
    """Drop the first segment; root-level paths are returned unchanged."""

def check_flatten_collisions(discovered: list[Path], base_dir: Path) -> None:
    """Raise ValueError naming each colliding destination and its sources."""

# merge_entries: dest = data_dir / flatten_first_level(relative)
#   local = "data/" + flat.as_posix(); remote = str(PurePosixPath(flat))
# copy_files:    dest = data_dir / flatten_first_level(relative)

# codebook.generate_all(cfg) -> list[str]
#   writes codebooks for all non-colliding files, then raises ValueError on
#   same-output collision listing colliding sources (CLI → exit 1); the root
#   index is written only when there are no collisions; returns written paths
#   incl. index on success

# upload(cfg, ...) -> int
#   order: data files → per-file codebooks → root index; 0/1 exit
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit — flatten | root file, single dir, nested dirs, multi-suffix | `tmp_path` tree + exact `Path` assertions |
| Unit — scan collision | `A/x.csv` + `B/x.csv` → error names both, no copy, no TOML mutation | direct `check_flatten_collisions` call + `_cmd_scan` integration → exit 1 |
| Unit — merge/copy | flattened `local`/`remote`, lazy subdirs, dry-run | existing tests updated to new dests |
| Unit — codebook | rel-stem under `data/`, outside `data/`, same-stem collision (exit 1; colliding files listed AND no codebook written for them; non-colliding files written to disk), nested file, skips | `DatasetConfig.from_toml` + `generate_all` (raises) + CLI exit code + `tmp_path` disk assertions |
| Unit — upload | order (data before codebooks), root index + per-file remotes, missing artifacts skipped, legacy `cfg.codebook` not uploaded | monkeypatched `_api.upload_file` recording `path_in_repo` |
| CLI | scan preview shows flattened paths; codebook `help=` text | capsys + parser assertions |

## Migration / Rollout

No data migration. Breaking change: remote HF paths for already-published repos (documented in RC-C01); affects only future `scan`/`upload` runs. Rollback: revert the 4 modules + tests, delete generated `data/codebooks/` (proposal §Rollback Plan).

## Open Questions

- [ ] When legacy `cfg.codebook` is set, should `upload` print a deprecation notice to aid migration?
