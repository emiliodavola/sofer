```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:988ede4d712fec839ff5f2c45cef8036c03c26166cefa4f69f7e001fb5addaf2
verdict: pass
blockers: 0
critical_findings: 0
requirements: 10/10
scenarios: 38/38
test_command: "uv run pytest tests/test_config.py tests/test_cli.py tests/test_scanner.py -q && uv run pytest -q"
test_exit_code: 0
test_output_hash: sha256:1c23152d4e90c5c4493a91e916cfec1c4345f07352ae90305f3373403a16257d
build_command: "uv run ruff check . && uv run ruff format --check . && uv run mypy src/"
build_exit_code: 0
build_output_hash: sha256:73554b837008397f298cf12224ed0ba3228d50d182d1c59c726a7919470b103c
```

## Verification Report

**Change**: 2026-08-29-feat-raw-folder-organization
**Version**: N/A
**Mode**: Standard (strict_tdd=false, review_budget 2000, artifact_store=both)

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 18 |
| Tasks complete | 18 |
| Tasks incomplete | 0 |

All 18 tasks verified complete in `tasks.md` and `apply-progress.md` (updated remediation 442f773). Previous verify report 695 FAIL flagged 18/38 UNTESTED with `git diff dev -- tests/` empty — remediated by 25 committed tests (7 config + 11 cli + 7 scanner) in commit 442f773. `git diff dev -- tests/` now non-empty and `git diff dev --stat` shows 18 files changed with tests covering all delta scenarios.

### Build & Tests Execution
**Build**: PASSED
```
$ uv run ruff check .
All checks passed!

$ uv run ruff format --check .
64 files already formatted

$ uv run mypy src/
Success: no issues found in 27 source files
```

**Tests**: PASSED
```
$ uv run pytest tests/test_config.py tests/test_cli.py tests/test_scanner.py -q
152 passed in 1.29s

$ uv run pytest -q
984 passed, 2 skipped, 13 warnings in 14.36s
```

Scoped 152 vs previous 127 (+25 raw-folder tests). Full suite 984 vs previous 959 (+25). 2 skipped unrelated (pre-existing). Warnings 13 are pre-existing `DeprecationWarning` in `tests/test_codebook.py` `_infer_type`.

**Coverage**: Not measured (no coverage threshold configured)

