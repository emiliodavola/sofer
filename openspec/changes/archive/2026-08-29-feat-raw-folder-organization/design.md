# Design: Raw Folder Organization

## Technical Approach

Establish `raw/` as the tracked source root for `raw/DPTO.csv → cache/DPTO.csv → build/*.parquet`. Minimal code: add `raw_dir="raw"` as a tool-wide `[tool.sofer]` bootstrap key mirroring `output_dir` (cwd walk-up via `reload(None)`), make `sofer init` scaffold `raw/` idempotently with opt-in `--move-existing`, keep `scan` copy-only by reusing `flatten_first_level` / `check_flatten_collisions`. Docs reconcile `data/`→`cache/` drift and add the `raw→cache→build` diagram. No `raw/` in `EXCLUSIONS`; no per-dataset `raw_dir`.

Maps to proposal phases B+C: config bootstrap, init scaffolding, scan doc-only, docs sync.

## Architecture Decisions

### Decision: `raw_dir` as tool-wide bootstrap key

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Hardcode `"raw"` | No config, violates AGENTS.md #1 | Rejected |
| `[dataset] raw_dir` per-dataset | Needs schema/validation | Deferred |
| `[tool.sofer] raw_dir` walk-up | Mirrors `output_dir`, TC-07 precedent | **Chosen** |

Reuse `_DEFAULTS`+`_discover`+`reload(None)`; override via one TOML edit.

### Decision: `init` always creates `raw/`; move is opt-in

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Auto-move on `init`/`scan` | Surprising, needs two-stage guards | Rejected |
| Never create `raw/` | Docs-only, leaves root mixed | Rejected |
| `mkdir -p raw/` + `--move-existing` | Idempotent, opt-in safe | **Chosen** |

`exist_ok=True` is harmless; move needs consent + preview + collision check.

### Decision: Scanner unchanged; `raw/` not excluded

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Add `raw` to `EXCLUSIONS` | Scan empty, breaks discovery | Rejected |
| Filter at handler | Unnecessary, already strips `raw/` | Rejected |
| Keep `EXCLUSIONS`; only `cache` excluded via `EXCLUSIONS\|{OUTPUT_DIR}` | Minimal diff | **Chosen** |

`flatten_first_level` (`scanner.py:29`) + `cli.py:289` already correct.

### Decision: `--move-existing` scope depth-1 + `SUPPORTED_FORMATS`

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Recursive move | Moves nested datasets unpredictably | Rejected |
| All extensions | Moves `notes.txt`, `README.md` | Rejected |
| Depth-1, `SUPPORTED_FORMATS` (`.csv/.tsv/.parquet/.xlsx/.jsonl`), exclude `cache/build/raw/EXCLUSIONS` children | Precise, matches `scan` registry | **Chosen** |

**Rationale**: Matches `scan` registry; avoids moving `notes.txt`.

## Data Flow

```
sofer init my-ds [--move-existing]
  → config.reload(None) cwd walk-up → RAW_DIR
  → mkdir -p RAW_DIR (idempotent)
  → (--move-existing) depth-1 SUPPORTED_FORMATS
      → check_flatten_collisions → --dry-run/--force/!isatty/prompt → shutil.move

sofer scan (copy-only, no move)
  raw/DPTO.csv ──flatten_first_level──► cache/DPTO.csv ──prepare──► build/*.parquet
  raw/Labels/a.csv ─────────────────► cache/Labels/a.csv
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/config.py` | Modify | `_DEFAULTS["raw_dir"]="raw"`, `RAW_DIR`, update TC-07 note |
| `pyproject.toml` | Modify | `[tool.sofer] raw_dir="raw"` |
| `src/sofer/cli.py` | Modify | `_INIT_TEMPLATE` → `# Source files → raw/ (scan copies to cache/)`; `_cmd_init` mkdir-p + `--move-existing`/`--dry-run`/`--force`, depth-1 `SUPPORTED_FORMATS`, `check_flatten_collisions`, isatty guard; parser `help`/`description` |
| `src/sofer/scanner.py` | Modify | Docstring only; `EXCLUSIONS` unchanged |
| `docs/configuration.md` | Modify | Bootstrap keys + `raw/→cache/→build/` diagram |
| `README.md` + `README_ES.md` | Modify | Layout + diagram; `data/`→`cache/`; sync §13 |

## Interfaces / Contracts

```python
# config.py — new constant (mirrors OUTPUT_DIR)
_DEFAULTS["raw_dir"] = "raw"
RAW_DIR: str = _DEFAULTS["raw_dir"]  # rebound by reload()

# cli.py — init flags
sofer init <name> [--move-existing] [--dry-run] [--force]
# --move-existing: move depth-1 SUPPORTED_FORMATS files into RAW_DIR
# --dry-run: list a.csv → raw/a.csv, no mkdir/move
# --force: skip prompt; also skipped when not sys.stdin.isatty()

# scanner.py — reuse (no new API)
def flatten_first_level(relative: Path) -> Path: ...  # raw/a.csv → a.csv
def check_flatten_collisions(discovered: list[Path], base_dir: Path) -> None: ...
EXCLUSIONS: frozenset[str]  # unchanged; raw never added
```

Exit codes: 0 success/idempotent, 1 on collision or TOML exists.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `raw_dir` default/override/cwd walk-up | `test_config.py` — temp trees + `reload(None)` |
| Unit | `init` mkdir, depth-1 filter, collision, dry-run, !isatty, prompt | `test_cli.py` — `tmp_path`, monkeypatch `isatty`/`input` |
| Unit | `scan` discovers `raw/`, excludes `cache` | `test_scanner.py` + new scenario |
| Integration | `init --move-existing --force` → `scan --force` → `cache/` | `tmp_path` e2e |

## Migration / Rollout

No migration. Empty `raw/` harmless; revert commit restores behavior. Move reversible (`raw/* → .` + `scan --force`). `prepare`/`publish` unchanged. Follow-up `scan --migrate-raw` deferred. Bootstrap: `cli.main` `reload(None)` Phase-0 before parser; dataset commands re-resolve via `DatasetConfig.from_toml` (TC-04/05).

## Open Questions

- [ ] Confirm flag spelling `--move-existing` vs `--organize` — proposal locks `--move-existing`.
- [ ] Whether to surface `raw_dir` in `sofer init --help` extended text beyond `raw/→cache/→build/` — help budget.
