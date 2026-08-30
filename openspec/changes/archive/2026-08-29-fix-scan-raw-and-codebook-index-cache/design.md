# Design: fix-scan-raw-and-codebook-index-cache

## Technical Approach

Two fixes. **Scan**: turn copy-only (`raw/→cache/` flatten) into MOVE-then-copy. Phase 1 discovers loose files outside `raw/`/`cache/`/`EXCLUSIONS`, checks collisions, `shutil.move` preserving `relative_to(base_dir)` into `raw/`. Phase 2 is unchanged `discover→check_flatten_collisions→merge→copy→write`. **Codebook**: one line at `codebook.py:441` from `base_dir/"codebook.md"` to `write_root/"codebook.md"` so standalone index colocates with `cache/codebooks/*`. Honors `--dry-run`/`--force`/`[y/N]` atomically, reuses `config.RAW_DIR`/`OUTPUT_DIR`/`CODEBOOKS_DIR`.

## Architecture Decisions

### Decision: Scan MOVE shape

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Flatten MOVE (`raw/<flat>`) | Mangles `a/b/x.csv→raw/x.csv` | Rejected |
| Preserve tree (`raw/<relative_to(base_dir)>`) | Keeps subdirs, `mkdir -p` parents, per spec | **Chosen** |
| Scaffold-only (no MOVE) | Contradicts MOVE requirement | Rejected |

### Decision: Collision & atomicity

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Check during move | Partial moves, TOML drift | Rejected |
| Pre-flight check all `dest=raw_dir/rel` before any `shutil.move` | Atomic, fail-fast | **Chosen** |

Helper `check_raw_collisions(candidates, raw_dir, base_dir)` raises `ValueError` naming both paths; `_cmd_scan` exits 1 before any mutation.

### Decision: Discovery scope

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Single `discover_files` call | Conflates MOVE vs cache sources | Rejected |
| Two-phase: P1 `EXCLUSIONS‖{RAW_DIR,OUTPUT_DIR}` for MOVE; P2 `EXCLUSIONS‖{OUTPUT_DIR}` for cache (after moves) | Separation, `.venv/.git` never moved | **Chosen** |

### Decision: Dry-run / force / prompt

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Prompt only for cache copy | Loose files moved silently | Rejected |
| Single prompt for `→ raw/...` preview; `--dry-run` prints both previews, no mutation; `--force` skips | One gate, atomic abort | **Chosen** |

### Decision: Codebook routing

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Dual-write `base_dir`+`cache` | Drift, contradicts CB-R04 | Rejected |
| `root_path=write_root/"codebook.md"` when `output_dir is None` | Colocated, consistent with `build/` | **Chosen** |

## Data Flow

```
Scan: base_dir/** ──P1 discover(excl raw/cache/EXC)──→ loose=[a.csv, sub/b.xlsx] (5 exts only)
        ├─ raw_dir.mkdir(exist_ok) [skip dry-run]
        ├─ check_raw_collisions(loose→raw/<rel>) ─× exit 1, no mutation
        ├─ prompt/--force/--dry-run ─ N/dry-run → exit 0, no mutation
        ├─ for src: dest.parent.mkdir; shutil.move(src,dest)
        └─P2 discover(excl cache/EXC)→ check_flatten→ merge→ copy(raw→cache flatten)→ write

Codebook: generate_all(cfg, None) → write_root=base_dir/cache, root=write_root/codebook.md ← FIX
          generate_all(cfg, build) → write_root=build.resolve(), root=write_root/codebook.md
          codebooks_dir=write_root/codebooks; links=out.relative_to(write_root) → codebooks/<stem>.md
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/scanner.py` | Modify | Add `check_raw_collisions` + `move_to_raw` (`shutil.move`, `relative_to`, `mkdir`); update docstring |
| `src/sofer/cli.py` | Modify | Rewrite `_cmd_scan` to MOVE-then-copy; update parser help |
| `src/sofer/codebook.py:441` | Modify | `root_path=write_root/"codebook.md"` when `output_dir is None` |
| `tests/test_codebook.py` | Modify | 6 assertions (`:556,:573,:591,:679,:772,:806`) to `cache/codebook.md` |
| `tests/test_scanner.py` | Modify | `TestSourceLayoutCopyOnly`/`TestIntegration` for MOVE semantics |
| `tests/test_cli.py` | Modify | Scan e2e for dry-run/collision/prompt |
| `README*.md`, `docs/configuration.md` | Modify | Layout diagram `raw/→cache/→build/` |
| `.gitignore` | Modify | Ensure `cache/` ignored |

## Interfaces / Contracts

```python
def check_raw_collisions(candidates: list[Path], raw_dir: Path, base_dir: Path) -> None: ...
def move_to_raw(candidates: list[Path], base_dir: Path, raw_dir: Path, *, dry_run: bool = False) -> list[tuple[Path, Path]]:
    """dest=raw_dir/src.relative_to(base_dir); mkdir parents; shutil.move; no flatten"""
```

`_cmd_scan`: atomic — collision/`N` aborts before first move, TOML untouched; `--dry-run` prints `→ raw/<rel>` no mutation; 5 exts via `SUPPORTED_FORMATS`.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit scanner | `check_raw_collisions` names both paths; `move_to_raw` preserves tree, removes source | pytest tmp_path |
| Unit codebook | `generate_all` standalone → `cache/codebook.md` + `cache/codebooks/*`, nested `Labels/` links | pytest |
| Integration | `scan --dry-run`/`--force`/`N` abort atomic, idempotent second run | `_cmd_scan(Namespace)` |
| E2E | `a.csv`+`sub/b.xlsx` → `raw/a.csv`+`raw/sub/b.xlsx` gone, `cache/` copies, `.venv`/`f.txt` untouched | tmp_path |

6 codebook tests + scanner suite updated together.

## Migration / Rollout

No migration. Single-commit revert. Breaking: `codebook --all-files` consumers must read `cache/codebook.md` (release note). `cache/` gitignored.

## Open Questions

- [ ] Non-interactive `scan` without `--force` should auto-abort with hint like `init --move-existing`?
- [ ] Ensure `raw/.gitkeep` when empty?
