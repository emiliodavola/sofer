```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:dffd9862f70631202e87f8118df647c0b82d0388cd1094cf069ed95f53114303
verdict: pass
blockers: 0
critical_findings: 0
requirements: 9/9
scenarios: 52/52
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:a6f2687758c59116eac9a653bc5a27a057fd98c8f11cddb6a0516a7b8397da50
build_command: uv run mypy src/ && uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && git diff --check
build_exit_code: 0
build_output_hash: sha256:9574935ed411d5a6430d6fffe93763022edca4a8171867320f9663c9b55ffcaa
```

## Verification Report

**Change**: fix-dataset-identity-context
**Version**: N/A (delta specs, not yet merged into `openspec/specs/`)
**Mode**: Standard (strict_tdd false — no Strict TDD module loaded)

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 22 (1.1–1.6, 2.1–2.8, 3.1–3.5, 4.1–4.3, 5.1–5.2) |
| Tasks complete | 22 |
| Tasks incomplete | 0 |

All tasks marked `[x]` in `tasks.md`; `apply-progress.md` documents 4 slices, all complete. Full verification run (proposal + specs + design + tasks all present).

### Build & Tests Execution
**Build**: ✅ Passed (exit 0 on every gate)

```text
uv run mypy src/                              -> Success: no issues found in 30 source files
uv run ruff check src/ tests/                 -> All checks passed!
uv run ruff format --check src/ tests/        -> 60 files already formatted
git diff --check                              -> clean (exit 0)
```

**Tests**: ✅ 1332 passed / 0 failed / 2 skipped (exit 0)

```text
uv run pytest tests/ -q  ->  1332 passed, 2 skipped, 13 warnings in 28.38s
```

The actual count **matches** the claimed re-baseline exactly (1332 passed, 2 skipped). Dev baseline was 1269; branch is 1332 = **+63 net** (slice deltas: +49 → +7 → +5 → +2, per apply-progress; arithmetic confirmed: 1269+49+7+5+2 = 1332).

**Coverage**: ➖ Not available (no coverage threshold configured; not part of the gates).

### Spec Compliance Matrix

**mcp-server (5 requirements, 25 scenarios)**

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| INIT-05 | Valid identity accepted | `test_execution_context.py::TestValidateIdentity::test_valid_pair_returns_no_errors`; `test_mcp_server.py::TestInitCreate::test_creates_toml_and_raw` (user=testuser, ok:true, repo_id testuser/my-ds) | ✅ COMPLIANT |
| INIT-05 | Missing or blank identity refused before write | `test_execution_context.py::test_missing_or_blank_name_refused` (None/""/" "), `test_missing_or_blank_user_refused`; `test_mcp_server.py::test_missing_user_refused_before_write` (no TOML, no raw/) | ✅ COMPLIANT |
| INIT-05 | Placeholder user banned pre-write | `test_execution_context.py::test_placeholder_user_refused` (YOUR_USER/Your_User/your-username); `test_mcp_server.py::test_placeholder_user_refused_before_write`; `test_cli.py::test_init_placeholder_user_rejected` | ✅ COMPLIANT |
| INIT-05 | Unsafe or injection-shaped name rejected | `test_execution_context.py::test_separator_refused` (a/b, a\b), `test_drive_path_refused`, `test_exact_dot_components_refused`, `test_nested_traversal_refused`, `test_quote_refused`, `test_control_char_refused`; `test_mcp_server.py::TestInitTraversal` (4), `test_unsafe_name_*` (4); `test_cli.py::test_init_unsafe_name_rejected` | ✅ COMPLIANT |
| INIT-05 | Non-conforming user rejected | `test_execution_context.py::test_user_regex_rejects_non_conforming` (user.name, user name) | ✅ COMPLIANT |
| INIT-02 | cwd omitted with live CWD strictly inside root | `test_execution_context.py::test_strict_descendant_inside_returns_live`; `test_mcp_server.py::test_auto_cwd_inside_root`; `test_mcp_process.py::TestNestedCwd::test_init_writes_under_nested_cwd` | ✅ COMPLIANT |
| INIT-02 | cwd omitted with live CWD equal to root fails closed | `test_execution_context.py::test_live_equal_root_fails_closed`; `test_mcp_process.py::TestParentRootIdentity` (a) | ✅ COMPLIANT |
| INIT-02 | cwd omitted with live CWD outside root fails closed | `test_execution_context.py::test_live_outside_root_fails_closed`, `test_error_message_names_cwd_with_guidance`; `test_mcp_server.py::test_cwd_none_fails_closed`, `test_auto_cwd_outside_fails_closed` | ✅ COMPLIANT |
| INIT-02 | cwd contained succeeds | `test_execution_context.py::test_explicit_cwd_relative_contained`, `test_explicit_cwd_absolute_contained`, `test_explicit_cwd_expanduser_tilde`, `test_explicit_cwd_equal_root_accepted`; `test_mcp_server.py::test_cwd_contained_succeeds` | ✅ COMPLIANT |
| INIT-02 | cwd outside rejected | `test_execution_context.py::test_explicit_cwd_escape_rejected`; `test_mcp_server.py::test_cwd_outside_rejected` (ToolError) | ✅ COMPLIANT |
| INIT-02 | traversal rejected | `test_execution_context.py::test_explicit_cwd_traversal_rejected`; `test_mcp_server.py::test_cwd_traversal_rejected` (ToolError) | ✅ COMPLIANT |
| INIT-02 | no global mutation | `test_mcp_server.py::test_no_global_mutation` (before/after `_get_root()` equality) | ✅ COMPLIANT |
| INIT-03 | stale-root anchored | `test_mcp_server.py::TestInitStaleRoot::test_stale_root_anchored` | ✅ COMPLIANT |
| INIT-03 | idempotent | `test_mcp_server.py::TestInitStaleRoot::test_idempotent_preserves_keep` | ✅ COMPLIANT |
| INIT-03 | cleanup not parent | `test_mcp_server.py::TestInitStaleRoot::test_cleanup_not_parent` | ✅ COMPLIANT |
| INIT-03 | canonical identity reported | `test_mcp_server.py::test_creates_toml_and_raw` (envelope absolute config_path/dataset_root); `test_execution_context.py::test_report_identity_absolute_strings`; `test_mcp_process.py::TestParentRootIdentity` (b) | ✅ COMPLIANT |
| MSP-R03 | Constrained schemas | `test_mcp_schema.py::TestToolCount::test_fourteen_tools`, `TestParamDescriptions::test_no_legacy_params`, `test_target_enum`, `test_run_checks_exists`, `test_every_param_has_description` | ✅ COMPLIANT |
| MSP-R03 | Annotations and output_schema typed | `test_mcp_schema.py::TestAnnotations::test_annotations_present`, `TestOutputSchema::test_output_schema_typed` | ✅ COMPLIANT |
| MSP-R03 | sofer_init cwd schema | `test_mcp_server.py::TestInitCwdSchema::test_sofer_init_cwd_schema`; `test_cwd_outside_via_mcp_schema_rejected` (C:/Windows → ToolError) | ✅ COMPLIANT |
| MSP-R03 | sofer_init identity fields in schema | `test_mcp_schema.py::TestOutputSchema::test_sofer_init_identity_fields_in_schema` (string props, NOT in required, required==["ok","exit_code","output"]) | ✅ COMPLIANT |
| MSP-R10 | Tool config resolves per dataset directory | `test_mcp_server.py::test_codebook_honors_tool_sofer_delimiter` (post-reload `[tool.sofer]` applied); `test_model.py::test_discovery_root_applies_at_or_below` | ✅ COMPLIANT |
| MSP-R10 | Discovery bounded at server root | `test_model.py::TestFromTomlDiscoveryRoot::test_discovery_root_blocks_above_root_override`; all 4 MCP `from_toml` sites pass `discovery_root=_get_root()` (source-verified L510/1235/1358/1423); `_bound_discovery` retired (no matches) | ✅ COMPLIANT |
| MSP-R10 | Relative output override anchors to config dir | `test_mcp_server.py::TestOutputAnchoringMspR10::test_relative_output_dir_anchors_to_config_dir` (proj/build not root/build); `test_cli.py::test_codebook_relative_output_anchors_to_input_parent` (data/out.md not cwd/out.md) | ✅ COMPLIANT |
| MSP-R10 | Codebook honors configured delimiter/encoding | `test_mcp_server.py::test_codebook_honors_tool_sofer_delimiter`, `test_codebook_all_honors_meta_delimiter` (cfg.csv_delimiter/csv_encoding from `[meta]`) | ✅ COMPLIANT |
| MSP-R10 | No silent default config name | `test_mcp_server.py::test_scan_requires_config` (config in required), `test_missing_required_arg_raises_schema_error` (no config → ToolError) | ✅ COMPLIANT |

