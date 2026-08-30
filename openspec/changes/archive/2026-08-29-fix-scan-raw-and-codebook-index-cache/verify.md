```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:ee8250fb76e094b34b471f13a73dbbe51d1ae142e9df59d7c0d31ec20f0a0a8e
verdict: pass
blockers: 0
critical_findings: 0
requirements: 2/2
scenarios: 12/12
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:8578a96c94714cfe88a9de8f5d899f4faa267ee8adcd3acfb67c718c681b5d9d
build_command: uv run ruff check src/ && uv run mypy src/
build_exit_code: 0
build_output_hash: sha256:125f72c90b0bc64e4e537ef2494a27f1da1f839710b532af94ecdbd71c6354dd
```

## Verification Report

**Change**: fix-scan-raw-and-codebook-index-cache
**Version**: N/A
**Mode**: Standard

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 14 |
| Tasks complete | 14 |
| Tasks incomplete | 0 |

All 14 tasks across 4 phases marked `[x]` in `tasks.md`:
- P1 Foundation 1.1–1.4 (scanner helpers + codebook one-liner)
- P2 Core 2.1–2.2 (CLI MOVE-then-Copy + parser help)
- P3 Tests 3.1–3.3 (codebook 6 asserts, scanner unit, CLI e2e)
- P4 Docs 4.1–4.3 (`.gitignore` + README/config docs + ruff/mypy green)

### Build & Tests Execution

**Build**: ✅ Passed
```text
$ uv run ruff check src/
All checks passed!

$ uv run mypy src/
Success: no issues found in 27 source files
```

**Tests**: ✅ 1022 passed / 2 skipped / 0 failed
```text
$ uv run pytest tests/ -q
........................................................................ [  7%]
........................................................................ [ 14%]
........................................................................ [ 21%]
...............................s.........................s.............. [ 28%]
........................................................................ [ 35%]
........................................................................ [ 42%]
........................................................................ [ 49%]
........................................................................ [ 56%]
........................................................................ [ 63%]
........................................................................ [ 70%]
........................................................................ [ 77%]
........................................................................ [ 84%]
........................................................................ [ 91%]
........................................................................ [ 98%]
................                                                         [100%]
1022 passed, 2 skipped, 13 warnings in 14.70s
```

Targeted suites (runtime evidence for spec scenarios):
```text
$ uv run pytest tests/test_scanner.py -q -v
71 passed in 1.00s

$ uv run pytest tests/test_cli.py -k scan -v
13 passed (TestScanParser 8 + TestScanMoveCLI 5)

$ uv run pytest tests/test_codebook.py -v
73 passed

$ uv run pytest tests/test_mcp_server.py -v
74 passed, 2 skipped
```

**Coverage**: ➖ Not available (no coverage threshold configured)

### Spec Compliance Matrix

#### SCN-07 — Source Layout and Move-to-Raw (8 scenarios)

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| SCN-07 | Move preserves tree and removes source | `test_scanner.py::TestScanMoveScenarios::test_move_preserves_tree_and_removes_source` + `TestMoveToRaw::test_preserves_tree_and_removes_source` + `test_cli.py::TestScanMoveCLI::test_e2e_move_tree` | ✅ COMPLIANT |
| SCN-07 | Supported extensions only | `test_scanner.py::TestScanMoveScenarios::test_supported_extensions_only` + `TestMoveToRaw::test_five_exts_vs_txt` + `TestScanMoveCLI::test_five_exts_vs_txt` | ✅ COMPLIANT |
| SCN-07 | Excluded dirs never moved | `test_scanner.py::TestScanMoveScenarios::test_excluded_dirs_never_moved` + `TestMoveToRaw::test_exclusions_and_txt_not_moved_via_discover` | ✅ COMPLIANT |
| SCN-07 | Dry-run previews without mutation | `test_scanner.py::TestScanMoveScenarios::test_dry_run_previews_without_mutation` + `TestScanMoveCLI::test_dry_run_no_fs_or_toml` + `TestIntegration::test_dry_run_no_disk_changes` | ✅ COMPLIANT |
| SCN-07 | Collision fails before any move | `test_scanner.py::TestScanMoveScenarios::test_collision_fails_before_any_move` + `TestCheckRawCollisions::test_collision_names_both` + `TestScanMoveCLI::test_collision_fails_atomically` | ✅ COMPLIANT |
| SCN-07 | Interactive abort is atomic | `test_scanner.py::TestScanMoveScenarios::test_interactive_abort_is_atomic` + `TestScanMoveCLI::test_prompt_n_aborts_atomically` | ✅ COMPLIANT |
| SCN-07 | Idempotency when already under raw | `test_scanner.py::TestScanMoveScenarios::test_idempotency_when_already_under_raw` + `TestIntegration::test_idempotent_scan` | ✅ COMPLIANT |
| SCN-07 | Docs show diagram | `test_scanner.py::TestSourceLayoutCopyOnly::test_docs_show_diagram` + manual `README.md`/`docs/configuration.md` inspection (`raw/DPTO.csv → cache/DPTO.csv → build/`) | ✅ COMPLIANT |

