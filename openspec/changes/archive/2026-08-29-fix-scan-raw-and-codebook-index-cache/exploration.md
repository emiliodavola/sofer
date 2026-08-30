# Exploration: fix-scan-raw-and-codebook-index-cache

## Current State

### Scan / raw folder (Bug 1)

* **Pipeline documented:** `raw/` (tracked source root) -> `cache/` (`OUTPUT_DIR`, gitignored) -> `build/` (gitignored). `sofer init` scaffolds `raw/` (`mkdir -p raw/` idempotent); `sofer init --move-existing` moves depth-1 supported files into `raw/`. `sofer scan` is defined as **copy-only**: it discovers supported files under the config directory, flattens the first path segment via `flatten_first_level`, and copies to `cache/` (`scanner.copy_files` + `shutil.copy2`). Sources are never moved/deleted.
* **Discovery:** `scanner.discover_files(root, extensions, exclude_dirs)` walks `root.rglob("*")`, prunes any path where a part is in `exclude_dirs`, and keeps files whose suffix is in `SUPPORTED_FORMATS` (`.csv`, `.tsv`, `.parquet`, `.xlsx`, `.jsonl`). `_cmd_scan` builds `exclude = EXCLUSIONS | {OUTPUT_DIR}` where `EXCLUSIONS = {.git, __pycache__, .venv, node_modules, dist, build}`. Consequence: `raw/a.csv` is discovered, `cache/a.csv` is excluded, loose `a.csv` at root is discovered.
* **Merge vs copy:** `merge_entries` registers `local = cache/<flat>` and `remote = <flat>` for each discovered file, deduplicating on resolved absolute path and on remote (migration-safe for old `data/` layouts). `copy_files` copies **every** discovered file to `data_dir / flat` (lazy `mkdir(parents)`), honoring `force`/`dry_run`. TOML write happens **after** copy, skipped on `dry_run`.
* **What the CLI does today:** `_cmd_scan` ( `src/sofer/cli.py:264` ) never creates `raw/`. It resolves `data_dir = base_dir / config.OUTPUT_DIR` and delegates to `discover_files` / `copy_files`. Verified by probe: with loose files `a.csv, b.tsv, c.xlsx, d.jsonl, e.parquet` at root, all five are discovered and copied to `cache/`; with files under `raw/`, they are flattened to `cache/` (e.g. `raw/Labels/a.csv -> cache/Labels/a.csv`). No `raw/` mkdir, no move into `raw/`.
* **User observation:** "crea la carpeta raw/ pero NO copia los archivos .csv, .tsv, .xlsx, .jsonl y .parquet a raw/". Literal reading conflicts with code: `_cmd_scan` does **not** create `raw/` and its contract is to copy **to `cache/`**, not to `raw/`. Two plausible interpretations:
  1. The user labels `cache/` as `raw/` (documentation confusion) and actually observes `cache/` empty — the real symptom is that `cache/` is not populated despite `raw/` existing.
  2. The user expects `scan` to **collect** loose files into `raw/` as the canonical source (like `init --move-existing` does automatically), because the documented pipeline says "put files in raw/, scan copies to cache/". With loose files, the current `scan` bypasses `raw/` entirely (root `a.csv -> cache/a.csv`), so `raw/` stays empty — which matches "crea raw/ pero no copia a raw/".
* **Hard evidence for bug 2 but not for total copy failure:** Probes on current `main` show all five extensions are discovered and `copy_files` writes them to `cache/` correctly. No filter drops `.tsv`/`.xlsx`/etc. The only path where `cache/` would stay empty is: collision error early-exit (no copy), interactive prompt answered `N` (abort before copy), or `FileExistsError` without `--force`.

### Codebook index cache vs root (Bug 2) — CONFIRMED

* **Routing in `src/sofer/codebook.py:387` (`generate_all`):**
  ```python
  if output_dir is None:
      write_root = data_dir          # base/cache
      root_path = base_dir / "codebook.md"   # BUG: base/codebook.md
  else:
      write_root = out.resolve()     # build/
      root_path = write_root / "codebook.md" # correct: build/codebook.md
  codebooks_dir = write_root / CODEBOOKS_DIR  # cache/codebooks or build/codebooks
  # per-file: (codebooks_dir / rel_stem).with_suffix(".md")
  # index: root_path.write_text(...)
  ```
  Per-file pages always go to `cache/codebooks/*.md` in standalone mode, but the **root index** goes to `./codebook.md` (project root). `Option B` ( `prepare --all-files` passes `output_dir=build` ) is consistent: everything under `build/`.
* **Downstream expectations:** `prepare.py` checks `output_dir / "codebook.md"` and `codebooks_dir` for overwrite protection; `publish.py` collects `output_dir / "codebook.md"` + `codebooks/**/*.md`. Those paths assume `build/codebook.md` — correct for `prepare`. The standalone `codebook --all-files` path, however, should be `cache/codebook.md` + `cache/codebooks/` per `README` ("codebook --all-files writes cache/codebooks/") and per `cli.py:712` description. Tests in `tests/test_codebook.py` currently assert `tmp_path / "codebook.md"` (root) — they **encode the bug** and will need updating.
* **Reproduced by static inspection:** `uv run python scratch/probe_cb2.py` prints `root_path = base_dir / "codebook.md"` for the `output_dir is None` branch. Issue is line 441.