**cli (1 requirement, 15 scenarios)**

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| CLI-R07 | init creates raw/ | `test_cli.py::TestInitRawFolder::test_init_creates_raw_dir` | ✅ COMPLIANT |
| CLI-R07 | Idempotent | `test_cli.py::TestInitRawFolder::test_init_idempotent` | ✅ COMPLIANT |
| CLI-R07 | Depth-1 only supported | `test_cli.py::TestInitRawFolder::test_move_existing_depth1_only_supported` | ✅ COMPLIANT |
| CLI-R07 | Collision guard | `test_cli.py::TestInitRawFolder::test_move_existing_collision_guard` | ✅ COMPLIANT |
| CLI-R07 | Dry-run preview | `test_cli.py::TestInitRawFolder::test_move_existing_dry_run_no_mutation` | ✅ COMPLIANT |
| CLI-R07 | Non-interactive guard | `test_cli.py::TestInitRawFolder::test_move_existing_non_interactive_guard` | ✅ COMPLIANT |
| CLI-R07 | Prompt N aborts | `test_cli.py::TestInitRawFolder::test_move_existing_prompt_n_aborts` | ✅ COMPLIANT |
| CLI-R07 | Template mentions raw/ | `test_cli.py::TestInitRawFolder::test_template_mentions_raw_no_stale_path` | ✅ COMPLIANT |
| CLI-R07 | Windows-safe placeholder | `test_cli.py::TestInitCommand::test_init_template_windows_safe_placeholder` (`raw/example.csv`, no `:`) | ✅ COMPLIANT |
| CLI-R07 | ntpath drive | `test_cli.py::test_init_template_windows_safe_placeholder` (ntpath.splitdrive == ("", ...)) | ✅ COMPLIANT |
| CLI-R07 | scan xlsx after init | `test_mcp_server.py::TestInitXlsxIntegration::test_xlsx_registered_validate_passes_and_idempotent` (DATA_GOT_ALL.xlsx → cache/ registered, validate passes) | ✅ COMPLIANT |
| CLI-R07 | --user required | `test_cli.py::TestParser::test_init_requires_user` (SystemExit 2 naming --user); `test_init_missing_user_rejected_subprocess` (rc 2, no TOML) | ✅ COMPLIANT |
| CLI-R07 | Placeholder user rejected pre-write | `test_cli.py::TestSubprocessBoundary::test_init_placeholder_user_rejected` (rc 1, stderr names placeholder, no TOML/raw) | ✅ COMPLIANT |
| CLI-R07 | Unsafe identity rejected pre-write | `test_cli.py::TestSubprocessBoundary::test_init_unsafe_name_rejected` (rc 1, names component, no file) | ✅ COMPLIANT |
| CLI-R07 | canonical config_path printed | `test_cli.py::TestSubprocessBoundary::test_init_prints_absolute_config_path` (rc 0, absolute `config_path` in stdout) | ✅ COMPLIANT |

**tool-config (1 requirement, 2 scenarios)**

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| TC-05 | Library load honors sibling pyproject | `test_model.py::TestFromTomlDiscoveryRoot::test_discovery_root_applies_at_or_below` (250 applied), `test_omitted_discovery_root_stays_unbounded` (unbounded CLI path) | ✅ COMPLIANT |
| TC-05 | Discovery bounded by discovery_root | `test_model.py::TestFromTomlDiscoveryRoot::test_discovery_root_blocks_above_root_override` (above-root 999 blocked, defaults kept) | ✅ COMPLIANT |

