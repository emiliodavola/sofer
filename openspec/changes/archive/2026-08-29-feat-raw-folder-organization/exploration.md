# Exploration: feat-raw-folder-organization — organize inputs in `raw/` to avoid mixing with .toml and artifacts

## Current State

### How `sofer` organizes inputs vs. artifacts today

* **Entry points (`src/sofer/cli.py`)**
  - `_cmd_init(args)` (`cli.py:429`): writes `{name}.toml` in `Path.cwd()` using `_INIT_TEMPLATE` (contains `[dataset] build_dir = "build"` and placeholder `[[file]] local = "TODO: path/to/file.csv"`). No directory creation, no `raw/` handling. The TOML lands next to whatever CSVs are already in `.`.
  - `_cmd_scan(args)` (`cli.py:263`): resolves `config_path = Path(args.config).resolve()`, `base_dir = config_path.parent`, `data_dir = base_dir / config.OUTPUT_DIR` (`config.OUTPUT_DIR` default `"cache"` per `config.py:31` / `pyproject.toml:92`). Discovers via `discover_files(base_dir, ...)` recursively from `base_dir`, excluding `EXCLUSIONS | {OUTPUT_DIR}` (so `cache/` itself is never scanned). Then `check_flatten_collisions` → `merge_entries` → optional prompt → `copy_files` → `write_toml`.
  - `_cmd_prepare(args)` / `_cmd_publish(args)`: load via `DatasetConfig.from_toml(args.config)` which anchors `config.reload(base_dir)` on the TOML directory (TC-01/TC-05). Output directory resolved by `prepare.resolve_output_dir(cfg, override)` → `cfg._base_dir / cfg.build_dir` (default `build`) or `--output` override anchored to `cfg._base_dir`, **not** CWD. Conversion stages into the mirror layout under that output dir; `prepare` now converts `.csv/.tsv/.xlsx/.jsonl` universally (0cbea73).
  - `_cmd_profile` / `_cmd_render` / `_cmd_codebook`: `profile` writes `metadata.yaml` next to the dataset file (or `--output` dir); `render` writes `README.md` next to `metadata.yaml`; `codebook --all-files` writes `cache/codebooks/` or `output_dir/codebooks/` (Option B). No `raw/` awareness.

* **Config resolution (`src/sofer/config.py` + `src/sofer/model.py`)**
  - Tool-wide defaults in `_DEFAULTS` (`config.py:28`): `output_dir = "cache"`, `build_dir` is **per-dataset** `[dataset] build_dir` (`model.py:264`, default `"build"`). Comment at `config.py:29` says _"`data/` stays reserved for raw source files (user decision for the prepare/publish split)"_ — but actual default is `cache/`, and `scan` writes `cache/`. `README.md` Directory layout still documents `data/ source files only` alongside `cache/` (`README.md` Directory layout section) — slight drift.
  - `DatasetConfig.from_toml` (`model.py:322`) re-anchors `[tool.sofer]` discovery on the TOML directory, then parses `[dataset] build_dir`, `[meta] csv_delimiter/csv_encoding`, `[[file]] local/remote`, etc. `FileEntry.resolve(base_dir)` (`model.py:97`) resolves relative `local` against `cfg._base_dir`. Validation checks `local` existence and case-fold collisions on normalized parquet keys.
  - No `raw_dir` / `raw/` config key exists. No TOML property points at a raw folder. Paths are fully explicit per `[[file]]`.

