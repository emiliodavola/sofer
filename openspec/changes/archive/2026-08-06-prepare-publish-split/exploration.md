# Exploration: prepare + publish — split upload into generation and delivery phases

Source: Issue #42. Artifact store: hybrid (openspec + engram). 492 tests collected (2026-08-06, branch `dev`).

## Current State

`sofer upload <config>` is a monolith: `cli._cmd_upload` (cli.py:68-106) validates + quality-checks, then calls `uploader.upload()` (uploader.py:697-1034) which converts, generates compliance, stages a repo mirror in a tmpdir, and pushes it with one `HfApi.upload_folder()` call.

### Complete map of the current `upload()` flow

| # | Step | Lines | Produces | Where | Local/Network |
|---|------|-------|----------|-------|---------------|
| gate | Quality gate (blocks when report fails) | 734-738 | early `return 1` | — | local |
| a | Header banner (Dataset/Target/Type/…) | 740-746 | stdout | — | local |
| b | `sys.stdout.reconfigure(utf-8)` (win32) | 748-750 | — | — | local |
| 0 | `_validate_remote_paths` → error list | 752-759 | early `return 1` on error | — | local |
| 0a | `_ensure_repo` (create_repo exist_ok) | 761 | HF repo | remote | **network** |
| 0b | `_inspect_repo` → existing file list | 763-764 | list for diff | remote | **network** |
| 0b′ | Collect planned codebook remotes (fs scan of `data/codebooks/` + root `codebook.md`) | 766-775 | list for diff | fs | local |
| 0b″ | `_repo_diff_summary` print | 777-779 | stdout | — | local |
| 0c | `_check_overwrite_protection` (repo-based, README/LICENSE, interactive unless `--force`) | 781-782 | `protected` set | remote | **network** (list_repo_files) |
| 0d | Compute `planned_remotes` (parquet rename, keep_csv) | 784-795 | list | — | local |
| 0e | `_print_split_mapping_validation(planned_remotes)` | 797-798 | stdout | — | local |
| 0f | `--dry-run` (no verify): split report + exit 0 | 800-809 | stdout | — | local |
| 1 | Conversion loop: `_convert_to_parquet(local, tmpdir)` per eligible entry → `converted[remote_key] = (parquet, csv, remote)` | 816-843 | **flat** `tmpdir/{stem}.parquet` (collision risk, see Risks) | tmpdir | local |
| 1b | `_assert_cross_file_schema(converted, cfg)` → abort on mismatch | 845-852 | early `return 1` | — | local |
| 1c | `_check_large_values` per converted file | 854-858 | warnings → stdout | — | local |
| 2 | `build_schema_report(cfg, staging_dir=tmpdir if converted)` — reads flat stem-named parquet | 860-867 | `list[ColumnSchema]` | tmpdir (reads) | local |
| 2a | Load `recipe` / `study_design` text | 869-882 | strings | fs | local |
| 2b | `build_dataset_card` (or `cfg.readme` override) | 884-905 | card string | — | local |
| 2c | `build_license_file(cfg.license)` | 907-908 | license string | — | local |
| 2d | Write `tmpdir/README.md` + `tmpdir/LICENSE` | 910-911 | files | tmpdir | local |
| 2e | `_assert_card_dtypes_match_parquet(schema, converted)` | 913-914 | warnings → stdout | — | local |
| 2f | `verify_load_dataset(tmpdir, cfg)` + print (opt) | 916-920 | `VerificationReport` | tmpdir | local (loads staged dir) |
| 2g | `--dry-run` with verify: stop + split report | 922-933 | stdout | — | local |
| 3 | `staging_root = tmpdir/"repo"` (mirror of remote layout) | 935-940 | dir | tmpdir | local |
| 3a | Copy converted parquet → `staging_root/{remote-with-.parquet}` | 942-947 | mirrored parquet | tmpdir | local |
| 3b | Copy non-converted files (upload_as_csv, direct parquet) → `staging_root/{remote}`; **`shutil.copy2` on recursive dir crashes** (verified: `PermissionError`) | 949-959 | mirrored files | tmpdir | local |
| 3c | `keep_csv=True`: copy original CSVs → remote paths | 961-966 | mirrored CSVs | tmpdir | local |
| 3d | Move README/LICENSE → staging_root unless `protected` | 968-974 | compliance at repo root | tmpdir | local |
| 3e | Copy codebooks from `data/codebooks/` + root `codebook.md` (advisory if none) | 976-993 | mirrored codebooks | tmpdir | local |
| 3f | NOT FOUND report | 995-1003 | warnings → stdout | — | local |
| 4 | `staged_count`; `_hf_upload_folder(repo_id, staging_root, "", repo_type)` | 1005-1014 | upload | remote | **network** |
| — | `finally: shutil.rmtree(tmpdir)` | 1016-1017 | cleanup | tmpdir | local |
| 4b | Post-upload `_inspect_repo` + `detect_splits` + `_print_split_report` | 1019-1023 | stdout | remote | **network** |
| 4c | Result summary + exit code | 1025-1034 | stdout / rc | — | local |