**process-boundary (2 requirements, 10 scenarios)**

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| PB-04 | Empty config | `test_mcp_process.py::TestConfigStates::test_empty_config_documented_result` | ✅ COMPLIANT |
| PB-04 | Existing config | `test_mcp_process.py::TestConfigStates::test_existing_config_validates_without_registration` | ✅ COMPLIANT |
| PB-04 | Greenfield bootstrap | `test_mcp_process.py::TestConfigStates::test_greenfield_bootstrap_init_scan_apply_validate` | ✅ COMPLIANT |
| PB-04 | Triage | `test_mcp_process.py::TestConfigStates::test_triage_scan_dry_run_preview_read_only` | ✅ COMPLIANT |
| PB-04 | Nested output CWD | `test_mcp_process.py::TestNestedCwd::test_init_writes_under_nested_cwd` | ✅ COMPLIANT |
| PB-04 | Real-process parent-root launch, cwd omitted fails closed | `test_mcp_process.py::TestParentRootIdentity::test_cwd_omitted_fails_closed_then_cwd_child_anchors` (a): refusal naming cwd, NO parent test.toml, NO parent raw/ — **the #116 reproduction over the real process** | ✅ COMPLIANT |
| PB-04 | Real-process parent-root launch, cwd=child anchors identity | same test (b): child/test.toml + child/raw/ exist, parent/test.toml absent, envelope absolute config_path/dataset_root | ✅ COMPLIANT |
| PB-09 | One server per test | every in-process test builds its own server via `build_server()` (test_mcp_server.py / test_mcp_process.py — verified throughout; no shared `_SERVER_ROOT` leakage by construction) | ✅ COMPLIANT |
| PB-09 | Shared conftest helpers | `tests/conftest.py` holds `mcp_payload`, `call_tool`, `run_cli`, `McpStdioServer`, `_make_dataset`, `mcp_stdio_server`, `mcp_stdio_parent_root`; `test_mcp_process.py` imports `call_tool`/`_make_dataset` from conftest — no re-implementation | ✅ COMPLIANT |
| PB-09 | Lean process spawns | module-scoped `mcp_stdio_server` (one spawn per module) + second module-scoped `mcp_stdio_parent_root` (one spawn per module per fixture) | ✅ COMPLIANT |

**Compliance summary**: 52/52 scenarios compliant, 9/9 requirements implemented and tested.

### Correctness (Static Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| INIT-05 identity validation | ✅ Implemented | `execution_context.validate_identity` (name/user mandatory, single component, `^[\w\-]+$`, `_PLACEHOLDERS` ban, control chars); called first in `sofer_init` (mcp_server.py:1681) and `_cmd_init` (cli.py:870); placeholder fallback deleted; `_INIT_TEMPLATE` never embeds YOUR_USER |
| INIT-02 cwd containment | ✅ Implemented | `resolve_dataset_root` 3 modes (D5); MCP cwd=None strict-descendant → envelope refusal naming cwd; str-cwd keeps `_contained_path` → `PathOutsideRootError`; per-call `effective_root`, `_SERVER_ROOT` never mutated |
| INIT-03 anchored writes + identity | ✅ Implemented | writes anchored to `effective_root`; `report_identity` in all 3 success envelopes (L1780/1795/1815) + output_schema (L2087-2088, not in required) |
| MSP-R03 roster/schema | ✅ Implemented | 14 callables registered; `sofer_init` output_schema declares config_path/dataset_root string props |
| MSP-R10 config contract | ✅ Implemented | `from_toml(path, discovery_root=None)` → conditional `stop_at` (only when bound given — TC-04 spy safe); `_bound_discovery` deleted; 4 MCP sites pass `discovery_root=_get_root()`; 6 config-bearing `root=cfg._base_dir` + 3 single-file `root=input.parent`; codebook delimiter/encoding from config, not hardcoded debt |
| CLI-R07 init contract | ✅ Implemented | argparse `--user required=True` (exit 2); handler `validate_identity` defense-in-depth (exit 1); `resolve_dataset_root` mode (a); absolute `OK  Created {output}` at all 5 write sites; single-file `--output` anchored to input's parent (codebook/profile/render) |
| TC-05 from_toml bound | ✅ Implemented | `discovery_root` optional param; docstring notes the bound; unbounded CLI path byte-identical |
| PB-04 real-process proof | ✅ Implemented | `TestParentRootIdentity` via `mcp_stdio_parent_root` fixture — real `sofer-mcp` stdio spawn, both scenarios in one session |
| PB-09 fixtures | ✅ Implemented | second module-scoped fixture `mcp_stdio_parent_root`; shared helpers in conftest; no pytest-asyncio, `asyncio.run` convention |

### Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| D1 execution_context module | ✅ Yes | New `src/sofer/execution_context.py` (262 LOC), stdlib + `model._PLACEHOLDERS` only, acyclic imports |
| D2 DatasetIdentity frozen + derived config_path | ✅ Yes | `@dataclass(frozen=True)`, `config_path` property, `from_parts` resolves only |
| D3 validate_identity returns list, first msg "name must be non-empty" | ✅ Yes | `test_empty_name_returns_ok_false` green without flip; placeholder ban user-only |
| D4 IdentityResolutionError in execution_context | ✅ Yes | Not in model.py; import direction acyclic |
| D5 resolve_dataset_root 3 modes; str-branch keeps _contained_path | ✅ Yes | Mode (b) unit-matrix-only; ToolError kept for str escapes (L2582/2595/2841) |
| D6 IdentityResolutionError → envelope refusal | ✅ Yes | `_refusal([str(exc)])` with `next: {}`; PathOutsideRootError still ToolError |
| D7 CLI --user required + handler defense-in-depth | ✅ Yes | argparse required=True AND `validate_identity` in `_cmd_init` |
| D8 from_toml discovery_root per-call | ✅ Yes | 4 MCP sites; `_bound_discovery` def + call sites deleted; Finding-1 conditional `stop_at` fix present (10e7eb8) |
| D9 Output anchoring via _contained_path reuse | ✅ Yes | 6 config-bearing `root=cfg._base_dir`, 3 single-file `root=input.parent`; CLI single-file inline anchoring; no new helper |
| D10 Envelope + schema same change | ✅ Yes | PB-03 satisfied; FastMCP projection verified empirically |
| D11 Mechanical sweep | ✅ Yes | ~43 sites swept; only L2576 untouched (already correct); TestNestedCwd keeps cwd=None intentionally (strict-descendant scenario) |
| README/README_ES same commit | ✅ Yes | baf6eff touches both; rows mirror (rule 13); technical tokens English |

### Intentional Flips Re-baseline