* **Scanner flattening (`src/sofer/scanner.py`)**
  - `flatten_first_level(relative)` (`scanner.py:29`): drops the first path segment; `raw/DPTO.csv → DPTO.csv`, `raw/Labels/a.csv → Labels/a.csv`, `x.csv → x.csv`. This is the **existing bridge** between a `raw/` layout and the artifact cache.
  - `merge_entries(discovered, raw_toml, base_dir, data_dir)` (`scanner.py:114`): strips `TODO:` templates, dedups by both `dest = data_dir / flat` and `remote = flat.as_posix()`, then appends `local = "<OUTPUT_DIR>/<flat>"`, `remote = "<flat>"`. So a discovered `raw/DPTO.csv` registers as `local = "cache/DPTO.csv" remote = "DPTO.csv"`.
  - `copy_files` (`scanner.py:201`): copies `data_dir / flat` (i.e. `cache/<flat>`), creating parents lazily, flattening identically.
  - `discover_files` (`scanner.py:83`): walks `root.rglob("*")`, prunes `EXCLUSIONS = {.git, __pycache__, .venv, node_modules, dist, build}` — note `raw` is **not** excluded, so `raw/` contents are discovered. `OUTPUT_DIR` (`cache`) is excluded by the CLI handler (`cli.py:289`).

* **Prepare / publish mirror layout (`src/sofer/prepare.py`, `src/sofer/publish.py`, `src/sofer/_mirror.py`)**
  - `resolve_output_dir` is always build-oriented (`build/`), not source-oriented. `copy_to_mirror(src, dest_root, remote)` stages at `dest_root / remote`. No `raw/` reference.
  - `_validate_case_fold_collisions` and `planned_remotes` operate on normalized parquet remotes, agnostic to source folder structure.

* **Current behavior when running in `.` with loose CSVs**
  - User has `mi-proyecto/` with `encuesta.csv`, `hogares.csv` loose in `.`. They run `sofer init mi-proyecto` → `mi-proyecto.toml` lands in `.` next to the CSVs. They run `sofer scan` (or manually edit TOML) → `discover_files(".")` finds `encuesta.csv` at root, `flat = encuesta.csv`, so `local = "cache/encuesta.csv"`; copies to `cache/encuesta.csv` but **originals stay loose in `.`** alongside `.toml`, `build/`, and any prior `cache/`/`codebooks/`. `sofer prepare` writes `build/*.parquet`, `build/README.md`, `build/LICENSE`, optionally `build/codebooks/`. `sofer validate/publish` read from `cache/` copies (or originals if TOML still points at `.`). Result: inputs, config, and derived artifacts are visually mixed; cleaning or `.gitignore` is error-prone and `raw/` is never enforced.
  - If user **already** uses `raw/` (e.g. `raw/DPTO.csv`), scan handles it cleanly (flatten strips `raw/`), but nothing *encourages* or *automates* the move — they must create `raw/` and move files manually. No `--raw` flag, no `init --raw`, no auto-move.

* **Tests and their layout assumptions**
  - `tests/test_cli.py`: `TestInitCommand` asserts `init` writes `{name}.toml` in `tmp_path` and checks `build_dir = "build"` in the template; no raw.
  - `tests/test_scanner.py`: core contract. `TestFlattenFirstLevel` asserts `raw/a.csv → a.csv`; `TestMergeEntries.test_merge_flattened_local_and_remote` asserts `raw/DPTO.csv → local data/DPTO.csv remote DPTO.csv` (but test fixture still uses `data/` as `data_dir` in that test — reflects pre-`cache/` rename); `TestCopyFiles` and `TestIntegration` exercise `cache/` (`TestConfigConstants.test_output_dir_default_is_cache`). `test_scan_preview_shows_flattened_paths` expects `cache/a.csv` not `cache/raw/a.csv`. No test creates or asserts a `raw/` directory.
  - `tests/test_prepare.py`, `test_publish.py`, `test_model.py`, `test_config.py`: build `DatasetConfig` with explicit `FileEntry(local=tmp_path / "data.csv", remote="data.csv")` or ad-hoc temps; output dir is `tmp_path / "build"` or override. No `raw/` involvement.
  - `tests/conftest.py`: likely provides `pytree` for config discovery tests — anchors on TOML dir vs CWD.
  - Overall: ~795 tests pass; the scan flatten contract already encodes `raw/` semantics but the CLI never creates/migrates it, so tests would need updating only if the scanner's `data_dir` contract or dedup keys change.