## Affected Areas

- `src/sofer/scanner.py` — `discover_files`, `merge_entries`, `copy_files`, `flatten_first_level`, `EXCLUSIONS` constant, module docstring (`raw/ -> cache/ -> build`).
- `src/sofer/cli.py` — `_cmd_scan` orchestration (phases discover -> merge -> copy -> write), `_cmd_init` (`raw/` scaffold + `--move-existing` move), parser help text for `scan`.
- `src/sofer/config.py` — `RAW_DIR` (`raw`), `OUTPUT_DIR` (`cache`), `_DEFAULTS` (`output_dir`, `raw_dir`), `reload` anchoring, `SOURCE_PATH`.
- `src/sofer/_formats.py` — `SUPPORTED_FORMATS` registry (keys drive discovery).
- `src/sofer/codebook.py` — `generate_all` (write_root/root_path/codebooks_dir split, index generation, collision handling), `generate` single-file path.
- `src/sofer/prepare.py` — `_check_local_overwrite`, `prepare` codebook step (Option B, `generate_all(cfg, output_dir=...)`), `_GENERATED_ROOT_FILES`.
- `src/sofer/publish.py` — `_collect_codebook_remotes`, `_copy_package`, `_print_split_report` (codebook remotes).
- `openspec/specs/scan/spec.md` — SCN-01..SCN-07, flatten semantics, EXCLUSIONS, dry-run/idempotency.
- `openspec/specs/codebook/spec.md` — codebook generation + index location.
- `openspec/specs/tool-config/spec.md` — `output_dir`/`raw_dir` tool defaults.
- `tests/test_scanner.py` — `TestFlattenFirstLevel`, `TestDiscoverFiles`, `TestMergeEntries`, `TestCopyFiles`, `TestIntegration`, `TestRawCacheDiscovery`, `TestSourceLayoutCopyOnly`.
- `tests/test_codebook.py` — `TestGenerateAll*`, `TestEdgeCases`, index path assertions.
- `tests/test_cli.py` / `tests/test_config.py` — `raw_dir` bootstrap, `init --move-existing`, scan e2e.
- Docs: `README.md`, `README_ES.md`, `docs/configuration.md` — directory layout diagram `raw/DPTO.csv -> cache/DPTO.csv -> build/*.parquet`.
- `.gitignore` — `cache/` is not explicitly ignored today (only `build/` and `__pycache__/`, etc.) — `OUTPUT_DIR` being `cache/` relies on user adding it or on prepare ignoring? Worth confirming.

## Approaches

### Bug 1 — `scan` raw/ handling

#### 1A. Minimal — ensure `raw/` scaffold + fix cache copy reliability (Low effort)

* Make `_cmd_scan` `mkdir -p raw/` (idempotent) at start, matching `_cmd_init` behavior and guaranteeing SCN-07's "tracked source root exists". Keep `scan` as `raw/ -> cache/` copy-only; do **not** move loose files into `raw/`.
* Audit that all five extensions are indeed copied to `cache/` (they already are) and add explicit five-format e2e test.
* Update `scanner.py` docstring and `cli.py` help to state `raw/` is never populated by `scan` — `init --move-existing` is the only collector.

- Pros: smallest diff (one `mkdir`), no behavior change for existing `raw/` users, no risk of duplicating loose files into both `raw/` and `cache/`, trivial rollback.
- Cons: does not address the user's literal expectation that loose files should end up in `raw/`; user would still need `sofer init --move-existing` or manual move before `scan`.
- Effort: Low

#### 1B. Collector — `scan` gathers loose/out-of-raw files into `raw/` before `raw/ -> cache/` (Medium effort)

* Add a pre-phase in `_cmd_scan`: after discovering, partition discovered files into `under_raw/` vs `loose/` (files whose flattened first segment equals their original relative path, i.e. root-level or non-raw subdirs). Copy (or optionally move) `loose/` files into `raw/` (preserving substructure after first segment), then re-discover or map them through `raw/` for the normal `cache/` copy. Guard with `--force` / prompt, respect `EXCLUSIONS` and collision checks.
* Optionally deduplicate: if `raw/X.csv` already exists, skip collector copy.

- Pros: matches the literal bug description ("scan should copy to raw/"), makes `scan` a one-step organizer for messy working directories, aligns with `init --move-existing` intent but without requiring a separate command.
- Cons: changes `scan` from idempotent copy-only to a **state-mutating collector** — surprises existing workflows where loose files are intentionally kept outside `raw/`; introduces new overwrite/collision surface between loose and `raw/`; needs spec change (SCN-01/SCN-03) and migration of `init --move-existing` docs.
- Effort: Medium

#### 1C. Fix-only-cache — clarify naming, no new raw/ write (Low effort, docs-only + test hardening)