The design enumerated 9 named flips + 6th template site (L2300-2302) + 3 hidden template sites (L2157/2170-2172) + 4 traversal flips (L2245-2263). Diff vs `dev` confirms **exactly 4 deleted test functions**, all intentional with replacements:

| Deleted (dev) | Replaced by (branch) | Intent |
|----------------|----------------------|--------|
| `test_init_default_user_placeholder` | `test_init_requires_user` + `test_init_missing_user_rejected_handler` + `test_init_missing_user_rejected_subprocess` + 3 more new CLI tests | placeholder default removed → required `--user` (CLI-R07) |
| `test_default_user_placeholder` | `test_missing_user_refused_before_write` + `test_placeholder_user_refused_before_write` | placeholder fallback → pre-write refusal (INIT-05) |
| `test_cwd_none_back_compat` | `test_cwd_none_fails_closed` | back-compat parent-root write → fail-closed refusal (INIT-02) |
| `test_auto_cwd_outside_fallback` | `test_auto_cwd_outside_fails_closed` | silent parent fallback → fail-closed refusal (INIT-02) |

The 4 traversal tests (L2245-2263) were **flipped in place** (ToolError → envelope refusal) — they still exist under TestInitTraversal with no-write asserts. The 3 template sites + 6th site now assert `user="testuser"` (verified at L2159/2178/2205/2252/2278/2292-2337). **No test was deleted without replacement; no net coverage loss beyond the intentional flips.** Suite count arithmetic: 1269 → 1332 = +63 net, consistent with the per-slice gates (1318/1325/1330/1332).

### Ground Truth — issue #116 reproduction

```text
uv run pytest "tests/test_mcp_process.py::TestParentRootIdentity" -v
tests/test_mcp_process.py::TestParentRootIdentity::test_cwd_omitted_fails_closed_then_cwd_child_anchors PASSED [100%]
1 passed in 2.03s
```

Real MCP process (parent server root + existing `child/`), live CWD = parent: `cwd` omitted → `ok:False` refusal whose `config_errors` name `cwd`, NO `parent/test.toml`, NO `parent/raw/`; then `cwd="child"` → `child/test.toml` + `child/raw/` exist, parent absent, envelope reports absolute `config_path`/`dataset_root`. **The exact issue #116 scenario is proven over the real process boundary.**

### Spec Drift Check

- `openspec/specs/mcp-server/spec.md` is NOT yet merged (deltas live in the change folder; archive merges later) — confirmed no premature merge.
- Every requirement ID in the 4 delta specs (INIT-02/03/05, MSP-R03/R10, CLI-R07, TC-05, PB-04/09) maps to implemented code AND passing tests. No unimplemented requirement found.
- No scope creep: all production changes trace to spec requirements or design decisions (D5 mode (b), D9 CLI single-file anchoring, D11 sweep). The `test_explicit_cwd_still_overrides_auto` test is additional coverage consistent with INIT-02, not a new requirement.
- Spec prose calls the Root-unwrap helper `_mcp_payload`; the code names it `mcp_payload` (public, no underscore) — functionally identical, PB-09 scenario 2 satisfied.

### Cross-cutting (AGENTS.md)

| Rule | Status | Evidence |
|------|--------|----------|
| 1 No hardcoded values | ✅ | `_USER_RE`/`_CONTROL_CHARS_RE` constants; delimiter/encoding read from config at tool layer (mcp_server L1067-1068/1112-1113, codebook.generate_all L519-520) |
| 2 Docstrings | ✅ | `execution_context.py` module + every public function; `sofer_init`/`_cmd_init`/`from_toml` docstrings updated (params, raises, side effects) |
| 3 Read from config | ✅ | `cfg.csv_delimiter`/`cfg.csv_encoding` used; MCP tools inject post-reload `config.CSV_DELIMITER`/`CSV_ENCODING`; no hardcoded `";"`/`"utf-8-sig"` in the changed tool paths |
| 4 No duplicated logic | ✅ | `execution_context` is the single home for identity; conftest helpers shared (`call_tool`, `mcp_payload`, `run_cli`, `McpStdioServer`, `_make_dataset`) |
| 7/13 CLI help + README mirror | ✅ | argparse help updated (cli.py:1337-1346); README.md L318/348 + README_ES.md L330/360 updated in the SAME commit baf6eff |
| 8 Naming conventions | ✅ | `_lowercase` private helpers, `UPPERCASE` constants, `from __future__ import annotations` throughout execution_context |
| 12 Conventional commits | ✅ | 17 commits, all `feat`/`fix`/`test`/`style`/`docs` conventional format |
| PB-08 SOFER_TRACE.md | ✅ | untracked (`??`), length 17210, mtime 2026-08-31 17:40:07 — unchanged, never staged |

### Issues Found

**CRITICAL**: None.

**WARNING**: None.

**SUGGESTION**:
1. Spec prose in PB-09 names the Root-unwrap helper `_mcp_payload`; the code calls it `mcp_payload` (public). At archive time, align the spec prose with the implemented public name (or rename to the private form) — cosmetic only, scenario already compliant.
2. `codebook.generate`'s signature retains `delimiter: str = ";"` / `encoding: str = "utf-8-sig"` defaults (codebook.py:400-401) as inert fallbacks for direct library calls; the tool paths no longer rely on them (injection at mcp_server L1067-1068, generate_all L519-520). If rule-3 is to be enforced at the signature level, consider removing the defaults — out of scope for this change, no behavior impact.
3. Interior-space names (`"my dataset"`) are still accepted by `validate_identity` (recorded as known decision S3 in apply-progress, contract-faithful per INIT-05 wording). A future tightening could reject interior whitespace in `name`.

### Verdict

**PASS** — all 9 requirements implemented, all 52 scenarios covered by passing tests, all 4 gates green (1332 passed / 2 skipped; mypy, ruff check, ruff format, git diff --check clean), the #116 ground-truth reproduction passes over the real MCP process, intentional flips re-baselined with no unexplained deletions, no spec drift, no CRITICAL/WARNING findings.

---

## Post-audit fixes (2026-09-04) — appended after independent audit

An independent audit found 5 real defects in the verified change. All 5 fixed on `fix/116-dataset-identity-context` (commits 615decc, ba59a57, 7bbd065, 9418621, 3f4f9ef) and re-verified. The YAML frontmatter hashes above reflect the PRE-audit state; the post-audit gates are recorded below.

