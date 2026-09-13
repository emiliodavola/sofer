# Tasks — Raise per-file coverage (amended: CLI-core 100% mandate + three ≥90 floors)

Change: `2026-09-13-raise-per-file-coverage` · Branch: `test/raise-coverage-90` · Base: `dev` · Phase: tasks
Status: ready for apply. Authoritative inputs: amended `proposal.md`, `specs/coverage/spec.md` (COV-01..COV-06), re-synced `design.md` (baseline pinned by parent — do NOT re-run A-0). **Resolution A (2026-09-13, parent-authorized): the cli.py `__main__` guard is KEPT and covered by an in-process runpy test (unit A-1) — zero `src/sofer/` edits anywhere in this change.**

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ≈1800–2900 (mid ≈2300: test bodies ~1770–2600, gates/policy/contract ~230–290, spec/artifacts ~40–90, zero src edits — runpy guard test +~25) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | Single PR vs `dev` with work-unit commits A→V (design intent), OR if the user picks chaining at the ask-on-risk gate: PR 1 = A (guard runpy test); PR 2 = B+C; PR 3 = D; PR 4 = E; PR 5 = F+G+H (floors); PR 6 = I+J+K+L (gates/policy/contract); PR 7 = V (evidence) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

```text
Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High
```

**Decision needed before apply: Yes** — the size expectation ≈1800–2900 crosses the 1500-line review budget with near-certainty (>95%). Per ask-on-risk, when the measured `git diff origin/dev --stat` crosses 1500 the user must choose **chain vs size-exception**; the choice is never invented. Trim lever if both sizes are rejected: only the floors' margin-above-90 tests are trimmable, and only down to the hard 90.3 local floor — the binding contract (four 100% rows + three ≥90 floors + TOTAL ≥90) has no trim.

## 0. Execution contract (applies to every unit)

- **Per-batch measurement**: after each unit, run `uv run coverage run -m pytest -q && uv run coverage report -m` and RECORD the unit's target row(s) in the apply log (robot: exact `%` + missed count before moving on).
- **Stop rule**: stop the unit when its row(s) hit target — 100.00 for the core four (cli/scanner/prepare/publish), ≥91 local for the three floors (hard min 90.3 with a written justification). Do NOT chase extra tests beyond the target. Do NOT continue a unit that has not reached its target (fix or escalate).
- **Re-anchor contract (design §2, Resolution A)**: NO src edit — `cli.py` line numbers stay as pinned; the `__main__` guard at 1575 is covered by the in-process runpy test (unit A-1), never removed. Reconcile every pinned line against apply-time `coverage report -m` output by **function + behavior**, never by the raw number.
- **Zero `# pragma: no cover`** anywhere in the four core modules — no exceptions. A line that cannot be reached is a test-strategy defect or a design-doc escalation (never a pragma, and **never a `src` edit — Resolution A: this change has zero src touches**).
- **COV-05**: every new test asserts an observable outcome (return, output text, rc, side effect, exception) with config/fixture values — never merely executing a line. No test asserts measured percentages.
- In-process invocation only (`conftest.run_cli`, direct `cli._cmd_*(Namespace(...))` dispatch, `runpy.run_module("sofer.cli", run_name="__main__")` for the guard, monkeypatch, fake `HfApi`, `patch.dict(sys.modules)`) — subprocess execution escapes coverage and cannot be 100%-real.
- Commit style: Conventional Commits (design §6.1); every commit leaves `uv run pytest tests/ -q` green.

## 1. Unit A — cli.py `__main__` guard executed in-process (FIRST; zero `src` edits, Resolution A)
    
