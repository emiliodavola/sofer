# Archive Report: feat-publish-clean-and-prune-orphans

**Change**: `feat-publish-clean-and-prune-orphans` (GitHub #92, PR #93)
**Date archived**: 2026-08-30
**Artifact store**: hybrid (openspec + Engram) — both
**Execution mode**: auto
**Status**: archived — SDD cycle complete
**Verify verdict**: PASS 14/14 (verify-report #721 — 0 blockers, 0 critical)
**Merge commit**: `a7f09ca` — Merge pull request #93 from emiliodavola/feat/92-publish-clean-and-prune-orphans
**Branch**: `feat/92-publish-clean-and-prune-orphans` → `dev` (PR #93)

## Summary

`publish` previously cleaned only `staging_root`; `cache/` + `build/` persisted (3× duplication) and `build/` accrued orphan `.parquet` when TOML entries or XLSX sheets were removed (`#90` `__` → `_` normalization leak). This change adds opt-in cleanup while preserving `prepare → inspect → publish`.

- `publish --clean` (default off, build-only) deletes the resolved build directory only after a successful `hf` upload (`fail == 0`). No delete on `--dry-run`, quality-gate block, or `upload_folder` failure. `--clean-cache` / `--all` (aliases, dest `clean_cache`) deletes `cache/` (`cfg._base_dir / config.OUTPUT_DIR`, tool-wide sibling-shared) with a warning.
- For `--target local`, `--clean` deletes the resolved `--output` destination only; without `--clean` nothing is deleted. Build path resolved via `resolve_output_dir(cfg, --output)` so `--output ./staging` deletes `./staging`, not default `build/`.
- `prepare(force=True)` prunes orphans after staging+codebooks via shared helper `src/sofer/_clean.py` (`allowed_output_remotes` + `prune_orphans`) reusing `expanded_planned_remotes` with dual `__`/`_` guard identical to `prepare.py:615-622`, so single-underscore sheets (`DATA_GOT_ALL.xlsx` → `data_got_all_aristas.parquet`) are recognized as owned, not orphan. `force is False` skips prune entirely. Idempotent; `try/except` per file; logs absolute paths.

No new `[tool.sofer]` defaults; `config.py` unchanged.

## Files Changed

| File | Action | Details |
|------|--------|---------|
| `src/sofer/_clean.py` | Created (227 lines) | `allowed_output_remotes(cfg, keep_csv, output_dir)` — unions `expanded_planned_remotes` (dual `__`/`_` guard) + `{README.md, LICENSE, codebook.md, codebooks/**}` prefix + recursive `remote + "/"` sentinels + `keep_csv` CSV remotes; `prune_orphans(output_dir, allowed)` — `rglob`, per-file `try/except`, log absolute path; `clean_build`/`clean_cache` — existence check + `shutil.rmtree` + `try/except`, `clean_cache` anchored to `cfg._base_dir / config.OUTPUT_DIR`, warning siblings |
| `src/sofer/cli.py` | Modified | Added `--clean` (build-only, default off) + `--clean-cache`/`--all` alias to `publish` (dest `clean_cache`), plumbed to `run_publish(clean, clean_cache)`, help warns `cache/` is sibling-shared, `resolve_output_dir` mention |
| `src/sofer/publish.py` | Modified | Added `clean`/`clean_cache` params to `run_publish`; `hf` path gates on `clean and not dry_run and quality_passed and fail == 0`; build via `resolve_output_dir(cfg, _output)`; cache via `cfg._base_dir / config.OUTPUT_DIR` when `clean_cache`; `local` path gates on `clean and not dry_run` and deletes resolved destination only; `try/except` without `ignore_errors=True`; rmtree `tmpdir` in `finally` preserved |
| `src/sofer/prepare.py` | Modified | After codebooks, when `force is True` calls `allowed_output_remotes` then `prune_orphans` (lines 895-905); `force is False` skips entirely |
| `src/sofer/config.py` | None | Reuse `OUTPUT_DIR`/`CODEBOOKS_DIR` constants; no new defaults |
| `tests/test_clean.py` | Created (262 lines) | `TestAllowedOutputRemotes` (single-`_` `DATA_GOT_ALL` in allowlist, `keep_csv` adds CSV), `TestPruneOrphans` (stale delete, compliance/codebooks retained, keep_csv retained, idempotent, single-underscore orphan), `TestCleanHelpers` (`clean_build`/`clean_cache` anchored, noop when missing) |
| `tests/test_publish.py` | Modified (+185 lines) | `TestPublishClean` — 8 PUB-11 scenarios: `test_clean_deletes_build_on_success`, `test_clean_and_cache_deletes_both`, `test_dry_run_with_clean_does_not_delete`, `test_quality_fail_with_clean_does_not_delete`, `test_upload_failure_with_clean_does_not_delete`, `test_local_without_clean_does_not_delete`, `test_local_with_clean_deletes_destination_not_build`, `test_custom_output_clean_anchored` (mock `upload_folder`) |
| `tests/test_prepare.py` | Modified (+100 lines) | `TestPreparePruneOrphans` — 6 PRP-09 scenarios: `test_single_underscore_orphan_via_prepare`, `test_force_true_prunes_stale_parquet`, `test_compliance_survives_force_prune`, `test_idempotent_second_force`, `test_force_false_retains_orphan`; plus compliance/keep_csv retention |
| `tests/test_cli.py` | Modified (+75 lines) | `publish --help` contains `--clean`/`--clean-cache`/`--all`; parser plumbs `clean`/`clean_cache` correctly |
| `README.md` | Modified | Documented `--clean`/`--clean-cache`/`--all`, build-only default, sibling `cache/` warning, `--output` anchoring |
| `README_ES.md` | Modified | Mirrored per AGENTS.md rule 13 — headings/order synced, flags/commands English, only prose translated |
| `openspec/specs/publish/spec.md` | Modified | PUB-11 delta synced — ADDED Requirement `Build cleanup on successful publish` (8 scenarios) appended after PUB-08 |
| `openspec/specs/prepare/spec.md` | Modified | PRP-09 delta synced — ADDED Requirement `Orphan pruning on force prepare` (6 scenarios) appended after PRP-07 |
| `openspec/changes/feat-publish-clean-and-prune-orphans/specs/publish/spec.md` | Delta | ADDED PUB-11 — source of publish merge |
| `openspec/changes/feat-publish-clean-and-prune-orphans/specs/prepare/spec.md` | Delta | ADDED PRP-09 — source of prepare merge |
| `openspec/project.md` | Modified | Sync (via PR #93) — tech stack/testing context |

## Delivery

| Field | Value |
|-------|-------|
| Estimated changed lines | 260–360 (code ~120, tests ~140, docs ~60) — actual 1633 insertions across 18 files in merge commit (includes deltas + docs) |
| 400-line budget risk | Low |
| Chained PRs recommended | No — single PR |
| Delivery strategy | auto (single PR 3000-line budget) |
| Review scope | Single work unit — helper + CLI + publish/prepare wiring + tests + docs atomic |
| Commits (PR #93) | `2fd1764 feat(publish): add --clean and prune orphans (PUB-11/PRP-09)` · `921a620 docs: document --clean/--clean-cache/--all and orphan pruning` · `05025a0 chore(sdd): add feat-publish-clean-and-prune-orphans specs and design` · `c972003 chore(sdd): add apply-progress` — merged as `a7f09ca` |

## Spec Sync

| Domain | Action | Details |
|--------|--------|---------|
| publish | Updated | ADDED PUB-11 appended to `openspec/specs/publish/spec.md` (1 added requirement, 8 added scenarios) — preserved PUB-01, PUB-02, PUB-09, PUB-10, PUB-03, PUB-04, PUB-05, PUB-07, PUB-08 |
| prepare | Updated | ADDED PRP-09 appended to `openspec/specs/prepare/spec.md` (1 added requirement, 6 added scenarios) — preserved PRP-01, PRP-02, PRP-02a, PRP-02b, PRP-03, PRP-04, PRP-05, PRP-06, PRP-08, PRP-07 |

Delta `specs/{publish,prepare}/spec.md` → canonical `specs/{publish,prepare}/spec.md`. Other requirements unchanged. No REMOVED/RENAMED deltas. Merge was append-only (non-destructive) — no warning required per `openspec/config.yaml` `rules.archive: Warn before merging destructive deltas`.

**Index**: `openspec/specs` contains 14 domain specs; no separate index file to update — each domain `spec.md` is the source of truth.

## Task Completion

| Phase | Tasks | Status |
|-------|-------|--------|
| 1 Foundation — Shared Helper | 1.1 allowed_output_remotes · 1.2 prune_orphans · 1.3 clean_build/clean_cache | 3/3 ✅ |
| 2 Core — CLI and Publish/Prepare Wiring | 2.1 cli --clean/--clean-cache/--all · 2.2 publish clean/clean_cache gating + resolve_output_dir · 2.3 hf cache cleanup · 2.4 local dest-only · 2.5 prepare force prune | 5/5 ✅ |
| 3 Testing — PUB-11/PRP-09 | 3.1 test_clean · 3.2 test_publish (8) · 3.3 test_prepare (6) · 3.4 test_cli help/plumb · 3.5 ruff+mypy+pytest green | 5/5 ✅ |
| 4 Documentation and Polish | 4.1 README · 4.2 README_ES · 4.3 CLI help strings · 4.4 deltas verified | 4/4 ✅ |
| **Total** | **17** | **17/17 ✅** |

All task checkboxes `[x]` in archived `tasks.md`. No stale unchecked tasks. No exceptional reconciliation needed — `sdd-apply` already marked persisted tasks complete and `verify-report` confirms `Tasks complete: 17`.

## Verification Evidence

- **Test command**: `uv run pytest tests/ -q` → `1062 passed, 2 skipped, 13 warnings in 16.28s` at verify time (hash `sha256:6e54a3fb08efb99a63b891f7ebd22bb95aa5b3c30f10200ff908e08cc061b177`) — exit 0; current branch `feat/77-mcp-registration-automation` now shows `1149 passed, 2 skipped` (1062 + subsequent profile/render batch), confirming no regression. Targeted subset `tests/test_clean.py tests/test_publish.py tests/test_prepare.py tests/test_cli.py` → `184 passed in 2.83s`.
- **Build**: `uv run ruff check src/ tests/` → `All checks passed!`; `uv run mypy src/` → `Success: no issues found in 28 source files` — exit 0 — hash `sha256:03f9e664b02d3ab063da47fd53aceca010149a42c83a7a617985f636727a5227`.
- **Spec compliance**: 14/14 scenarios COMPLIANT (8 PUB-11 + 6 PRP-09) — each with a covering test that passed at runtime. See verify-report Spec Compliance Matrix for test names.
- **Correctness**: PUB-11 gate `clean && !dry_run && quality_passed && fail==0` at `publish.py:748`; build vs cache isolation via `cli.py:819,828` dest `clean_cache`; local dest-only at `publish.py:662-668`; PRP-09 allowlist via `_clean.py:58-116` unions `expanded_planned_remotes` dual guard + compliance + keep_csv; no hardcoded values (`config.OUTPUT_DIR`/`CODEBOOKS_DIR`, `cfg._base_dir`, `resolve_output_dir`); docstrings present; READMEs synced per rule 13; CLI help accurate.
- **Coherence**: Shared helper `_clean.py` single source of truth; CLI granularity build-only + `--clean-cache`/`--all` respects HIGH blast radius with warning; gating + anchoring exactly as `design.md:54-66`; orphan prune after staging+codebooks when `force=True`, idempotent, `force=False` no-op.
- **Critical issues**: 0; **Warnings**: 0; **Suggestions**: 3 non-blocking (deferred `sofer clean` subcommand, explicit `force=False` no-prune unit at `_clean` level, README publish row readability) — no action now.
- **Verdict**: **PASS** — Archive-ready.

## Rollback Plan

Revert cleanup wiring:

- Remove `--clean`/`--clean-cache`/`--all` flags in `src/sofer/cli.py` (dest `clean_cache`, plumbed `clean`/`clean_cache`) and `publish.py` gated deletion blocks (`clean and not dry_run and quality_passed and fail==0` for `hf`; `clean and not dry_run` for `local` dest) + `clean_build`/`clean_cache` calls anchored via `resolve_output_dir`/`cfg._base_dir / config.OUTPUT_DIR`.
- Remove `force` prune call in `src/sofer/prepare.py:895-905` (`allowed_output_remotes` + `prune_orphans`).
- Delete `src/sofer/_clean.py` (allowed_output_remotes, prune_orphans, clean_build, clean_cache, `_AUTO_GENERATED`/`_is_auto_generated`).
- Revert `openspec/specs/publish/spec.md` PUB-11 and `openspec/specs/prepare/spec.md` PRP-09 (remove appended requirements).
- No migration; single commit revert; on-disk `build/`/`cache/` remain valid.

## Lessons & Follow-ups

- **Sibling-shared cache**: `config.OUTPUT_DIR` (`cache/`) is tool-wide (`cfg._base_dir / "cache"`), shared by all datasets — `--clean` MUST stay build-only; cache deletion requires explicit opt-in with warning to avoid HIGH blast radius.
- **Dual guard reuse**: `expanded_planned_remotes` fallback `stem_*.parquet` filtered `c.stem != stem` (mirrors `prepare.py:615-622`) correctly handles single-underscore `DATA_GOT_ALL` sheets — reuse, don't reimplement.
- **Anchoring**: `resolve_output_dir(cfg, _output)` for build vs `cfg._base_dir / config.OUTPUT_DIR` for cache keeps `--output` overrides independent; log absolute paths via `_clean.py`.
- **Idempotency**: `prune_orphans` is safe to rerun (second `force=True` deletes 0); `force=False` must not scan at all.
- **Gotcha**: `_AUTO_GENERATED` duplicated in `_clean.py` to avoid circular import with `publish.py` — intentional; behavior identical (case-insensitive, `codebooks/` prefix).
- **Follow-up (deferred, non-blocking)**: `sofer clean` standalone subcommand reusing `_clean` — per `proposal.md` Out of Scope and `design.md` Deferred; no action this slice.
- **Pre-commit**: `ruff --fix + ruff-format + mypy (uv run mypy src/)` runs on every commit — CI rejects type errors; verify used `uv run ruff check src/ tests/ && uv run mypy src/` green.

## Engram Traceability

| Artifact | Observation ID | sync_id | Topic key |
|----------|---------------|---------|-----------|
| proposal | #716 | obs-9f41d562da841422 | sdd/feat-publish-clean-and-prune-orphans/proposal |
| spec (delta) | #717 | obs-0d807ab28ebf41c1 | sdd/feat-publish-clean-and-prune-orphans/spec |
| design | #718 | obs-069be0c2a201d05b | sdd/feat-publish-clean-and-prune-orphans/design |
| tasks | #719 | obs-8bfc939d4d73f592 | sdd/feat-publish-clean-and-prune-orphans/tasks |
| apply-progress | #720 | obs-634537570b5c6026 | sdd/feat-publish-clean-and-prune-orphans/apply-progress |
| verify-report | #721 | obs-2c31e0ff80361fcd | sdd/feat-publish-clean-and-prune-orphans/verify-report |
| archive-report | (this) | sdd/feat-publish-clean-and-prune-orphans/archive-report | sdd/feat-publish-clean-and-prune-orphans/archive-report |

Delta spec files: `openspec/changes/feat-publish-clean-and-prune-orphans/specs/{publish,prepare}/spec.md` → canonical `specs/{publish,prepare}/spec.md`.
Archived to: `openspec/changes/archive/2026-08-30-feat-publish-clean-and-prune-orphans/` (closed 2026-08-30; hybrid artifact store).

Filesystem archive contains: `proposal.md` ✅ · `specs/publish/spec.md` (PUB-11 delta) ✅ · `specs/prepare/spec.md` (PRP-09 delta) ✅ · `design.md` ✅ · `tasks.md` (17/17) ✅ · `apply-progress.md` ✅ · `verify-report.md` ✅ · `explore.md` ✅ · `archive-report.md` (this) ✅
Active changes directory no longer contains `feat-publish-clean-and-prune-orphans` (moved to archive).

## Source of Truth Updated

The following specs now reflect the new behavior:

- `openspec/specs/publish/spec.md` — now includes PUB-11 (Build cleanup on successful publish) after PUB-08; 8 scenarios covering hf build/cache isolation, dry-run/quality-fail/upload-fail no-delete, local dest-only, and `--output` anchoring.
- `openspec/specs/prepare/spec.md` — now includes PRP-09 (Orphan pruning on force prepare) after PRP-07; 6 scenarios covering single-underscore orphan deletion, stale TOML pruning, compliance/keep_csv retention, idempotency, and non-force no-prune.
