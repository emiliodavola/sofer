# Tasks: Raw Folder Organization

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 530-580 (code ~155, docs ~110, tests ~270) |
| 400-line budget risk | High (vs 400 default) / **Low vs project budget 2000** |
| Chained PRs recommended | No (fits 2000 budget); Yes if enforcing strict 400 |
| Suggested split | Single PR (see Work Units below for 400-enforced split) |
| Delivery strategy | auto-forecast -> auto-chain (no gate; first slice proceeds) |
| Chain strategy | pending (single PR; stacked-to-main only if 400 enforced) |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Config bootstrap + init scaffolding | PR 1 | `config.py`/`pyproject.toml`/`cli.py`; tests `test_config`+`test_cli` |
| 2 | Scanner/docs/e2e wiring | PR 2 if 400 enforced | `scanner.py` docstring + `docs/configuration.md` + `README*` §13; `test_scanner`+e2e |
| Single-PR | All + docs sync | PR 1 | Fits 2000 budget; preferred |

> If 400 strictly enforced: PR1 ~250 lines, PR2 ~280; PR2 base = PR1 branch.

## Phase 1: Foundation / Config Bootstrap

- [x] 1.1 Add `_DEFAULTS["raw_dir"]="raw"` + `RAW_DIR` in `src/sofer/config.py`; update TC-07 docstring
- [x] 1.2 Add `raw_dir = "raw"` in `pyproject.toml` `[tool.sofer]`
- [x] 1.3 Verify `reload(None)` cwd walk-up rebinds `RAW_DIR` via `_discover` (TC-10/TC-07)

## Phase 2: Core Implementation — CLI init & Scanner

- [x] 2.1 Update `_INIT_TEMPLATE` in `src/sofer/cli.py` -> `# Source files -> raw/ (scan copies to cache/)`
- [x] 2.2 Extend `_cmd_init`: `mkdir -p RAW_DIR` idempotent (`exist_ok=True`) before TOML write
- [x] 2.3 Implement `--move-existing`: depth-1 `SUPPORTED_FORMATS` excluding `cache`/`build`/`RAW_DIR`/`EXCLUSIONS`; `check_flatten_collisions` pre-move; `--dry-run` preview no mutation; `--force`|`not isatty` skips prompt else `[y/N]` abort; `shutil.move`
- [x] 2.4 Update `_build_parser` `init`: add `--move-existing`/`--dry-run`/`--force` flags + `raw/->cache/->build/` help
- [x] 2.5 Update `src/sofer/scanner.py` docstring for `raw/->cache/->build` copy-only; `EXCLUSIONS` unchanged

## Phase 3: Integration / Wiring

- [x] 3.1 Verify `cli.main` Phase-0 `reload(None)` rebinds `RAW_DIR` before parser; dataset cmds re-resolve via `DatasetConfig.from_toml`
- [x] 3.2 Confirm `scan` exclude `EXCLUSIONS|{OUTPUT_DIR}` only; `raw/` discoverable, `cache/` excluded; flatten `raw/DPTO.csv->cache/DPTO.csv`

## Phase 4: Testing

- [x] 4.1 `tests/test_config.py`: `raw_dir` default `"raw"` (TC-10), `pyproject.toml` override, cwd vs dataset-dir precedence via temp trees + `reload(None)`
- [x] 4.2 `tests/test_cli.py` init: idempotent mkdir, depth-1 filter (moves `a.csv` only), collision fail, `--dry-run` no mutation, `--force`/`not isatty`/`N` abort (CLI-R07)
- [x] 4.3 `tests/test_scanner.py`: `raw/a.csv` discovered, `cache/a.csv` excluded, `EXCLUSIONS` skip, `--ext` filter (SCN-01/03)
- [x] 4.4 E2E `tmp_path`: `init --move-existing --force` -> `scan --force` -> `cache/` flattened `local`/`remote`, `raw/` untouched (SCN-02/03/06)

## Phase 5: Documentation / Cleanup

- [x] 5.1 `docs/configuration.md`: add `raw_dir` to bootstrap keys (cwd-only) + `raw/->cache/->build` diagram; `data/`->`cache/`
- [x] 5.2 `README.md` Directory layout: `raw/(tracked)->cache/->build/` + `raw/DPTO.csv->cache/DPTO.csv` diagram
- [x] 5.3 `README_ES.md` mirror 5.2 per §13 (same commit, English technical content)
- [x] 5.4 Verify: `uv run ruff check --fix . && uv run ruff format . && uv run mypy src/ && uv run pytest -q`