- [x] add runpy test `test_cli_main_guard_executed_via_runpy` (runs `runpy.run_module('sofer.cli', run_name='__main__')` with argv pointing at a harmless subcommand, asserts rc/exit-call, strict coverage under tracer). Covers `cli.py:1575` — the ONLY cli.py line needing an explicit entry-point test; all other cli.py lines are covered by the units B–E tests. The guard is KEPT (parent-authorized Resolution A; the removal plan is superseded — `conftest.run_cli`'s `-m sofer.cli` PB-02 boundary fails 14 tests on removal, and runpy executes the guard body under the tracer). <!-- sdd-owner: implementation -->
- [x] A-2 Land the runpy test in `tests/test_cli.py` (or the module where it fits); confirm the next per-batch scan measures the guard region covered (no line-number shift — no deletion) and record the cli.py row; full suite green. Commit: `test(cli): cover cli.py __main__ guard in-process via runpy (COV-06)`. <!-- sdd-owner: implementation -->

## 2. Unit B — cli.py 100% (tests/test_cli.py; ~29 new test functions, §3.1)

Run in-process per the strategy legend (D = direct `_cmd_*` Namespace dispatch + capsys; M = monkeypatch `builtins.input`/`sys.stdin.isatty`/`Path.cwd`/module fns; real tmp datasets). Each test asserts an observable outcome.

- [x] B-1 `TestNoChecksPath::test_prepare_no_checks_runs_happy_path` (covers 83 `return cfg, None` --no-checks short-circuit + 129-130 `_cmd_prepare` happy tail: `resolve_output_dir` + real `run_prepare`; assert rc 0 + `build/` artifacts exist). <!-- sdd-owner: implementation -->
- [x] B-2 `TestCodebookAllFilesErrors::test_all_files_valueerror_returns_1` + `test_codebook_requires_file_or_all_files` (209-211 ValueError → stderr + rc 1 via monkeypatched `sofer.cli.generate_all_codebooks`; 231 missing FILE/--all-files → rc 1). <!-- sdd-owner: implementation -->
- [x] B-3 `TestProfileRenderFlagCoverage::test_profile_all_files_toml_selection_variants` (parametrized ×3; 278, 283-285 effective-TOML selection `elif dataset_raw` / `else` config-path fallback) + `test_profile_all_files_no_file_entries_returns_1` (292-293) + `test_profile_all_files_unreadable_toml_returns_1` (298-300) + `test_profile_requires_dataset_or_all_files` (304-305). <!-- sdd-owner: implementation -->
- [x] B-4 `TestProfileRenderFlagCoverage::test_profile_relative_output_anchors_to_dataset_parent` (310 relative `--output` anchoring; in-process twin of test_cli.py:1365) + `test_render_all_files_selection_and_error_variants` (parametrized; 352, 357-359, 366-367 mirror of profile set) + `test_render_requires_package_and_reports_toml_errors` (372-374, 378-379) + `test_render_relative_output_and_existing_readme_hint` (384-385 relative output + `FileExistsError` hint; twin of test_cli.py:1377). <!-- sdd-owner: implementation -->
- [x] B-5 `TestScanPromptGate::test_scan_phase1_prompt_preview_and_yes` (485-486 Phase-1 preview + `input("y")` + `sys.stdin.isatty`) + `test_scan_phase2_eof_aborts_atomically` (552-553, 555-556 P2 gate `EOFError → "n"`, assert "OK  Aborted." + TOML untouched). <!-- sdd-owner: implementation -->
- [x] B-6 `TestScanCliFailurePaths::test_scan_move_failure_returns_1` (494-496 monkeypatch `sofer.cli.move_to_raw` → OSError) + `test_scan_flatten_collision_aborts_before_copy` (530-532 ValueError abort) + `test_scan_copy_collision_returns_1` (561-563 pre-created differing dest, no force). <!-- sdd-owner: implementation -->
- [x] B-7 `TestScanDryRun::test_scan_dry_run_idempotent_cache` (571 "Nothing to copy — all files already present") + `test_scan_dry_run_all_registered` (578 "All discovered files already registered"). <!-- sdd-owner: implementation -->
- [x] B-8 `TestMcpAddCliCoverage::test_mcp_add_defaults_to_cwd` (652 `Path.cwd()`-default resolve; monkeypatch `Path.cwd` under home) + `test_mcp_add_native_delegation_skips_file_edit` (681-682) + `test_mcp_add_native_failure_falls_back` (684-685) + `test_mcp_add_project_scope_path_anchoring` (parametrized ×2; 697-700 both `resolve_config_path` project branches). <!-- sdd-owner: implementation -->
- [x] B-9 `TestMcpAddCliFailure::test_mcp_add_backup_failure_returns_1` (720-723 monkeypatch `mcp_registration.backup` → raise) + `test_mcp_add_write_failure_returns_1` (728-731 monkeypatch `mcp_registration.atomic_write` → raise). <!-- sdd-owner: implementation -->
- [x] B-10 `TestMcpRemoveCliCoverage::test_mcp_remove_native_success_and_fallback` (765-772) + `test_mcp_remove_idempotent_absent` (790-791 `remove_entry→(doc, False)`) + `test_mcp_remove_dry_run_no_mutation` (794-797) + `TestMcpRemoveCliFailure::test_mcp_remove_error_paths_return_1` (parametrized ×3; 801-804 unreadable config / backup / write). <!-- sdd-owner: implementation -->
- [x] B-11 `TestInitMoveExistingCoverage::test_move_existing_no_candidates_dry_run` (957->965, 971 skips collision check, dry-run "No supported files to move.") + `test_move_existing_prompt_eof_aborts_but_creates_toml` (1000-1001 `isatty→True` + `input` EOFError → still writes TOML + raw/). <!-- sdd-owner: implementation -->
- [x] B-12 Verify the `import tomli`→`except ImportError` fallback arcs (cli.py 435-439) resolved in-process on the first full-batch scan; add a `builtins.__import__`-blocker test ONLY if the arc shows missed on the local interpreter. <!-- sdd-owner: implementation -->
- [x] B-13 Measure: cli.py row MUST read 100.00 (zero missed, zero pragma tokens — scan `#pragma: no cover`/`# pragma: no cover`); full suite green. The 100.00 row MUST include the guard region — confirm unit A-1/A-2's runpy test landed and measures covered before calling B done. Record row; commit: `test(cli): drive cli.py to 100.00% line coverage`. Stop B here — do not add tests beyond the target. <!-- sdd-owner: implementation -->

## 3. Unit C — scanner.py 100% (tests/test_scanner.py; 6 new test functions, §3.2)

- [x] C-1 `TestLinkDetection::test_is_link_reparse_point_and_oserror_branches` (parametrized; 78, 80, 83-84 `_is_link` tail: `FakePath` stub + `monkeypatch.setattr("os.name","nt")`; reparse-point lstat, lstat OSError, attrs=0; real-symlink leg already covered). <!-- sdd-owner: implementation -->
- [x] C-2 `TestCollectInitMoves::test_collect_init_moves_existing_raw_and_absent_raw` (parametrized ×2; 200, 204, 211->210 raw_dir exists-with-files vs absent; assert `(candidates, existing)` split). <!-- sdd-owner: implementation -->
- [x] C-3 `TestDiscoverFiles::test_default_extension_registry` (264->270 default `ext_set = set(SUPPORTED_FORMATS.keys())`; mixed tree, assert registry extensions found). <!-- sdd-owner: implementation -->
- [x] C-4 `TestMergeEntries::test_merge_dedups_by_remote_migration` (330-333 remote-based dedup pairs legacy `remote` entry) + `test_merge_skips_malformed_entry_without_dedup` (335->327 `except Exception: continue`). <!-- sdd-owner: implementation -->
- [x] C-5 `TestCopyFiles::test_files_identical_oserror_treated_as_different` (429-430 monkeypatch `scanner.filecmp.cmp` → OSError → treated as differing). <!-- sdd-owner: implementation -->
- [x] C-6 Measure: scanner.py row MUST read 100.00; suite green. Record; commit: `test(scanner): drive scanner.py to 100.00% line coverage`. Stop C. <!-- sdd-owner: implementation -->

## 4. Unit D — prepare.py 100% (tests/test_prepare.py; ~22 new/extended, §3.3)

- [x] D-1 `TestPrepareParity` — `test_raw_values_empty_file_returns_empty` (177-178 `([], [])`, StopIteration), `test_parity_unreadable_csv_reports_cannot_read` (181-182, 205), `test_parity_row_count_mismatch_returns_false` (215-219), `test_parity_column_count_mismatch_returns_false` (222-226), `test_parity_header_divergence_returns_false` (229-233), `test_parity_ragged_row_handled` (241->240 soft check, no crash). <!-- sdd-owner: implementation -->
- [x] D-2 `TestPrepareConversion` — `test_parity_failure_falls_back_to_csv` (299 `return None`; assert "conversion failed — staging original" log, rc 0; extend existing conversion-failure test), `test_oversized_shard_warns` (317; monkeypatch `config.PARQUET_SHARD_WARNING_MB` tiny via `restore_tool_config`; assert ⚠ shard line in capsys), `test_opt_out_csv_staged_at_remote` (822 opt-out `.csv` staged at remote path; extend `test_converted_parquet_mirrors_remote_layout` with absolute-path assert for 795). <!-- sdd-owner: implementation -->
- [x] D-3 `TestAssertCrossFileSchema` — `test_skip_cross_file_schema_short_circuits` (355-356), `test_xlsx_sheet_keys_match_grouping` (384->383), `test_no_detected_splits_returns_clean` (396), `test_split_membership_break` (401->400; reconcile — if still missed add a 3-file split with one file outside any split), `test_no_split_files_returns_clean` (407), `test_unreadable_schema_reports_error` (421-423 monkeypatch `pq.read_schema` → raise). <!-- sdd-owner: implementation -->
- [x] D-4 `TestCheckLargeValues` — `test_unreadable_parquet_skips_silently` (471-472 `pq.read_table` raising), `test_warns_when_first_row_value_exceeds_threshold` (485, 488-494 null-string skip + >max_bytes warning), `test_large_value_warnings_surfaced_in_prepare` (786-790 in `prepare` output). <!-- sdd-owner: implementation -->
- [x] D-5 `TestPrepareCardLicense` — `test_card_float64_vs_parquet_integral_flagged` (536->527 dtype mismatch branch), `test_card_dtype_check_unreadable_parquet` (543-544). <!-- sdd-owner: implementation -->
- [x] D-6 `TestPrepareOverwriteMatrix` (parametrized) — `test_overwrite_detects_xlsx_multisheet_and_alt_layout`, `test_overwrite_detects_single_sheet_xlsx_candidate`, `test_overwrite_detects_passthrough_and_codebooks_dir` (615-616, 622->621, 627, 631, 639, 649 artifact-shape branches; assert rc 1 + refusal list contents). <!-- sdd-owner: implementation -->
- [x] D-7 `TestPrepareCaseFoldCollision::test_case_fold_collision_aborts` (734-736 cfg `_validate_case_fold_collisions` errors → rc 1 before writes). <!-- sdd-owner: implementation -->
- [x] D-8 `TestPrepareRecursiveStaging::test_xlsx_single_underscore_not_re_staged` (813->816 step-7 xlsx `is_converted` single-underscore arc). <!-- sdd-owner: implementation -->
- [x] D-9 Extend `TestPrepareOffline::test_full_run_produces_artifacts_offline` — assert the manifest file content parses (887-889 `MANIFEST_NAME.json_bytes()`) AND fold in the win32 reconfigure cover: `monkeypatch.setattr("sys.platform","win32")` to execute the `if sys.platform == "win32"` reconfigure body (691) — REQUIRED for the ubuntu CI 100% row (the pinned dev-Windows baseline shows it covered; the CI gate will not). <!-- sdd-owner: implementation -->
- [x] D-10 Measure: prepare.py row MUST read 100.00; suite green. Record; commit: `test(prepare): drive prepare.py to 100.00% line coverage`. Stop D. <!-- sdd-owner: implementation -->

## 5. Unit E — publish.py 100% (tests/test_publish.py; ~16 new/extended, §3.4)

- [x] E-1 `TestRemoteFailClosed::test_ensure_repo_raises_on_unrelated_error` (135 fake api `create_repo` raises `RuntimeError` → re-raise fail-closed). + `TestHfUpload::test_hf_upload_success_and_failure` (parametrized ×2; 159-173 fake api upload_file raises/returns). <!-- sdd-owner: implementation -->
- [x] E-2 `TestRepoDiffSummary` — `test_diff_truncates_long_added_list` (303 "… and N more"), `test_diff_truncates_long_modified_list` (310), `test_diff_lists_manifest_missing_lines` (313-314 `required_missing()` non-empty). <!-- sdd-owner: implementation -->
- [x] E-3 `TestOverwriteProtection::test_interactive_skip_variants` (parametrized ×4; 367-376 `isatty→True` + `builtins.input` "n"/"no"/EOFError/KeyboardInterrupt → skip). <!-- sdd-owner: implementation -->
- [x] E-4 `TestSplitReportPrinting` — `test_print_split_report_ignores_foreign_object` (397), `test_print_split_report_empty_splits` (400), `test_print_split_report_truncates_long_split` (408), `test_print_split_report_unclassified_count` (411), `test_print_split_report_layout_warnings` (421). <!-- sdd-owner: implementation -->
- [x] E-5 `TestSplitMappingValidation::test_print_mapping_validation_warns` (431->exit conflicting-remotes warnings block). <!-- sdd-owner: implementation -->
- [x] E-6 `TestCopyPackageProtection` — `test_copy_package_local_csv_fallback` (553->542..567->570 mirror-lacks-CSV fallback with `keep_csv` opt-out entry), `test_copy_package_readme_license_skip_and_absent` (parametrized; `protected={"readme.md","license"}`, build without README/LICENSE), `test_copy_package_non_dir_source` (537 `planned_remotes` non-dir). <!-- sdd-owner: implementation -->
- [x] E-7 `TestAutoPrepare::test_autoprepare_failure_returns_rc` (695 monkeypatch `prepare` → rc 1; `_needs_prepare` forced True) + `TestBatchStaging::test_publish_reports_not_found_sources` (830 real missing local file → rc 0 + "NOT FOUND" in capsys). <!-- sdd-owner: implementation -->
- [x] E-8 `TestHfPublish` — `test_protected_out_populated` (804 `protected_out=set()` side-channel write) + `test_post_upload_inspection_failure_warns_and_skips_report` (855-858 tracking fake raises only on 2nd `list_repo_files`; rc 0 + warning) + fold win32 reconfigure cover (`monkeypatch.setattr("sys.platform","win32")`, 685) into `test_full_publish_upload_folder_called_once` — REQUIRED for the ubuntu CI 100% row. <!-- sdd-owner: implementation -->
- [x] E-9 Measure: publish.py row MUST read 100.00; suite green. Record; commit: `test(publish): drive publish.py to 100.00% line coverage`. Stop E. <!-- sdd-owner: implementation -->

## 6. Unit F — profile.py ≥90 (tests/test_profile.py; ~14 new/extended, §4.1)

Local targets: ≥91 (hard min 90.3 with written justification); CI (ubuntu 3.13) is the arbiter.

- [x] F-1 `TestProfileMultisheetPrf05::test_profile_output_for_rel_multisuffix` (76 `a.tar.csv` → `.tar.metadata.yaml`) + extend `TestProfileWritesMetadataYaml::test_tsv_writes_metadata_yaml` with TSV delimiter assert (158-159). <!-- sdd-owner: implementation -->
- [x] F-2 `TestProfileNonStreamedFormats` — `test_profile_parquet_writes_metadata` + `test_profile_jsonl_writes_metadata` (166-169 non-streamed `_read_file` branch; assert rows + delimiter "") + `test_batch_reads_parquet_and_xlsx` (488-490 batch cfg). <!-- sdd-owner: implementation -->
- [x] F-3 Extend `TestProfileMissingFields` for the missing-fields gap print arc (196->198 empty documentation fields). + `TestProfileWritesMetadataYaml::test_stream_columns_truncates_long_rows` (528->527 ragged longer row). <!-- sdd-owner: implementation -->
- [x] F-4 `TestProfileBatchSkipPaths` (parametrized) — `test_batch_skips_dir_missing_unsupported_and_empty` (250-251, 254-255, 259-260, 265 skip paths + 303 `not expanded` fast return; assert the three ⚠ lines), `test_batch_xlsx_read_error_skips` (280-282 monkeypatch `_read_xlsx_sheets` → raise), `test_batch_profile_read_error_skips` (330-332 monkeypatch `_read_dataset_for_profile` → raise). <!-- sdd-owner: implementation -->
- [x] F-5 `TestProfileXlsxEdges` — `test_xlsx_zero_sheets_writes_empty_metadata` (284-287 zero-sheet workbook → 354-377 empty-cache stub write), `test_sheet_out_path_missing_skip_guards` (325, 387, 411, 417 `out_path is None` guards). <!-- sdd-owner: implementation -->
- [x] F-6 `TestProfileBatchPrf05::test_collision_names_sources_outside_base` (445-446, 451-452 collision `rel_out`/`base_rel` non-relative fallback + stderr prints). <!-- sdd-owner: implementation -->
- [x] F-7 Measure: profile.py row ≥91 (min 90.3 justified); suite green. Record; commit: `test(profile): cover batch skips, non-streamed formats, xlsx edges`. Stop F. <!-- sdd-owner: implementation -->

## 7. Unit G — mcp_registration.py ≥90 (tests/test_mcp_registration.py; ~11 new, §4.2)

- [x] G-1 `TestResolveConfigPath::test_unknown_agent_raises_both_scopes` (84, 93 user+project) + `TestBuildEntry::test_unknown_agent_raises` (175). <!-- sdd-owner: implementation -->
- [x] G-2 `TestReadConfigMalformed::test_rejects_non_object_json_and_non_table_toml` (124, 135 json `[1,2]` / scalar-root toml). <!-- sdd-owner: implementation -->
- [x] G-3 `TestIdempotency` — `test_normalize_codex_command_non_string_returns_empty` (183), `test_entries_equal_per_agent_matrix` (parametrized; 192, 195, 200-206 codex cwd/env mismatch + gemini + opencode branches), `test_atomic_write_toml_roundtrip` (385-386 tomli-w dump, read back via tomllib). <!-- sdd-owner: implementation -->
- [x] G-4 `TestMerge::test_gemini_idempotent_no_change` (259) + `TestMerge::test_merge_unknown_agent_raises` (263). <!-- sdd-owner: implementation -->
- [x] G-5 `TestRemove::test_remove_codex_pops_empty_table` (284, 295) + `test_remove_gemini_pops_empty_table` (302, 306, 310 last-server pop → `(doc, True)` + parent table removed). <!-- sdd-owner: implementation -->
- [x] G-6 `TestDelegation::test_delegate_add_success_and_failure_variants` (parametrized; 408, 421, 424 fake `shutil.which` + fake `subprocess.run` rc 0 / rc 1 / TimeoutExpired) + `test_delegate_remove_variants` (parametrized ×4; 438-447 absent exe / rc 0 / rc != 0 / timeout / bare exception). <!-- sdd-owner: implementation -->
- [x] G-7 `TestCwdContainment::test_validate_cwd_project_scope_and_resolve_failure` (519-520 project scope + `Path.resolve` OSError → False). <!-- sdd-owner: implementation -->
- [x] G-8 Measure: mcp_registration.py row ≥91 (min 90.3 justified); suite green. Record; commit: `test(mcp-registration): cover malformed configs, delegation, pop-empty, toml write`. Stop G. <!-- sdd-owner: implementation -->

## 8. Unit H — verification.py ≥90 (tests/test_splits.py + tests/test_prepare.py leg; ~5 new, §4.3)

- [x] H-1 `TestVerifyLoadDataset::test_split_row_count_unknown_when_len_raises` (102-103, 107 `len(ds[name])` success + `except → -1`; existing `patch.dict(sys.modules)` harness, one container raising `TypeError` on `len`). <!-- sdd-owner: implementation -->
- [x] H-2 `TestPrintVerificationReport` — `test_print_skipped_report` (142-143 SKIPPED + warnings), `test_print_failed_report_status` (146 FAILED status), errors-list print (149-150, folded), `test_print_expected_and_warning_lines` (pins pass-shape output). <!-- sdd-owner: implementation -->
- [x] H-3 `TestPrepareVerify` — extend `test_prepare_verify_skipped_when_datasets_absent` (test_prepare.py leg): real small dataset + parquet; `patch.dict(sys.modules)` datasets-absent → SKIPPED; datasets-present fake → PASSED/FAILED shapes (both functions end-to-end, `prepare(verify=True)`). <!-- sdd-owner: implementation -->
- [x] H-4 Measure: verification.py row ≥91 (min 90.3 justified); suite green. Record; commit: `test(verification): cover report printing and split-row-count edge`. Stop H. <!-- sdd-owner: implementation -->

## 9. Unit I — gate script + ci.yml step (COV-06 enforcement; script shape, design §5.1)

- [x] I-1 Create `scripts/check_core_coverage.sh` (NEW; apply-ready text in design §5.1): `#!/usr/bin/env bash`, `set -euo pipefail`, loop `for f in cli scanner prepare publish; do uv run coverage report --include="src/sofer/${f}.py" --fail-under=100 -m; done`. Non-Python — ruff/mypy ignore it; `pythonpath = ["scripts"]` unaffected. <!-- sdd-owner: implementation -->
- [x] I-2 Add ONE step to the `ci.yml` coverage job, after the existing `Report coverage with missing lines (the gate)` step (line ~77-78): `- name: Gate core module coverage (COV-06)` / `run: bash scripts/check_core_coverage.sh` (same indentation as siblings; exact YAML in design §5.1). `release.yml` NOT mirrored (rejected under COV-03 bounded-machinery). <!-- sdd-owner: implementation -->
- [x] I-3 Verify locally (all four rows at 100.00 from units B–E): `bash scripts/check_core_coverage.sh` exits 0 and prints four 100.00 rows; record the four gate rows. <!-- sdd-owner: implementation -->

## 10. Unit J — CI-01 S2 carve-out + canonical `ci` clause (design §5.2)

- [x] J-1 Narrow `tests/test_ci_workflows.py::test_coverage_gate_is_config_driven_without_cli_floor` (line 202): re-scope the docstring to "the TOTAL gate only", explicitly naming `scripts/check_core_coverage.sh` + `test_coverage_job_gates_core_modules_at_100` as the COV-06 documented exception; assertions unchanged except one ADDED assertion pinning that the TOTAL report step stays the flag-free `uv run coverage report -m`. <!-- sdd-owner: implementation -->
- [x] J-2 Add `tests/test_ci_workflows.py::test_coverage_job_gates_core_modules_at_100` (COV-06 gate-shape scan): parse `scripts/check_core_coverage.sh` + the ci.yml coverage job; (a) each of the four `src/sofer/<file>.py` paths paired with `--fail-under=100 -m` and the script referenced by a job step; (b) no `--fail-under` value other than 100 anywhere in script/workflows; (c) config-key spelling `fail_under` (underscore) appears in neither. <!-- sdd-owner: implementation -->
- [x] J-3 Add `tests/test_ci_workflows.py::test_agents_md_declares_core_100_mandate` (COV-06 AGENTS scan): AGENTS.md rule 14 text names the four modules, declares 100.00%, forbids `# pragma: no cover`. <!-- sdd-owner: implementation -->
- [x] J-4 Append the one-line carve-out to CI-01 in `openspec/specs/ci/spec.md` (recorded follow-up per proposal DP5; exact clause text in design §5.2): COV-06 is the documented additive exception — per-file scoped `--fail-under=100` gates exist only as the four invocations in `scripts/check_core_coverage.sh` referenced by the `ci.yml` coverage job, and SHALL NOT weaken or re-declare the config-owned TOTAL floor. Commit unit J+I+K+L (design §6.1 G): `ci: gate CLI-core modules at 100% (COV-06); AGENTS rule 14; static contract guard`. <!-- sdd-owner: implementation -->

## 11. Unit K — AGENTS.md rule 14 (design §5.3; exact text)

- [x] K-1 Insert rule 14 after rule 13 in `AGENTS.md` using the exact apply-ready text from design §5.3 (100.00% mandate for the four modules under `uv run coverage report -m`; `# pragma: no cover` FORBIDDEN; TOTAL gate stays config-owned CI-01; the `cli.py` `__main__` guard is exercised in-process — `runpy.run_module("sofer.cli", run_name="__main__")` — as part of the 100% row, and NO `src/sofer/` edit is justified under this rule; mandate covers exactly those four modules). No README/README_ES change (rule 13 untouched). <!-- sdd-owner: implementation -->

## 12. Unit L — tests/test_coverage_contract.py (NEW ~120 lines; design §5.4)

- [x] L-1 `test_core_modules_contain_no_pragma_tokens` — full-text scan of `cli.py`/`scanner.py`/`prepare.py`/`publish.py` for `pragma: no cover` (catches `# pragma:` and `#pragma:`): zero matches per file. (Maps COV-03/COV-06 pragma scenarios.) <!-- sdd-owner: implementation -->
- [x] L-2 Guard-execution assertion (already covered by unit A-1) — the planned `test_cli_has_no_main_guard` guard-absent static scan is REPLACED by the in-process guard-EXECUTION test `test_cli_main_guard_executed_via_runpy` (unit A-1; design §3.1 row 1575); the guard is kept, so no absence scan applies. Confirm A-1's test is the mapped assertion for spec COV-06 scenario (d). <!-- sdd-owner: implementation -->
- [x] L-3 Floor guard (skip-if-absent): `@pytest.mark.skipif(not (_REPO_ROOT / ".coverage").exists(), ...)`; import `coverage.CoverageData` INSIDE the function; read ONLY via the read API (`read()`, `measured_files()`, per-file `line_counts()`) — assert the three floor module paths ≥90 each and TOTAL ≥90; treat an empty/partial DB as absent → skip. Helper `_REPO_ROOT` = repo root. (COV-01 regression pin; CI measurement is the arbiter.) <!-- sdd-owner: implementation -->
- [x] L-4 `test_gate_machinery_bounded` (optional, low-cost): `pyproject.toml` text scan — `fail_under = 90` present, no extra coverage keys, no XML/Codecov references in workflow text (COV-03 scan assist). <!-- sdd-owner: implementation -->
- [x] L-5 Verify the guard skips naturally on a clean checkout (no `.coverage`) and the suite passes. Suite green; run `uv run pytest tests/ -q` and record the new suite count. <!-- sdd-owner: implementation -->

## 13. Unit V — verify evidence (apply-owned verification; COV-01/02/03/05/06)

- [x] V-1 Reproduce the full measurement: `uv run coverage run -m pytest -q && uv run coverage report -m` — capture and record rows: `cli.py`/`scanner.py`/`prepare.py`/`publish.py` each **100.00**; `profile.py`/`mcp_registration.py`/`verification.py` each **≥90**; **TOTAL ≥90** (expected ≈91-92); process rc **0**. <!-- sdd-owner: implementation -->
- [x] V-2 Run `bash scripts/check_core_coverage.sh` — the four per-file gate rows each 100.00, rc 0 (the rows the CI coverage job will reproduce). <!-- sdd-owner: implementation -->
- [x] V-3 Static evidence scans: `git diff origin/dev --stat` shows **ZERO** `src/sofer/` paths (test-only change, Resolution A); zero `# pragma: no cover` tokens in the four core modules (full-text); `__main__` guard present and executed under the tracer (`tests/test_cli.py::test_cli_main_guard_executed_via_runpy` green); AGENTS.md rule 14 present; `pyproject.toml` absent from the diff; no `pytest-cov`/XML/Codecov references. <!-- sdd-owner: implementation -->
- [x] V-4 Quality gates: `uv run pytest tests/ -q` green with suite count ≥ baseline (1567 passed / 6 skipped) + new tests; `uv run ruff check src/ tests/ scripts/` clean; `uv run mypy src/` clean; `git diff --check` clean. <!-- sdd-owner: implementation -->
- [x] V-5 Assertion-quality audit (COV-05): every new test asserts an observable outcome; zero measured-percentage assertions in the test diff. <!-- sdd-owner: implementation -->
- [x] V-6 Close the unit with a docs commit if not already landed: `docs(sdd): ci CI-01 carve-out note for COV-06 gates; tasks + verify report` (J-4's `specs/ci` clause + this tasks/verify artifact set). <!-- sdd-owner: implementation -->

## 14. Parent-owned lifecycle gates (after implementation work)

- [ ] Ask-on-risk gate: when the measured `git diff origin/dev --stat` crosses 1500 changed lines, PAUSE and request the user decision — chain vs size-exception; never invent a chain strategy or an exception. Record the decision in the verify report. <!-- sdd-owner: parent -->
- [ ] Post-apply bounded review of the full PR diff (review lens): assertion quality per COV-05, no pragma relapse, **zero `src/sofer/` paths** (Resolution A), gate-shape correctness, floor margins recorded. <!-- sdd-owner: parent -->
- [ ] Delivery: open the single PR against `dev` from `test/raise-coverage-90`, assign emiliodavola, fill the PR template (.github/PULL_REQUEST_TEMPLATE.md) with the real verification output from V — coverage rows, gate rows, suite count, ruff/mypy. <!-- sdd-owner: parent -->