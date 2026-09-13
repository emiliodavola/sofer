# Design — Raise per-file coverage (amended: CLI-core 100% mandate + three ≥90 floors)

Change: `2026-09-13-raise-per-file-coverage` · Branch: `test/raise-coverage-90` · Base: `dev`
Phase: design · Status: **ready** (baseline pinned by parent; supersedes the prior design that pinned the five-90/cheapest-wins scope)

> **Re-sync note**: the previous design.md pinned the SUPERSEDED scope (five ≥90 floors
> incl. cli/publish, zero src changes, cheapest-wins COV-04, no gate machinery). This
> rewrite tracks the amendment 2026-09-13 (proposal + `specs/coverage/spec.md` COV-01..COV-06):
> four core modules at **100.00% with zero pragmas** (COV-06), three ≥90 floors
> (profile/mcp_registration/verification — COV-01), COV-04 retired, **zero** src
> touches — Resolution A 2026-09-13 (parent-authorized) keeps the cli.py `__main__`
> guard and covers it in-process via `runpy.run_module("sofer.cli", run_name="__main__")`
> (COV-03), and enforced per-file
> scoped gates. Nothing in the old design is reused except the pinned baseline numbers.

## 1. Context and locked decisions (from the amended proposal/spec — not reopened)

| # | Decision | Value |
| --- | --- | --- |
| 1 | Binding contract | `cli.py`, `scanner.py`, `prepare.py`, `publish.py` **100.00%** line coverage each, **zero `# pragma: no cover`** tokens anywhere in the four files (COV-06); `profile.py`, `mcp_registration.py`, `verification.py` **≥90%** each (COV-01); TOTAL ≥90 (COV-02, config-owned `fail_under = 90` untouched, CI-01). |
| 2 | COV-04 | **Retired** — no adjacent cheapest-wins set; no coverage-raising tests outside the four core + three floors. |
| 3 | Pragma policy | Absolute ban in the four core modules; every line must actually execute. A "genuinely untestable" line is a test-strategy defect or a design escalation, never a pragma. Pre-existing pragma in `mcp_registration.py::atomic_write` (tomli-w import guard) is untouched (not a core module). |
| 4 | Sole src edit | **NONE — Resolution A (parent-authorized 2026-09-13): zero `src/sofer/` edits.** The dead `if __name__ == "__main__": main()` guard at `cli.py:1574-1575` is KEPT and covered by an in-process runpy test (`runpy.run_module("sofer.cli", run_name="__main__")` with argv at a harmless subcommand; asserts rc/exit-call; under the tracer). The removal premises were false: `conftest.run_cli` spawns `-m sofer.cli` (PB-02 boundary) so removal breaks 14 tests, and the guard body executes in-process via runpy (probe verified). Static absence test REPLACED by the guard-EXECUTION test. |
| 5 | Enforcement | COV-06 per-file scoped gates `coverage report --include=src/sofer/<file>.py --fail-under=100 -m`. **Shape (this design): one committed `scripts/check_core_coverage.sh`** referenced by the `ci.yml` coverage job — justification in §5.1. TOTAL gate stays config-owned; `--fail-under=100` is a fixed policy constant, never a tunable floor. `release.yml` is NOT mirrored (see §5.1). |
| 6 | Floors enforcement | Verify-phase runtime evidence + skip-if-absent contract guard (`tests/test_coverage_contract.py`, local `.coverage` read via `coverage.CoverageData`). Core four rely on the CI gates, not this guard. |
| 7 | Measurement env | CI interpreter (ubuntu, Python 3.13) is the arbiter — binary for the four 100% rows. Local margin: floors ≥91 preferred (min 90.3 with justification); TOTAL ≥90.5 locally. |
| 8 | Docs | AGENTS.md rule 14 ONLY (exact text §5.3). README/README_ES/CONTRIBUTING/PR template untouched (rule 13 applies to translated READMEs, not AGENTS.md). |
| 9 | Delivery | Single PR vs `dev`, branch `test/raise-coverage-90`, assignee emiliodavola. Size expectation ≈1800–2600 (amended proposal) — fresh bottom-up §6.2 lands ≈1800–2900 (mid ≈2300). **Ask-on-risk above 1500 changed lines: the range crosses it with near-certainty → a user decision (chain vs size-exception) is required before/at apply; never invented silently.** Premises of the old design (size-exception ≤1500 pre-authorized, chaining deferred) are superseded by the amended DP9. |

## 2. Baseline (pinned by parent on this branch — TRUST, do NOT re-run)

Parent-executed `uv run coverage run -m pytest` + `uv run coverage report -m` on `test/raise-coverage-90`:

| Module | Stmts | Missed | Arcs | % | Notes (pinned) |
| --- | --- | --- | --- | --- | --- |
| cli.py | 564 | 87 | 162/22 | 84 | 1575 = `__main__` body → covered via the in-process runpy test (kept, not removed; Resolution A) |
| scanner.py | 159 | 12 | 76/7 | 92 | |
| prepare.py | 432 | 46 | 226/26 | 88 | |
| publish.py | 326 | 36 | 138/22 | 87 | `HfApi` import + module `_api = HfApi()` covered; HF paths driven through fakes |
| profile.py | 253 | 49 | 96/17 | 80 | floor |
| mcp_registration.py | 235 | 39 | 106/20 | 80 | floor; pre-existing pragma at atomic_write untouched |
| verification.py | 60 | 8 | 22/4 | 83 | floor |
| **TOTAL** | 5995 | 638 | — | 88 | core-100 clears ≈181 (87+12+46+36) → ≈92.4% before floors; floors push higher → TOTAL ≥90 with margin |

**A-0 is satisfied** (parent-pinned). Re-anchor contract (Resolution A): NO src edit — `cli.py` line numbers stay as pinned (the guard at 1575 is kept and covered by the runpy test, never removed); per-module missed lists below are keyed by *function + behavior*, with the pinned line numbers attached — reconcile each region against the apply-time `coverage report -m` output and re-anchor on the function, not the raw number.

**Quantified target to clear per module**: cli 87 stmts (+ residual arcs) → 0; scanner 12 → 0; prepare 46 → 0; publish 36 → 0; profile 49 → ≤25 missed (253 stmts + 96/17 arcs: ≥90 needs ≤~25 missed+arcs); mcp_registration 39 → ≤~22; verification 8 → ≤~6.

## 3. Core-module 100% plans (COV-06)