### Historical note: `data/` → `cache/` rename

`config.py:29` still comments `_DATA/` semantics while `_DEFAULTS["output_dir"] = "cache"` is the live value. `tests/test_scanner.py:TestMergeEntries` still passes `tmp_path / "data"` as `data_dir` in unit tests (legacy). `README.md` Directory layout lists `data/ source files only` + `cache/` + `build/`. The scanner's `EXCLUSIONS` does not contain `raw`, but `cache`/`build` are excluded. Any `raw/` proposal should reconcile this naming drift (decide whether user-facing docs say `raw/` → `cache/` or `data/`).

## Affected Areas

- `src/sofer/cli.py` — `_INIT_TEMPLATE` (add `raw/` guidance/comments), `_cmd_init` (optionally create `raw/` and/or move loose inputs), `_cmd_scan` (discover/copy/flatten base, optional auto-move, new flags), `EXCLUSIONS` usage and prompt copy.
- `src/sofer/config.py` — new tool-wide defaults if raw layout becomes configurable: e.g. `raw_dir = "raw"` (bootstrap key like `output_dir`), `default_config_name` unchanged; discovery and `reload` unchanged but new constant participates in `[tool.sofer]` overrides per TC-01/TC-02.
- `src/sofer/model.py` — no schema change required (paths stay explicit), but could add optional `[dataset] raw_dir` or `[meta]` hint if proposal wants per-dataset raw location; otherwise `DatasetConfig` validation unchanged.
- `src/sofer/scanner.py` — `flatten_first_level`, `merge_entries`, `copy_files` already implement raw-stripping; needs decision whether scanner stays copy-only (current) or gains a `move_to_raw` step for loose files.
- `src/sofer/prepare.py` / `src/sofer/publish.py` / `src/sofer/_mirror.py` / `src/sofer/codebook.py` — unaffected (they read from staged `cache/` / `build/`); only docs referencing `data/` need alignment.
- `pyproject.toml` `[tool.sofer]` — add `raw_dir` default if adopted.
- `README.md` / `README_ES.md` / `docs/configuration.md` — Directory layout, Typical workflow, Configuration, TOML reference sections must document the new `raw/` convention and the scan/prepare/publish interplay; READMEs must stay in sync per AGENTS.md §13.
- `tests/test_cli.py` / `tests/test_scanner.py` / `tests/test_config.py` — new scenarios: init creates `raw/`, init --move-existing, scan with raw present, migration idempotency, EXCLUSIONS for `raw`, config.toml `raw_dir` override; existing flatten tests remain but fixtures should migrate from `data/` to `cache`/`raw` to avoid confusion.
- `openspec/specs/scan/spec.md`, `openspec/specs/tool-config/spec.md`, `openspec/specs/cli/spec.md` — delta specs will formalize the new requirement and the `raw_dir` config contract if adopted.

## Approaches

1. **A — Convention-only + docs (no code change)**
   - Declare `raw/` as the recommended home for source files (Leek-guide-aligned), document it in README/TOML template comments, and add `raw/` examples to `sofer scan` help and `docs/configuration.md`. Keep scanner behavior unchanged — users create `raw/` and move files manually; `flatten_first_level` already does the right thing. Optionally add `.gitignore` snippet (`/build/`, `/cache/` keep but `/raw/` is tracked).
   - Pros: Zero risk to existing projects/CI; no new flags, no move semantics, no config key; leverages the already-shipped flatten contract; smallest review surface (<100 lines docs).
   - Cons: Does not solve the "loose CSVs in `.` stay mixed" pain — users who already have a messy worktree still do manual work; discoverability is docs-only.
   - Effort: Low

