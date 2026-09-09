```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:b8a10a38fdf757c5e343fa83b6d549497cb483d7ec8b7e2c70ae486c9a0d4d02
verdict: pass
blockers: 0
critical_findings: 0
requirements: 3/3
scenarios: 20/20
test_command: uv run pytest tests/ -q
test_exit_code: 0
test_output_hash: sha256:4c33f3049710e05bf7fbbb9d1d7031acd0d9c2ec3db5b5bd61ee65956645ebfd
build_command: uv run ruff check src/ tests/ && uv run mypy src/
build_exit_code: 0
build_output_hash: sha256:22b50f20acf2f21555da5769aff2e139a721aff8d0e674202602380c30f16809
```

## Verification Report

**Change**: feat-mcp-registration-automation
**Version**: N/A
**Mode**: Standard

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 17 |
| Tasks complete | 17 |
| Tasks incomplete | 0 |

All 17 tasks across 5 phases marked [x] in `tasks.md` and `apply-progress.md`. No unchecked implementation task.

### Build & Tests Execution
**Build**: ✅ Passed
```text
$ uv run ruff check src/ tests/
All checks passed!

$ uv run mypy src/
Success: no issues found in 29 source files
```

**Tests**: ✅ 1149 passed / 0 failed / 2 skipped
```text
$ uv run pytest tests/ -q
1149 passed, 2 skipped, 13 warnings in 18.04s
New MCP suites: tests/test_mcp_registration.py (31 tests) + tests/test_cli.py::TestMcpCliHelp (5 tests) → 36 new, all green.
Targeted: uv run pytest tests/test_mcp_registration.py tests/test_cli.py -q → 106 passed.
Warnings are pre-existing DeprecationWarning in test_codebook.py (_infer_type), unrelated to this change.
```

**Coverage**: Not available (no threshold configured) — not blocking.

**CLI smoke**:
```text
$ sofer --help → contains mcp
$ sofer mcp --help → contains add, remove
$ sofer mcp add --help → --agent, --scope, --cwd, --dry-run
$ sofer mcp remove --help → --agent, --scope, --dry-run (no --cwd)
```