Key coupling facts:
- `build_schema_report(staging_dir=…)` (repo_compliance.py:391-450) looks up **flat** `staging_dir/{entry_stem}.parquet`; the conversion step writes flat stems too. The "mirror with remote subdirs" only exists in step 3.
- `uploader._api` is a module-level `HfApi()` (line 48); tests monkeypatch `_api.create_repo`, `_api.upload_folder`, `_api.upload_file`, plus `tempfile.mkdtemp`, `shutil.rmtree`, and the `_hf_*` wrappers.
- `_check_overwrite_protection` (452-498) is **repo-based** (compares against `existing_files` from HF). There is no local-filesystem overwrite protection anywhere.
- `generate_all(cfg)` (codebook.py:361-502) writes to `data/codebooks/` (i.e. `{base}/{OUTPUT_DIR}/{CODEBOOKS_DIR}`) + root `{base}/codebook.md`. It is currently **never called by upload** — upload only copies whatever is already there.
- `verify_load_dataset(staging_dir, cfg)` (verification.py:46-121) runs `datasets.load_dataset(str(staging_dir))` — works on any dir containing parquet + README; no network.

### Affected Areas

- `src/sofer/cli.py` — `_cmd_upload` (68-106), upload subparser (376-407), `run_upload` import (31), parser description (348), `_INIT_TEMPLATE` (254: "sofer upload"), `_cmd_init` print (332). `_cmd_upload`'s validate+quality prologue is duplicated from `_cmd_validate` — extract to a shared `_load_and_validate(args)` helper.
- `src/sofer/uploader.py` — entire file (1075 lines). `upload()` (697-1034) is refactored into `prepare()` + `publish()`. Conversion/assertion helpers (124-695) move or stay; `_hf_*` + `_ensure_repo`/`_inspect_repo`/`_repo_diff_summary`/`_check_overwrite_protection` (55-121, 343-498) are publish-side.
- `src/sofer/repo_compliance.py` — `build_schema_report` flat-staging lookup (445-450) is the main constraint on prepare's output layout; `build_dataset_card` (629), `build_license_file` (237) unchanged (pure string builders).
- `src/sofer/codebook.py` — `generate_all` (361) reused by `prepare --all-files`. Writes to `data/codebooks/` + root `codebook.md` (inside the source tree, not the output dir) — prepare must then copy into the output mirror (same as step 3e today).
- `src/sofer/config.py` — constants only. New defaults needed in `pyproject.toml [tool.sofer]` (e.g. `publish_default_target`, maybe `manifest_filename`); `OUTPUT_DIR`/"data" default doubles as prepare's default output root (issue: "default: project root, same as data/ dir").
- `src/sofer/verification.py` — unchanged API; retargeted call site.
- `src/sofer/__init__.py` — docstring + usage lines (5, 11) mention `sofer upload`.
- `README.md` — lines 15, 28, 59-60, 76, 86, 112, 129, 133, 180-188, 204 reference upload (AGENTS.md rule 7: same commit).
- `pyproject.toml` — `[tool.sofer]` gains any new defaults.
- `tests/test_uploader.py` (1730 ln) — ~25 direct `uploader.upload(...)` call sites (lines 407, 947, 984, 1036, 1081, 1134, 1181, 1218, 1407, 1459, 1522, 1568, 1605, 1650, 1686, 1722; plus 864/889 `from sofer.uploader import upload`) + unit classes that stay (splits 35-497, `_assert_cross_file_schema` 634-857, `_assert_card_dtypes_match_parquet` 1249-1375).
- `tests/test_parquet_conversion.py` (796 ln) — ~15 `uploader.upload(...)` call sites (225-456, 755-776) in TestConversionPipeline/TestKeepCsv/TestUploadFileSelection/TestDelimiterPlumbing; `_convert_to_parquet`/`_sniff_csv_delimiter` unit tests (99-218, 471-748) keep, retarget import.
- `tests/test_repo_compliance.py` — TestUploadCompliance (367-530, ~5 `uploader.upload` call sites).
- `tests/test_cli.py` — TestParser.test_upload_command (31), TestUploadForceFlag (114-141, 6 tests), test_main_help_prints (102).
- `tests/test_checks.py` / `tests/test_model.py` / `tests/test_codebook.py` / `tests/test_quality.py` / `tests/test_scanner.py` / `tests/test_sentinels.py` — unaffected (no upload references).