2. **B — `init` creates `raw/` (and optionally moves loose inputs)**
   - `sofer init my-dataset` creates `raw/` alongside `{name}.toml` (`mkdir(exist_ok=True)`). New flag `sofer init --move-existing` (or `--raw`) scans `.` for loose supported files (excluding `cache`/`build`/EXCLUSIONS) and moves them into `raw/` (preserving sub-dirs with flatten-aware dedup check), then `sofer scan` registers them. Without the flag, `init` only creates the dir and updates the TOML template comment to say `# Source files -> raw/ (sofer scan will copy to cache/)`.
   - Pros: One-command setup for green-field projects; opt-in move avoids surprising users who intentionally keep files in `.`; matches `git init` / `npm init` scaffolding expectations.
   - Cons: Move semantics need careful edge handling (flatten collisions like `raw/a.csv` + `processed/a.csv` → same dest, hidden files, permission errors, `--dry-run` preview). Tests must cover move vs. copy distinction.
   - Effort: Medium

3. **C — Config-driven `raw_dir` in `[tool.sofer]` (and optionally `[dataset] raw_dir`)**
   - Add `raw_dir: str = "raw"` to `_DEFAULTS` / `[tool.sofer]` (tool-wide, walk-up-resolved like `output_dir`) and optionally allow `[dataset] raw_dir` to override per-dataset. `scan` uses `raw_dir` as the **preferred** discovery root: when `raw/` exists, discover only under `raw/` (plus root loose files optionally migrated); `flatten_first_level` becomes `strip first segment IFF it equals raw_dir`, otherwise keep path. This makes `raw/` configurable (e.g. `data-raw/`) without hardcoding.
   - Pros: Follows AGENTS.md rule 1 (no hardcoded values) and the existing `[tool.sofer]` walk-up contract (TC-01/TC-02); power users can rename; CI can pin `raw_dir` per repo; mirrors `output_dir` / `build_dir` pattern and is testable via `pytree` overrides.
   - Cons: Adds a bootstrap-like key (like `output_dir`) that must be documented as cwd-anchored before any TOML exists; slightly more config surface.
   - Effort: Medium

4. **D — `scan` auto-migrates loose files into `raw/` (opt-out)**
   - `sofer scan` (or `sofer init` + `scan` combined flow) detects supported files at the config root (depth 1) and offers to move them into `raw/` before copying to `cache/` — interactive prompt by default, `--no-move` to keep them, `--force` to move without prompt, `--dry-run` to preview. This is the most proactive variant of B, applied at scan time rather than init time.
   - Pros: Fixes the existing-project pain automatically; lowest manual effort; visible preview keeps it safe.
   - Cons: Most invasive; changes default `scan` interaction (needs new prompt wording, stdin handling in tests); risks surprising users who intentionally keep a flat layout; requires overwrite/collision guards at two stages (move + copy).
   - Effort: Medium-High

5. **E — Do nothing / defer (explicit rejection)**
   - Conclude that the current flatten + `cache/` + `build/` separation is sufficient and `raw/` is a user-side organization choice, not a tool concern. Document the recommended layout without adding code, and close #84 as `wontfix` or `docs-only`.
   - Pros: No churn, no risk.
   - Cons: Leaves the reported mixing problem unaddressed.
   - Effort: None (docs patch only)

## Recommendation

**Phased B + C, starting with A.**

1. **Immediate (low-risk, ships with this change): A + B-minimal + C-minimal.** Add `raw_dir = "raw"` as a tool-wide `[tool.sofer]` default (mirrors `output_dir`), update `_INIT_TEMPLATE` to mention `raw/` and set `[[file]]` example to `local = "cache/..."` → but document that sources live in `raw/`. Make `sofer init` create `raw/` (`mkdir -p`) — idempotent, no move. Add `sofer init --move-existing` as an opt-in that moves loose supported files at depth 1 into `raw/` (respecting flatten collision checks and printing a preview). This gives green-field ergonomics without breaking brown-field flows and satisfies the acceptance criteria: "`sofer init crea/usa raw/` y mueve inputs alli (o propone hacerlo)" via `--move-existing` / preview.
2. **`scan` stays copy-only for now;** rely on existing `flatten_first_level` (strip `raw/`). Optionally add a `scan --migrate-raw` flag in a follow-up that auto-moves root loose files detected by `discover_files` — only if user feedback shows A+B is insufficient. Keeping `scan` non-mutating on first pass preserves the principle that `scan` never deletes/moves originals (only copies).
3. **Docs:** update Directory layout to `raw/ source files (tracked) → cache/ artifact cache (gitignored) → build/ prepare output (gitignored)`, add a `raw/` → `cache/` flatten diagram (`raw/DPTO.csv → cache/DPTO.csv → build/data/prov/...parquet`), and sync `README_ES.md`.

