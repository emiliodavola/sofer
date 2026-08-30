# Exploration: feat-publish-clean-and-prune-orphans (GitHub #92)

> Change: `feat-publish-clean-and-prune-orphans` — `feat(publish): add --clean flag to remove cache/build after successful publish (and prune build orphans)`
> Issue: https://github.com/emiliodavola/sofer/issues/92
> Mode: hybrid (Engram `sdd/feat-publish-clean-and-prune-orphans/explore` + filesystem)
> Date: 2026-08-30

## Exploration: feat-publish-clean-and-prune-orphans

### 1. Problem Validation

**Verdict: VALID — confirmed by code evidence.**

Issue #92 verbatim evidence (confirmed against source):

> "`sofer publish` leaves `cache/` (`config.OUTPUT_DIR`, scan destination via `flatten_first_level`) and `build/` (`DatasetConfig.build_dir`, prepare output - Parquet mirror + README/LICENSE/codebooks) on disk after a successful Hub upload. Only the temp `staging_root` (`tmpdir/repo` in `publish.py:679`) is cleaned."

Confirmed:

- `src/sofer/publish.py:679-708` creates `tmpdir = Path(tempfile.mkdtemp())` / `staging_root = tmpdir / "repo"` and `finally: shutil.rmtree(tmpdir, ignore_errors=True)` — **only** the staging tempdir is removed. `cache/` and `build/` are never touched.
- `src/sofer/config.py:32` `OUTPUT_DIR = "cache"` (scan cache) vs `src/sofer/model.py:264` `build_dir: str = "build"` (per-dataset) vs `src/sofer/prepare.py:550-570` `resolve_output_dir()` — the two directories are intentionally distinct but no cleanup path exists.
- `src/sofer/cli.py` — no `--clean` flag on `publish`, `prepare`, or `scan`; `_cmd_publish` delegates directly to `run_publish` without cleanup.
- `README.md` — documents `raw/ -> cache/ -> build/` pipeline and lists `publish` flags (`--target`, `--output`, `--force`, `--keep-csv`, `--dry-run`) but never mentions cleanup (issue states "README no documenta limpieza" — confirmed).
- `.gitignore` lists `cache/` and `build/` but does not delete them (issue correctly notes it "ignora pero no los borra").

> "For large datasets this is ~3x duplication (`raw/` tracked + `cache/` copy + `build/` Parquet package), and `build/` accumulates orphans when TOML entries or XLSX sheets change."

3x duplication is architecturally real: `raw/` is tracked, `scan` copies to `cache/`, `prepare` converts to `build/*.parquet`. No pruning exists.

> "The multisheet XLSX leak fixed in #90 (`DATA_GOT_ALL.xlsx` con hojas `aristas`/`nodos` stageaba `data_got_all_aristas.parquet`+`data_got_all_nodos.parquet` *plus* el `.xlsx` original en `build/` porque los guards en `prepare.py` chequeaban solo `__` mientras `normalize_parquet_remote` colapsa `__` -> `_`) demuestra el riesgo"

Confirmed in `fix-prepare-multisheet-xlsx-copy` (archived 2026-08-30): `normalize_parquet_remote` line 70 `re.sub(r"__+", "_", s)` collapses `__` to `_`. Prior guards in `prepare.py:848/603/364` checked only `__` and missed `data_got_all_aristas.parquet` (single `_` after normalization), leaking the original `.xlsx`. Fix now handles both forms (see `prepare.py:615-622` fallback `c.stem != stem` and `prepare.py:858-873` dual-prefix check). The orphan risk described in #92 is the **next** gap: removing a sheet or a `[[file]]` entry leaves the previously generated `.parquet` stale.

> "No hay flag `--clean` en `prepare`/`publish`/`scan`, y el README no documenta limpieza."

Confirmed — `rg "clean"` returns zero hits in `src/` and `README.md`.

> "`cache/` es compartido tool-wide mientras `build_dir` es por dataset - limpiar `cache/` tras publish de un dataset podria afectar datasets hermanos en mismo cwd."

This scoping risk is genuine and must drive design (see Risks).

**Problem statement is accurate and reproducible** — repro path described `C:/Users/elaze/Desktop/test` with `DATA_GOT_ALL.xlsx` multisheet is consistent with `tests/test_prepare.py:TestMultisheetLeakRegression`.