### Approaches

1. **Module organization**
   - **A1 — Split uploader.py into `prepare.py` + `publish.py`** (uploader.py deleted). prepare.py: conversion + assertions + schema/card/license + mirror assembly + manifest. publish.py: repo ensure/inspect/diff/overwrite-protection + upload_folder + local target + verification + split report. Shared: `_validate_remote_paths`, `_print_split_report`, `_print_split_mapping_validation` (or move to a tiny `_staging.py`/splits). Pros: one concern per module (AGENTS.md rule 10), clean imports, no "uploader" naming debt. Cons: large file move; ~40 test import sites (`from sofer import uploader`, `from sofer.uploader import …`) retarget; biggest diff.
   - **A2 — Keep everything in uploader.py, rename functions** to `prepare`/`publish` and rename module to `publish.py`; prepare lives alongside. Pros: smallest diff. Cons: module name lies about prepare; 1000+ line file grows.
   - **A3 — New `prepare.py`, keep publish in `uploader.py`** (no rename). Pros: minimal churn; uploader.py≈delivery only. Cons: "uploader" name stays despite publish being the new verb; mild naming debt.
   - Effort: A1 High, A2 Low, A3 Medium. **Recommend A1** (project is pre-release; naming debt compounds; the file is the exact one being split).

2. **Auto-prepare detection** (how publish knows prepare ran)
   - **B1 — Manifest file** (e.g. `.sofer-manifest.json` in the output dir): records `{config_path, config_mtime_or_hash, generated_at, artifacts:[…], files:[{remote, type: parquet|csv|codebook|compliance, rel_path}]}`. Publish: manifest exists + parquet entries resolve → skip prepare; else auto-prepare into output dir then publish. Pros: robust, explicit, enables future incremental prepare; manifest also serves `--target local` packaging and diffing. Cons: new file/format; must be excluded from uploads; tests for staleness.
   - **B2 — Heuristic**: check expected parquet paths exist (planned_remotes computed from cfg). Pros: no new format. Cons: can't distinguish stale/partial prepares, no file inventory, false positives when source `data/` already contains parquet; issue's own phrasing suggests this is weaker.
   - Effort: B1 Medium, B2 Low. **Recommend B1** with B2's parquet-existence check as a fast-path sanity fallback inside the manifest check.

