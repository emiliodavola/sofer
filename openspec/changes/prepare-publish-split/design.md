# Design: prepare + publish — split upload into generation and delivery

## Technical Approach

Delete `uploader.py` (1075 lines) and split `upload()` along its two halves, preserving every unit-testable helper:

- **`prepare.py`** — local generation: CSV→Parquet conversion, cross-file schema assertion, large-value checks, schema report + Dataset Card + LICENSE, codebook staging. Zero network calls. Writes the *mirror layout* (the structure `upload_folder` needs today) directly to a persistent output dir (default `<config-dir>/data/`).
- **`publish.py`** — delivery: repo ensure/inspect, diff summary, overwrite protection, batch `upload_folder` (target `hf`), mirror copy to `--output` (target `local`), auto-prepare, dry-run, post-publish split report.
- **`_mirror.py`** — shared layout helpers used by both halves (one-module-per-concern, `_parquet_helpers.py` precedent): remote-path validation, planned-remotes derivation, dir-aware copy (the `recursive=true` fix).

`prepare` output **is** the publish input: the persistent output dir is already the mirror, so `publish` never regenerates; it filters/copies planned artifacts out of it. Fixes the pre-existing recursive-entry staging crash (RC-R04: `shutil.copy2` on a directory → PermissionError/IsADirectoryError).

## Architecture Decisions

| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| Module split | One `pipeline.py` vs `prepare.py` + `publish.py` | Two modules | Generation (pure, offline, unit-testable without HF mocks) and delivery (network, interactive protection, gate) have zero shared state. A single pipeline module would keep the coupling the proposal exists to break; AGENTS.md §10 is one module per concern. |
| Auto-prepare signal | Manifest file vs input mtimes | TOML mtime + source mtimes for ALL supported formats, parquet existence fallback | Manifest is explicitly out of scope and would pollute the dataset dir (risk of accidental upload). TOML is the complete input declaration — if it changed, all derived artifacts are suspect. Adding source-file mtimes closes the gap where a **data-only** edit (no TOML change) would silently ship stale parquets — today's `upload()` always regenerates, so this preserves that guarantee without a manifest. Source check covers **every file in `SUPPORTED_FORMATS`** declared in `cfg.files` (CSV, TSV, Parquet, Excel, JSONL), not just CSV (user decision). |
| Mirror assembly reuse | Re-assemble in publish from scratch vs prepare output = mirror | Prepare writes mirror layout to output dir; publish copies *planned artifacts only* out of it | The output dir is both deliverable and input. Publish's copy filters to declared remotes + compliance + codebooks, so `--output` pointing at the config dir (out=base) can never blanket-upload the TOML or stray files (proposal risk: "publish uploads planned remotes only"). Batch `upload_folder` (1 call) is preserved. |
| Conversion helpers migration | Move to `_mirror.py` / publish / keep flat | Stay in `prepare.py` | `_sniff_csv_delimiter`, `_count_delimiters_outside_quotes`, `_cast_null_columns_to_string`, `_read_csv_raw_values`, `_check_conversion_parity`, `_convert_to_parquet` are generation-only; `test_parquet_conversion.py` retargets imports to `sofer.prepare`. Same for `_assert_cross_file_schema`, `_check_large_values`, `_assert_card_dtypes_match_parquet`. |
| Remote overwrite protection | Prompt-per-file (today) vs PUB-05 semantics | Keep today's `_check_overwrite_protection`, extend `_AUTO_GENERATED` to codebooks | PUB-05: auto-generated (README.md, LICENSE, codebook.md, codebooks/**/*.md) always overwrite; protected data files need `--force`. Existing unit tests for the helper survive unchanged. Local `--force` (PRP-07) is a **separate** existence check in prepare. |
| Checks location | In `prepare()`/`publish()` vs CLI | CLI runs validators; publish gates on the report (today's flow), prepare prints non-blocking | Keeps the quality-gate path identical to today (`upload(cfg, quality_report=...)`) so `TestUploadQualityGate` retargets verbatim. `--no-checks` (PRP-05) skips the CLI run. Extracted `_load_and_validate(args)` removes the validate/upload duplication. |
| Auto-prepare inside publish | Pass `force` from CLI vs internal `force=True` | Internal auto-prepare always passes `force=True` | An internal regeneration into the same output dir is expected to overwrite stale artifacts; user-facing `--force` is only for the standalone `prepare` command's refusal (PRP-07). Prevents the conflict where auto-prepare would exit 1 on existing files. |

## Data Flow

```
                       ┌───────────────────────────── prepare ──────────────────────────────┐
  dataset.toml ──→ validate cfg ──→ conversion loop ──→ output_dir/<parquet_remote>          │
  (cfg.files)         + checks  │        (parity, cast-null, large-values)                   │
                                ├──→ cross-file schema assert ──→ errors → exit 1            │
                                ├──→ build_schema_report(output_dir as staging_dir)          │
                                ├──→ README.md + LICENSE ──→ output_dir/                     │
                                ├──→ [--all-files] generate_all_codebooks ──→ data/codebooks/│
                                └──→ stage codebooks + non-converted + recursive trees ──→ output_dir/ (mirror layout)

  publish --target hf:
     cfg ──→ _needs_prepare? ──yes──→ prepare(force=True)
        │  no                          │
        ├──→ _ensure_repo → _inspect_repo → diff summary → overwrite protection (PUB-05)
        ├──→ quality gate (report from CLI) ──fail──→ exit 1
        ├──→ staging tmpdir = copy planned artifacts from output_dir (+ keep_csv CSVs from entry.resolve)
        ├──→ [--verify] load_dataset(staging)
        ├──→ HfApi.upload_folder(staging, path_in_repo="")   (single call)
        └──→ post-publish split report (re-inspect repo)

  publish --target local:
     cfg ──→ _needs_prepare? ──yes──→ prepare(force=True)
        │  no
        ├──→ [--output] copy planned artifacts output_dir → --output (no network, keep_csv ignored)
        └───→ --output omitted → in-place: print package summary, no mutation (PUB-02)

  publish --dry-run (both targets): diff summary + split report from planned remotes; NEVER
     executes prepare (no output-dir mutation, PUB-04) and never calls the network.
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/sofer/prepare.py` | Create | `prepare(cfg, output_dir, all_files, no_checks, force)`: conversion loop, cross-file assert, large-value check, schema report (passing output_dir as `staging_dir`), card/LICENSE write, codebook generation (Option B — writes directly into output_dir, never the shared cache), NOT FOUND report, `_check_local_overwrite` (PRP-07), `resolve_output_dir(cfg, override)` (default = `cfg.build_dir`, not `OUTPUT_DIR`) |
| `src/sofer/publish.py` | Create | `publish(cfg, target, output_dir, force, verify, keep_csv, dry_run, quality_report=None)`: `_ensure_repo`, `_inspect_repo`, `_repo_diff_summary`, `_check_overwrite_protection` (extended `_AUTO_GENERATED`), `_needs_prepare`, hf staging + `_hf_upload_folder`, local target, `_print_split_report`, `_print_split_mapping_validation` |
| `src/sofer/_mirror.py` | Create | `_validate_remote_paths(cfg)`, `planned_remotes(cfg, keep_csv)`, `copy_to_mirror(src, dest_root, remote)` (dir-aware: `copytree(dirs_exist_ok=True)` for dirs, never `copy2` on a dir — RC-R04) |
| `src/sofer/uploader.py` | Delete | Split into prepare + publish (+ `_mirror.py`); history retained for rollback |
| `src/sofer/cli.py` | Modify | Remove `upload` subparser + `_cmd_upload`; add `_cmd_prepare`/`_cmd_publish` with `--output/--all-files/--no-checks/--force` and `--target/--output/--force/--verify/--keep-csv/--dry-run`; extract `_load_and_validate(args)`; update `_INIT_TEMPLATE` (add `build_dir`), parser description, `_cmd_init` prints (CLI-R02) |
| `src/sofer/repo_compliance.py` | Modify | Docstring only: orchestrator reference `upload` → `prepare`; `build_schema_report` logic unchanged (`staging_dir` now = prepare output dir) |
| `src/sofer/codebook.py` | Modify | `generate_all(cfg)` writes to `cache/codebooks/` + root `codebook.md` (OUTPUT_DIR renamed `data` → `cache`); unchanged otherwise |
| `src/sofer/config.py` | Modify | `OUTPUT_DIR` default `"data"` → `"cache"` (user decision: `data/` stays for source files, sofer artifacts move to `cache/`) |
| `src/sofer/model.py` | Modify | `DatasetConfig` gains `build_dir: str = "build"`; parsed from `[dataset] build_dir` in `from_toml()` |
| `src/sofer/__init__.py`, `README.md` | Modify | Usage text: `upload` → `prepare`/`publish`; `data/` → `cache/`; document `build_dir` (rule 7) |
| `tests/*` | Modify | Retarget imports/call sites; new coverage (below) |

## Interfaces / Contracts

```python
# prepare.py
def prepare(cfg: DatasetConfig, output_dir: Path, all_files: bool = False,
            no_checks: bool = False, force: bool = False) -> int: ...
def resolve_output_dir(cfg: DatasetConfig, override: str | None) -> Path:
    """cfg._base_dir / (override or cfg.build_dir) — single resolution for prepare + publish.
    User decision: the default output lives in the dataset.toml ([dataset] build_dir),
    NOT in OUTPUT_DIR. --output overrides it per-run without touching the TOML."""

# publish.py
def publish(cfg: DatasetConfig, target: str = "hf", output_dir: str | None = None,
            force: bool = False, verify: bool = False, keep_csv: bool = False,
            dry_run: bool = False, quality_report: ValidationReport | None = None) -> int: ...
def _needs_prepare(cfg: DatasetConfig, output_dir: Path) -> bool: ...

# _mirror.py
def _validate_remote_paths(cfg: DatasetConfig) -> list[str]: ...
def planned_remotes(cfg: DatasetConfig, keep_csv: bool) -> list[str]: ...
def copy_to_mirror(src: Path, dest_root: Path, remote: str) -> None: ...
```

### Auto-prepare detection (exact definition — PUB-03)

```python
def _needs_prepare(cfg, output_dir) -> bool:
    parquets = sorted(output_dir.rglob("*.parquet"))
    if not parquets:
        return True                                  # missing → prepare (existence fallback)
    newest = max(p.stat().st_mtime for p in parquets)
    if cfg_toml_path.stat().st_mtime > newest:
        return True                                  # config changed after last conversion
    sources = [e.resolve(base) for e in cfg.files if e.resolve(base).exists()]
    if sources and max(s.stat().st_mtime for s in sources) > newest:
        return True                                  # data changed (design decision, no manifest)
    return False                                     # up-to-date → deliver existing
```

Caveats (documented): mtime granularity can miss same-second edits (acceptable pre-release); hand-edited artifacts (e.g. README tweaks) do NOT trigger re-prepare — the signal keys on *inputs* (TOML + all source files in SUPPORTED_FORMATS), so users re-run `prepare` (or `--force`) after manual artifact edits. `--dry-run` never executes prepare (PUB-04: no output-dir mutation).

### Mirror layout contract (prepare output = publish input)

```
build_dir/                          (default "build"; configurable via [dataset] build_dir in dataset.toml)
├── README.md  LICENSE
├── codebook.md
├── codebooks/<rel-path>.md
├── <parquet_remote>            (converted CSVs; upload_as_csv stays CSV)
├── <entry.remote>              (non-converted files AND recursive trees, preserved)
```

### Directory contract (user decisions)

```
data/           source files only (declared in dataset.toml [[file]] local=) — NEVER written by sofer
cache/          sofer artifact cache (renamed from data/): codebook --all-files writes cache/codebooks/
build/          prepare output + publish input (per-dataset [dataset] build_dir, default "build")
```

### CLI flags

- `prepare CONFIG [--output DIR] [--all-files] [--no-checks] [--force]` — `--output` overrides `build_dir` for this run
- `publish CONFIG [--target hf|local] [--output DIR] [--force] [--verify] [--keep-csv] [--dry-run]`
- `upload` absent → `sofer upload ...` exits 2 (CLI-R01).

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `_validate_remote_paths`, `planned_remotes` | `TestRemotePathValidation` imports `sofer.uploader` → `sofer._mirror`; assertions unchanged |
| Unit | Conversion (parity, sniff, cast-null) | `test_parquet_conversion.py` (~40 imports of `_convert_to_parquet`/`_sniff_csv_delimiter`) retarget to `sofer.prepare`; no behavioral change |
| Unit | `_assert_cross_file_schema`, `_assert_card_dtypes_match_parquet`, large values | `TestAssertCrossFileSchema` + `TestSchemaAssertion` imports → `sofer.prepare` |
| Unit | `_repo_diff_summary`, `_check_overwrite_protection` | `TestRepoDiffSummary` + `TestOverwriteProtection` imports → `sofer.publish`; extend `_AUTO_GENERATED` test for codebook paths (PUB-05) |
| Unit | Quality gate | `TestUploadQualityGate` → `TestPublishQualityGate`: `publish(cfg, quality_report=failing)` returns 1 before any network (signature keeps the optional report param) |
| Integration | prepare (PRP-01…07) | New `test_prepare.py`: offline generation (patch network layer to raise — zero calls), mirror layout (subdirs, upload_as_csv not converted), card/LICENSE content, codebook staging, `--no-checks`, `--output` isolation, `--force` refusal/overwrite |
| Integration | publish hf (PUB-01…07) | New `test_publish.py`: retarget today's staging tests (`TestBatchStaging`, `TestReadmeOverride`, `TestCodebookUpload`) from `uploader.upload(cfg)` → `publish(cfg)` with the same `tmp_path`/`mkdtemp`/`_api` mocks; `--verify` (PUB-06), `--keep-csv` (PUB-07), NOT FOUND skip, `upload_folder` failure exit 1 |
| Integration | publish local (PUB-02) | New tests: `--target local --output ./out/` writes complete package, no network; `--output` omitted = in-place summary |
| Integration | auto-prepare (PUB-03) | New tests: missing parquet → prepare runs first; TOML mtime newer → prepare runs; up-to-date → no prepare, existing delivered; `--dry-run` never mutates output dir (PUB-04) |
| Integration | recursive staging (RC-R04) | New test: `recursive=true` dir with nested subdirs stages tree without exception; empty dir stages zero files |
| CLI | subparsers (CLI-R01/R02) | `test_cli.py`: `test_upload_command` + `TestUploadForceFlag` replaced with prepare/publish parser tests; `upload` parse fails; `--help` text checks |
| Regression | Split/verification suites | `TestDetectSplits*`, `TestVerifyLoadDataset`, etc. import `splits`/`verification` only — untouched; full `uv run pytest tests/ -q` must keep all 492+ passing |

Retarget tally: `test_uploader.py` (16 direct `upload()` calls + helper imports), `test_parquet_conversion.py` (10 `upload()` calls), `test_repo_compliance.py` (6 `upload()` calls) — each `uploader.upload(cfg)` becomes `publish(cfg)` with identical mocks; each pure-helper import moves to its new module.

## Migration / Rollout

No data migration. Pre-release removal of `upload` (no deprecation, per proposal): the change commit documents `upload` → `publish` (and `prepare`). Rollback = revert commit restoring `uploader.py`; `uploader.py` git history retained. README + `--help` updated in the same change (rule 7).

## Resolved Decisions (user-confirmed)

- **Auto-prepare signal**: TOML mtime + source mtimes for ALL supported formats (CSV, TSV, Parquet, Excel, JSONL), parquet-existence fallback. Re-prepares whenever any source file OR the TOML is touched (user decision 1).
- **`--verify` semantics**: `prepare --verify` loads the generated parquet files locally against the output dir — verify belongs to prepare, not publish. Publish does NOT re-verify after upload (user decision 2).
- **`--all-files` + `--output ./build/`**: Option B — prepare generates codebooks DIRECTLY into the output dir, never mutating `cache/codebooks/`. `codebook.py` gains an output-dir parameter so the standalone `codebook --all-files` still writes `cache/codebooks/` (user decision 3).
- **`data/` → `cache/`**: `OUTPUT_DIR` default renamed `data` → `cache` across all commands. `data/` stays reserved for source files; sofer artifacts (codebooks, etc.) live under `cache/`.
- **`build_dir` in `[dataset]`**: default output of `prepare`/`publish` comes from `dataset.toml` `[dataset] build_dir` (default `"build"`); `--output` flag overrides per-run.