### 2. Current State

#### Lifecycle: `scan -> prepare -> publish`

```
raw/ (tracked) --scan--> cache/ (config.OUTPUT_DIR, flatten_first_level)
                      --prepare--> build/ (DatasetConfig.build_dir, mirror layout)
                      --publish--> HF Hub (via staging_root tmpdir)
```

**`scanner.py` (290-335, `flatten_first_level`, cache destination):**
- `flatten_first_level(relative)` drops first path segment: `raw/DPTO.csv -> DPTO.csv`, `raw/Labels/a.csv -> Labels/a.csv`. Pure, no side effects.
- `cache/` location is `config.OUTPUT_DIR` (`"cache"` default, overridable via `[tool.sofer] output_dir`). Anchored to TOML `base_dir` in `cli.py:314-315`.
- `EXCLUSIONS` contains `build` but **not** `cache` or `raw` — `cache` excluded via `EXCLUSIONS|{OUTPUT_DIR}`, `raw` excluded only during MOVE phase. This is intentional (SCN-01/SCN-07).
- `copy_files` raises `FileExistsError` without `--force`; `--dry-run` previews without mutation. `scan` never touches `build/`.

**`config.py` (`OUTPUT_DIR` vs `build_dir`, `resolve_output_dir`):**
- `OUTPUT_DIR` (tool-wide, `cache/`) and `RAW_DIR` (`raw/`) live in `config.py` defaults, rebound by `reload(start)` anchored on dataset TOML dir (Phase 1) or cwd (Phase 0, `cli.py:1031`).
- `resolve_output_dir()` in `prepare.py:550-570` returns `cfg._base_dir / (override or cfg.build_dir)` resolved — **never** `config.OUTPUT_DIR`. Per-dataset scoping is correct.
- `OUTPUT_DIR` is `cfg._base_dir / config.OUTPUT_DIR` in `cli.py:314` for scan; `build_dir` is independent.

**`model.py` (`DatasetConfig.build_dir`):**
- `build_dir: str = "build"` (line 264), optional per `[dataset] build_dir`. `from_toml` reloads config anchored on TOML dir. `_base_dir` stores the TOML directory for resolution.
- No `cache_dir` field — cache is tool-wide, not per-dataset.

**`prepare.py` (653-916, `expanded_planned_remotes`, orphan handling):**
- `prepare(cfg, output_dir, force, all_files, ...)` never prunes. It overwrites known remotes when `force=True` but **no deletion** of files absent from `cfg.files`.
- Lines 615-622: `_check_local_overwrite` now handles both `__` and `_` sheet suffixes (fallback glob), confirming the #90 fix is shipped.
- Lines 858-873: `is_converted` check also dual-form. Lines 364-385: `_assert_cross_file_schema` matches both `__` and `_*` prefixes.
- Orphan handling: **none**. After staging converted files via `copy_to_mirror` (lines 797-798), nothing scans `output_dir` for files not in `expanded_planned_remotes`. A removed sheet or deleted `[[file]]` entry leaves a stale `.parquet`.
- `prepare` is called by `publish` with `force=True, all_files=True` (line 611) — so orphans accumulate even on auto-prepare.

**`publish.py` (543-719, `staging_root` cleanup, prepare force):**
- `publish()` resolves `source = resolve_output_dir(cfg, output_dir if target=="hf" else None)` — for `hf` it's the `build/` to publish; for `local` it's the source to copy from.
- Auto-prepare at line 609-613: `if not dry_run and _needs_prepare(cfg, source): prepare(cfg, source, force=True, all_files=True)` — idempotent overwrite, no prune.
- Staging at 679-708: copies via `_copy_package` (which uses `expanded_planned_remotes`) into `tmpdir/repo`, single `upload_folder`, then `shutil.rmtree(tmpdir)` in `finally`. Success check is `fail==0` (line 719 `return 0 if fail==0 else 1`). No post-upload cleanup of `source` or `cache/`.
- Quality gate at 650-653 blocks `hf` target when `quality_report.passed == False`. `--dry-run` at 622-633 skips prepare and upload.