* Keep code change minimal (maybe just ensure `raw/` scaffold for completeness, no collector), but treat the report as a **naming confusion**: update `README`/`docs/configuration.md`/`SCN-07` to emphasize that `scan` never writes to `raw/` — it reads `raw/` and writes `cache/`. Add CLI log line `raw/ -> cache/` and test that `cache/` contains exactly the five extensions.

- Pros: zero risk, addresses 80% of confusion via docs.
- Cons: does not satisfy a user who genuinely needs auto-collection into `raw/`.
- Effort: Low

### Bug 2 — codebook index location

#### 2A. Move root index to `cache/` in standalone mode (Low effort — RECOMMENDED for code)

* Change `src/sofer/codebook.py:441` from `root_path = base_dir / "codebook.md"` to `root_path = write_root / "codebook.md"` (i.e. `cache/codebook.md` when `output_dir is None`). Then per-file `cache/codebooks/` + index `cache/codebook.md` are co-located, and `prepare`'s `build/codebook.md` stays correct.
* Consequences: `_collect_codebook_remotes` and `_copy_package` already look at `output_dir / "codebook.md"` for `build/` case — for standalone, callers that previously expected `./codebook.md` will now look in `cache/`; need to update those call sites or document that standalone index is now under `cache/`. Update `tests/test_codebook.py` assertions from `tmp_path / "codebook.md"` to `tmp_path / "cache" / "codebook.md"`, and fix `cli.py` help text "...written under cache/codebooks/ plus cache/codebook.md".

- Pros: one-line fix, makes both modes consistent (index beside its pages), satisfies user report ("Debe ir a cache").
- Cons: breaking for users/scripts that hardcode `./codebook.md` after `codebook --all-files` — migration note needed; tests that encode the bug will fail until updated.
- Effort: Low

#### 2B. Dual-write — keep root index plus cache mirror (Medium effort)

* After generating `base_dir / "codebook.md"`, also write a copy to `cache/codebook.md` (or vice versa).

- Pros: backward compatible, no breakage for existing `./codebook.md` consumers.
- Cons: two sources of truth, drift on reruns, contradicts user's "Debe ir a cache" (should **go** to cache, implying not root), extra complexity for publish (which file to pick).
- Effort: Medium

## Recommendation

* **Bug 1:** Implement **1A** (minimal scaffold) and document the `raw/ -> cache/` contract explicitly. Treat the report's "no copia a raw/" as a **terminology mix-up** (`cache/` empty, not `raw/` empty) unless follow-up confirms the user needs auto-collection. If product confirms auto-collection is desired, follow with **1B** as a separate, specced change — do not bundle it with the bug fix because it changes copy-only semantics.
* **Bug 2:** Implement **2A** (move index to `cache/codebook.md`). It is the intended design per `config.CODEBOOKS_DIR = "codebooks"` + `OUTPUT_DIR = "cache"` and is a single-line correction. The alternative 2B hides the bug rather than fixing it.

Both fixes are small enough to ship as one PR without exceeding the 400-line review budget (estimated: `codebook.py` 1 line + `cli.py` 2-3 lines for `raw/` mkdir + tests 10-20 lines + doc updates 5 lines).

## Risks

- **Test suite encodes bug 2:** `tests/test_codebook.py:556`, `:573`, `:591`, `:679`, `:772`, `:806` assert `tmp_path / "codebook.md"` exists. After 2A they will fail until pointed at `tmp_path / "cache" / "codebook.md"`. Coordinate the fix with test updates in the same commit or CI will go red.
- **Users depending on `./codebook.md`:** Any downstream that opens `codebook.md` at the project root after `codebook --all-files` will break. Mitigate with a release note and a one-release symlink/migration warning (optional).
- **`.gitignore` gap for `cache/`:** `cache/` is the artifact directory but `.gitignore` only ignores `build/` and `__pycache__/`, not `cache/`. After the fix, `cache/codebook.md` and `cache/codebooks/` will appear as untracked files. Add `cache/` to `.gitignore` or document that `[tool.sofer] output_dir = "cache"` is expected to be gitignored via the template.
- **Bug 1 ambiguity:** If the user's actual need is 1B (auto-collect into `raw/`) and we ship 1A only, the report will be considered unfixed. Mitigate by confirming with the user: "Do you expect `scan` to move loose `.csv` etc. at the project root into `raw/` automatically, or only to copy `raw/` into `cache/`?"
- **Collision semantics for raw/ scaffold:** Adding `mkdir -p raw/` is safe, but if we later add 1B collector, we must re-run `check_flatten_collisions` after the `raw/` copy to avoid double-flatten collisions.

## Ready for Proposal

Yes — root causes identified with file-level precision (codebook bug confirmed on `src/sofer/codebook.py:439-441`; scan behavior characterized via `src/sofer/scanner.py` + `src/sofer/cli.py:264-351` + probes). Decision on Bug 1 variant (1A vs 1B) should be confirmed with the user/product before drafting the proposal, but a proposal can be written immediately assuming 1A + 2A. Next phase: `sdd-propose` to lock scope (`scan` mkdir `raw/` vs collector, and `cache/codebook.md` relocation) and acceptance criteria.

