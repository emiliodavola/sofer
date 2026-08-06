# Proposal: prepare + publish — split upload into generation and delivery

## Intent

`upload` (uploader.py:697-1034) generates and publishes in one shot inside a tmpdir, so users can't inspect or edit artifacts (README, LICENSE, codebooks) before they reach HF. Split into `prepare` (local generation) + `publish` (delivery). Remove `upload` entirely — pre-release, no deprecation. Also fixes a pre-existing bug: `recursive=true` directory entries crash staging (`shutil.copy2` on a directory → PermissionError on Windows).

## Scope

### In Scope
- `prepare <config> [--output] [--all-files] [--no-checks] [--force]`: CSV→Parquet, README.md, LICENSE, codebooks (index + per-file), schema report + quality checks. No network/auth. Output default = project `data/` dir.
- `publish <config> [--target hf|local] [--output] [--force] [--verify] [--keep-csv] [--dry-run]`: `hf` (default) via upload_folder; `local` writes complete package to disk; auto-prepares when needed; `--dry-run` shows diff without publishing.
- Auto-prepare detection: `dataset.toml` is source of truth (NO manifest). Re-prepare if TOML mtime is newer than output-dir parquet; parquet existence is the fallback check.
- Delete `uploader.py` → new `prepare.py` + `publish.py`.
- Fix recursive-entry staging crash; add staging test (closes #31, #42).

### Out of Scope
- S3/GCS targets (future issues); changing internal conversion/compliance logic; interactive editing; incremental/partial prepare; manifest file.

## Capabilities

### New Capabilities
- `prepare`: local generation of all package artifacts (parquet, card, LICENSE, codebooks, reports) into an inspectable output dir.
- `publish`: delivery of prepared artifacts to `hf`/`local` targets with auto-prepare, dry-run diff, and verification.

### Modified Capabilities
- `repo-compliance`: README/LICENSE/schema-report generation moves from upload tmpdir to prepare output dir.
- `data-quality`: checks run in prepare (`--no-checks` skips); publish keeps the blocking quality gate.
- `parquet-conversion`: conversion output location changes (prepare output, not tmpdir); recursive entries handled.

## Approach

Split upload() along its two halves. Generation → `prepare()`: conversion loop (816-843), cross-file schema assert (845), schema report (860), card build (884-905), LICENSE (907), card-dtype assert (913). Delivery → `publish()`: ensure/inspect repo (761-764), diff summary (777), overwrite protection (781), mirror assembly (935-993), `upload_folder` (1005), post-report (1019). Keep internal flat staging for `build_schema_report` flat-lookup; reuse mirror assembly for both targets (local = mirror → `--output`, no network). Extract shared `_load_and_validate()` from `_cmd_upload`/`_cmd_validate`; remove `upload` subparser + `_cmd_upload`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/sofer/uploader.py` | Removed | split into `prepare.py` + `publish.py` |
| `src/sofer/cli.py` | Modified | remove upload subparser/`_cmd_upload`; add prepare/publish; help, `_INIT_TEMPLATE`, description |
| `src/sofer/codebook.py` | Modified | `generate_all` called by `prepare --all-files` |
| `src/sofer/repo_compliance.py` | Modified | schema-report flat-lookup coupling |
| `src/sofer/config.py`, `pyproject.toml` | Modified | new `[tool.sofer]` defaults |
| `README.md`, `__init__.py` | Modified | `upload` references (rule 7) |
| `tests/*` | Modified | ~50 `upload()` call sites retarget; new prepare/publish/local/removal tests |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Recursive staging crash | High (exists) | `copytree` or explicit unsupported error + staging test |
| Flat-stem collision (PROV/train vs DPTO/train) | Med | remote-derived staging names; verify multi-file tests |
| Schema-report flat-lookup coupling | Med | internal flat staging dir for `build_schema_report` |
| Output-dir mixing when out=base | Med | publish uploads planned remotes only, never blanket |
| Stale/partial prepares (no manifest) | Med | TOML mtime vs parquet mtime + existence fallback |
| ~50 test call sites + imports | Med | retarget imports; keep unit-class assertions (splits, cross-file, card-dtype, convert) |

## Rollback Plan

Pre-release: revert the commit restores `upload`. `uploader.py` history retained; no data migration. Removal is documented in the change commit (migration: `upload` → `publish`).

## Dependencies

- None new — pyarrow, huggingface_hub already present.

## Success Criteria

- [ ] `sofer prepare dataset.toml` generates all artifacts locally, zero network calls
- [ ] `sofer publish dataset.toml` uploads to HF Hub (same behavior as `upload` today)
- [ ] `sofer publish dataset.toml --target local --output ./out/` writes complete package to disk
- [ ] `upload` absent from `--help`; `prepare` and `publish` present as top-level commands
- [ ] `publish` auto-prepares when parquet missing or TOML newer than parquet
- [ ] `sofer prepare dataset.toml --output ./build/` uses custom output dir
- [ ] `recursive=true` entries stage without crashing
- [ ] Existing 492 tests updated; new tests cover prepare, publish, local target, and upload removal
