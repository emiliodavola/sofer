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
| `tests/test_config.py` | Modified | Added `TestTc10RawDirBootstrap` — 7 tests: default raw_dir, pyproject override, dataset-dir wins, cwd supplies raw_dir, walk-up, docs, pyproject key |
| `tests/test_cli.py` | Modified | Added `TestInitRawFolder` (9 tests) + `TestInitHelp` (2 tests): CLI-R07/R08 init mkdir, depth-1 filter, collision, dry-run, force/isatty, prompt N/Y, template, help flags |
| `tests/test_scanner.py` | Modified | Added `TestRawCacheDiscovery` (3), `TestSourceLayoutCopyOnly` (2), `TestE2EInitMoveScan` (2): raw/cache discover, EXCLUSIONS, copy-only, docs diagram, e2e init→scan flatten |
| `openspec/changes/2026-08-29-feat-raw-folder-organization/tasks.md` | Modified | Marked all 18 tasks [x] — remediation verifies 4.1-4.4 now honest |

### Deviations from Design

None — implementation matches design. One clarification: `--dry-run` with `--move-existing` still creates the TOML (preview only for moves) and does not create `raw/` when absent, per CLI-R07 scenario. Non-interactive skip creates `raw/` but not moves, with hint `Use --force`.

### Issues Found

- Remediation 2026-08-29: verify report 695 FAIL flagged 18/38 scenarios UNTESTED (`git diff dev -- tests/` empty). Ported 18 manual probes into 25 committed tests (config 7, cli 11, scanner 7). No implementation reverted.

### Remaining Tasks

None — all 18 tasks complete. Ready for verify (remediation).

### Workload / PR Boundary

- Mode: single PR (fits 2000 budget; ~600 lines with tests)
- Current work unit: single-pr all phases + remediation tests
- Boundary: Phase 1 (config) + Phase 2 (cli/scanner) + Phase 3 (wiring) + Phase 4 (test verification) + Phase 5 (docs) — one autonomous PR `feat/raw-folder-organization -> dev`
- Estimated review budget impact: ~600 lines (Low vs 2000, High vs 400 but auto-forecast single PR — remediation adds ~270 test lines)

### Status

18/18 tasks complete. Ready for verify.

### Verification

- `uv run ruff check --fix .` → All checks passed
- `uv run ruff format .` → 2 files reformatted, 62 unchanged (second pass clean)
- `uv run mypy src/` → Success: no issues in 27 source files
- `uv run pytest tests/test_config.py tests/test_cli.py tests/test_scanner.py -q` → 152 passed
- `uv run pytest -q` → 984 passed, 2 skipped (was 959 before remediation — +25 raw-folder tests)
- `git diff dev -- tests/` → non-empty (shows test_config + test_cli + test_scanner deltas)
- Manual probes (pre-remediation, still valid): `init` creates `raw/`, `--move-existing` depth-1 only, collision fails, `--dry-run` no mutation, `not isatty` skips with hint, `N` aborts, `raw/` discovered / `cache/` excluded, `raw/DPTO.csv->cache/DPTO.csv` flatten
- Spec scenarios: 18 previously UNTESTED now covered by committed tests (TC-10 ×3, TC-07 raw_dir, CLI-R07 ×8, CLI-R08, SCN-07 ×2, SCN-01 raw/cache ×1, bootstrap docs)