Strategy legend (existing repo templates, in-process — subprocess escapes coverage and can't be 100%-real):
**D** = direct `cli._cmd_*(Namespace(...))` / direct domain-function call + `capsys` (repo precedent: `TestLoadAndValidate`, `TestHfPublish`); **M** = monkeypatch (`builtins.input`, `sys.stdin.isatty`, `sys.platform`, `shutil.which`, `subprocess.run`, `sys.modules` via `patch.dict`, config constants via `restore_tool_config`); **F** = fake object (fake `HfApi` per `TestHfPublish._mock_hf_api` style, `FakePath`, real parquet/xlsx fixtures — deps already present); **S** = `conftest.run_cli` subprocess (user-visible flows only; cannot close 100%, used where the behavior is console-level). Every new test asserts an observable outcome (rc, stdout/stderr text, written file content, exception) — COV-05; values from `[tool.sofer]`/`DatasetConfig`/`conftest` fixtures, never hardcoded magic (AGENTS 1/3).

### 3.1 `cli.py` (564 stmts, 87 missed, 84% → 100%)

| Pinned missed | Behavior (function anchor) | Strategy | NEW test (tests/test_cli.py) |
| --- | --- | --- | --- |
| 83 | `_load_and_validate` `return cfg, None` — `--no-checks` short-circuit | D: `_cmd_prepare(Namespace(no_checks=True, ...))` on a tiny valid dataset — also drives the happy tail 129-130 (`resolve_output_dir` + real `run_prepare`) | `TestNoChecksPath::test_prepare_no_checks_runs_happy_path` |
| 129-130 | `_cmd_prepare` happy tail (output resolve + `run_prepare`) | D (same test as above; assert rc 0 + `build/` artifacts exist) | (above) |
| 209-211 | `_cmd_codebook` all-files `generate_all_codebooks` raises ValueError → stderr + rc 1 | D + M: `monkeypatch.setattr("sofer.cli.generate_all_codebooks", raise ValueError)` on a valid all-files toml; assert rc 1 + `Error:` in stderr | `TestCodebookAllFilesErrors::test_all_files_valueerror_returns_1` |
| 231 | `_cmd_codebook` missing FILE / `--all-files` arg → rc 1 | D: `Namespace(all_files=False, csv=None, ...)`; assert rc 1 + "Must specify a FILE" | `TestCodebookAllFilesErrors::test_codebook_requires_file_or_all_files` |
| 278, 283-285 | `_cmd_profile` all-files effective-TOML selection variants (`elif dataset_raw`, `else` config-path fallback) | D: three Namespace combos (explicit `--config`, bare `dataset` positional, both default) on valid tomls; assert dispatch happens (rc 0) | `TestProfileRenderFlagCoverage::test_profile_all_files_toml_selection_variants` (parametrized ×3) |
| 292-293 | `_cmd_profile` all-files no `[[file]]` entries → rc 1 | D: toml with `[dataset]` but no files | `TestProfileRenderFlagCoverage::test_profile_all_files_no_file_entries_returns_1` |
| 298-300 | `_cmd_profile` all-files `DatasetConfig.from_toml` exception → rc 1 | D: nonexistent toml path | `TestProfileRenderFlagCoverage::test_profile_all_files_unreadable_toml_returns_1` |
| 304-305 | `_cmd_profile` single-file missing dataset arg → rc 1 | D: `Namespace(dataset=None, all_files=False, ...)` | `TestProfileRenderFlagCoverage::test_profile_requires_dataset_or_all_files` |
| 310 | `_cmd_profile` single-file **relative `--output` anchoring** + `_cmd_render` analog (MSP-R10) | D: dataset in tmp subdir + relative output; assert metadata lands next to dataset | `TestProfileRenderFlagCoverage::test_profile_relative_output_anchors_to_dataset_parent` (in-process twin of the subprocess test at test_cli.py:1365) |
| 352, 357-359, 366-367 | `_cmd_render` all-files toml-selection variants + no-entries + unreadable → mirror of profile set | D (mirror rows above, `_cmd_render` + `package`) | `TestProfileRenderFlagCoverage::test_render_all_files_selection_and_error_variants` (parametrized) |
| 372-374, 378-379 | `_cmd_render` single-file missing package arg + from_toml exception | D | `TestProfileRenderFlagCoverage::test_render_requires_package_and_reports_toml_errors` |
| 384-385 | `_cmd_render` single-file relative `--output` anchoring + `FileExistsError` hint | D + tmp_path (in-process twin of test_cli.py:1377) | `TestProfileRenderFlagCoverage::test_render_relative_output_and_existing_readme_hint` |
| 485-486 | `_cmd_scan` Phase-1 prompt preview ("The following files will be moved to raw/") | D: run_cli-level already covered by existing `TestScanMoveCLI`; add direct `_cmd_scan` with candidates + monkeypatched `input("y")` and `sys.stdin.isatty` (Phase 1 + Phase 2 both gate) | `TestScanPromptGate::test_scan_phase1_prompt_preview_and_yes` |
| 494-496 | `_cmd_scan` `move_to_raw` generic exception → stderr + rc 1 | D + M: monkeypatch `sofer.cli.move_to_raw` to raise `OSError` | `TestScanCliFailurePaths::test_scan_move_failure_returns_1` |
| 530-532 | `_cmd_scan` Phase-2 `check_flatten_collisions` ValueError abort | D + M: two files flattening to same name at cache/ (real path; or monkeypatch the check to raise) | `TestScanCliFailurePaths::test_scan_flatten_collision_aborts_before_copy` (extend existing TestScanIntegration analog) |
| 552-553, 555-556 | `_cmd_scan` P2 interactive gate (no Phase-1 candidates + not force): preview + `input` + `EOFError → "n"` | D + M: monkeypatch `builtins.input` to raise `EOFError`; assert "OK  Aborted." and TOML untouched | `TestScanPromptGate::test_scan_phase2_eof_aborts_atomically` |
| 561-563 | `_cmd_scan` `copy_files` `FileExistsError` → stderr + rc 1 | D + M: pre-create a differing dest file (real, no force) | `TestScanCliFailurePaths::test_scan_copy_collision_returns_1` |
| 571 | `_cmd_scan` dry-run "Nothing to copy — all files already present" (idempotent) | D: pre-stage identical files in cache/, run with `--dry-run` | `TestScanDryRun::test_scan_dry_run_idempotent_cache` |
| 578 | `_cmd_scan` dry-run "All discovered files already registered" (new_count == 0) | D: TOML already registers every discovered file; `--dry-run` | `TestScanDryRun::test_scan_dry_run_all_registered` |
| 652 | `_cmd_mcp_add` `Path.cwd()`-default cwd resolve (no `--cwd`) | D + M: `--cwd None`, project scope, monkeypatch `Path.cwd` to tmp under home; assert registers under cwd | `TestMcpAddCliCoverage::test_mcp_add_defaults_to_cwd` |
| 681-682 | `_cmd_mcp_add` native-delegation success ("delegated via native mcp add" + continue) | D + M: `probe_native→True`, `delegate_add→True` (monkeypatch module fns) | `TestMcpAddCliCoverage::test_mcp_add_native_delegation_skips_file_edit` |
| 684-685 | `_cmd_mcp_add` probe True / delegate False → "falling back to file edit" | D + M: `probe_native→True`, `delegate_add→False` (with `delegate_add` raising → `except Exception: delegated=False`) | `TestMcpAddCliCoverage::test_mcp_add_native_failure_falls_back` |
| 697-700 | `_cmd_mcp_add` project-scope path anchoring: `--cwd` given vs `None` (both `resolve_config_path` project branches) | D + M: monkeypatch `Path.cwd`; run with and without `--cwd` | `TestMcpAddCliCoverage::test_mcp_add_project_scope_path_anchoring` (parametrized ×2) |
| 720-723 | `_cmd_mcp_add` `backup` failure → stderr + overall 1 | D + M: monkeypatch `mcp_registration.backup` to raise | `TestMcpAddCliFailure::test_mcp_add_backup_failure_returns_1` |
| 728-731 | `_cmd_mcp_add` `atomic_write` failure → stderr + overall 1 | D + M: monkeypatch `mcp_registration.atomic_write` to raise | `TestMcpAddCliFailure::test_mcp_add_write_failure_returns_1` |
| 765-772 | `_cmd_mcp_remove` native-delegation branches (probe True → delegate success "delegated remove via native mcp remove"; delegate fail → fallback note) | D + M (module-fn monkeypatches) | `TestMcpRemoveCliCoverage::test_mcp_remove_native_success_and_fallback` |
| 790-791 | `_cmd_mcp_remove` "already absent (idempotent)" | D + M: monkeypatch `remove_entry→(doc, False)` | `TestMcpRemoveCliCoverage::test_mcp_remove_idempotent_absent` |
| 794-797 | `_cmd_mcp_remove` dry-run "Would remove … at …" | D + M: `dry_run=True` with changed doc | `TestMcpRemoveCliCoverage::test_mcp_remove_dry_run_no_mutation` |
| 801-804 | `_cmd_mcp_remove` failure paths: unreadable config / backup failure / write failure (overall 1) | D + M: three monkeypatched raises | `TestMcpRemoveCliFailure::test_mcp_remove_error_paths_return_1` (parametrized ×3) |
| 957->965, 971 | `_cmd_init --move-existing` **no-candidates** path: skips collision check; dry-run "No supported files to move." | D + M: empty dataset root, `move_existing=True, dry_run=True` | `TestInitMoveExistingCoverage::test_move_existing_no_candidates_dry_run` |
| 1000-1001 | `_cmd_init --move-existing` prompt `EOFError → "n"` abort branch (still writes TOML + raw/) | D + M: `isatty→True`, `input` raises EOFError | `TestInitMoveExistingCoverage::test_move_existing_prompt_eof_aborts_but_creates_toml` |
| 1575 | dead `__main__` guard body | **kept + runpy (Resolution A)**: in-process `runpy.run_module("sofer.cli", run_name="__main__")` with argv at a harmless subcommand — executes `main()` through the guard under the tracer; asserts rc/exit-call; the ONLY cli.py line needing an explicit entry-point test (all other cli.py lines are covered by the units B–E tests) | `test_cli_main_guard_executed_via_runpy` (tests/test_cli.py) |

Blocked notes: 129-130 and 83 are a single new test; the `_cmd_validate` happy path and `report.passed` False are already covered (TestValidateRanChecks) — no new work. `import tomli`→`except ImportError` fallback in `_cmd_scan` (435-439) resolves naturally in-process on 3.11+ (tomli absent per marker; a raising import counts as executed and the except body executes) — verify at first batch, add a `__import__`-blocker test only if the arc shows missed (risk register §6.3). **`sys.platform` guards: cli.py has none.**

### 3.2 `scanner.py` (159 stmts, 12 missed, 92% → 100%)

| Pinned missed | Behavior | Strategy | NEW test (tests/test_scanner.py) |
| --- | --- | --- | --- |
| 78, 80, 83-84 | `_is_link` tail: is_symlink True; non-NT short-circuit; Windows reparse-point try/except-OSError/bool | D + M: call `_is_link` with a small `FakePath` stub (`is_symlink`/`lstat` injectable, no Path attrs needed) + `monkeypatch.setattr("os.name","nt")`; cover lstat with `FILE_ATTRIBUTE_REPARSE_POINT`, lstat OSError, and plain attrs=0; plus real symlink for line 78 (tmp_path, skip-on-windows-already covered) | `TestLinkDetection::test_is_link_reparse_point_and_oserror_branches` (parametrized) |
| 200, 204, 211->210 | `collect_init_moves` existing-raw branch: raw_dir exists with supported files; loop collect + returns | D: root with depth-1 files + pre-populated `raw/`; assert `(candidates, existing)` split; also raw_dir absent → empty existing | `TestCollectInitMoves::test_collect_init_moves_existing_raw_and_absent_raw` (parametrized ×2) |
| 264->270 | `discover_files` default `ext_set = set(SUPPORTED_FORMATS.keys())` (no `--ext`) | D: direct `discover_files(root)` with a mixed tree; assert registry extensions found (sibling of `test_filter_by_extension`) | `TestDiscoverFiles::test_default_extension_registry` |
| 330-333 | `merge_entries` remote-based dedup (`existing_remotes` add for entries carrying `remote`) | D: TOML with a legacy entry `local="data/a.csv", remote="a.csv"` where resolved dest differs; re-scan must not duplicate | `TestMergeEntries::test_merge_dedups_by_remote_migration` (extends the existing remote-migration test's data_dir-outside shape if needed) |
| 335->327 | `merge_entries` unparseable `[[file]]` entry skipped (`except Exception: continue`) | D: TOML entry missing `local`/`remote` keys; merge succeeds, entry preserved, no block on new discoveries | `TestMergeEntries::test_merge_skips_malformed_entry_without_dedup` |
| 429-430 | `_files_identical` compare + OSError fallback via `copy_files` | D + M: `copy_files` dry-run with identical (already covered) plus: monkeypatch `scanner.filecmp.cmp` to raise OSError → treated as differing; differing-content dest with force overwrites (covered) — add the OSError arm | `TestCopyFiles::test_files_identical_oserror_treated_as_different` |

### 3.3 `prepare.py` (432 stmts, 46 missed, 88% → 100%)

| Pinned missed | Behavior | Strategy | NEW test (tests/test_prepare.py) |
| --- | --- | --- | --- |
| 177-178 | `_read_csv_raw_values` empty file → `([], [])` (StopIteration) | D: empty `.csv` through `_check_conversion_parity`-adjacent direct call (or empty-file prepare end-to-end) | `TestPrepareParity::test_raw_values_empty_file_returns_empty` |
| 181-182, 205 | `_read_csv_raw_values` unreadable → None; parity "Cannot read CSV" fail path | D: unreadable csv (bad encoding/binary) → `raw is None` → parity False | `TestPrepareParity::test_parity_unreadable_csv_reports_cannot_read` |
| 215-219 | parity row-count mismatch branch | D: build a parquet extracted from a csv with extra lines (row count differ) — or direct `_check_conversion_parity` unit with mismatched `table` | `TestPrepareParity::test_parity_row_count_mismatch_returns_false` |
| 222-226 | parity column-count mismatch | D: direct unit (table with extra column) | `TestPrepareParity::test_parity_column_count_mismatch_returns_false` |
| 229-233 | parity header vs parquet names divergence | D: direct unit (renamed column) | `TestPrepareParity::test_parity_header_divergence_returns_false` |
| 241->240 | parity soft check ragged row (CSV row shorter than header) | D: csv with a short row; assert no crash + soft warnings still computed | `TestPrepareParity::test_parity_ragged_row_handled` |
| 299 | `_convert_to_parquet` parity fail → `return None` (conversion aborted, CSV fallback) | D: csv whose inferred values diverge (e.g. quoted numbers) → prepare logs "conversion failed — staging original" (asserts existing fallback), rc still 0 | `TestPrepareConversion::test_parity_failure_falls_back_to_csv` (extend the existing conversion-failure test) |
| 317 | large-shard warning print (> `PARQUET_SHARD_WARNING_MB`) | D + M: `restore_tool_config` + monkeypatch `config.PARQUET_SHARD_WARNING_MB` to a tiny value; assert the ⚠ shard line in capsys | `TestPrepareConversion::test_oversized_shard_warns` |
| 355-356 | `_assert_cross_file_schema` `skip_cross_file_schema` skip print + return | D: cfg with `skip_cross_file_schema=True` | `TestAssertCrossFileSchema::test_skip_cross_file_schema_short_circuits` |
| 384->383 | cross-file matching multi-key arc (sheet/key variants) | D: multi-sheet xlsx pair (existing multisheet harness) — assert no mismatch and specs grouped | `TestAssertCrossFileSchema::test_xlsx_sheet_keys_match_grouping` |
| 396 | `_assert_cross_file_schema` no detected splits → early return | D: remotes without split keywords, ≥2 specs | `TestAssertCrossFileSchema::test_no_detected_splits_returns_clean` |
| 401->400 | cross-file split-break arc (`remote in s.files` matched) | D: same-split pair (already exercised by existing same-split tests; reconcile — if still missed after batch, add a 3-file split with one file outside any split) | `TestAssertCrossFileSchema::test_split_membership_break` |
| 407 | `_assert_cross_file_schema` `not split_files` early return | D: files whose remotes match no split after grouping (directory-split naming mismatch) | `TestAssertCrossFileSchema::test_no_split_files_returns_clean` |
| 421-423 | cross-file `pq.read_schema` exception → error appended | D + M: monkeypatch `pq.read_schema` to raise on one parquet | `TestAssertCrossFileSchema::test_unreadable_schema_reports_error` |
| 471-472 | `_check_large_values` unreadable parquet → `return warnings` | D + M: `pq.read_table` raising (or a corrupt parquet path) | `TestCheckLargeValues::test_unreadable_parquet_skips_silently` |
| 485, 488-494 | `_check_large_values` None-value skip + byte_len > max_bytes warning append | D: parquet with a null string + a >10KB string value (or threshold monkeypatched low via a config-constant patch) | `TestCheckLargeValues::test_warns_when_first_row_value_exceeds_threshold` |
| 536->527 | `_assert_card_dtypes_match_parquet` integral-vs-float64 mismatch branch | D: card declares `hf_dtype: float64`, parquet actual is int64 | `TestPrepareCardLicense::test_card_float64_vs_parquet_integral_flagged` |
| 543-544 | card-dtype check unreadable parquet `except Exception` | D + M: monkeypatch `pq.read_schema` raise | `TestPrepareCardLicense::test_card_dtype_check_unreadable_parquet` |
| 615-616, 622->621, 627, 631, 639, 649 | `_check_local_overwrite` artifact-shape branches: xlsx `stem__*` matched; xlsx single-underscore alt; xlsx single-sheet candidate (search_dir missing); non-xlsx convertible candidate; non-eligible passthrough candidate; all_files codebooks-dir | D: cfg × existing-on-disk matrix driving each branch (reuse `_check_local_overwrite`/`prepare` without force, assert rc 1 + refusal list contents) | `TestPrepareOverwriteMatrix::test_overwrite_detects_xlsx_multisheet_and_alt_layout`, `test_overwrite_detects_single_sheet_xlsx_candidate`, `test_overwrite_detects_passthrough_and_codebooks_dir` (parametrized) |
| 734-736 | `prepare` case-fold collision abort (`_validate_case_fold_collisions` errors) | D: two remotes differing only in case → rc 1 before any write (extend existing TestPrepareCaseCollision analog) | `TestPrepareCaseFoldCollision::test_case_fold_collision_aborts` |
| 786-790 | `prepare` large-value warnings printed into output | D: converted table with oversized string (same fixture as 485 row) | `TestCheckLargeValues::test_large_value_warnings_surfaced_in_prepare` |
| 795 | `prepare` stage converted parquet into mirror (copy_to_mirror leg) | D: full prepare on a nested-remote csv; assert mirror path exists (extend `TestPrepareConversion::test_converted_parquet_mirrors_remote_layout` with absolute-path assert) | (extend existing) |
| 813->816 | `prepare` step-7 xlsx `is_converted` single-underscore arc | D: single-sheet xlsx (single-underscore key) — assert not double-staged | `TestPrepareRecursiveStaging::test_xlsx_single_underscore_not_re_staged` |
| 822 | `prepare` step-7 non-converted passthrough/opt-out copy (`copy_to_mirror` original) | D: opt-out `.csv` (`upload_as_csv` / `convert_to_parquet=False`) registered; assert original staged at remote path | `TestPrepareConversion::test_opt_out_csv_staged_at_remote` |
| 887-889 | `prepare` tail: manifest write (`MANIFEST_NAME.json_bytes()`) | D: strengthen the existing full-run test to also assert the manifest file content parses (honest assertion, not a line-touch — if the baseline says the write is missed, the happy path currently ends short; assert artifact presence) | extend `TestPrepareOffline::test_full_run_produces_artifacts_offline` |
| win32 guard (691) | `if sys.platform == "win32" and hasattr(stdout,"reconfigure")` reconfigure body — **executes only on Windows** | **M + D (required for CI 100%)**: `monkeypatch.setattr("sys.platform","win32")` inside the full-run test (stdout.reconfigure exists on all Pythons ≥3.7) | fold into the full-run test above |

### 3.4 `publish.py` (326 stmts, 36 missed, 87% → 100%)

| Pinned missed | Behavior | Strategy | NEW test (tests/test_publish.py) |
| --- | --- | --- | --- |
| 135 | `_ensure_repo` non-"already exists" exception → re-raise (fail-closed) | D + F: fake api whose `create_repo` raises `RuntimeError("boom")`; `pytest.raises` (or via publish gate rc 1) | `TestRemoteFailClosed::test_ensure_repo_raises_on_unrelated_error` (extend existing row) |
| 159-173 | `_hf_upload` single-file upload: success True / exception False | D + F: fake api (upload_file raises / returns); direct `_hf_upload(...)` | `TestHfUpload::test_hf_upload_success_and_failure` (parametrized ×2) |
| 303 | `_repo_diff_summary` ADDED-list truncation "… and N more" | D: > `REPORT_MAX_ITEMS` new files | `TestRepoDiffSummary::test_diff_truncates_long_added_list` |
| 310 | `_repo_diff_summary` OVERWRITTEN-list truncation | D: > `REPORT_MAX_MODIFIED` existing files | `TestRepoDiffSummary::test_diff_truncates_long_modified_list` |
| 313-314 | `_repo_diff_summary` manifest MISSING lines | D: `PackageManifest` fake with `required_missing()` non-empty | `TestRepoDiffSummary::test_diff_lists_manifest_missing_lines` |
| 367-376 | `_check_overwrite_protection` interactive: user "n"/invalid skip; `EOFError`/`KeyboardInterrupt` skip | D + M: `isatty→True` + `builtins.input` "n", "no", EOFError, KeyboardInterrupt (parametrized ×4) | `TestOverwriteProtection::test_interactive_skip_variants` |
| 397 | `_print_split_report` foreign object → no-op return | D: `_print_split_report(None)` / plain dict | `TestSplitReportPrinting::test_print_split_report_ignores_foreign_object` |
| 400 | `_print_split_report` empty splits → return | D: `SplitReport()` with no splits | `TestSplitReportPrinting::test_print_split_report_empty_splits` |
| 408 | `_print_split_report` per-split truncation "… and N more" | D: synthetic SplitReport split with > `REPORT_MAX_MODIFIED` files | `TestSplitReportPrinting::test_print_split_report_truncates_long_split` |
| 411 | `_print_split_report` unclassified count | D: synthetic report with unclassified entries | `TestSplitReportPrinting::test_print_split_report_unclassified_count` |
| 421 | `_print_split_report` layout-validation warnings loop | D: synthetic report whose files trip `validate_layout` (e.g. missing train) | `TestSplitReportPrinting::test_print_split_report_layout_warnings` |
| 431->exit | `_print_split_mapping_validation` warnings block (conflicting remotes) | D: remotes that produce mapping warnings (missing split keywords across dirs) | `TestSplitMappingValidation::test_print_mapping_validation_warns` |
| 537, 553->542..567->570 | `_copy_package`: non-dir source (`planned_remotes`); local-CSV fallback when mirror lacks the CSV (entry.remote match + local exists); `skip` containing readme.md/license; readme/license src absent | D + tmp exact-mirror; cfg with `keep_csv` opt-out entry whose parquet exists but original CSV missing from mirror → fallback copy; second call with `protected={"readme.md","license"}`; build without README/LICENSE | `TestCopyPackageProtection::test_copy_package_local_csv_fallback`, `test_copy_package_readme_license_skip_and_absent` (parametrized), `test_copy_package_non_dir_source` |
| 695 | `publish` auto-prepare failure → rc propagated | D + M: monkeypatch `prepare` (publish-module import) to return 1; `_needs_prepare` forced True via missing parquet | `TestAutoPrepare::test_autoprepare_failure_returns_rc` |
| 804 | `publish` hf `protected_out` side-channel write | D: `publish(..., protected_out=set())` with one protected remote; assert set populated | `TestHfPublish::test_protected_out_populated` |
| 830 | `publish` NOT FOUND advisory for a missing declared source (local-exists check during staging) | D: cfg entry whose local file is absent (real, no monkeypatch) → publish rc 0 + "NOT FOUND" in capsys | `TestBatchStaging::test_publish_reports_not_found_sources` (extend existing not-found row) |
| 855-858 | `publish` post-upload inspection failure → warn + skip split report (upload still succeeds) | D + F: `_api.list_repo_files` raises only on the second call (tracking fake) → rc 0 + "Post-upload inspection failed" warning | `TestHfPublish::test_post_upload_inspection_failure_warns_and_skips_report` |
| win32 guard (685) | `if sys.platform == "win32"` reconfigure body — Windows-only | M: `monkeypatch.setattr("sys.platform","win32")` in one full hf-run test | fold into `TestHfPublish::test_full_publish_upload_folder_called_once` (or the local-target test) |

## 4. Floor plans (COV-01 — ≥90 per file, 91+ local margin)

### 4.1 `profile.py` (253 stmts, 49 missed, 80% → ≥90; clear ≥24)

| Pinned missed | Behavior | Strategy | NEW test (tests/test_profile.py) |
| --- | --- | --- | --- |
| 76 | `_profile_output_for_rel` multi-suffix (`a.tar.csv` → `.tar.metadata.yaml`) | D unit (extend `TestProfileMultisheetPrf05::test_profile_output_helper_purepath_suffixes`) | `test_profile_output_for_rel_multisuffix` |
| 158-159 | `profile()` TSV/stream branch (tab delimiter) + stream path | D: real `.tsv` (existing `test_tsv_writes_metadata_yaml` covers TSV — extend with delimiter assert in YAML) | extend `TestProfileWritesMetadataYaml::test_tsv_writes_metadata_yaml` |
| 166-169 | `profile()` non-streamed `_read_file` branch (parquet/xlsx/jsonl single-file) | D: real parquet (pyarrow) + jsonl fixtures; assert metadata written with rows/delimiter "" | `TestProfileNonStreamedFormats::test_profile_parquet_writes_metadata`, `test_profile_jsonl_writes_metadata` |
| 196->198 | `profile()` missing-fields gap print arc | D: dataset with empty documentation fields (extend existing `test_missing_fields_printed` — reconcile; `_build_column` empty-values produces doc gaps) | extend `TestProfileMissingFields` |
| 250-251, 254-255, 259-260, 265 | `generate_all_profiles` skip paths: directory, missing file, unsupported format, no-entries return | D: batch cfg mixing all three skip shapes + empty-files cfg; capsys asserts the three ⚠ lines | `TestProfileBatchSkipPaths::test_batch_skips_dir_missing_unsupported_and_empty` (parametrized) |
| 280-282 | `generate_all_profiles` xlsx read error → skip w/ stderr | D + M: monkeypatch `_read_xlsx_sheets` (profile module) to raise | `TestProfileBatchSkipPaths::test_batch_xlsx_read_error_skips` |
| 284-287 | `generate_all_profiles` xlsx with zero sheets → single entry + empty-cache write | D: xlsx with only headers/empty workbook (openpyxl-created, 0 named sheets) → asserts the 354-377 empty-metadata branch writes a stub | `TestProfileXlsxEdges::test_xlsx_zero_sheets_writes_empty_metadata` |
| 303 | `generate_all_profiles` `not expanded` fast return | D: all entries skipped (subset of the 250-265 test) | (folded) |
| 325, 387, 411, 417 | `generate_all_profiles` `out_path is None` guards in the non-xlsx / single-sheet / multi-sheet loops | D: construct expanded entries so a second loop pass finds no matching out (e.g. xlsx sheet key dropped after cache rebuild — monkeypatch cache or two-sheet→one-sheet conflict) | `TestProfileXlsxEdges::test_sheet_out_path_missing_skip_guards` |
| 330-332 | `generate_all_profiles` per-file read exception → skip stderr | D + M: monkeypatch `_read_dataset_for_profile` raise | `TestProfileBatchSkipPaths::test_batch_profile_read_error_skips` |
| 354-377 | xlsx empty-cache stub metadata write (see 284-287) | (folded) | |
| 445-446, 451-452 | collision raise: relative-fallback paths (`rel_out`/`base_rel` when not `relative_to(base_dir)`) + collision stderr prints | D: xlsx-vs-csv collision where outputs are under `cache/profiles` (existing `test_collision_partial_write_then_value_error` covers the happy-collision; add the non-relative variant via outside-data-dir entries) | `TestProfileBatchPrf05::test_collision_names_sources_outside_base` |
| 488-490 | `_read_dataset_for_profile` non-streamed tail (parquet/xlsx/jsonl batch read) | D: batch cfg with a parquet + an xlsx entry | `TestProfileNonStreamedFormats::test_batch_reads_parquet_and_xlsx` |
| 528->527 | `_stream_columns` row-longer-than-header truncation arc | D: csv with a ragged longer row | `TestProfileWritesMetadataYaml::test_stream_columns_truncates_long_rows` |

### 4.2 `mcp_registration.py` (235 stmts, 39 missed, 80% → ≥90; clear ≥17)

| Pinned missed | Behavior | Strategy | NEW test (tests/test_mcp_registration.py) |
| --- | --- | --- | --- |
| 84, 93 | `resolve_config_path` unknown-agent raises (user + project scope) | D: `resolve_config_path("nope", "user")` / `"nope","project"` → `pytest.raises(ValueError)` | `TestResolveConfigPath::test_unknown_agent_raises_both_scopes` |
| 124, 135 | `read_config` non-object JSON / non-table TOML raises | D: json `[1,2]` file / toml with scalar root | `TestReadConfigMalformed::test_rejects_non_object_json_and_non_table_toml` |
| 175 | `build_entry` unknown-agent raise | D | `TestBuildEntry::test_unknown_agent_raises` |
| 183 | `_normalize_codex_command` non-str/non-list → `[]` | D unit | `TestIdempotency::test_normalize_codex_command_non_string_returns_empty` |
| 192, 195, 200-206 | `_entries_equal` codex cwd/env mismatch returns False; gemini branch; opencode branch | D unit: matrix of (doc_a, doc_b) per agent | `TestIdempotency::test_entries_equal_per_agent_matrix` (parametrized) |
| 259, 263 | `merge` gemini idempotent-equality branch + unknown-agent raise | D | `TestMerge::test_gemini_idempotent_no_change`, `TestMerge::test_merge_unknown_agent_raises` |
| 284, 295, 302, 306, 310 | `remove_entry` codex/gemini last-server pop (empty table removed) | D: existing doc with ONLY sofer under codex/gemini → pop parent table + `(doc, True)` | `TestRemove::test_remove_codex_pops_empty_table`, `test_remove_gemini_pops_empty_table` |
| 385-386 | `atomic_write` TOML branch (tomli-w dump) | D: `atomic_write(path, doc, "toml")` then read back via tomllib and assert content | `TestIdempotency::test_atomic_write_toml_roundtrip` |
| 408, 421, 424 | `delegate_add`: rc==0 success; timeout/OSError except; post-loop return | D + M: fake `shutil.which` + fake `subprocess.run` (rc 0 / rc 1 / TimeoutExpired) | `TestDelegation::test_delegate_add_success_and_failure_variants` (parametrized) |
| 438-447 | `delegate_remove`: absent exe / rc 0 / rc != 0 / timeout / bare exception | D + M (same fake-subprocess harness) | `TestDelegation::test_delegate_remove_variants` (parametrized ×4) |
| 519-520 | `validate_cwd` project-scope branch + resolve-failure → False | D: tmp under home w/ project scope; unresolvable path (`Path("") `/ non-existent with resolve raising, monkeypatch `Path.resolve` OSError) | `TestCwdContainment::test_validate_cwd_project_scope_and_resolve_failure` |

### 4.3 `verification.py` (60 stmts, 8 missed, 83% → ≥90)

| Pinned missed | Behavior | Strategy | NEW test (tests/test_splits.py + tests/test_prepare.py leg) |
| --- | --- | --- | --- |
| 102-103, 107 | `verify_load_dataset` per-split row-count: `len(ds[name])` success + `except → -1` (unknown) | D + M: `pres-slash` fake datasets (existing `patch.dict(sys.modules)` harness in `TestVerifyLoadDataset`); one split whose container raises `TypeError` on `len` | `TestVerifyLoadDataset::test_split_row_count_unknown_when_len_raises` |
| 142-143 | `_print_verification_report` SKIPPED branch (prints SKIPPED + warnings) | D: synthetic `VerificationReport(skipped=True, warnings=[...])` → capsys | `TestPrintVerificationReport::test_print_skipped_report` |
| 146 | FAILED status line (report not skipped) | D: synthetic `VerificationReport(passed=False)` | `TestPrintVerificationReport::test_print_failed_report_status` |
| 149-150 | FAILED errors list print | D: same with `errors=["..."]` | (folded) |
| — (already covered) | expected-splits line, warnings line, `?` row formatting | covered by the same synthetic-report class | `TestPrintVerificationReport::test_print_expected_and_warning_lines` (pins existing pass-shape output) |
| prepare verify leg | `prepare(verify=True)` end-to-end (both functions) | D: real small dataset + parquet; `patch.dict(sys.modules, {"datasets": fake})` for PASSED/FAILED, datasets-absent for SKIPPED (extend existing `TestPrepareVerify`; keep the SKIPPED test as the `test_prepare.py` leg) | extend `TestPrepareVerify::test_prepare_verify_skipped_when_datasets_absent` |

## 5. Enforcement design (COV-06 + CI-01 carve-out + AGENTS rule 14 + contract guard)

### 5.1 Gate mechanism — committed script, one step in the ci.yml coverage job

**Shape chosen: `scripts/check_core_coverage.sh`** (the proposal's permitted alternative C over the inline Appendix-B form). Justification:

1. **CI-01 S2 keeps its force**: "no `--fail-under` / `fail_under` / `fail-under` in ci.yml or release.yml" stays literally TRUE for both workflows under the script shape — the COV-06 exception lives outside workflow text, so the existing canonical scan survives with a docstring re-scope instead of an allowlist rewrite.
2. **One home for the four invocations**: the script lists all four `--include=src/sofer/<file>.py --fail-under=100 -m` invocations once; AGENTS rule 14, the static gate test, and local dev all parse the single artifact — no 4×YAML duplication, no drift between docs and gates.
3. **CI-agnostic + local**: `bash scripts/check_core_coverage.sh` runs identically pre-push locally and in the ubuntu coverage job; enforcement is not CI-only.
4. **Tooling-safe**: ruff/mypy ignore `.sh`; `pythonpath = ["scripts"]` (pyproject) is unaffected by adding a non-Python file.
5. **`release.yml` deliberately NOT mirrored**: COV-06 binds the `ci.yml` coverage job (spec scenario); the config-owned TOTAL gate already gates release (CI-03). Mirroring would duplicate machinery and widen the static-test surface — rejected under COV-03's bounded-machinery rule.

Script (apply-ready):

```bash
#!/usr/bin/env bash
# COV-06 / AGENTS.md rule 14: per-file scoped 100% gates for the CLI core.
# coverage.py cannot express a per-file floor in config, so each core module gets
# its own scoped invocation. --fail-under=100 is a fixed policy constant, never a
# tunable floor — the config-owned TOTAL gate (ci CI-01, fail_under = 90) is
# untouched and enforced by the flag-free `coverage report -m` step in the same job.
set -euo pipefail
for f in cli scanner prepare publish; do
  uv run coverage report --include="src/sofer/${f}.py" --fail-under=100 -m
done
```

ci.yml coverage job insertion (after the existing `Report coverage with missing lines (the gate)` step, same indentation as siblings):

```yaml
          # ── CLI-core 100% gates (COV-06, AGENTS.md rule 14) ─────────────
          # Four scoped per-file invocations in scripts/check_core_coverage.sh:
          # each core module must measure 100.00% with zero `# pragma: no cover`.
          # Additive and scoped per file; the TOTAL gate stays config-owned.
          - name: Gate core module coverage (COV-06)
            run: bash scripts/check_core_coverage.sh
```

### 5.2 CI-01 S2 narrowing + one-line canonical `ci` clause (tasks/apply)

- **Narrowed `tests/test_ci_workflows.py::test_coverage_gate_is_config_driven_without_cli_floor`**: keeps both workflow text scans unchanged (they still hold — script shape), but the docstring is re-scoped from "no floor literal or flag in the workflows" to **"the TOTAL gate only"**, explicitly naming `scripts/check_core_coverage.sh` + `test_coverage_job_gates_core_modules_at_100` as the COV-06 documented exception (per-file 100 invocations are NOT the TOTAL floor and do not weaken CI-01). Assertions unchanged; one added assertion pins that the TOTAL report step remains the flag-free `uv run coverage report -m`.
- **New `tests/test_ci_workflows.py::test_coverage_job_gates_core_modules_at_100`**: reads `scripts/check_core_coverage.sh` text + parses the `ci.yml` coverage job; asserts (a) each of the four `src/sofer/<file>.py` paths appears paired with `--fail-under=100 -m` in the script and the script is referenced by a coverage-job step; (b) no `--fail-under` value other than 100 appears in script or workflows; (c) the config-key spelling `fail_under` (underscore) appears nowhere in script or workflows (`pyproject.toml` remains its only home — existing `test_pyproject_declares_coverage_fail_under_90` unchanged).
- **New `tests/test_ci_workflows.py::test_agents_md_declares_core_100_mandate`**: AGENTS.md rule 14 text inspection (names the four modules, declares 100.00%, forbids `# pragma: no cover`).
- **One-line canonical `ci` clause** (edits `openspec/specs/ci/spec.md` CI-01, applied in tasks/apply — recorded follow-up per proposal; not part of this change's src/test diff): append to CI-01's paragraph:
  > COV-06 (spec `coverage`) is the documented, additive exception: per-file scoped `--fail-under=100` gates exist only as the four invocations in `scripts/check_core_coverage.sh` referenced by the `ci.yml` coverage job, and SHALL NOT weaken or re-declare the config-owned TOTAL floor.

### 5.3 AGENTS.md rule 14 — exact text (inserted after rule 13, repo bullet style)

```markdown
### 14. CLI-core coverage: 100% mandate, zero pragmas
- `src/sofer/cli.py`, `src/sofer/scanner.py`, `src/sofer/prepare.py`, and
  `src/sofer/publish.py` MUST each measure **100.00% line coverage** under
  `uv run coverage report -m` (the `[tool.coverage.run]` configuration:
  `branch = true`, `source = ["src/sofer"]`), over the complete suite
  (`coverage run -m pytest`). The per-file scoped gates
  (`coverage report --include=src/sofer/<file>.py --fail-under=100 -m`, listed in
  `scripts/check_core_coverage.sh` and run by the CI coverage job) are the
  enforcement; a drop below 100.00% in any of the four files fails CI.
- `# pragma: no cover` is **FORBIDDEN** in those four modules — no exception,
  including "genuinely untestable" lines. Every line must actually execute in
  tests; a line that cannot be reached from a test is a defect in the test
  strategy or a design-doc escalation, never a pragma.
- The TOTAL gate stays config-owned (`[tool.coverage.report] fail_under = 90`,
  spec `ci` CI-01) and is never weakened, bypassed, or re-declared by the
  per-file mandate. The per-file 100% gates are additive and scoped per file;
  they hardcode 100 only because 100 is a fixed policy constant, not a tunable
  floor.
- This rule justifies NO `src/sofer/` edit: the dead `if __name__ == "__main__":
  main()` guard in `cli.py` is kept and exercised in-process
  (`runpy.run_module("sofer.cli", run_name="__main__")` with argv at a harmless
  subcommand) as part of the 100.00% row — `python -m sofer.cli` remains a
  working entry point (`tests/conftest.py::run_cli` drives it as the PB-02
  subprocess boundary).
- This rule's 100% mandate covers exactly those four modules. Other modules are
  governed by their own per-file floors (spec `coverage` COV-01) or have no
  floor.
```

### 5.4 `tests/test_coverage_contract.py` (NEW, ~120 lines)

Skip-if-absent local read + static scans only — NO measured-percentage asserts beyond the sanctioned local `.coverage` read (COV-01-S3 / COV-05 carve-out):

- `test_core_modules_contain_no_pragma_tokens` — full-text scan of `cli.py`/`scanner.py`/`prepare.py`/`publish.py` for the substring `pragma: no cover` (catches both `# pragma:` and `#pragma:` spellings): zero matches per file. (Maps COV-03/COV-06 pragma scenarios; the shared assertion is reused by the COV-06 row.)
- `test_cli_has_no_main_guard` — **REPLACED (Resolution A)** by the in-process guard-EXECUTION test `tests/test_cli.py::test_cli_main_guard_executed_via_runpy` (runpy under the tracer; see §3.1 row 1575). No guard-absence scan applies — the guard is kept.
- `test_three_floor_modules_and_total_meet_90_when_data_file_present` — `@pytest.mark.skipif(not (_REPO_ROOT / ".coverage").exists(), reason="no local .coverage data file")`; imports `coverage.CoverageData` **inside the function** (dev-dep `coverage>=7.16.0` installed; lazy import keeps the test job robust); reads ONLY through the read API: `CoverageData().read()`, `measured_files()`, per-file `line_counts()` for the three floor module paths (≥90 each) and TOTAL over all measured files (≥90). If the DB exists but is empty/partial (mid-run artifact), treat as absent → skip (best-effort local regression pin; CI measurement is the arbiter per COV-01-S2). Function names: `test_three_floor_modules_meet_90`, `test_total_coverage_meets_90` (or one combined guard per spec's "asserts the three rows + TOTAL").
- `test_gate_machinery_bounded` (optional, low-cost) — `pyproject.toml` text scan: `fail_under = 90` present, no extra coverage keys; no XML/Codecov references in the diff-visible workflow text. (COV-03 scan assist; the workflow bounds are also verify-phase static evidence.)

In CI this guard skips naturally: the coverage job writes `.coverage` mid-run (absent/partial → skip); the plain test job's fresh checkout has none → skip. Floors remain verify-phase evidence (COV-01), exactly per spec.

## 6. Execution order, commit plan, and changed-line estimate

### 6.1 Units (each commit leaves `uv run pytest tests/ -q` green; per-batch measurement `uv run coverage run -m pytest -q && uv run coverage report -m`)

| Unit | Contents | Est. changed lines | Commit |
| --- | --- | --- | --- |
| A-0 | Baseline already pinned by parent (this design). Apply starts at A. | 0 | — |
| A | `test(cli)`: add `test_cli_main_guard_executed_via_runpy` — in-process `runpy.run_module("sofer.cli", run_name="__main__")` with argv at a harmless subcommand; asserts rc/exit-call under the tracer (covers cli.py:1575, the only line needing an explicit entry-point test). **Do this first** so the cli.py 100.00 row includes the guard region. Zero `src` edits (Resolution A). | ~25 | `test(cli): cover cli.py __main__ guard in-process via runpy (COV-06)` |
| B | cli.py 100% tests (§3.1, ~26 new tests incl. parametrizations) | ~600–850 | `test(cli): drive cli.py to 100.00% line coverage` |
| C | scanner.py 100% tests (§3.2, ~6) | ~120–180 | `test(scanner): drive scanner.py to 100.00% line coverage` |
| D | prepare.py 100% tests (§3.3, ~20) | ~320–480 | `test(prepare): drive prepare.py to 100.00% line coverage` |
| E | publish.py 100% tests (§3.4, ~15) | ~300–450 | `test(publish): drive publish.py to 100.00% line coverage` |
| F | Floors: profile (§4.1 ~11), mcp_registration (§4.2 ~10), verification + prepare leg (§4.3 ~4-5) | ~430–640 | `test(profile): cover batch skips, non-streamed formats, xlsx edges` / `test(mcp-registration): cover malformed configs, delegation, pop-empty, toml write` / `test(verification): cover report printing and split-row-count edge` |
| G | Gates + policy + contract: `scripts/check_core_coverage.sh` (NEW ~12), ci.yml step (~7), AGENTS.md rule 14 (~12), `tests/test_coverage_contract.py` (NEW ~120-130), `test_ci_workflows.py` narrowed S2 + 2 new tests (~80-110) | ~230–290 | `ci: gate CLI-core modules at 100% (COV-06); AGENTS rule 14; static contract guard` |
| H | CI-01 canonical one-line clause in `openspec/specs/ci/spec.md` + this change's task/verify artifacts | ~40–90 | `docs(sdd): ci CI-01 carve-out note for COV-06 gates; tasks + verify report` |
| V | Verify: `coverage report -m` rows (4×100.00, 3×≥90, TOTAL ≥90, rc 0), four gate invocations rc 0, suite count, `uv run ruff check src/ tests/ scripts/`, `uv run mypy src/`, `git diff origin/dev --stat` (zero `src/sofer/` paths), PR template filled | 0 (evidence) | `docs(sdd): verify report for coverage change` |

**Per-batch stop rule**: after each unit, the per-file row must read 100.00 (core) or ≥91 local (floors, hard min 90.3 with written justification) and the full suite must be green. Stop the unit when its row hits target — do NOT chase extra tests beyond the target (margin policy §6.3). If a region's pinned anchor doesn't reconcile with apply-time output, re-anchor on the function (A-0 reconciliation contract §2) and write the missing test; unresolved-forever lines escalate to the design (never a pragma).

### 6.2 Changed-line estimate (honest) and the ask-on-risk trigger

- Prior estimate (amended proposal): **≈1800–2600**.
- Fresh bottom-up (§6.1): **≈1800–2900**, mid ≈**2300** — of which test bodies ~1770–2600, gates/policy/contract ~230–290, spec/artifacts ~40–90, and **zero src edits** (the guard is kept; the ~25-line runpy test replaces the −2-line removal).
- **Ask-on-risk: the range crosses 1500 with near-certainty (est. >95%)**. Per DP9 and SDD delivery policy, when the measured `git diff origin/dev --stat` crosses 1500 the delivery pauses for a user decision — **chain vs size-exception** — never silently invented. Pre-set trim lever if the user rejects both sizes: none for the binding contract (four 100% rows + three floors are mandated); only the floor *margin-above-90* tests (targeting extra pp) are trimmable, and only to the hard 90.3 local floor.
- Single-PR intent is preserved *unless* the user picks chaining at the ask-on-risk gate; chain strategy remains deferred until selected.

### 6.3 Risk register (CI-interpreter / 100%-row hazards)

- **`sys.platform == "win32"` reconfigure guards** (`prepare.py:691`, `publish.py:685`) execute only on Windows; the CI gate is ubuntu → **must** be covered by the `monkeypatch.setattr("sys.platform","win32")` tests in §3.3/§3.4. The pinned dev baseline (Windows) shows them covered — that is the trap; the CI 100% rows depend on the patched tests.
- **`tomli`→`tomllib` fallback arcs** (`cli.py:435-439`, `mcp_registration` read_config): on 3.11+ tomli is absent per the pyproject marker, so `import tomli` raises inside the function and both the import line and the except body count as executed — arcs resolve naturally in-process. Only an environment that CAN import tomli would miss the fallback arc; the ubuntu 3.13 gate arbiter has no tomli. Verify at first batch; if a local interpreter (with tomli) shows the arc missed, add a `builtins.__import__` blocker test for the function call.
- **`datasets` optional dependency**: all verification paths are driven with `patch.dict(sys.modules)` so both present/absent shapes execute on any interpreter.
- **Python-version statement-count variance**: floors ≥90 with the ≥91 local bar absorb 3.10→3.13 drift; the four 100% rows are binary — the CI gate itself is the arbiter.
- **False-positive 100%**: review lens checks assertion quality per §3 discipline (COV-05); the pragma scan + rule 14 make a pragma relapse impossible to land silently.
- **contract guard mid-run skew**: `.coverage` read during the coverage job sees a partial DB → skip path (spec COV-01-S3).

## 7. File changes and contracts

| Path | Change | Contract |
| --- | --- | --- |
| tests/test_cli.py | U | §3.1 (extend existing ~1400-line module; no removal of existing tests) incl. `test_cli_main_guard_executed_via_runpy` (row 1575) |
| tests/test_scanner.py | U | §3.2 |
| tests/test_prepare.py | U | §3.3 + §4.3 verify leg |
| tests/test_publish.py | U | §3.4 |
| tests/test_profile.py | U | §4.1 |
| tests/test_mcp_registration.py | U | §4.2 |
| tests/test_splits.py | U | §4.3 |
| tests/test_coverage_contract.py | **NEW** | §5.4 (~120 lines) |
| tests/test_ci_workflows.py | U | §5.2 (narrowed S2 + `test_coverage_job_gates_core_modules_at_100` + `test_agents_md_declares_core_100_mandate`) |
| tests/conftest.py | U **only if reuse justified** (expected: none, or ≤1 tiny helper) | AGENTS rule 4 |
| src/sofer/cli.py | **Untouched** (Resolution A) | `__main__` guard kept; covered by `tests/test_cli.py::test_cli_main_guard_executed_via_runpy` (§3.1 row 1575) — zero `src/sofer/` paths in the diff |
| scripts/check_core_coverage.sh | **NEW** | §5.1 (sh, non-Python — ruff/mypy ignore) |
| .github/workflows/ci.yml | U | coverage job += 1 COV-06 step (§5.1); `release.yml` untouched |
| AGENTS.md | U | rule 14 (§5.3) after rule 13 |
| openspec/specs/ci/spec.md | U (apply-time, H) | CI-01 one-line carve-out clause (§5.2) |
| openspec/changes/2026-09-13-raise-per-file-coverage/ | U | this design + tasks.md + verify report |
| pyproject.toml, other workflows, other src/sofer/, docs | **Untouched** | COV-02/COV-03/DP8 |
| README.md / README_ES.md | Untouched | rule 13 applies to translated READMEs only; AGENTS.md rule 14 is not a README section |

## 8. Success criteria (design acceptance → applied state)

1. `uv run coverage report -m`: four core rows **100.00**, three floor rows **≥90**, TOTAL **≥90** (expected ≈91-92), rc 0.
2. CI coverage job green (ubuntu 3.13): the four COV-06 gate invocations exit 0 AND the config-owned `fail_under = 90` TOTAL gate passes — CI-01 untouched.
3. `scripts/check_core_coverage.sh` + ci.yml step present; AGENTS.md rule 14 present (static tests green).
4. Zero `# pragma: no cover` tokens in the four core modules; `__main__` guard KEPT and executed under the tracer (`tests/test_cli.py::test_cli_main_guard_executed_via_runpy` green).
5. `git diff origin/dev --stat` shows **zero** `src/sofer/` paths (test-only change, Resolution A).
6. Full suite green; ruff/mypy/git-diff --check clean; suite count ≥ baseline + new tests.
7. Every §3/§4 region reconciled against apply-time missing lists (none unclassified); every scenario in COV-01..COV-06 maps to a test or verify-phase evidence (rule 6).
8. Single PR vs dev, PR template with real verification output, assignee emiliodavola; **ask-on-risk** fired (not silently expanded) when changed lines cross 1500.

---

## Result Contract

- **status**: design-ready — amended scope fully re-synced; baseline pinned by parent (no re-run); per-module 100% and floor plans grounded in the current source of all seven modules plus the existing test-module conventions (`TestLoadAndValidate` direct-Namespace dispatch, `TestHfPublish` fake-HfApi, `TestVerifyLoadDataset` `patch.dict(sys.modules)`, `conftest.run_cli`).
- **executive_summary**: Rewrote the superseded design to the amended contract: four core modules (cli/scanner/prepare/publish) to 100.00% with zero pragmas via ≈67 new behavior-asserting tests, three ≥90 floors (profile/mcp_registration/verification) via ≈25 more, **zero `src` edits (Resolution A)** — the cli.py `__main__` guard is kept and covered by a new in-process runpy test (`test_cli_main_guard_executed_via_runpy`, §3.1 row 1575) after the guard-removal premise proved false (conftest.run_cli's `-m sofer.cli` PB-02 boundary fails 14 tests on removal; runpy executes the guard body under the tracer) — enforcement via a committed `scripts/check_core_coverage.sh` + one ci.yml coverage-job step (script shape chosen: keeps CI-01 S2's workflow-text scan literally true, one home for the four invocations, CI-agnostic, release.yml not mirrored), the CI-01 S2 narrowing + one-line canonical `ci` clause, AGENTS.md rule 14 exact text, and a ≈120-line skip-if-absent `tests/test_coverage_contract.py`. Critical CI-interpreter hazards recorded (win32 reconfigure guards must be sys.platform-patched for the ubuntu 100% rows). Honest changed-line estimate ≈1800–2900 (mid ≈2300; +~25 runpy test) — **ask-on-risk above 1500 fires with near-certainty; a chain-vs-exception user decision is required, never invented**.
- **artifacts**:
  - `openspec/changes/2026-09-13-raise-per-file-coverage/design.md` (this rewrite — authoritative)
  - Read inputs: `proposal.md` (amended), `specs/coverage/spec.md` (COV-01..COV-06), `openspec/specs/ci/spec.md` (CI-01), `.github/workflows/ci.yml`, `tests/test_ci_workflows.py`, `AGENTS.md`, all seven target modules, the six touched test modules, `tests/conftest.py`, `pyproject.toml`, `.gitignore`, PR template
  - Pending: `tasks.md` (apply), one-line `openspec/specs/ci/spec.md` CI-01 clause (apply unit H), verify report
- **next_recommended**: apply — unit A (the new `test_cli_main_guard_executed_via_runpy` in-process runpy test, first), then B→H in order with the per-batch measurement + stop rule; pause at the ask-on-risk gate (measured diff > 1500) for the chain-vs-exception decision before V.
- **risks**:
  - **RESOLVED (2026-09-13, Resolution A, parent-authorized)**: the guard-removal plan was blocked at apply (14 PB-02 failures) — replaced by the kept-guard + in-process runpy test; zero src edits. Remaining risk: the runpy test itself must land for the cli.py 100.00 row (tasks A-1/A-2, before B-13's measure).
  - **HIGH**: `sys.platform == "win32"` reconfigure guards in prepare.py/publish.py are Windows-covered in the pinned (dev-Windows) baseline but will fail the ubuntu 100% gates unless covered via the mandated sys.platform-patched tests — the single most likely way this change's CI fails.
  - HIGH: total changed lines ≈1800–2900 guarantees the ask-on-risk gate fires; without a pre-agreed user decision the apply stalls at ~1500 measured lines.
  - MEDIUM: Python-version variance for floors (3.13 vs dev) — mitigated by ≥91 local bar + CI-arbiter rule.
  - MEDIUM: false-positive 100% via weak assertions — mitigated by COV-05 discipline, per-new-test observable-outcome rule, review assertion audit.
  - LOW: contract guard mid-run `.coverage` skew — skip path per COV-01-S3.
  - LOW: `tomli` fallback arc in unusual environments — resolves on the 3.13 gate arbiter; blocker test only if a first-batch scan shows it missed.
- **skill_resolution**: `paths-injected` — read the parent-injected `gentle-ai/SKILL.md` before work (no fallback needed).

## Key Learnings

- **The pinned baseline is dev-Windows, the gate is ubuntu-Linux**: the `sys.platform == "win32"` `stdout.reconfigure` guards in prepare.py and publish.py show *covered* on the pinned run yet *cannot* reach 100% on the CI interpreter unless tests monkeypatch `sys.platform` — for 100% mandates the win-only branches stop being absorbable margin and become first-class test targets. Check every OS- or version-gated branch before trusting a locally-green 100%.
- **The script shape is the clean carve-out**: putting the four `--fail-under=100` invocations in a committed `scripts/*.sh` (instead of inline YAML) keeps CI-01 S2's "no flags in workflows" scan literally true, so the canonical test needs only a docstring re-scope, not an allowlist — the exception lives in one parseable artifact that AGENTS rule 14, the static test, and local dev all read.
- **100% never needs pragmas and rarely needs new seams**: the whole core-surface missed set decomposes into existing templates — direct Namespace dispatch, monkeypatched `input`/`isatty`/`sys.platform`, fake HfApi, `patch.dict(sys.modules)`, and real parquet/xlsx fixtures whose deps are already present. "Genuinely untestable" is empty here; the one body the pinned baseline flagged (cli.py `__main__` guard) is covered by the in-process runpy test under Resolution A — real execution, never a pragma, never a removal.
- **Coverage.py counts raising imports as executed**: an `import tomli` that raises inside a handler covers both the import line and the `except ImportError` fallback — a concern only on interpreters that CAN import tomli; the 3.13 gate arbiter (tomli absent by marker) resolves the arcs for free, which is why they don't even appear in the pinned missed list.
- **The `__main__` guard was the wrong hill to die on — runpy solves it**: the "unreachable without removal" premise collapsed under an in-process `runpy.run_module("sofer.cli", run_name="__main__")` probe that executes `main()` through the guard under the coverage tracer; combined with `conftest.run_cli`'s `-m sofer.cli` PB-02 boundary, removal was both unnecessary and destructive (14 failing tests). For 100% mandates, an entry guard is a first-class execution target (a real line to cover), not a removal candidate — "cannot be driven without subprocess-coverage machinery" was false advice.