### Fixes applied

| Blocker | Defect | Fix | Tests |
|---------|--------|-----|-------|
| B1 | `_USER_RE` used `$` which matches before a trailing `\n`; MCP stripped while CLI did not | `^[\w\-]+\Z` end anchor + control-char check for `user` in `validate_identity` | +4 unit cells, +1 MCP newline-user boundary refusal |
| B2 | `sofer_init` read global `sofer_config.RAW_DIR` without reloading for `effective_root` | `_reload_tool_config(effective_root)` before `raw_dir = effective_root / sofer_config.RAW_DIR` | +1 per-root raw_dir reload test (sources vs raw, no leakage) |
| B3 | MCP render anchored output to `package_path.parent`; CLI anchored inside a dir package | `root = package_path if package_path.is_dir() else package_path.parent` | +2 tests (dir package inside, file package parent) |
| B4 | Both dry-run branches wrote the TOML; test `test_dry_run_no_mutation` codified the bug | Dry-run branches print `DRY RUN Would create/scaffold` preview lines and write NOTHING; Field/Args wording tightened | flip `test_dry_run_no_mutation` (`is_file()` → `not exists()`), +1 `test_dry_run_plain_no_toml` |
| B5a | Quick start `sofer init my-dataset` exits 2 without `--user` | `--user myuser` added in README.md + README_ES.md (same commit, rule 13) | docs-only |
| B5b | Audit: verify all 14 tools documented | VERIFIED — all 14 names present in both READMEs' prose + table; no edit needed | — |
| B5c | `sofer_init` schema exposed `user` as optional/nullable (INIT-05 requires it) | `user: Annotated[str, Field(...)]` (required, non-nullable; moved before defaulted params); `assert user is not None` removed | +1 schema test (user in required, type string); flip `test_missing_user_refused_before_write` → ToolError |

### Post-audit gates

```text
uv run pytest tests/ -q                                -> 1342 passed, 2 skipped, 0 failed (1332 baseline + 10 new)
uv run pytest tests/test_execution_context.py tests/test_mcp_server.py tests/test_mcp_schema.py -q  -> 214 passed, 2 skipped
uv run pytest tests/test_mcp_process.py -q             -> 12 passed
uv run mypy src/                                       -> Success: no issues found in 30 source files
uv run ruff check src/ tests/                          -> All checks passed
uv run ruff format --check src/ tests/                 -> 60 files already formatted
git diff --check                                       -> clean
git status                                             -> SOFER_TRACE.md untracked, mtime 2026-08-31 17:40, length 17210 (PB-08 untouched)
```

### Live-spec alignment (blocker 4)

Conditional spec change checked: `openspec/specs/mcp-server/spec.md` INIT-01/INIT-02/INIT-03 do NOT state dry_run writes the TOML — no spec edit was required. Implementation, tests, and tool descriptions now agree: dry_run performs NO writes.

### Boundary contract note (B5c)

Absent `user` is now rejected at FastMCP input validation (ToolError) instead of an envelope refusal; blank `user=""`/`"   "` still reach the tool and refuse via envelope. INIT-05 "missing or blank identity refused before write" holds at schema boundary (absent) and envelope (blank).

### Verdict (post-audit)

**PASS** — all 5 blockers fixed, full suite re-baselined at 1342 passed / 2 skipped, all build gates green, SOFER_TRACE.md untouched.

---

## Post-audit re-verification (2026-09-04) — independent re-run after the 5 blocker fixes

Re-verification of the archived change after the independent audit's 5 blockers were fixed in 5 commits (`615decc`, `ba59a57`, `7bbd065`, `9418621`, `e1dec80`). All gates re-run from scratch on `fix/116-dataset-identity-context`; spec conformance re-checked against the live `openspec/specs/` (already delta-merged at archive). Verification-only — no source/test files modified.

### Gates (ACTUAL output, re-run)

```text
uv run pytest tests/ -q                                -> 1342 passed, 2 skipped, 13 warnings in 30.46s (exit 0)
                                                          (2nd confirm run: 1342 passed, 2 skipped, 13 warnings in 29.01s, exit 0)
uv run mypy src/                                       -> Success: no issues found in 30 source files (exit 0)
uv run ruff check src/ tests/                          -> All checks passed! (exit 0)
uv run ruff format --check src/ tests/                 -> 60 files already formatted (exit 0)
git diff --check                                       -> clean (exit 0)
```

- `test_output_hash`: `sha256:8710d3012344aa5559194a81cff3509985544119843eb26ea0f1046e398cf569`
- `build_output_hash`: `sha256:5b108d7c22076b839e0139746620132c7dc923055d637c7f29c7f84e57d5f3a0`
- Expected suite **1342 passed / 2 skipped — MATCHES ACTUAL exactly.**

### Fix conformance after fixes (source + test evidence)