Rationale: Respects AGENTS.md rules 1 and 3 (configurable, no hardcoded paths; read from TOML not defaults), reuses the shipped `flatten_first_level`/`merge_entries` contract already tested, keeps the review under the 400-line budget (B+C are ~80 LOC + ~120 LOC tests + ~80 LOC docs), and gives a natural migration path (manual → `--move-existing` → `--migrate-raw` if needed) rather than an irreversible auto-move.

## Risks

- **Existing projects with `local = "data.csv"` at repo root.** If `raw/` becomes the recommended root, old TOMLs still validate (files exist in `.`), but a migration that physically moves them would break `local` paths until `scan` re-registers as `cache/...`. Mitigation: never auto-move without explicit flag; migration rewrites TOML via `merge_entries` which already dedups by `remote`, so re-scan after move is safe and idempotent.
- **Flatten collisions.** `raw/a.csv` and `processed/a.csv` already raise `ValueError: Collision in cache/` via `check_flatten_collisions`. Auto-move of root loose files does not create this, but mixing `raw/` + other first-level dirs does. Mitigation: reuse `check_flatten_collisions` in the move path and surface the named-source error before any filesystem mutation.
- **`data/` vs `cache/` naming drift.** `config.py:29` and `README.md` still reference `data/` while live code uses `cache/`. A `raw/` change that does not also reconcile this will confuse users (`raw/ → cache/` vs `raw/ → data/`). Mitigation: align all docs/spec comments to `raw/ → cache/` and add a `data/ → cache` migration note in `docs/configuration.md`.
- **Tool-wide bootstrap timing.** `raw_dir` needed before any dataset TOML exists (like `output_dir`). Its override must be discovered via cwd walk-up (`config.reload(None)` in `cli.main`), not dataset-dir walk. Mitigation: mirror the `output_dir` bootstrap pattern and add a TC-07-style test (`default_config_name` precedent).
- **CI / non-interactive scans.** `scan`'s confirmation prompt (`input("[y/N]")`) already gates copy; any new move prompt must also be skipped under `--force` / `--dry-run` / non-interactive (`not sys.stdin.isatty()`) or it will hang CI. Follow the `copy_files(force)` / `dry_run` contract exactly.
- **`raw/` being excluded or not.** `EXCLUSIONS` currently excludes `cache`/`build` but not `raw` — correctly, since `raw` is the source to discover. If `raw_dir` becomes configurable, the excluded dir must stay as `OUTPUT_DIR` only; never exclude the raw dir itself, or scan becomes empty.
- **README_ES sync.** AGENTS.md §13 mandates `README.md` ↔ `README_ES.md` section sync in the same commit. Any Directory layout or Typical workflow change must land in both files or CI will flag drift.

## Ready for Proposal

Yes — sufficient context to draft `proposal.md` and proceed to `sdd-spec`. Open questions for the proposal to lock before spec:

1. Confirm `raw_dir` lives in `[tool.sofer]` (tool-wide) with default `"raw"` and no per-dataset override initially, to keep the first slice minimal — or include `[dataset] raw_dir` from day one?
2. Should `sofer init` without flags always create `raw/` (empty `mkdir -p`), or only when `--raw` is passed? Recommendation above is always-create (harmless, idempotent).
3. Is `--move-existing` the right flag name, or prefer `sofer init --organize` / `sofer scan --migrate-raw` to make the manual vs. auto-move distinction clearer for users?
