```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:9adb104736b1491f1f6f59d74d98524a243768be601f5df443d46c155485a549
verdict: pass
blockers: 0
critical_findings: 0
requirements: 2/2
scenarios: 14/14
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:6e54a3fb08efb99a63b891f7ebd22bb95aa5b3c30f10200ff908e08cc061b177
build_command: uv run ruff check src/ tests/ && uv run mypy src/
build_exit_code: 0
build_output_hash: sha256:03f9e664b02d3ab063da47fd53aceca010149a42c83a7a617985f636727a5227
```

## Verification Report

**Change**: feat-publish-clean-and-prune-orphans (GitHub #92, PR #93)
**Version**: N/A (delta specs PUB-11 / PRP-09)
**Mode**: Standard (strict_tdd: false)

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 17 |
| Tasks complete | 17 |
| Tasks incomplete | 0 |

All 4 phases checked [x] in `openspec/changes/feat-publish-clean-and-prune-orphans/tasks.md`:
- Phase 1 (1.1-1.3) _clean.py helpers — done
- Phase 2 (2.1-2.5) CLI/publish/prepare wiring — done
- Phase 3 (3.1-3.5) tests PUB-11/PRP-09 + lint/type — done
- Phase 4 (4.1-4.4) docs sync — done

Branch `feat/92-publish-clean-and-prune-orphans`, PR #93 targeting `dev`, single-PR review budget 3000 lines (Low risk, 260-360 actual diff — no chained PRs needed).

### Build & Tests Execution

**Build**: ✅ Passed
```text
$ uv run ruff check src/ tests/
All checks passed!

$ uv run mypy src/
Success: no issues found in 28 source files
```

**Tests**: ✅ 1062 passed / 2 skipped / 0 failed
```text
$ uv run pytest tests/ -q
1062 passed, 2 skipped, 13 warnings in 16.28s

Targeted subset (PUB-11 / PRP-09 + CLI):
$ uv run pytest tests/test_clean.py tests/test_publish.py tests/test_prepare.py tests/test_cli.py -q
184 passed in 2.83s
```

**Coverage**: ➖ Not available (no coverage threshold configured; no coverage gate in CI for this change)

### Spec Compliance Matrix

#### PUB-11 — Build cleanup on successful publish (8 scenarios)

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| PUB-11 | Successful hf publish with --clean deletes build | `tests/test_publish.py::TestPublishClean::test_clean_deletes_build_on_success` | ✅ COMPLIANT |
| PUB-11 | --clean --clean-cache deletes build and cache | `tests/test_publish.py::TestPublishClean::test_clean_and_cache_deletes_both` | ✅ COMPLIANT |
| PUB-11 | Dry-run with --clean does not delete | `tests/test_publish.py::TestPublishClean::test_dry_run_with_clean_does_not_delete` | ✅ COMPLIANT |
| PUB-11 | Quality-gate block does not delete | `tests/test_publish.py::TestPublishClean::test_quality_fail_with_clean_does_not_delete` | ✅ COMPLIANT |
| PUB-11 | Upload failure does not delete | `tests/test_publish.py::TestPublishClean::test_upload_failure_with_clean_does_not_delete` | ✅ COMPLIANT |
| PUB-11 | Local target without explicit --clean does not delete | `tests/test_publish.py::TestPublishClean::test_local_without_clean_does_not_delete` | ✅ COMPLIANT |
| PUB-11 | Local target with explicit --clean deletes destination | `tests/test_publish.py::TestPublishClean::test_local_with_clean_deletes_destination_not_build` | ✅ COMPLIANT |
| PUB-11 | Custom --output build cleanup anchored correctly | `tests/test_publish.py::TestPublishClean::test_custom_output_clean_anchored` | ✅ COMPLIANT |

Ancillary PUB-11 unit coverage in `tests/test_clean.py::TestCleanHelpers` (4 tests):
`test_clean_build_removes_resolved_dir`, `test_clean_build_respects_output_override`, `test_clean_cache_anchored_to_base_dir`, `test_clean_cache_noop_when_missing` + `test_clean_build_noop_when_missing` — all ✅.

#### PRP-09 — Orphan pruning on force prepare (6 scenarios)

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| PRP-09 | Single-underscore orphan deleted on force | `tests/test_prepare.py::TestPreparePruneOrphans::test_single_underscore_orphan_via_prepare` + `tests/test_clean.py::TestAllowedOutputRemotes::test_single_underscore_data_got_all_sheets_in_allowlist` | ✅ COMPLIANT |
| PRP-09 | Stale file from removed TOML entry pruned | `tests/test_prepare.py::TestPreparePruneOrphans::test_force_true_prunes_stale_parquet` + `tests/test_clean.py::TestPruneOrphans::test_deletes_stale_file` | ✅ COMPLIANT |
| PRP-09 | Compliance auto-generated files retained | `tests/test_prepare.py::TestPreparePruneOrphans::test_compliance_survives_force_prune` + `tests/test_clean.py::TestPruneOrphans::test_retains_compliance_and_codebooks` | ✅ COMPLIANT |
| PRP-09 | keep_csv originals retained | `tests/test_clean.py::TestPruneOrphans::test_retains_keep_csv_original` + `tests/test_clean.py::TestAllowedOutputRemotes::test_keep_csv_adds_csv_remote` | ✅ COMPLIANT |
| PRP-09 | Idempotent second force run | `tests/test_prepare.py::TestPreparePruneOrphans::test_idempotent_second_force` + `tests/test_clean.py::TestPruneOrphans::test_idempotent_second_run` | ✅ COMPLIANT |
| PRP-09 | Non-force run does not prune | `tests/test_prepare.py::TestPreparePruneOrphans::test_force_false_retains_orphan` | ✅ COMPLIANT |

Additional `tests/test_clean.py::TestPruneOrphans::test_single_underscore_orphan_pruning` (stale TOML entry with single-underscore build) also covers the dual-guard path — ✅.

**Compliance summary**: 14/14 scenarios compliant (2/2 requirements), each with a covering test that passed at runtime.

### Correctness (Static Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| PUB-11 gate `clean && !dry_run && quality_passed && fail==0` | ✅ Implemented | `src/sofer/publish.py:748`; hf path gates on `clean and not dry_run and quality_passed and fail==0`; local path gates on `clean and not dry_run` (quality gate hf-only). Build resolved via `resolve_output_dir(cfg, _output)` so `--output ./staging` deletes `./staging` not default `build/`. Cache anchored to `cfg._base_dir / config.OUTPUT_DIR`. |
| PUB-11 build vs cache isolation (`--clean` build-only, `--clean-cache`/`--all` for cache) | ✅ Implemented | `src/sofer/cli.py:819,828` dest=`clean_cache` with aliases `--clean-cache`/`--all`; `publish.py:753-756` only deletes cache when `clean_cache` truthy. Warning printed in `_clean.py:225`. |
| PUB-11 local dest-only | ✅ Implemented | `publish.py:662-668` `local --clean` deletes resolved destination `output_dir` via `clean_build(cfg, output_dir)`, source build untouched. Verified by `test_local_with_clean_deletes_destination_not_build`. |
| PRP-09 allowlist = expanded_planned_remotes ∪ compliance ∪ keep_csv | ✅ Implemented | `src/sofer/_clean.py:58-116` `allowed_output_remotes` unions `expanded_planned_remotes` (dual `__`/`_` guard inherited) + `README.md`/`LICENSE`/`codebook.md` + `codebooks/**` prefix + recursive `remote + "/"` sentinels + keep_csv via `expanded_planned_remotes(keep_csv=True)`. |
| PRP-09 dual `__`/`_` guard (single-underscore `DATA_GOT_ALL`) | ✅ Implemented | Reused from `_mirror.expanded_planned_remotes` (fallback glob `stem_*.parquet` filtered `c.stem != stem` identical to `prepare.py:615-622`). `prune_orphans` respects `_is_auto_generated` case-insensitive + prefix + recursive sentinels before deleting. No orphan deletion when `force is False` (`prepare.py:898`). |
| PRP-09 idempotent + no-prune on non-force | ✅ Implemented | `prune_orphans` iterates `rglob`, per-file `try/except`, logs absolute path, returns removed list; second run deletes 0. `prepare(force=False)` skips prune entirely (line 898 guard). |
| No hardcoded values | ✅ Implemented | `_clean.py` uses `config.OUTPUT_DIR`/`config.CODEBOOKS_DIR`; `cli.py`/`publish.py`/`prepare.py` use `cfg._base_dir`, `cfg.build_dir`, `config.OUTPUT_DIR` via `resolve_output_dir` — no literal `"cache"` or `";"` defaults in new code (searched `_clean.py`, `cli.py` new flags, `publish.py` clean block, `prepare.py` prune block). |
| Docstrings for new module/public funcs | ✅ Implemented | `src/sofer/_clean.py` has module docstring + `allowed_output_remotes`/`prune_orphans`/`clean_build`/`clean_cache` docstrings with Args/Returns; `cli.py::_cmd_publish` documents `--clean` teardown; `publish.publish(clean/clean_cache)` documents gating. |
| README + README_ES sync (AGENTS.md rule 13) | ✅ Implemented | `README.md:263-264,280-282` and `README_ES.md:275-276,292-294` mirror headings, section order, and flag descriptions; technical strings (`--clean`, `--clean-cache`, `--all`, `cfg._base_dir/cache`, `resolve_output_dir`) kept English in both files; only prose translated. |
| CLI help accuracy for --clean/--clean-cache | ✅ Implemented | `uv run python -m sofer.cli publish --help` shows `--clean` (build-only, gated, resolve_output_dir) and `--clean-cache, --all` (tool-wide OUTPUT_DIR at cfg._base_dir/cache, sibling-shared, opt-in) — verbatim match to spec delta. |

### Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| Shared helper `src/sofer/_clean.py` (allowed_output_remotes + prune_orphans + clean_build/clean_cache) | ✅ Yes | Single source of truth; `prepare.py:899-904` and `publish.py:664,749-756` both import from `_clean`. One-module-per-concern honored. |
| CLI granularity `--clean` build-only + `--clean-cache`/`--all` for cache | ✅ Yes | Implemented as `cli.py` aliases dest=`clean_cache`; design tradeoff (sibling-shared HIGH blast radius) respected with warning. |
| Publish gating + anchoring (`resolve_output_dir`/`cfg._base_dir/config.OUTPUT_DIR`) | ✅ Yes | Exactly as data-flow in `design.md:54-66`; no unconditional delete; `try/except` without `ignore_errors=True`; logs absolute paths. |
| Orphan prune placement after staging+codebooks when `force=True` | ✅ Yes | `prepare.py:895-905` runs after codebooks, before NOT FOUND report; `force is True` guard; idempotent; `force is False` no-op. |
| Config: reuse `OUTPUT_DIR`/`CODEBOOKS_DIR` via `config`, no new `[tool.sofer]` defaults | ✅ Yes | No new defaults added to `config.py`; existing constants reused. |

One design deviation to note (not a violation): `_clean.py` also ships `_AUTO_GENERATED`/`_is_auto_generated` mirroring `publish._is_auto_generated` — intentional to avoid circular import; behavior identical (case-insensitive, `codebooks/` prefix).

### Issues Found

**CRITICAL**: None

**WARNING**: None

**SUGGESTION**:
- Consider adding a `sofer clean` standalone subcommand reusing `_clean` (deferred per design.md) — no action now.
- `prepare(force=False)` idempotency guard for orphans (`test_force_false_retains_orphan` uses `rc==1` path) documents that non-force retains orphans via overwrite refusal — behavior matches spec (orphan scan shall not execute) but could be made more explicit with a dedicated `force=False` no-prune unit test at `_clean` level.
- README `command reference` publish row is long (single-line table cell) — readability could improve with a line break, but AGENTS.md rule 13 sync is already satisfied.

### Verdict

**PASS** — All 17 tasks complete, 14/14 spec scenarios have passing covering tests (184 targeted + 1062 full suite), build checks green (ruff + mypy), no hardcoded values, docstrings present, READMEs synced, CLI help accurate, orphan prune respects dual `__`/`_` guard and compliance/keep_csv allowlist, design coherence maintained. Archive-ready.