| Blocker | Fix (commit) | Source evidence | Test evidence | Spec conformance |
|---------|--------------|-----------------|---------------|------------------|
| B1 | Control chars + `\Z` anchor (615decc) | `execution_context.py:39` `_USER_RE = re.compile(r"^[\w\-]+\Z")` — `\Z` NOT `$` (Python `$` matches before trailing `\n`); `:43` `_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")`; `validate_identity` checks `_CONTROL_CHARS_RE.search(user)` BEFORE `_USER_RE.match(user)` (L176-179) | `test_user_control_char_refused` 4 cells (`alice\n`, `alice\t`, `alice\x00`, `alice\x7f`) + `test_control_char_refused` 4 cells for `name`; MCP boundary `test_newline_user_refused_before_write` — all PASSED | INIT-05 compliant — requirement body bans control chars for both `name` and `user`; `\Z` is a strict superset of the prose regex `^[\w\-]+$` (see SUGGESTION 1) |
| B2 | Reload tool config per effective root (ba59a57) | `mcp_server.py:1712` `_reload_tool_config(effective_root)` runs BEFORE `raw_dir = effective_root / sofer_config.RAW_DIR` (L1722); `_reload_tool_config` bounded by `stop_at=_get_root()` (L461); raw_dir containment guard L1724-1735 | `TestInitToolConfigReload::test_init_reloads_raw_dir_per_root` — PASSED | MSP-R10 compliant — no stale RAW_DIR across roots; discovery stays bounded at server root |
| B3 | Render anchors dir-packages inside package (7bbd065) | `mcp_server.py:1314` `root=package_path if package_path.is_dir() else package_path.parent` — CLI parity documented in comment | `test_render_output_dir_anchors_inside_package_dir` + `test_render_output_dir_file_package_anchors_to_parent` — PASSED | D9 / MSP-R10 parity — dir package output lands INSIDE the package, file package anchors to parent |
| B4 | dry_run performs NO writes (9418621) | Both dry-run branches (L1776-1794 move_existing, L1795-1804 plain) print `DRY RUN Would create/scaffold` preview lines and return BEFORE `raw_dir.mkdir` (L1805) and `write_text` (L1806); tool docstring + `dry_run` Field description updated | `test_dry_run_no_mutation` flipped in place (`is_file()` → `not exists()`) + new `test_dry_run_plain_no_toml` — PASSED | CLI-R07 "previews no mutation" — compliant; INIT-01/02/03 prose never claimed dry_run writes (live-spec check in prior post-audit section holds) |
| B5 | `--user` required in quick start + `user` REQUIRED in schema (e1dec80) | `mcp_server.py:1647-1652` `user: Annotated[str, Field(...)]` no default, positioned before defaulted params; README.md + README_ES.md both `sofer init my-dataset --user myuser` | `test_sofer_init_user_required` (user in input-schema `required`, type string, `"null" not in str(user_schema)`) — PASSED; `test_missing_user_refused_before_write` flipped in place to `pytest.raises(ToolError)` (absent user rejected at FastMCP input validation) | INIT-05 mandatory user — compliant; boundary contract: absent → ToolError (schema), blank `""`/`"   "` → envelope refusal |

### Ground truth — issue #116 (real stdio process)

```text
uv run pytest "tests/test_mcp_process.py::TestParentRootIdentity" -v
tests/test_mcp_process.py::TestParentRootIdentity::test_cwd_omitted_fails_closed_then_cwd_child_anchors PASSED [100%]
============================== 1 passed in 2.71s ==============================
```

Still green over the real `sofer-mcp` stdio process after all 5 fixes.

### SOFER_TRACE.md (PB-08)

`git status --short` → `?? SOFER_TRACE.md` (untracked, never staged); not modified, not read by this re-verification. **Untouched.**

### Flips / count reconciliation (1332 → 1342 = +10)

`git diff 62da878..HEAD` (the 5 fix commits) shows **+8 new test functions, 0 deleted** (`^-def test_` / `^-    def test_` count = 0):

| New test | Cells | Fix |
|----------|-------|-----|
| `test_user_control_char_refused` (parametrized `alice\n/alice\t/alice\x00/alice\x7f`) | +4 | B1 |
| `test_newline_user_refused_before_write` (MCP boundary) | +1 | B1 |
| `TestInitToolConfigReload::test_init_reloads_raw_dir_per_root` | +1 | B2 |
| `test_render_output_dir_anchors_inside_package_dir` | +1 | B3 |
| `test_render_output_dir_file_package_anchors_to_parent` | +1 | B3 |
| `test_dry_run_plain_no_toml` | +1 | B4 |
| `test_sofer_init_user_required` (schema) | +1 | B5b |

4+1+1+1+1+1+1 = **+10 cells exactly**. Two in-place flips, no deletions: `test_dry_run_no_mutation` (`is_file()` → `not exists()`, codified-bug flip) and `test_missing_user_refused_before_write` (envelope refusal → `ToolError` at schema boundary, B5c boundary contract). **No unexplained test deletion.**

### Spec drift check

- No requirement block contradicted by the 5 fixes — each fix tightens behavior toward the spec text (control-char ban, mandatory `user`, no-mutation dry-run, per-root config isolation, render parity).
- `openspec/specs/` already carries the delta merge (archive-replace); all re-read requirement bodies (INIT-02/03/05, MSP-R03/R10, CLI-R07, TC-05, PB-04/09) match the verified 52/52 map.

### Issues

**CRITICAL**: None.

**WARNING**: None.

**SUGGESTION**:
1. INIT-05 prose regex reads `^[\w\-]+$` but the implementation is `^[\w\-]+\Z` (stricter — rejects trailing `\n`). Behaviorally compliant (superset); align the spec regex literal with `\Z` at the next spec edit for exactness.
2. `openspec/project.md` still records "1332 passed, 2 skipped" (updated at archive time, pre-post-audit); bump to 1342 to match the post-fix baseline.
3. The prior post-audit append in this file cites commit `3f4f9ef` for B5c; the actual commit is `e1dec80` (confirmed via `git log`). Cosmetic doc typo in the earlier append — corrected here.

### Verdict (post-audit re-verification)

**VERIFIED** — all 5 audit blockers confirmed fixed and spec-compliant on the live `openspec/specs/`, all gates green with ACTUAL counts matching the expected 1342 passed / 2 skipped, mypy/ruff/format/diff-check clean, the #116 ground-truth reproduction still passes over the real MCP process, the +10 count reconciles with zero unexplained test deletions, and SOFER_TRACE.md remains untouched. No CRITICAL or WARNING findings; 3 cosmetic SUGGESTIONs.
---

## Merge-review evidence reconciliation (2026-09-04)

