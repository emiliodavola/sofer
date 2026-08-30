# Proposal: Raw Folder Organization

## Intent

Loose CSV/XLSX/JSONL in root mix with `.toml`/`cache/`/`build/`. Make `raw/` the tracked source root so `flatten_first_level` (`raw/DPTO.csv→cache/DPTO.csv`) works by convention.

## Scope

### In Scope
- `raw_dir="raw"` in `[tool.sofer]` (`config.RAW_DIR`), `reload(None)` bootstrap (TC-07)
- `sofer init` `mkdir -p raw/` idempotent; `--move-existing` moves depth-1 loose supported files into `raw/` with `check_flatten_collisions`; respects `--dry-run`/`--force`/non-interactive
- `scan` copy-only; docs `raw/(tracked)→cache/(gitignored)→build/(gitignored)` + `raw/DPTO.csv→cache/DPTO.csv→build/*.parquet` diagram; reconcile `data/`→`cache/`; `raw/` never in `EXCLUSIONS`; sync `README_ES.md`

### Out of Scope
- `scan --migrate-raw` / auto-move on scan (follow-up)
- Per-dataset `[dataset] raw_dir` (tool-wide only)
- `prepare`/`publish`/`codebook` changes

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `scan`: `raw/` canonical source; copy-only; flatten clarified
- `tool-config`: `raw_dir` bootstrap key, cwd walk-up precedence
- `cli`: `init` `raw/` + `--move-existing`, help/template/layout

## Approach

Phased B+C:
1. `config.py` `_DEFAULTS["raw_dir"]="raw"` + `RAW_DIR`; `pyproject.toml` default; `reload(None)` bootstrap
2. `_cmd_init`: `mkdir -p raw/` always; `--move-existing` moves depth-1 `SUPPORTED_FORMATS` loose files, `check_flatten_collisions` first, `--dry-run` preview, `--force`/non-interactive guard
3. `scan` unchanged (copy-only). `_INIT_TEMPLATE` → `# Source files → raw/ (scan copies to cache/)`
4. Docs `raw/→cache/→build/` + diagram; `raw/` never in `EXCLUSIONS`

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/config.py` | Modified | `raw_dir` default, `RAW_DIR`, bootstrap docs |
| `src/sofer/cli.py` | Modified | `_cmd_init` mkdir + `--move-existing`, template/help |
| `src/sofer/scanner.py` | Modified | Docstring; reuse `check_flatten_collisions` |
| `pyproject.toml` | Modified | `[tool.sofer] raw_dir = "raw"` |
| `README.md`/`README_ES.md`/`docs/configuration.md` | Modified | Layout + diagram + `raw_dir` ref |
| `openspec/specs/scan` `tool-config` `cli` | Modified | Delta specs |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Move breaks `local` paths | Med | Opt-in only; `remote` dedup → re-scan idempotent |
| Flatten collisions | Med | `check_flatten_collisions` before move; fail with sources |
| `raw/` excluded → empty scan | Low | `raw/` never in `EXCLUSIONS`; only `cache` excluded |
| CI hangs | Low | `--force`/`--dry-run`/`not isatty` skip prompt |
| README_ES drift | Med | Same commit (§13) |

## Rollback Plan

Revert commit. `raw/` harmless. Moved files: `raw/* → .` + `sofer scan --force` re-registers `cache/`. Move-only, no delete.

## Dependencies

- `flatten_first_level`/`check_flatten_collisions`/`discover_files`; `reload(None)` bootstrap; no new deps

## Success Criteria

- [ ] `init` creates `raw/`; `--move-existing` depth-1 + guard; `--dry-run`/`--force`/non-interactive ok
- [ ] `raw_dir` defaults `"raw"` via `[tool.sofer]`, cwd walk-up
- [ ] `scan` copy-only; `raw/DPTO.csv→cache/DPTO.csv` flatten ok
- [ ] Docs `raw/→cache/→build/` diagram; `README_ES.md` synced
- [ ] Delta specs (`scan`/`tool-config`/`cli`) + tests