### Spec Compliance Matrix
| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| **tool-config: Raw directory bootstrap key (TC-10)** | Default raw_dir is "raw" | `tests/test_config.py::TestTc10RawDirBootstrap::test_default_raw_dir_is_raw` | COMPLIANT |
|  | pyproject overrides raw_dir | `tests/test_config.py::TestTc10RawDirBootstrap::test_pyproject_overrides_raw_dir_via_reload_none` | COMPLIANT |
|  | Dataset-dir wins over cwd for raw_dir | `tests/test_config.py::TestTc10RawDirBootstrap::test_dataset_dir_wins_over_cwd_for_raw_dir` | COMPLIANT |
| **tool-config: Bootstrap keys anchor on cwd (TC-07 MOD)** | cwd pyproject supplies default_config_name | `tests/test_config.py::TestTc07BootstrapKeys::test_cwd_pyproject_supplies_default_config_name` | COMPLIANT |
|  | cwd pyproject supplies raw_dir | `tests/test_config.py::TestTc10RawDirBootstrap::test_cwd_pyproject_supplies_raw_dir` | COMPLIANT |
|  | Bootstrap limitation documented | `tests/test_config.py::TestTc10RawDirBootstrap::test_bootstrap_limitation_documented` | COMPLIANT |
| **cli: init creates raw/ and --move-existing (CLI-R07)** | init creates raw/ | `tests/test_cli.py::TestInitRawFolder::test_init_creates_raw_dir` | COMPLIANT |
|  | Idempotent | `tests/test_cli.py::TestInitRawFolder::test_init_idempotent` | COMPLIANT |
|  | Depth-1 only supported | `tests/test_cli.py::TestInitRawFolder::test_move_existing_depth1_only_supported` | COMPLIANT |
|  | Collision guard | `tests/test_cli.py::TestInitRawFolder::test_move_existing_collision_guard` | COMPLIANT |
|  | Dry-run preview | `tests/test_cli.py::TestInitRawFolder::test_move_existing_dry_run_no_mutation` | COMPLIANT |
|  | Non-interactive guard | `tests/test_cli.py::TestInitRawFolder::test_move_existing_non_interactive_guard` | COMPLIANT |
|  | Prompt N aborts | `tests/test_cli.py::TestInitRawFolder::test_move_existing_prompt_n_aborts` | COMPLIANT |
|  | Template mentions raw/ | `tests/test_cli.py::TestInitRawFolder::test_template_mentions_raw_no_stale_path` | COMPLIANT |
| **cli: Help for init --move-existing (CLI-R08)** | Help lists flags | `tests/test_cli.py::TestInitHelp::test_help_lists_flags` | COMPLIANT |
| **cli: Help text accurate (CLI-R02 MOD)** | prepare help | `tests/test_cli.py::TestPrepareParser` | COMPLIANT |
|  | publish help | `tests/test_cli.py::TestPublishParser` | COMPLIANT |
|  | No stale upload | `tests/test_cli.py::TestParser::test_help_shows_prepare_publish_not_upload` | COMPLIANT |
| **scan: Source Layout and Copy-Only (SCN-07)** | Sources untouched | `tests/test_scanner.py::TestSourceLayoutCopyOnly::test_sources_untouched_after_scan` | COMPLIANT |
|  | Docs show diagram | `tests/test_scanner.py::TestSourceLayoutCopyOnly::test_docs_show_diagram` | COMPLIANT |
| **scan: File Discovery (SCN-01 MOD)** | Discover supported | `tests/test_scanner.py::TestDiscoverFiles::test_filter_by_extension` | COMPLIANT |
|  | Excluded dirs skipped | `tests/test_scanner.py::TestDiscoverFiles::test_excluded_dirs_are_skipped` | COMPLIANT |
|  | --ext filters | `tests/test_scanner.py::TestDiscoverFiles::test_ext_override` | COMPLIANT |
|  | raw discovered, cache excluded | `tests/test_scanner.py::TestRawCacheDiscovery::test_raw_discovered_cache_excluded` | COMPLIANT |
| **scan: TOML Merge (SCN-02 MOD)** | Merge new files | `tests/test_scanner.py::TestMergeEntries::test_new_entries_are_appended` | COMPLIANT |
|  | Duplicate skipped | `tests/test_scanner.py::TestMergeEntries::test_dedup_by_resolved_path` | COMPLIANT |
|  | No loss | `tests/test_scanner.py::TestMergeEntries::test_section_preservation` | COMPLIANT |
|  | Flattened paths | `tests/test_scanner.py::TestMergeEntries::test_merge_flattened_local_and_remote` | COMPLIANT |
|  | Root file | `tests/test_scanner.py::TestMergeEntries::test_root_level_file_keeps_name` | COMPLIANT |
| **scan: File Copy (SCN-03 MOD)** | Flatten copy | `tests/test_scanner.py::TestCopyFiles::test_creates_subdirs_lazily` | COMPLIANT |
|  | Root copy | `tests/test_scanner.py::TestFlattenFirstLevel::test_root_file_unchanged` | COMPLIANT |
|  | Nested preserved | `tests/test_scanner.py::TestFlattenFirstLevel::test_nested_strips_only_first_segment` | COMPLIANT |
|  | Dry-run | `tests/test_scanner.py::TestCopyFiles::test_dry_run_no_copy` | COMPLIANT |
| **scan: Error Handling (SCN-06 MOD)** | Config missing | `tests/test_scanner.py::TestIntegration::test_missing_config_returns_error` | COMPLIANT |
|  | No files | `tests/test_scanner.py::TestIntegration::test_no_supported_files_returns_ok` | COMPLIANT |
|  | Dest exists | `tests/test_scanner.py::TestCopyFiles::test_file_exists_error_without_force` | COMPLIANT |
|  | Malformed TOML | `tests/test_scanner.py::TestIntegration::test_malformed_toml_returns_error` | COMPLIANT |
|  | Flatten collision | `tests/test_scanner.py::TestCheckFlattenCollisions::test_collision_raises_naming_sources` | COMPLIANT |

**Compliance summary**: 38/38 scenarios compliant (100%). 18 previously UNTESTED now COMPLIANT via commit 442f773.

### Verdict
**PASS**
All 38 delta scenarios are COMPLIANT with passing covering tests (25 new tests in 442f773 resolve prior 18 UNTESTED). Build green (ruff, ruff format, mypy), 984 passed / 2 skipped full suite, 152 scoped passed. Archive-ready; no blockers.

### Evidence Collected
- Branch: `feat/raw-folder-organization` @ `442f773`
- Specs: `openspec/changes/2026-08-29-feat-raw-folder-organization/specs/{tool-config,cli,scan}/spec.md` (10 requirements, 38 scenarios)
- Design: `openspec/changes/2026-08-29-feat-raw-folder-organization/design.md`
- Tasks: `openspec/changes/2026-08-29-feat-raw-folder-organization/tasks.md` 18/18 complete
- Implementation: `src/sofer/config.py`, `src/sofer/cli.py`, `src/sofer/scanner.py`, `pyproject.toml`, `docs/configuration.md`, `README.md`, `README_ES.md`
- Tests: 25 new tests (7 config + 11 cli + 7 scanner) — 152 scoped, 984 full
- Build: ruff check/format clean, mypy success 27 files

### Next Steps for Archive Readiness
Ready for `sdd-archive`. No further remediation required.
