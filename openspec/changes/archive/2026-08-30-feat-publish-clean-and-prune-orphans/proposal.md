# Proposal: feat-publish-clean-and-prune-orphans (GitHub #92)

## Intent

`publish` cleans only `staging_root`; `cache/`+`build/` persist -> 3x dup. `build/` accrues orphan `.parquet` when TOML/sheets removed (#90 `__`->`_` leak). Opt-in cleanup, keep `prepare->inspect->publish`.

## Scope

### In Scope
- `publish --clean` (off): delete `build/` on `hf` `fail==0`; never on `--dry-run`/quality fail/upload error.
- `--clean-cache`/`--all` deletes `cache/`; default build-only.
- `prepare(force=True)` prune via `allowed_output_remotes` + `remove_orphans` after staging; reused by deferred `sofer clean`.
- Specs `PUB-11`/`PRP-09`, tests, README pair, CLI help.

### Out of Scope
- Auto-clean; deleting `raw/`; `sofer clean` subcommand this slice.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `publish`: `PUB-11` teardown, `hf` vs `local`, `--output` anchoring, cache sibling warning.
- `prepare`: `PRP-09` prune on `force=True`, allowlist = `expanded_planned_remotes`+compliance+`keep_csv`, dual `__`/`_` guard.

## Approach

Minimal `--clean` + `prepare(force=True)` prune via `src/sofer/_clean.py` (`allowed_output_remotes`, `remove_orphans`). Reuses `sanitize_sheet_name`/`normalize_parquet_remote` + `expanded_planned_remotes` glob (`__*.parquet` fallback `_*`). Logs paths; `try/except`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/cli.py` | Modified | `--clean`/`--clean-cache` on `publish` |
| `src/sofer/publish.py` | Modified | Gated post-upload cleanup |
| `src/sofer/prepare.py` | Modified | `force=True` -> prune |
| `src/sofer/_clean.py` | New | Shared helper |
| `src/sofer/config.py` | Modified? | `[tool.sofer]` defaults if needed |
| `openspec/specs/publish/spec.md` | Modified | `PUB-11` |
| `openspec/specs/prepare/spec.md` | Modified | `PRP-09` |
| `README.md`, `README_ES.md` | Modified | Docs + warning |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Cache sibling blast (HIGH) | High | Build-only; cache via `--clean-cache`/`--all`; warn; log path |
| `--output` mismatch | Med | Resolve indep.; `--output` only `build/` |
| Allowlist drift | Med | Reuse `_AUTO_GENERATED`+`keep_csv`; fixture test |
| Single-`_` alias | Med | Via `expanded_planned_remotes` glob (dual guard) |
| Review budget | Low | Forecast 250-350; chain if needed |
| Windows rmtree | Low | `Path`+`try/except` |

## Rollback Plan

Remove flag in `cli.py`/`publish.py` and prune call in `prepare.py`; delete `_clean.py`; revert `PUB-11`/`PRP-09`. No migration.

## Dependencies

- Explore #715 + `explore.md`; #92; `fix-prepare-multisheet-xlsx-copy`; specs `publish`/`prepare`; `pyproject [tool.sofer]`.

## Alternatives Rejected

| Alternative | Reason |
|-------------|--------|
| Auto-clean always | Breaks inspect/verify |
| Cache-only clean | Misses stale `build/` |
| `sofer clean` only | CI needs one flag; orphans manual |
| Manual `rm -rf` | Disk + stale uploads |

## Success Criteria

- [ ] `--clean` deletes `build/` only on `hf` success; not on dry-run/fail/error
- [ ] `--clean-cache` deletes `cache/`; default preserves siblings
- [ ] `prepare(force=True)` prunes orphans, keeps compliance/keep_csv/single-`_`
- [ ] `local --clean` cleans dest only when explicit
- [ ] Tests per scenario; `pytest -q` + `ruff`+`mypy` green
- [ ] README pair + CLI help accurate
