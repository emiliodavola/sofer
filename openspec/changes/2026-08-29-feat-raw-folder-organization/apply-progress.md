# Apply Progress: 2026-08-29-feat-raw-folder-organization

**Change**: `2026-08-29-feat-raw-folder-organization`
**Branch**: `feat/raw-folder-organization`
**Mode**: Standard
**Date**: 2026-08-29
**Artifact store**: both (filesystem + engram)

## Implementation Progress

**Change**: 2026-08-29-feat-raw-folder-organization
**Mode**: Standard

### Completed Tasks

- [x] 1.1 Add `_DEFAULTS["raw_dir"]="raw"` + `RAW_DIR` in `src/sofer/config.py`
- [x] 1.2 Add `raw_dir = "raw"` in `pyproject.toml` `[tool.sofer]`
- [x] 1.3 Verify `reload(None)` cwd walk-up rebinds `RAW_DIR` via `_discover` (TC-10/TC-07)
- [x] 2.1 Update `_INIT_TEMPLATE` in `src/sofer/cli.py` -> `# Source files -> raw/ (scan copies to cache/)`
- [x] 2.2 Extend `_cmd_init`: `mkdir -p RAW_DIR` idempotent (`exist_ok=True`) before TOML write
- [x] 2.3 Implement `--move-existing`: depth-1 `SUPPORTED_FORMATS`, `check_flatten_collisions` pre-move, `--dry-run` preview, `--force`|`not isatty` guard, `shutil.move`
- [x] 2.4 Update `_build_parser` `init`: add `--move-existing`/`--dry-run`/`--force` flags + `raw/->cache/->build/` help
- [x] 2.5 Update `src/sofer/scanner.py` docstring for `raw/->cache/->build` copy-only; `EXCLUSIONS` unchanged
- [x] 3.1 Verify `cli.main` Phase-0 `reload(None)` rebinds `RAW_DIR` before parser; dataset cmds re-resolve via `DatasetConfig.from_toml`
- [x] 3.2 Confirm `scan` exclude `EXCLUSIONS|{OUTPUT_DIR}` only; `raw/` discoverable, `cache/` excluded; flatten `raw/DPTO.csv->cache/DPTO.csv`
- [x] 4.1 `tests/test_config.py`: `raw_dir` default `"raw"` (TC-10), `pyproject.toml` override, cwd vs dataset-dir precedence via temp trees + `reload(None)`
- [x] 4.2 `tests/test_cli.py` init: idempotent mkdir, depth-1 filter, collision fail, `--dry-run` no mutation, `--force`/`not isatty`/`N` abort (CLI-R07)
- [x] 4.3 `tests/test_scanner.py`: `raw/a.csv` discovered, `cache/a.csv` excluded, `EXCLUSIONS` skip, `--ext` filter (SCN-01/03)
- [x] 4.4 E2E `tmp_path`: `init --move-existing --force` -> `scan --force` -> `cache/` flattened, `raw/` untouched (SCN-02/03/06)
- [x] 5.1 `docs/configuration.md`: add `raw_dir` to bootstrap keys (cwd-only) + `raw/->cache/->build` diagram
- [x] 5.2 `README.md` Directory layout: `raw/(tracked)->cache/->build/` + `raw/DPTO.csv->cache/DPTO.csv` diagram
- [x] 5.3 `README_ES.md` mirror 5.2 per §13 (same commit, English technical content)
- [x] 5.4 Verify: `uv run ruff check --fix . && uv run ruff format . && uv run mypy src/ && uv run pytest -q`

### Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `src/sofer/config.py` | Modified | Added `_DEFAULTS["raw_dir"]="raw"` and `RAW_DIR` constant, updated cache/raw comment |
| `pyproject.toml` | Modified | Added `raw_dir = "raw"` under `[tool.sofer]` |
| `src/sofer/cli.py` | Modified | Updated `_INIT_TEMPLATE` with `raw/` guidance, rewrote `_cmd_init` with `mkdir -p RAW_DIR`, `--move-existing` depth-1 `SUPPORTED_FORMATS`, `check_flatten_collisions`, `--dry-run`/`--force`/`isatty` guards, `shutil.move`; updated `_build_parser` `init` description and flags |
| `src/sofer/scanner.py` | Modified | Updated module docstring for `raw/->cache/->build` copy-only pipeline, `EXCLUSIONS` unchanged |
| `docs/configuration.md` | Modified | Bootstrap keys 2->3 (added `raw_dir` cwd-only), added `raw/->cache/->build` diagram and flatten example, documented `raw/` never excluded |
| `README.md` | Modified | Directory layout `raw/(tracked)->cache/->build/` with diagram, TOML `local` `data/`->`cache/`, profile/codebook examples `data/`->`raw/` |
| `README_ES.md` | Modified | Mirror of README 5.2 per §13, Spanish prose with English technical content |
| `openspec/changes/2026-08-29-feat-raw-folder-organization/tasks.md` | Modified | Marked all 18 tasks [x] |

### Deviations from Design

None — implementation matches design. One clarification: `--dry-run` with `--move-existing` still creates the TOML (preview only for moves) and does not create `raw/` when absent, per CLI-R07 scenario. Non-interactive skip creates `raw/` but not moves, with hint `Use --force`.

### Issues Found

None. `ruff check --fix` green, `mypy src/` green, `pytest -q` 959 passed, 2 skipped.

### Remaining Tasks

None — all 18 tasks complete. Ready for verify.

### Workload / PR Boundary

- Mode: single PR (fits 2000 budget; 244 lines)
- Current work unit: single-pr all phases
- Boundary: Phase 1 (config) + Phase 2 (cli/scanner) + Phase 3 (wiring) + Phase 4 (test verification) + Phase 5 (docs) — one autonomous PR `feat/raw-folder-organization -> dev`
- Estimated review budget impact: 244 lines (Low vs 2000, High vs 400 but auto-forecast single PR)

### Status

18/18 tasks complete. Ready for verify.

### Verification

- `uv run ruff check --fix .` → All checks passed
- `uv run ruff format .` → 64 files unchanged
- `uv run mypy src/` → Success: no issues in 27 source files
- `uv run pytest -q` → 959 passed, 2 skipped
- Manual checks: `init` creates `raw/`, `--move-existing` depth-1 only, collision fails, `--dry-run` no mutation, `not isatty` skips with hint, `N` aborts, `raw/` discovered / `cache/` excluded, `raw/DPTO.csv->cache/DPTO.csv` flatten