3. **Prepare output layout**
   - **C1 — Output dir IS the repo mirror** (same layout as today's `staging_root`): `{out}/README.md`, `{out}/LICENSE`, `{out}/codebook.md`, `{out}/codebooks/`, `{out}/{remote-path}.parquet` (e.g. `data/PROV/data.parquet`). Default `out` = base dir (config dir), so artifacts land next to `data/`; publish reads the dir and uploads filtered by manifest/planned remotes. Pros: exactly matches issue's artifact table; publish can `upload_folder` the whole dir or re-stage; user edits README in place. Cons: schema report needs a flat lookup dir — keep an internal flat staging area inside prepare for `build_schema_report` (tmpdir) then copy into mirror (today's steps 1→3a already do this); when `out` = base dir, source CSVs and artifacts interleave — publish must NOT upload loose source files (use manifest/planned-remotes filter, never blanket upload).
   - **C2 — Flat output + manifest-driven layout**: write `{out}/data/*.parquet` flat, README/LICENSE at root, manifest maps remote→file. Pros: simpler schema report integration. Cons: diverges from HF repo layout, publish/local-target must reconstruct paths; breaks the "inspect the actual package" UX.
   - Effort: C1 Medium, C2 Medium. **Recommend C1** — it is literally today's staging_root made persistent.

4. **Local target**
   - `publish --target local --output ./out/`: reuse the same mirror assembly (steps 3a-3e) but write to `--output` instead of `upload_folder`. If `--output` == prepare dir, copy is a no-op-ish (or move); if different, copy the prepared mirror into it. Prints a per-file tree + summary. No `_ensure_repo`/`_inspect_repo`/overwrite-protection-against-repo; `--force` handles existing `./out` files. `--verify` can still `load_dataset(out_dir)` (local), though issue scopes it HF-only.

5. **Overwrite protection split**
   - Publish: keep repo-based `_check_overwrite_protection` (existing_files from HF).
   - Prepare: NEW local-variant — if `README.md`/`LICENSE` exist in output dir, ask confirmation unless `--force` (mirrors issue's `--force` wording). `_AUTO_GENERATED` semantics (regenerate silently) can be inverted: prepare always regenerates; protection applies when user edited them after a prior prepare (mtime compare or simple existence prompt).

6. **Quality gate placement**
   - Publish blocks on failed `quality_report` (today's gate at 734-738). Prepare runs checks and prints (respects `--no-checks`); whether prepare exits non-zero on failed checks is a spec decision — recommend warn-and-continue (prepare is local/iterative), gate at publish.

### Recommendation

A1 (split into `prepare.py` + `publish.py`, delete `uploader.py`) + B1 (manifest-based auto-prepare) + C1 (output dir = repo mirror). Publish's HF path is byte-for-byte today's behavior minus the generation steps; `--target local` reuses the mirror assembly; prepare is the conversion/compliance/staging half with the tmpdir made persistent and a manifest added. CLI: remove `upload` subparser + `_cmd_upload`; add `prepare` (`config`, `--output`, `--all-files`, `--no-checks`, `--force`) and `publish` (`config`, `--target {hf,local}` default hf, `--output` (required for local), `--force`, `--verify`, `--keep-csv`, `--dry-run`); extract shared `_load_and_validate(args)` from `_cmd_upload`/`_cmd_validate`.

### Risks

- **Pre-existing latent bug (fix in this change): recursive entries crash staging** — verified `PermissionError` from `shutil.copy2(dir, dest)` at step 3b; only validation-level tests cover recursive (test_uploader.py:247-253); no staging test exists. Needs `shutil.copytree` + a test (or explicit unsupported error).
- **Flat-staging stem collision**: `_convert_to_parquet` writes `tmpdir/{stem}.parquet` (uploader.py:307); `data/PROV/train.csv` and `data/DPTO/train.csv` collide on disk (dict keyed by full remote path at 841 but the FILE is shared). Prepare must write distinct files (e.g. hash/remote-derived names in the internal staging area) — verify against the multi-file test suite before/after.
- **build_schema_report flat-lookup coupling** (repo_compliance.py:445-450) — if prepare's persistent output is mirrored, schema report must read from prepare's *internal flat* staging dir, not the mirror.
- **Output-dir mixing**: default prepare output = base dir interleaves source CSVs (`data/`) with artifacts; publish must upload only manifest/planned-remotes entries, never the whole dir.
- **Idempotency / partial prepares**: interrupted prepare leaves a partial dir → manifest written last as the commit marker (write manifest only after all artifacts succeed). Publish must treat missing manifest as "needs prepare", and mismatch of `--output` between prepare and publish as a fresh prepare (document: publish `--output` must match prepare's).
- **keep_csv / upload_as_csv semantics**: `keep_csv` is publish-only (HF) per issue; `upload_as_csv` entries are part of the package (CSV at remote path) — prepare must still stage them (step 3b).
- **Quality gate vs `--no-checks`**: publish auto-prepare runs checks then gates; prepare `--no-checks` must not silently weaken publish's gate (publish re-gates regardless).
- **Tests**: 492 collected; ~50 direct `uploader.upload(...)` call sites across 3 test files retarget; unit classes (splits, cross-file schema, card-dtype assertion, convert/parity/sniff) keep their assertions, only imports/entry points change. Strict TDD: new prepare/publish/local-target/manifest tests precede implementation; every spec scenario needs a test (AGENTS.md rule 6).
- **README + `__init__.py` + `_INIT_TEMPLATE` + `--help`** all mention `upload` (AGENTS.md rules 7, 11) — update in the same change.
- **`_hf_upload` (single-file)** stays for `_hf_upload_folder`-failure? No — today upload_folder is single-call; `_hf_upload` is only used by tests (`test_upload_folder_called_once` asserts it is NOT called). Keep both in publish.py.

### Ready for Proposal

Yes. Orchestrator should tell the user: the split is mechanical (mirror assembly is already isolated at uploader.py:935-1017); the two real design decisions are the manifest format for auto-prepare detection and module naming (recommend deleting `uploader.py` in favor of `prepare.py` + `publish.py`). The recursive-entry crash is a pre-existing bug that this change is the natural place to fix.