### Spec Compliance Matrix
| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| MCP-REG-01 | Add all | `test_mcp_registration.py::TestDryRun::test_add_all_dry_run_no_files` + `TestRemove::test_remove_all` (indirect) + manual `add --agent all` path exercised via `_run_add` with `all` expansion in `cli._cmd_mcp_add` (branch `all→[opencode,codex,gemini]`) | ✅ COMPLIANT |
| MCP-REG-01 | Add single | `TestMerge::test_preserve_other_servers` (opencode), `test_gemini_preserve_other` | ✅ COMPLIANT |
| MCP-REG-01 | Idempotent | `TestIdempotency::test_idempotent_no_backup_no_write` (byte-identical, no .bak) | ✅ COMPLIANT |
| MCP-REG-01 | Dry-run | `TestDryRun::test_add_dry_run_no_mutation`, `test_add_all_dry_run_no_files` — asserts no file/.bak mutation | ✅ COMPLIANT |
| MCP-REG-01 | Backup | `TestBackup::test_backup_pre_edit` — asserts `.bak` holds pre-edit content | ✅ COMPLIANT |
| MCP-REG-01 | Unreadable | `TestUnreadable::test_unreadable_malformed_json`, `test_unreadable_malformed_toml` — exit 1, no .bak, file unchanged | ✅ COMPLIANT |
| MCP-REG-01 | Cwd custom | `TestBuildEntry::test_cwd_custom_absolute` + `build_entry` `cwd.resolve()` → stored absolute verified via `read_config` | ✅ COMPLIANT |
| MCP-REG-01 | Gemini env | `TestBuildEntry::test_gemini_env_both_tokens`, `TestEnvForwarding::test_gemini_explicit_env` — `mcpServers.sofer.env` contains HF_TOKEN + SOFER_MCP_APPROVAL_PHRASE | ✅ COMPLIANT |
| MCP-REG-01 | Codex merge | `TestMerge::test_codex_normalize_string_vs_array` — string/array normalized, `other` preserved; `TestEnvForwarding::test_codex_env_vars` | ✅ COMPLIANT |
| MCP-REG-01 | OpenCode scope | `TestResolveConfigPath::test_opencode_scope_routing` — user vs project paths distinct, `opencode.json` name, `is_relative_to` | ✅ COMPLIANT |
| MCP-REG-01 | Native delegation | `TestDelegation::test_present_delegates`, `test_absent_fallback`, `test_fail_fallback`, `test_timeout_fallback`, `test_opencode_never_delegates` — which+run mocked, fallback to file-edit | ✅ COMPLIANT |
| MCP-REG-02 | Remove single | `TestRemove::test_remove_single` — sofer absent, others preserved | ✅ COMPLIANT |
| MCP-REG-02 | Remove all | `TestRemove::test_remove_all` — each agent sofer removed | ✅ COMPLIANT |
| MCP-REG-02 | Idempotent remove | `TestRemove::test_remove_idempotent` — exit 0, no write, path not exists | ✅ COMPLIANT |
| MCP-REG-02 | Remove dry-run | `TestDryRun::test_remove_dry_run_no_mutation` — no .bak, byte-identical | ✅ COMPLIANT |
| MCP-REG-02 | Remove backup | `TestBackup::test_remove_backup` — .bak holds pre-edit, other preserved | ✅ COMPLIANT |
| CLI-R09 | mcp in top help | `test_cli.py::TestMcpCliHelp::test_sofer_help_has_mcp` | ✅ COMPLIANT |
| CLI-R09 | mcp lists children | `TestMcpCliHelp::test_mcp_help_has_add_remove` | ✅ COMPLIANT |
| CLI-R09 | add help | `TestMcpCliHelp::test_mcp_add_help_flags` — --agent, --scope, --cwd, --dry-run | ✅ COMPLIANT |
| CLI-R09 | remove help | `TestMcpCliHelp::test_mcp_remove_help_flags` + `test_mcp_add_no_cwd_on_remove` (negation) | ✅ COMPLIANT |