**`cli.py` (`publish`/`prepare`/`scan` flags):**
- `publish` flags: `--target {hf,local}`, `--output`, `--force`, `--keep-csv`, `--dry-run` (lines 752-803). No `--clean`.
- `prepare` flags: `--output`, `--all-files`, `--no-checks`, `--force`, `--verify` (lines 702-751). No orphan/prune flag.
- `scan` flags: `--dry-run`, `--force`, `--ext` (lines 951-1014). No clean.
- `publish` quality gate delegates to `_load_and_validate` which runs `QualityValidator`; `publish` receives `quality_report` as param.

**Tests (795+ tests, README mentions 1029; both in flux):**
- `tests/test_publish.py` — covers PUB-01..10, multi-sheet diff/copy, `keep_csv` CSV-only, `local` offline, split counts. No test for `staging_root` deletion (implicit via `tempfile`) or for `build/`/`cache/` cleanup (issue is open).
- `tests/test_prepare.py` — PRP-01..08, RC-R04, leak regression (`TestMultisheetLeakRegression`), overwrite fallback, schema grouping. No test for orphan pruning (the `is_converted` guard already tested for not leaking originals, but not for deleting stale outputs).
- `tests/test_scanner.py` — `flatten_first_level`, `copy_files`, `merge_entries`, `discover_files`, `EXCLUSIONS`, MOVE-then-copy integration. No test for `clean`.
- No coverage for `publisher --clean` anywhere (preliminary `rg` zero hits).

**README current cleanup docs:**
- Zero mentions of `clean`, `rm -rf`, or post-publish deletion. Layout diagram `raw/ -> cache/ -> build/` is documented, but lifecycle ends at `publish` without noting that `cache/`+`build/` persist. `.gitignore` suppresses git noise but not disk usage, worsening discoverability.

### 3. Proposed Solution Alignment

Issue proposes three complementary pieces:

1. **`sofer publish --clean` (opt-in, default off; never on `--dry-run` or on upload/quality-gate failure):** on successful `hf` upload (`fail==0`), delete `build/` (resolved via `resolve_output_dir(cfg, override)`) and optionally `cache/` (tool-wide `config.OUTPUT_DIR` anchored to `cfg._base_dir`). For `local` target, clean only if explicitly requested.
2. **`sofer clean [cache|build|--all]` *or* reuse flag — mirrors `prepare --force` opt-in pattern. Document in `README.md` and `publish` help.**
3. **`prepare(force=True)` orphan pruning:** after staging, delete files under `output_dir` not in `expanded_planned_remotes(cfg, keep_csv, output_dir)` plus compliance auto-generated set. Reuse `sanitize_sheet_name`/`normalize_parquet_remote` and guard `__`/`_` (`c.stem != stem`) identical to `prepare.py:615-622` and `_mirror.py:PUB-10`.

**Alignment assessment:**

- **Publish --clean:** Aligned with current lifecycle. `publish.py` already computes `source` via `resolve_output_dir` (respects `build_dir` + `--output`), gates on `quality_report` and `fail==0`, and cleans `tmpdir` in `finally` — extending to `source` + `cache/` is a natural, contained addition. The "never on `--dry-run` or failure" constraint maps directly to existing branches (dry-run returns at 633, quality gate at 650-653, upload failure via `_hf_upload_folder` returning False).
- **Orphan pruning:** Aligned with mirror ground truth. `expanded_planned_remotes` already globs `__*.parquet` + fallback `_*` to enumerate actual sheet files on disk; reversing that set to compute orphans is consistent. Compliance files `README.md`/`LICENSE`/`codebook.md`/`codebooks/**` are auto-generated (`publish.PUB-05`/`_AUTO_GENERATED`) and should be part of the allowlist, not deleted as orphans.
- **sofer clean subcommand:** Alignment moderate — it's a convenience wrapper around the same deletion logic. Proposal suggests "flag first, subcommand second" — this matches AGENTS.md concern about duplicating logic (should share a helper). Could be deferred to a second PR if flag is sufficient for CI use case.

**Gaps in proposal:**

- Does not specify `--clean` semantics for `cache/` granularity: delete entire `cache/` tree vs only files owned by this dataset. The issue correctly flags that `cache/` is tool-wide and deleting it may affect sibling datasets.
- Does not specify interaction with `--output` override: when `publish --clean --output ./out` is used, `cache/` is still at `cfg._base_dir/cache`, not `./out`. Cleaning `cache/` in that case is surprising if user expected only `./out` cleaned.
- Does not specify whether `--clean` should also prune after `local` target (proposal says "only if explicit" — needs precise flag design).
- Does not specify ordering for orphan prune vs codebook generation (orphan prune must run after all staging, including `codebooks/`).

