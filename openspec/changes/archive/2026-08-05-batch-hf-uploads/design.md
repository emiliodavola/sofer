# Design: Batch Hugging Face Uploads via `upload_folder`

## Technical Approach

Replace three sequential upload stages (compliance files, data loop, codebook loop) with a single
`HfApi.upload_folder(tmpdir, …)` call. The existing `tmpdir` expands from holding flat converted
.parquet + compliance files to holding a full mirror of the HF repository tree: data files in
their remote-relative paths, compliance at root, codebooks under `codebooks/`.

## Architecture Decisions

| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| Upload primitive | `upload_folder` vs `create_commit` API | `upload_folder` | Already wrapped (`_hf_upload_folder`, L98), resumable, built-in progress bar via `hf_xet` |
| tmpdir structure | Flat (current) vs mirror of HF repo | Mirror HF repo | `upload_folder(path_in_repo="")` uploads directory tree as-is; flat would lose remote paths |
| _hf_upload / _hf_upload_folder | Delete vs keep as legacy | Keep as legacy | Safe cleanup — no other callers, but removal is deferred to avoid churn. May remove in follow-up |
| Counter (`ok`/`fail`) | Per-file count vs batch pass/fail | Batch pass/fail with staged count | No per-file granularity from `upload_folder`. Report N files staged, ok=1 or fail=1 |
| Codebook staging | Copy via `shutil.copy2` to `tmpdir/codebooks/` | `shutil.copy2` | Simple, preserves metadata. Compatible with existing `shutil.rmtree(tmpdir)` cleanup |

## Data Flow

```
cfg.files ──→ conversion loop ──→ .parquet in tmpdir/<remote-path>/  (structured)
    │
    ├──→ compliance generation ──→ README.md, LICENSE in tmpdir/      (already there)
    │
    ├──→ codebook detection ──→ copy to tmpdir/codebooks/             (NEW)
    │                                    tmpdir/codebook.md
    │
    └──→ HfApi.upload_folder(tmpdir, …) ──→ HF Hub
         (single call replaces all individual upload_file calls)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/uploader.py` | Modify | Restructure staging: place .parquet in subdirs, copy codebooks, replace L930–L1012 with `upload_folder` |

## Detailed Changes in `uploader.py`

### 1. Conversion loop: place .parquet in remote-relative subdirs (L808–838)

Current: `_convert_to_parquet` places `.parquet` flat in `tmpdir/`.
Change: compute `parquet_remote` (e.g., `data/PROV/train.parquet`) and write to
`tmpdir / parquet_remote`, creating parent dirs via `parquet_path.parent.mkdir(parents=True, exist_ok=True)`.

### 2. Codebook staging (NEW, before upload_folder call)

After conversion + compliance generation (L906), walk `data/codebooks/` and `codebook.md`:
```python
if codebooks_dir.is_dir():
    for cb_file in sorted(codebooks_dir.rglob("*.md")):
        rel = cb_file.relative_to(data_dir)           # "codebooks/DPTO.md"
        dest = tmpdir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cb_file, dest)
if root_index.exists():
    shutil.copy2(root_index, tmpdir / "codebook.md")
```

### 3. Replace upload loops (L930–L1012)

Remove the three upload stages. Replace with:
```python
try:
    _hf_upload_folder(cfg.repo_id, tmpdir, "", cfg.repo_type)
    ok = 1
except Exception as exc:
    print(f"  \u2717  upload_folder failed: {exc}")
    fail = 1
```

The per-file NOT FOUND check moves to the staging phase (before conversion attempt).

### 4. Remove dry-run guard duplication (L918–928)

The `if dry_run: return 0` block at L918 already handles dry-run correctly. No change needed.

## Interfaces / Contracts

- `_hf_upload_folder(repo_id, local_path, remote_path, repo_type) → bool` — existing, unchanged
- `_hf_upload(repo_id, local_path, remote_path, repo_type) → bool` — preserved as legacy, no callers after this change
- `HfApi.upload_folder(folder_path, path_in_repo, repo_id, repo_type)` — HF Hub API, no wrapper change

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | tmpdir structure after staging | `tmp_path`, inspect directory tree, assert file paths |
| Unit | `upload_folder` is called with correct args | Mock `_hf_upload_folder`, verify call count = 1, verify args |
| Unit | `_hf_upload` is NOT called for staged files | Mock `_hf_upload`, verify call count = 0 |
| Unit | Codebook copying preserves directory structure | `tmp_path`, create mock codebook dir, verify `tmpdir/codebooks/` tree |
| Unit | `upload_folder` failure sets fail=1, cleans up | Mock to raise, verify return code, verify tmpdir cleaned |
| Regression | Existing upload tests still pass | `uv run pytest tests/ -q` — no behavior change for conversion, compliance, diff summary |

## Migration / Rollout

No migration required. The change is internal to `uploader.py` — no CLI flag changes, no TOML schema changes. Rollback is reverting `uploader.py` to the individual-upload version.

## Open Questions

None.