#### CB-R04 — Root Index (4 scenarios)

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| CB-R04 | Standalone batch writes to cache | `test_codebook.py::TestGenerateAll::test_generates_for_all_toml_entries` + `TestCodebookPlaceholderValidation::test_valid_toml_generates_codebook` (asserts `cache/codebook.md` exists, `base_dir/codebook.md` absent) | ✅ COMPLIANT |
| CB-R04 | Prepare mode writes to build | `test_codebook.py::TestGenerateAllOutputDir::test_output_dir_receives_codebooks_and_root_index` | ✅ COMPLIANT |
| CB-R04 | Nested subdirectories preserved in links | `test_codebook.py::TestGenerateAll::test_root_index_links_for_nested_subdirs` | ✅ COMPLIANT |
| CB-R04 | Index links are relative paths | `test_codebook.py::TestGenerateAll::test_root_index_has_correct_links` + `TestGenerateAllOutputDir::test_output_dir_root_index_links_are_build_relative` | ✅ COMPLIANT |

**Compliance summary**: 12/12 scenarios compliant

### Correctness (Static Evidence)

| Requirement | Status | Notes |
|-------------|--------|-------|
| SCN-07 raw/ mkdir + MOVE preserving tree | ✅ Implemented | `scanner.py:252-288` `move_to_raw(dest=raw_dir/rel, shutil.move, mkdir parents)` no flatten; `cli.py:318-365` P1 discover `EXCLUSIONS\|{RAW_DIR,OUTPUT_DIR}`, `raw_dir.mkdir` skip dry-run, `check_raw_collisions` atomic, dry-run prints `-> raw/<rel>`, force/prompt gate |
| SCN-07 5 extensions + EXCLUSIONS pruning | ✅ Implemented | `SUPPORTED_FORMATS` keys drive `discover_files`; `EXCLUSIONS={.git,__pycache__,.venv,node_modules,dist,build}` pruned; `f.txt`/`.venv` never candidates verified by tests |
| SCN-07 collision atomicity | ✅ Implemented | `check_raw_collisions` raises ValueError naming dest+src; `_cmd_scan` exits 1 before any `shutil.move`, TOML untouched (dry-run/collision/N abort paths verified) |
| SCN-07 copy raw→cache flatten | ✅ Implemented | P2 `discover_files(EXCLUSIONS\|{OUTPUT_DIR})` → `check_flatten_collisions` → `merge_entries` → `copy_files(flatten_first_level, shutil.copy2)` → `write_toml` |
| CB-R04 codebook index at cache | ✅ Implemented | `codebook.py:439-441` `if output_dir is None: write_root=data_dir; root_path=write_root/codebook.md` (was `base_dir/codebook.md`); `else: write_root=out.resolve()` — per-file `codebooks_dir=write_root/CODEBOOKS_DIR` colocated; links `relative_to(write_root)` |
| .gitignore + docs | ✅ Implemented | `.gitignore:7` `cache/` added; `README.md:175-193` + `README_ES.md` + `docs/configuration.md:50-81` document `raw/→cache/→build` diagram |
| CLI help accuracy | ✅ Implemented | `cli.py:952-1015` scan help documents MOVE tree, dry-run/force, EXCLUSIONS; init help documents pipeline |

### Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| Preserve tree (`raw/<relative_to(base_dir)>`) not flatten | ✅ Yes | `move_to_raw` preserves full tree; flatten only in P2 copy via `flatten_first_level` |
| Pre-flight collision check before any move | ✅ Yes | `_cmd_scan` calls `check_raw_collisions` before `move_to_raw`; error names both paths, exit 1 |
| Two-phase discovery (P1 excl raw+cache, P2 excl cache) | ✅ Yes | `exclude_move=EXCLUSIONS\|{RAW_DIR,OUTPUT_DIR}`, `exclude_cache=EXCLUSIONS\|{OUTPUT_DIR}`; after moves P2 re-discovers from `raw/` |
| Single prompt gate for MOVE, skip second when moved | ✅ Yes | P1 prompt when candidates present; P2 prompt only when `not candidates` and not dry-run/force — atomic abort |
| Codebook one-liner to `write_root` | ✅ Yes | No dual-write; `root_path=write_root/codebook.md` in both branches |
| File changes per design.md | ✅ Yes | `scanner.py`, `cli.py`, `codebook.py`, `tests/test_codebook.py`, `tests/test_scanner.py`, `tests/test_cli.py`, `README*.md`, `docs/configuration.md`, `.gitignore` all modified as specified |
| No flatten mangling / no scaffold-only | ✅ Yes | Design 1A/1B alternatives correctly rejected; implementation matches chosen MOVE-then-Copy + one-liner |

### Issues Found

**CRITICAL**: None

**WARNING**: None
- Note: `src/sofer/cli.py:_cmd_scan` allows `dry_run + candidates` to return early after P1 preview (no P2 copy preview in same run). This correctly enforces `--dry-run` atomicity (`no FS/TOML mutation`) and is covered by tests asserting no `cache/` on dry-run with loose files. Not a deviation — intentional per spec "preview only, no mutation". If product wants dry-run to also preview P2 flattened copies in same run, file a follow-up enhancement; not a verifier blocker.

**SUGGESTION**:
- Consider adding explicit unit test asserting `codebook.py` docstring reflects `cache/codebook.md` standalone vs `build/codebook.md` prepare locations (currently covered indirectly via 6 codebook tests + integration).
- `README_ES.md` pipeline section diverged slightly before fix; now synced — ensure future doc changes land in both READMEs per `AGENTS.md` §13 (already done in this PR).

### Verdict

**PASS** — 14/14 tasks complete, 12/12 scenarios compliant with passing covering tests, `uv run pytest tests/ -q` 1022 passed, `ruff` + `mypy` green, file locations verified (MOVE preserves `relative_to` tree, index at `cache/codebook.md` not root). Ready for archive.