### 4. Affected Areas

- `src/sofer/cli.py` — add `--clean` flag to `publish` parser (and optionally `prepare`/`clean` subcommand); plumb through `_cmd_publish` -> `run_publish`; update `description`/`help=` per AGENTS.md rule 7.
- `src/sofer/publish.py` — implement post-upload cleanup in `publish()`: after `fail==0` check, before split report or after, gated on `clean` + `not dry_run` + quality passed + upload succeeded. Resolve `build/` via `resolve_output_dir(cfg, output_dir if target=="hf" else None)` and `cache/` via `cfg._base_dir / config.OUTPUT_DIR` (or `config.RAW_DIR` — but issue proposes only `cache/`+`build/`). Handle `local` target separately (no-op or explicit). Must not swallow `shutil.rmtree` errors silently without reporting.
- `src/sofer/prepare.py` — add orphan pruning step when `force=True` (or behind a flag): after staging (`copy_to_mirror` loops + codebook generation), enumerate `output_dir.rglob("*")`, compute allowlist = `expanded_planned_remotes(...)` + compliance set (`README.md`, `LICENSE`, `codebook.md`, `codebooks/**/*.md`), delete rest. Reuse `_mirror.expanded_planned_remotes` and `_converters.normalize_parquet_remote`/`sanitize_sheet_name` logic; mirror the `__`/`_` guard from `prepare.py:615-622`.
- `src/sofer/_mirror.py` — no change required, but `expanded_planned_remotes` is the ground truth to reuse. A helper `allowed_output_files(cfg, keep_csv, staging_dir)` could be extracted to share between publish and prepare, avoiding duplicated-allowlist bug.
- `src/sofer/config.py` — no change (reads `OUTPUT_DIR`/`build_dir` as today). If a new `[tool.sofer]` default for `clean` is desired, add it here per AGENTS.md rule 1 (no hardcoded values).
- `src/sofer/scanner.py` — no change for `publish --clean`; if `sofer clean` subcommand is added, it may reuse `config.OUTPUT_DIR`/`RAW_DIR` constants.
- `README.md` + `README_ES.md` (rule 13) — document `--clean` behavior, orphan pruning, and multi-dataset `cache/` warning in same commit.
- `openspec/specs/publish/spec.md` — new requirement `PUB-11` for `--clean` (opt-in teardown, never on dry-run/failure, hf vs local semantics, `--output` override).
- `openspec/specs/prepare/spec.md` — new requirement `PRP-09` for orphan pruning on `force` (allowlist = expanded remotes + compliance, dual `__`/`_` guard).
- `tests/test_publish.py` + `tests/test_prepare.py` + `tests/test_cli.py` — spec-driven tests per AGENTS.md rule 6 (every scenario needs a test).

### 5. Approaches

#### Approach 1: Minimal --clean on publish + prune orphans on prepare(force=True) (Recommended baseline)

Add `publish --clean` (default `False`) plus orphan pruning inside `prepare` when `force=True`. Share an `allowed_files` helper. Defer `sofer clean` subcommand.