**Compliance summary**: 20/20 scenarios compliant

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| MCP-REG-01 idempotent & safe | ✅ Implemented | `merge()` returns `(doc, False)` when `_entries_equal` (codex normalize, gemini env dict equality, opencode dict equality); caller skips backup/write. `backup()` copy2 → .bak overwrite, `atomic_write()` tmp+os.replace in same dir, parent mkdir. |
| Preserve other servers | ✅ Implemented | `merge` copies `existing` shallow then `dict(other)` before inserting `sofer`; `remove_entry` pops only `sofer`. Tests confirm `other` preserved for opencode/gemini. |
| Backup .bak + atomic | ✅ Implemented | `src/sofer/mcp_registration.py:300-341` — backup before first mutation, atomic via `path.with_name(+".tmp")` + `os.replace`. CLI guards: `not changed → no write`, `dry_run → no backup/write`. |
| Dry-run no mutation | ✅ Implemented | `_cmd_mcp_add:650-652` and `_cmd_mcp_remove:725-727` dry-run guard before backup; tests verify no file/.bak created for add all dry-run. |
| Unreadable/malformed exit1 | ✅ Implemented | `read_config` propagates `json.JSONDecodeError`/`tomli` error/ValueError; `_cmd_*` catches generic Exception, prints to stderr, `overall=1`, no backup/write. |
| Cwd absolute anchored + containment | ✅ Implemented | `build_entry` `cwd.resolve()` stored absolute; `validate_cwd` `Path.resolve()+is_relative_to(home/project)`; `_cmd_mcp_add` resolves cwd_raw or Cwd, validates before loop, exit1 with path message. Custom cwd test stores resolved absolute. |
| Gemini env explicit | ✅ Implemented | `collect_env()` only HF_TOKEN/SOFER_MCP_APPROVAL_PHRASE, non-empty; `build_entry` gemini `env` dict explicit, codex `env_vars` allow-list, opencode no env. No underscore variants, no shell inheritance (dict passed explicitly). |
| Codex TOML merge + normalize | ✅ Implemented | `_normalize_codex_command` str→[str], list→[str]; `_entries_equal` normalizes before compare, sorts env_vars; `merge` preserves `mcp_servers.other`. Uses `tomli_w` for write (comment loss documented). |
| Opencode scope routing | ✅ Implemented | `resolve_config_path` user: `Path.home()/.config/opencode/opencode.json`, project: `cwd/opencode.json`; codex/gemini analogous. Windows-aware via `Path.home()`. |
| Native delegation hybrid | ✅ Implemented | `probe_native` opencode→False, else `which`+`mcp --help` timeout 3s; `delegate_add/remove` try native, fallback to file-edit on miss/fail/timeout. Mocked which/run in tests. |
| CLI wiring | ✅ Implemented | `cli.py:1386-1461` mcp→add/remove subparsers, choices opencode|codex|gemini|all, scope user|project, cwd only on add, dry-run both; handlers aggregate exit codes. |
| No hardcodes | ✅ Implemented | Tool defaults stay in constants (`_ENV_KEYS`, `ADAPTERS`, `AgentName`/`Scope` Literals); timeout 3.0 is param default, not magic literal in body. |
| Docstrings | ✅ Implemented | Module docstring + every public `def`/`class` has numpydoc-style docstring; `_cmd_mcp_add/remove` have orchestration docstrings. |
| README sync | ✅ Implemented | `README.md` + `README_ES.md` both document `sofer mcp add/remove --agent all`, per-agent table, .bak, idempotency, cwd containment, env forwarding, delegation, TOML warning; CLI reference + flags at a glance updated. |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| Hybrid delegation-first (B) | ✅ Yes | `probe_native` + `delegate_add/remove` with file-edit fallback; opencode always file-edit. |
| TOML I/O tomli/tomli-w | ✅ Yes | `read_config` tomli/tomllib, `atomic_write` tomli_w; comment loss warned in docs + CLI description. |
| Backup single .bak overwrite | ✅ Yes | `backup()` copy2 to `.bak` overwrite; docs say single file overwrites. |
| Adapter shape functions+ADAPTERS | ✅ Yes | Flat module `ADAPTERS: dict[AgentName, Adapter]` with `fmt`/`key`, no classes. |
| Cwd containment resolve+is_relative_to | ✅ Yes | `validate_cwd` resolve + is_relative_to(home/project); `--cwd` stored absolute. |
| No new [tool.sofer] knob | ✅ Yes | Fixed `sofer-mcp` command, no config knob. |
| Data flow probe→delegate→file-edit | ✅ Yes | Loop per agent: probe_native → delegate → read→build→merge→dry-run→backup→atomic; aggregate exit codes. Spec deltas `mcp-registration/spec.md` + `cli/spec.md` present. |

### Issues Found
**CRITICAL**: None
**WARNING**: None
**SUGGESTION**:
- `delegate_add` declares `cmd_variants` with 3 shapes but only tries `cmd_variants[:1]`; unreachable branches 2-3 are dead code — either remove or document as future-proofing, or loop all variants.
- `validate_cwd` accepts `is_relative_to(home) or is_relative_to(project)` for both scopes (permissive). Matches design tolerance for tmp paths under home on Windows, but strictly a project-scoped cwd under user home still passes — consider scope-strict check if tighter containment is desired.
- `probe_native`/`delegate_*` catch broad `Exception` → silent False; good for fallback but could log at debug for diagnostics.

### Verdict
PASS
All 20 scenarios have passing covering tests, 1149 tests green, ruff/mypy clean, no hardcodes, docstrings present, README_EN/ES synced. Ready for archive.
