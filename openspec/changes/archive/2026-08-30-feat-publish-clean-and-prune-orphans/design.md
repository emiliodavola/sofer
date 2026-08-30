# Design: feat-publish-clean-and-prune-orphans (GitHub #92)

## Technical Approach

Opt-in cleanup keeping `prepare -> inspect -> publish`. `publish --clean` (off by default) deletes resolved build dir only after `hf` `fail==0`; `cache/` needs `--clean-cache` (tool-wide `config.OUTPUT_DIR` anchored to `cfg._base_dir`, sibling-shared). `prepare(force=True)` prunes orphans after staging via shared `src/sofer/_clean.py` (`allowed_output_remotes`/`prune_orphans`) reusing `expanded_planned_remotes` and `sanitize_sheet_name`/`normalize_parquet_remote` dual `__`/`_` guard (#90). No new `[tool.sofer]` defaults. Covers PUB-11/PRP-09.

## Architecture Decisions

### Decision: Shared helper

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Inline in `publish.py`+`prepare.py` | Duplicates allowlist, repeats #90 leak | Rejected |
| `src/sofer/_orphans.py` | Name misses `clean` teardown | Rejected |
| `src/sofer/_clean.py` (`allowed_output_remotes`+`prune_orphans`+`clean_build`/`clean_cache`) | Single truth, one-module-per-concern, future `sofer clean` reuse | **Chosen** |

### Decision: CLI flag granularity

| Option | Tradeoff | Decision |
|--------|----------|----------|
| `--clean` deletes `build/`+`cache/` | Blasts siblings sharing `cache/` (HIGH) | Rejected |
| `--clean` (build-only) + `--clean-cache`/`--all` for `cache/` | Explicit, warns siblings | **Chosen** |
| `sofer clean` only, no flag | CI needs second command; orphans manual | Deferred |

### Decision: Publish gating and anchoring

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Unconditional delete | Breaks dry-run/quality-fail/upload-error inspect | Rejected |
| Gate `clean and not dry_run and quality_passed and fail==0`; build via `resolve_output_dir(cfg, _output)`, cache via `cfg._base_dir / config.OUTPUT_DIR` | Honors `--output` override; `cache/` independent | **Chosen** |

`local`: without `--clean` no delete; with `--clean` deletes resolved destination not source build. Log absolute paths; `try/except` (no `ignore_errors=True`).

### Decision: Orphan prune placement

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Before staging | Re-creates; misses `codebooks/` | Rejected |
| After staging+codebooks when `force=True`; allowlist=`expanded_planned_remotes` ∪ `{README,LICENSE,codebook.md,codebooks/**}` ∪ keep_csv | Idempotent; `force=False` no-op; handles single-`_` `data_got_all_*` | **Chosen** |
| Always prune | Deletes debug drops in `build/` | Rejected |

Reuse `_AUTO_GENERATED` + `codebooks/` prefix; exclude recursive entries.

### Decision: Config

| Option | Tradeoff | Decision |
|--------|----------|----------|
| New `[tool.sofer] clean_*` defaults | Hardcodes; violates no-hardcoded rule | Rejected |
| Reuse `OUTPUT_DIR`/`CODEBOOKS_DIR` via `config` | Zero new values | **Chosen** |

## Data Flow

```
publish --clean (hf):
  _cmd_publish -> _load_and_validate -> quality_report
    -> run_publish(cfg, output_dir, dry_run, keep_csv, clean, clean_cache)
         ├─ dry_run? -> diff+split -> return 0 (no delete)
         ├─ quality_report.passed==False -> return 1 (no delete)
         ├─ _needs_prepare? -> prepare(force=True) -> prune_orphans
         ├─ local? -> _copy_package or summary; if clean: clean_build(dest)
         └─ hf: _ensure_repo -> _inspect_repo -> diff -> protection
               -> staging_root tmpdir/repo -> _hf_upload_folder -> ok/fail
               -> if clean and fail==0 and not dry_run and quality_passed:
                    clean_build(resolve_output_dir(cfg, _output))
                    if clean_cache: clean_cache(cfg._base_dir / config.OUTPUT_DIR) # warn
               -> rmtree tmpdir (finally) -> split report

prepare(force=True):
  resolve_output_dir -> _check_local_overwrite -> mkdir
    -> checks -> convert -> schema assert -> stage parquet
    -> card/LICENSE -> passthrough/recursive -> codebooks
    -> if force: allowlist=allowed_output_remotes(...); prune_orphans(output_dir, allowlist)
    -> verify? -> return 0
  force==False: skip prune
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/_clean.py` | Create | `allowed_output_remotes`, `prune_orphans` (rglob+try/except+log), `clean_build`/`clean_cache` (exist check+safe rmtree) |
| `src/sofer/cli.py` | Modify | Add `--clean`/`--clean-cache`/`--all` to `publish`; plumb to `run_publish`; update help |
| `src/sofer/publish.py` | Modify | Add `clean`/`clean_cache` params; gated post-upload deletion anchored via `resolve_output_dir`/`config.OUTPUT_DIR`; local dest handling |
| `src/sofer/prepare.py` | Modify | Call `prune_orphans` after codebooks when `force=True` |
| `src/sofer/config.py` | No change | Reuse existing constants |
| `README.md`, `README_ES.md` | Modify | Document flags, sibling `cache/` warning |

## Interfaces / Contracts

```python
# src/sofer/_clean.py
def allowed_output_remotes(cfg: DatasetConfig, keep_csv: bool, output_dir: Path) -> set[str]: ...
def prune_orphans(output_dir: Path, allowed: set[str]) -> list[Path]: ...
def clean_build(cfg: DatasetConfig, override: str | None) -> None: ...
def clean_cache(base_dir: Path) -> None: ...
```

`publish(..., clean: bool = False, clean_cache: bool = False) -> int` gated after `fail==0`. Existence checks before `shutil.rmtree`/`unlink`; backup-less; `try/except` logs path.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit _clean | Single-`_` XLSX sheets in allowlist; stale deleted, compliance/keep_csv retained, idempotent | pytest tmp_path with `DATA_GOT_ALL` layout |
| Unit publish | No delete on dry_run/quality-fail/upload-fail; build vs cache isolation; `--output` anchoring; local dest-only | `test_publish.py` mock upload |
| Unit prepare | PRP-09: force deletes orphan, non-force retains | `test_prepare.py` force T/F |
| Integration CLI | `--help` contains flags; plumb verified | `test_cli.py` parser |
| E2E | `prepare(force)` + `publish --clean --clean-cache` removes both | tmp_path |

Every PUB-11/PRP-09 scenario maps to one test; `ruff`+`mypy` green.

## Migration / Rollout

Backward compat: default off, existing behavior unchanged. No migration. Revert: remove flags+gated block+helper. Docs synced per rule 13. Follow-up `sofer clean` reuses helper. Forecast 250-350 lines; chain if needed.

## Open Questions

- [ ] `--clean-cache` vs `--all` alias?
- [ ] `local --clean` without `--output` no-op or warn?
- [ ] Sibling `cache/` warning to stdout or stderr?