- Pros:
  - Shortest path to fixing CI disk + stale-Parquet bug (#90 follow-up); no new top-level command bikeshed.
  - Opt-in preserves two-step `prepare -> inspect -> publish` contract (proposal rejects auto-clean as breaking it).
  - `prepare(force=True)` pruning reuses existing `expanded_planned_remotes` ground truth, so XLSX sheet dedup/normalization is correct.
  - Low blast radius: only touches `publish.py` + `prepare.py` + `cli.py` + specs/docs.
- Cons:
  - `cache/` cleaning still affects siblings if user passes `--clean` naively (needs docs + careful default).
  - Orphan pruning on every `force=True` may surprise users who manually drop files into `build/` for debugging.
- Effort: Medium (new flag, allowlist helper, cleanup helpers, tests, docs).

#### Approach 2: Dedicated `sofer clean [cache|build|--all]` subcommand (no publish flag)

Implement only a standalone `clean` command that deletes `cache/` and/or `build/` on demand; `publish` never deletes.

- Pros:
  - Explicit, discoverable, never implicit; safe for multi-dataset workspaces (user chooses scope).
  - Easy to test (just filesystem ops).
  - No risk of deleting artifacts during a publish that had buffered warnings.
- Cons:
  - Does not fix orphan leak automatically — user must remember to run `clean` + `prepare --force` before publish.
  - CI must add a second command (`publish && clean --all`) instead of one flag.
  - Still needs orphan-prune logic to be useful (otherwise just `rm -rf` wrapper).
- Effort: Low-Medium (new CLI subparser + helper).

#### Approach 3: Full hybrid — both `--clean` flag and `sofer clean` sharing a clean helper

Implement a shared `_clean.py` helper (or `src/sofer/clean.py`) with `clean_build(cfg, override)` and `clean_cache(cfg)` functions; both `publish --clean` and `sofer clean --all` call it. Orphan pruning remains in `prepare(force=True)`.

- Pros:
  - Satisfies both personas from issue: CI wants post-publish disk reclaim; local debug wants `build/` inspectable + manual `clean` + orphan prune without full wipe.
  - Single source of truth for "what is safe to delete" (allowlist vs recursive `shutil.rmtree`).
  - Cleanest spec coverage (PUB-11 + PRP-09 + CLI spec).
- Cons:
  - Largest surface: new module, two entry points, more tests, more docs.
  - Risk of inconsistency if `clean` and `--clean` diverge in behavior (must share resolve logic).
- Effort: Medium-High.

#### Approach 4: Auto-clean always (rejected by proposal — documented for completeness)

Always delete `cache/`+`build/` after a successful `publish`.

- Pros: simplest mental model (publish = done, disk clean).
- Cons: breaks `prepare -> inspect -> publish` contract; loses artifacts for `--verify`/codebook review; violates cache semantics; rejected in `Alternatives Considered`.
- Effort: Low.

### 6. Recommendation

**Approach 1 as the proposal's MVP, with Approach 3's shared helper as the implementation shape.**

Rationale:

- Issue's "Example" (`sofer publish dataset.toml --clean` and `sofer publish ... --clean --output ./out`) and the CI persona require the flag. Approach 2 alone leaves CI with a two-command workaround.
- Orphan pruning is inseparable from the leak fix: the `#90` normalization now collapses `__` to `_`, so any pruner must handle both forms — the allowlist helper is the natural place to encode that once.
- Extracting a tiny shared helper (e.g., `src/sofer/_clean.py` with `allowed_output_remotes(cfg, keep_csv, staging_dir)` + `remove_orphans(output_dir, allowed)` + `clean_cache(cfg)`/`clean_build(cfg, override)`) prevents the duplicated-allowlist bug class already seen in PR #90 and satisfies AGENTS.md "no duplicated logic" (cf. `_parquet_helpers.py` extraction).
- Deferring the `sofer clean` subcommand to a second slice keeps the first PR under the 400-line budget while leaving the helper in place to add it cheaply (promote to Approach 3 in a follow-up).

### 7. Risks

- **Multi-dataset `cache/` blast radius (HIGH):** `cache/` is tool-wide (`config.OUTPUT_DIR` anchored to `cfg._base_dir`), not per-dataset. `publish --clean` deleting it after a single dataset's publish will evict siblings' scanned files. Mitigation: document this explicitly in `publish --help` and `README.md`; consider defaulting `--clean` to prune only `build/` unless user adds `--clean-cache` or `--clean=all`. At minimum, print which paths will be removed and require `--force` semantics for the `cache/` part, or gate `cache/` cleanup behind `sofer clean` only.
- **`build/` inspected artifacts lost (MEDIUM):** Users run `prepare` then inspect `build/codebooks/` or `README.md` before publish. Auto-pruning inside `prepare(force=True)` or post-publish `--clean` deletes the inspection target. Mitigation: `--clean` default off, never on `--dry-run`; orphan prune only under `force=True` (explicit); print a pre-delete inventory (`N orphan(s) pruned: <list>`).
- **`--output` override mismatch (MEDIUM):** When `publish --output ./staging --clean` is used, `build/` that gets cleaned is `./staging`, but `cache/` is still `cfg._base_dir/cache`. Cleaning `cache/` may surprise. Mitigation: resolve both independently and log resolved absolute paths; specs must state that `--output` only affects `build/`; `cache/` cleanup is anchored to `cfg._base_dir` regardless.
- **Orphan allowlist drift (MEDIUM):** If orphan logic enumerates `expanded_planned_remotes` but forgets compliance files (`README.md`, `LICENSE`, `codebook.md`, `codebooks/**`) or `keep_csv` originals, they will be mis-identified as orphans and deleted. Mitigation: reuse `publish._collect_codebook_remotes` + `_AUTO_GENERATED` set and `keep_csv` flag; test with multi-sheet XLSX + codebooks fixture.
- **Normalization aliasing (MEDIUM, post-#90):** Ground truth must match the normalized layout on disk (`normalize_parquet_remote` collapses `__` -> `_`). A stale file like `data_got_all_aristas.parquet` (single `_`) must be recognized as owned, not orphan. Mitigation: compute allowlist via `expanded_planned_remotes` filesystem glob (which already globs `__*.parquet` then falls back to `_*`), not via logical `planned_remotes`.
- **Windows path + `OUTPUT_ENCODING`/`shutil.rmtree` errors (LOW):** `publish.py:603-604` reconfigures stdout to UTF-8 on Windows; cleanup logging must not assume POSIX separators. Use `Path` + `shutil.rmtree(..., ignore_errors=False)` with try/except and a clear error message, not `ignore_errors=True` for intentional deletes (silent failures hide permission issues).
- **Test coverage regression (LOW):** AGENTS.md mandates every spec scenario has a test (795+ tests passing today). New PUB-11/PRP-09 need `test_publish.py` + `test_prepare.py` cases for `--clean` only on success, `dry_run` no-delete, quality-gate block, `local` target no-op, `--output` override isolation, multi-sheet orphan, and `cache/` sibling safety. Missing tests will block `sdd-verify`.
- **Chained-PR size (LOW):** Single PR covering flag + orphan prune + specs + tests + README may approach the 400-line budget. Mitigation: forecast in `sdd-tasks` and split into `PUB-11` (publish clean) and `PRP-09` (prune orphans) if needed.

### 8. Alternatives Considered

| Alternative | Why not (verbatim from #92 where applicable) |
|---|---|
| Auto-clean both on every publish | "rechazado - rompe el contrato two-step `prepare` -> inspeccionar -> `publish`; pierde artefacto para `--verify`/revision de codebooks; viola semantica de cache." Confirmed: `prepare`+`publish` are deliberately two-step (AGENTS.md CLI dispatch, `publish` auto-prepares only when stale). |
| Auto-clean only `cache/` | "rechazado - `cache/` es barato de regenerar (`scan` recopia `raw/`), pero `build/` es la fuente de stale (leak PR #90). Limpiar solo cache no arregla Parquets huerfanos." Verified: `scan` can regenerate `cache/` via `copy_files`, but `build/` is the Parquet package with leak history. |
| Leave as is (`rm -rf` manual) | "viable pero acumula disco y archivos stale indefinidamente; usuarios de CI hacen `rm -rf` manual." This is the status quo; it works but violates "no surprises" for large datasets and hides stale-upload bugs. |
| `sofer clean` only without flag | "viable - se propone flag primero, subcomando segundo." Approach 2 above; kept as optional follow-up, not a substitute for CI's single-flag ergonomics. |

### 9. Open Questions

1. **Should `--clean` imply both `build/` and `cache/`, or `build/` only by default?** Issue says "borrar `build/` ... y opcionalmente `cache/`" and warns `cache/` is shared. Proposal's example `sofer publish dataset.toml --clean` is ambiguous whether `cache/` is included. Recommend: `--clean` deletes `build/` only; add `--clean-cache` or `--clean=all` for `cache/` (requires decision before spec).
2. **`local` target semantics:** Issue says "Para target `local`, limpiar solo si se pide explicito". Does `--clean` on `local` clean the destination (`--output`) or the source `build/`? Needs spec wording.
3. **Orphan prune flag vs implicit on `force`:** Should orphan pruning be unconditional on `prepare --force`, or behind a separate `--prune`? Current proposal ties it to `force=True` — confirm with reviewers (affects `PRP-09` GWT).

### 10. Readiness Verdict

**GO — with blockers noted.**

No blocker prevents drafting a proposal. Codebase is well-factored (`_mirror.expanded_planned_remotes` cleanly separates logical vs ground truth, `resolve_output_dir` already isolates `build_dir`, `config.OUTPUT_DIR` is the cache anchor), tests are comprehensive, and the `#90` fix provides the exact dual-`_`/`__` guard to reuse.

**Blockers / required pre-conditions for proposal:**

1. **[DECISION] Clean scope must be pinned before spec:** whether `--clean` => `build/` only or `build/`+`cache/` (recommend `build/` only + `--clean-cache`). Without this, `PUB-11` cannot be written with MUST/SHALL precision.
2. **[SPEC] `PUB-11` and `PRP-09` need GWT scenarios written before implementation:** in particular, the `cache/` sibling safety scenario and the single-`_` orphan scenario.
3. **[DOC] `README.md` + `README_ES.md` sync must be planned (AGENTS.md rule 13):** English prose vs Spanish prose, but commands/flags stay in English.
4. **[TEST] Plan to keep 400-line budget:** flag + prune + subcommand may exceed budget — `sdd-tasks` must forecast and recommend chaining if needed.

### 11. References

- Issue #92 body — verbatim evidence quoted in §1.
- `src/sofer/publish.py:543-719` (delivery + `tmpdir/repo` staging, `finally: rm -rf tmpdir`)
- `src/sofer/prepare.py:653-916` (conversion, `resolve_output_dir`, `is_converted`, `_check_local_overwrite` dual guard 615-622)
- `src/sofer/scanner.py:290-335` (`flatten_first_level`, `copy_files`, `merge_entries`, `EXCLUSIONS`, cache destination)
- `src/sofer/config.py:32-33` (`OUTPUT_DIR="cache"` vs `build_dir`), `src/sofer/model.py:264` (`build_dir="build"`)
- `src/sofer/cli.py` (`publish`/`prepare`/`scan` flags, no `--clean`)
- `src/sofer/_mirror.py:PUB-10` (`expanded_planned_remotes` with `__` + `_` fallback, `sanitize_sheet_name`/`normalize_parquet_remote`)
- `src/sofer/_converters.py:37-99` (`normalize_parquet_remote`, `sanitize_sheet_name`)
- `README.md` §§ Layout / Pipeline / publish flags (no cleanup docs); `.gitignore` (`cache/`, `build/` ignored)
- Tests: `tests/test_publish.py`, `tests/test_prepare.py` (incl. `TestMultisheetLeakRegression`), `tests/test_scanner.py` (795 tests passing)
- Prior fix: `openspec/changes/fix-prepare-multisheet-xlsx-copy` (archived 2026-08-30) and `openspec/specs/prepare:PRP-02` single-underscore norm.

### Risks (summary for envelope)

- Multi-dataset `cache/` blast radius (HIGH)
- Lost inspection artifacts (MEDIUM)
- `--output` override mismatch (MEDIUM)
- Allowlist drift deleting compliance/keep_csv files (MEDIUM)
- Normalization aliasing on single-underscore sheets (MEDIUM)
- 400-line budget if flag + prune + subcommand in one PR (LOW)

### Recommendation (summary)

Proceed with **Approach 1** (publish `--clean` + orphan prune on `prepare(force=True)`) implemented via a small shared helper (`allowed_output_remotes` / `remove_orphans`), specs `PUB-11`/`PRP-09`, and tests; add `sofer clean` subcommand as a follow-up slice if desired. Pin clean-scope decision before spec.

### Ready for Proposal

**Yes — GO.** Proposal can be drafted once clean-scope (build-only vs build+cache) and local-target semantics are decided. No code changes required for this exploration; artifact persisted to both backends.

---

*Evidence-checked on 2026-08-30 against `src/sofer/publish.py:679`, `src/sofer/prepare.py:615-622/653-916`, `src/sofer/scanner.py:290-335`, `src/sofer/config.py:32`, `src/sofer/model.py:264`, `src/sofer/cli.py` publish parser (no `--clean`), `src/sofer/_mirror.py:PUB-10`, `src/sofer/_converters.py:37-99`, `README.md`/`pyproject.toml`/`tests/test_*`.*
