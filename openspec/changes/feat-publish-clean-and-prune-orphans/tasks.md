# Tasks: feat-publish-clean-and-prune-orphans

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 260–360 (code ~120, tests ~140, docs ~60) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | auto-forecast |
| Chain strategy | pending |
| Review budget | 3000 lines |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Helper + CLI + publish/prepare + tests + docs | PR 1 → main | Single PR; 400-line overage note-only — 3000-line budget allows it |

## Phase 1: Foundation — Shared Helper

- [x] 1.1 Create `src/sofer/_clean.py` — `allowed_output_remotes(cfg, keep_csv, output_dir)` reusing `expanded_planned_remotes` + `_AUTO_GENERATED` + `codebooks/**` + keep_csv, dual `__`/`_` guard
- [x] 1.2 Implement `prune_orphans(output_dir, allowed)` in `src/sofer/_clean.py` — rglob, delete not in allowlist, `try/except` per file, log absolute paths
- [x] 1.3 Implement `clean_build`/`clean_cache` in `src/sofer/_clean.py` — existence check + `shutil.rmtree` + `try/except`; `clean_cache` anchored to `cfg._base_dir / config.OUTPUT_DIR`

## Phase 2: Core — CLI and Publish/Prepare Wiring

- [x] 2.1 Modify `src/sofer/cli.py` — add `--clean` (build-only, default off), `--clean-cache` + `--all` alias to `publish`; plumb to `publish()`; help warns `cache/` is sibling-shared
- [x] 2.2 Modify `src/sofer/publish.py` — add `clean`/`clean_cache` params; gate delete on `clean and not dry_run and quality_passed and fail==0`; resolve build via `resolve_output_dir(cfg, _output)`
- [x] 2.3 Handle `hf` cache cleanup in `src/sofer/publish.py` — when `clean_cache` delete `cfg._base_dir / config.OUTPUT_DIR` after build, warn siblings
- [x] 2.4 Handle `local` cleanup in `src/sofer/publish.py` — with `--clean` delete resolved destination only; without `--clean` delete nothing
- [x] 2.5 Modify `src/sofer/prepare.py` — after codebooks, when `force is True` call `allowed_output_remotes` then `prune_orphans`; `force is False` skips

## Phase 3: Testing — PUB-11/PRP-09

- [x] 3.1 Add `tests/test_clean.py` — `allowed_output_remotes` recognizes single-`_` `DATA_GOT_ALL` sheets; `prune_orphans` deletes stale, retains compliance/keep_csv, idempotent
- [x] 3.2 Extend `tests/test_publish.py` — mock `upload_folder`: no delete on dry_run/quality-fail/upload-fail; build vs cache isolation; `--output` anchoring; local dest-only
- [x] 3.3 Extend `tests/test_prepare.py` — `force=True` prunes single-`_` + stale TOML orphan; `force=False` retains; compliance files survive; idempotent second run
- [x] 3.4 Extend `tests/test_cli.py` — `publish --help` contains `--clean`/`--clean-cache`/`--all`; parser plumbs flags correctly
- [x] 3.5 Run `uv run pytest tests/ -q && uv run ruff check src/ tests/ && uv run mypy src/` — all green

## Phase 4: Documentation and Polish

- [x] 4.1 Update `README.md` — document `--clean`/`--clean-cache`/`--all`, build-only default, sibling `cache/` warning, `--output` anchoring
- [x] 4.2 Mirror in `README_ES.md` — keep headings/order per AGENTS.md rule 13; flags/commands stay English
- [x] 4.3 Verify CLI `help=` strings in `src/sofer/cli.py` match new flags
- [x] 4.4 Verify `openspec/specs/publish/spec.md` (PUB-11) and `prepare/spec.md` (PRP-09) deltas cover all scenarios — no extra spec edits