During merge review of the chained PRs (#134/#136/#135/#137) the archived
re-verification section (1342 passed / 2 skipped) was found to be inconsistent
with the final branch state. Reconciliation:

- **FINAL baseline: 1344 passed, 2 skipped, 0 failed** — verified by the
  pre-merge alignment gates on `fix/116-dataset-identity-context` (see
  apply-progress "Gates (post-alignment, ACTUAL output)").
- **1342 → 1344 delta (+2)**: the two CLI `--dry-run` no-mutation tests
  (`test_init_dry_run_no_mutation`, `test_init_plain_dry_run_no_mutation`)
  landed in the pre-merge alignment commit `a1cb36f` ("fix(cli): honor
  --dry-run as no-mutation in init") AFTER the post-audit re-verification ran,
  so the re-verification section legitimately recorded 1342. The final state
  is 1344 passed / 2 skipped.
- **Per-slice gate counts are historical, not the final state**: the 1318 /
  1325 / 1330 / 1332 counts recorded in apply-progress and the earlier
  verify-report sections are per-slice snapshots (each slice's gate on its
  own branch head). Arithmetic: 1269 (dev baseline) + 49 + 7 + 5 + 2 = 1332
  at slice 4; + 10 post-audit fixes = 1342; + 2 pre-merge CLI dry-run tests
  = 1344. The PR bodies' per-slice counts plus the "1344 at final state"
  checklist line are consistent with this reconciliation.

The authoritative count for the merged change is **1344 passed / 2 skipped**
(mypy, ruff check, ruff format, git diff --check all clean; SOFER_TRACE.md
untouched — PB-08).

---

## Post-merge-review re-verification (2026-09-04)

Re-verification after the maintainer's merge review found 6 blockers, all
fixed on `fix/116-pr4` (head of PR #137; 7 commits `4ff3d91..d6ac85f`) and
passed by an independent gate review (PASS, no CRITICAL). The 6 fixes updated
the live specs (`openspec/specs/scan/spec.md` SCN-01 symlink exclusion,
`openspec/specs/prepare/spec.md` PRP-03 doc containment,
`openspec/specs/mcp-server/spec.md` INIT-05 Windows-invalid/reserved names +
INIT-03 TOML-before-raw/, `openspec/specs/publish/spec.md` PUB-05 fail-closed
inspection). Verification-only — no source/test files modified.

### Gates (ACTUAL output, re-run on fix/116-pr4 @ d6ac85f)

```text
uv run pytest tests/ -q                                -> 1385 passed, 4 skipped, 13 warnings in 35.07s (exit 0)
                                                          (measured 3x: 34.81s, 36.33s, 35.07s — all 1385/4)
uv run mypy src/                                       -> Success: no issues found in 30 source files (exit 0)
uv run ruff check src/ tests/                          -> All checks passed! (exit 0)
uv run ruff format --check src/ tests/                 -> 60 files already formatted (exit 0)
git diff --check                                       -> clean (exit 0)
```

- `test_output_hash`: `sha256:e1e767b0befd714e338a2a83a76fdefac8eebaa0ef35b6ffda8e0a2e7f6ab581`
- `build_output_hash`: `sha256:3266b03d0ae65295cbe214aab624a4a998c8103ba8125e4be1291cc8077d123e`
- Expected suite **1385 passed / 4 skipped — MATCHES ACTUAL exactly.**

### The 4 skips explained

| Skip site | Test | Reason | Status |
|-----------|------|--------|--------|
| `test_mcp_server.py:583` | `test_symlink_inside_root_to_outside` | file-symlink creation requires elevated privileges on this win32 host | pre-existing (present at 4ff3d91) |
| `test_mcp_server.py:1110` | hatchling build-backend skipif | hatchling not installed in dev env (CI builds the wheel) | pre-existing |
| `test_scanner.py:384` | `test_symlinked_file_outside_not_discovered` | file-symlink creation unavailable on this host | NEW (+1 of the +2) |
| `test_scanner.py:418` | `test_regular_file_still_discovered_alongside_links` | file-symlink creation unavailable on this host | NEW (+1 of the +2) |

Note: the **junction** paths run for real on this host (NTFS junctions work
without elevation): `test_scanner.py:402 test_symlinked_dir_outside_not_discovered`
PASSED and `test_mcp_server.py:603 test_junction_dir_inside_root_to_outside`
PASSED — the `_is_link` reparse-point detection is exercised by real
execution, not just skipped.

### Fix conformance after fixes (source + spec + test evidence)

| Blocker | Fix (commit) | Source evidence | Test evidence | Spec conformance |
|---------|--------------|-----------------|---------------|------------------|
| B1 | Symlink exclusion (99750e5) | `scanner.py` `_is_link` (is_symlink OR Windows `FILE_ATTRIBUTE_REPARSE_POINT` on 3.10-3.12 where junction `is_symlink()` is False); `discover_files` skips linked entries AND entries with a linked ancestor (parents loop up to root); module docstring states the exfiltration rationale | `test_symlinked_file_outside_not_discovered` (skipped — env), `test_symlinked_dir_outside_not_discovered` (PASSED — junction), `test_regular_file_still_discovered_alongside_links` (skipped — env); scanner suite 72 passed/2 skipped | SCN-01 compliant — live spec now bans symlinks + junctions and both new scenarios are covered (junction vector executed green) |
| B2 | Doc-path containment (548a227) | `model.resolve_doc_path(value, base)` resolves against `cfg._base_dir` (never process cwd); used by `model.validate()` (4 doc fields) and `prepare.py` L809-830; MCP `_validate_doc_files(cfg)` containment-check wired into `_load_dataset` + `sofer_profile_all`/`render_all`/`auth_status` (collected errors, refusal `ok:False`) | `TestDocPathContainment` (3: outside-root readme refused, study_design+recipe refused, contained passes & reads relative to TOML dir); `test_relative_readme_resolves_against_config_dir` + `test_recipe_and_study_design_relative_to_config_dir` + `test_relative_readme_missing_warns_and_falls_back` (prepare.py domain); `test_prepare_reads_relative_readme_from_toml_dir` (CLI subprocess) — all PASSED | PRP-03 compliant — "relative README resolves against the TOML directory" and "declared doc path outside the server root refused" scenarios green |
| B3 | Windows-invalid/reserved names + TOML-before-raw (1fde058) | `execution_context.py` `_WINDOWS_INVALID_CHARS = '<>:"/\\|?*'`, `_RESERVED_DEVICE_NAMES` (CON/PRN/AUX/NUL/COM1-9/LPT1-9), `_reserved_device_name` stem-matched case-insensitive (CON.txt rejected); `validate_identity` `elif` branches; init write-order hardened TOML-before-raw/ in `_cmd_init` (4 sites) + `sofer_init` | `test_windows_invalid_chars_refused` (6 cells: a*b a?b a<b a>b a|b a1:b), `test_reserved_device_name_refused` (11 cells incl. CON.txt/con.toml), `test_normal_names_still_accepted`; MCP `test_unsafe_name_windows_invalid_char_refused` + `test_reserved_device_name_refused`; CLI `test_init_windows_invalid_name_rejected` + `test_init_reserved_device_name_rejected` — all PASSED | INIT-05 compliant — new "Windows-invalid or reserved name rejected" scenario green (NO TOML, NO raw/ pre-write); INIT-03 TOML-before-raw/ prose matches code |
| B4 | Publish fail-closed (a5f2365) | `publish.py` `_inspect_repo`: `RepositoryNotFoundError` → `[]`, ANY other exception → raise; `_ensure_repo`: raise on non-"already exists" `create_repo` errors; `publish()` wraps the remote prologue → rc 1 BEFORE any staging/upload; post-upload inspection failure warns + skips split report only | `TestRemoteFailClosed` (4: not-found → [], RuntimeError → raises, publish refuses before upload with `upload_folder` NOT called, ensure_repo raises) — all PASSED | PUB-05 compliant — all 3 new scenarios ("repo-not-found reads as empty", "inspection failure fails closed", "create_repo failure fails closed") green |
| B5 | Anchor tests present (49f0fd8) | CLI `profile`/`render` single-file `--output` anchored to input parent; MCP `sofer_codebook` output_file → input parent, `sofer_profile` output_dir → input parent, `sofer_codebook_all`/`profile_all`/`render_all` relative output_dir → `cfg._base_dir` (NOT server root) | `test_profile_relative_output_anchors_to_input_parent`, `test_render_relative_output_anchors_to_input_parent`, `test_codebook_single_file_output_anchors_to_input_parent`, `test_profile_single_file_output_anchors_to_input_parent`, `test_codebook_all_output_dir_anchors_to_config_dir`, `test_profile_all_output_dir_anchors_to_config_dir`, `test_render_all_output_dir_anchors_to_config_dir` — all PASSED | MSP-R10 / D9 parity — the previously code-verified anchoring contracts now have direct runtime coverage |
| B6 | Baseline recorded (625c98c + d6ac85f) | verify-report.md "Merge-review evidence reconciliation" (1344) + apply-progress "Merge-review blockers" section; this append records the post-fix 1385/4 | — | — |

### No regressions (previously-fixed behaviors re-run)

```text
uv run pytest tests/test_execution_context.py -q -k "control or windows_invalid or reserved or newline"   -> 25 passed   (user \Z + control chars + new checks)
uv run pytest tests/test_cli.py tests/test_mcp_server.py -q -k "dry_run or dry_run_no_mutation or dry_run_plain"  -> 15 passed  (dry-run no-write BOTH adapters)
uv run pytest tests/test_mcp_server.py -q -k "render_output_dir_anchors or render_output_dir_file_package"        -> 2 passed   (dir-package inside / file-package parent)
uv run pytest tests/test_mcp_server.py -q -k "init_reloads_raw_dir or raw_dir_per_root or RawDir"                 -> 1 passed   (per-root RAW_DIR reload)
uv run pytest tests/test_prepare.py -q                                                                           -> 50 passed
uv run pytest tests/test_publish.py -q -k "fail or inspect or ensure_repo"                                       -> 9 passed
uv run pytest tests/test_scanner.py -q                                                                           -> 72 passed, 2 skipped
```

### Ground truth — issue #116 (real stdio process)

```text
uv run pytest "tests/test_mcp_process.py::TestParentRootIdentity" -v
tests/test_mcp_process.py::TestParentRootIdentity::test_cwd_omitted_fails_closed_then_cwd_child_anchors PASSED [100%]
============================== 1 passed in 2.79s ==============================
```

Still green over the real `sofer-mcp` stdio process after all 6 fixes.

### Count reconciliation (1344 → 1385 passed, 2 → 4 skipped)

`git diff 4ff3d91..d6ac85f` shows **28 new test functions, 0 deleted**
(43 collected items after parametrize expansion):

| File | New functions | Items (cells) | Fix |
|------|---------------|---------------|-----|
| tests/test_scanner.py | 3 | 3 (1 passes + 2 Windows file-symlink skips) | B1 |
| tests/test_prepare.py | 3 | 3 | B2 |
| tests/test_mcp_server.py | 10 | 10 (3 doc-containment + 2 windows/reserved + 5 anchors) | B2/B3/B5 |
| tests/test_execution_context.py | 3 | 18 (6 + 11 + 1 parametrize cells) | B3 |
| tests/test_cli.py | 5 | 5 (2 windows/reserved + 2 anchors + 1 prepare-TOML-dir) | B3/B5/B2 |
| tests/test_publish.py | 4 | 4 | B4 |

Total items: 3+3+10+18+5+4 = **+43**; passed +41, skipped +2.
Arithmetic: 1344 + 41 passed = **1385 passed**; 2 + 2 skipped = **4 skipped**.
Zero test deletions (`^-def test_` count = 0). Matches the apply-progress
"+43 cells" table exactly.

### SOFER_TRACE.md (PB-08)

`git status --short` → `?? SOFER_TRACE.md` (untracked, never staged);
length 17210, mtime 2026-08-31 17:40:07 — unchanged, untouched by this
re-verification.

### Issues

**CRITICAL**: None.

**WARNING**: None.

**SUGGESTION**:
1. The two scanner file-symlink tests (`test_symlinked_file_outside_not_discovered`,
   `test_regular_file_still_discovered_alongside_links`) skip on this win32
   host (file-symlink creation needs developer mode/elevation). They run on
   POSIX CI. The junction variant of the same code path is exercised green on
   this host, so the exclusion logic is proven; no action required.
2. `test_mcp_server.py:603 test_junction_dir_inside_root_to_outside` is the
   pre-existing containment test that now passes for real on this host — the
   skip at 603 was already unreachable here (junction creation succeeds), so
   its skip-branch is dead code on Windows; harmless.

### Verdict (post-merge-review re-verification)

**VERIFIED** — all 6 merge-review blockers confirmed fixed and spec-compliant
against the updated live specs (SCN-01, PRP-03, PUB-05, INIT-05/INIT-03),
all gates green with ACTUAL counts matching the expected **1385 passed / 4
skipped** (measured 3x), mypy/ruff/format/diff-check clean, the +43 item
reconciliation (41 passed + 2 skipped) verified against the added test files
with zero deletions, the #116 ground-truth reproduction still passes over the
real MCP stdio process, previously-fixed behaviors (user `\Z`/control chars,
dry-run no-write both adapters, render dir-package parity, per-root RAW_DIR
reload, cwd fail-closed) all re-run green, and SOFER_TRACE.md remains
untouched. No CRITICAL or WARNING findings; 2 cosmetic SUGGESTIONs.
