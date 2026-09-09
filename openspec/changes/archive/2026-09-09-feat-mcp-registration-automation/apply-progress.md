# Apply Progress: feat-mcp-registration-automation

## Change
feat-mcp-registration-automation (#77)

## Mode
Standard (strict_tdd: false)

## Completed Tasks
- [x] 1.1 Create `src/sofer/mcp_registration.py` — module docstring, `AgentName`/`Scope` Literals, `ADAPTERS` TypedDict
- [x] 1.2 Implement `resolve_config_path(agent, scope, cwd)` — opencode/codex/gemini paths, user vs project, `Path.home()` Windows
- [x] 1.3 Implement `read_config`, `build_entry(agent,cwd,env)`, `merge(agent,existing,desired)` — Codex string/array normalize, preserve others, no-change check
- [x] 1.4 Implement `backup(path)` (copy2→`.bak` overwrite) + `atomic_write(path,doc,fmt)` (tmp+`os.replace`)
- [x] 2.1 Implement `probe_native` (`which`+`--help` timeout 3s) + `delegate_add`/`delegate_remove` (codex/gemini only; opencode always file-edit)
- [x] 2.2 Implement cwd containment — `Path.resolve()` + `is_relative_to` user/project else exit 1; store absolute cwd
- [x] 2.3 Implement env forwarding — `HF_TOKEN`/`SOFER_MCP_APPROVAL_PHRASE` → Codex `env_vars` list vs Gemini `env` dict
- [x] 3.1 Modify `src/sofer/cli.py` — add `mcp` → `add`/`remove` subparsers with `--agent/--scope/--cwd/--dry-run` choices + help text
- [x] 3.2 Implement `_cmd_mcp_add/_cmd_mcp_remove` — expand `all`, loop probe→delegate or file-edit (read/build/merge/dry-run guard/backup/atomic), aggregate exit codes
- [x] 3.3 Add orchestration docstrings for `_cmd_*` handlers; `--cwd` only on `add`
- [x] 4.1 Create `tests/test_mcp_registration.py` — idempotency byte-identical, preserve others, Codex normalize, atomic write
- [x] 4.2 Tests: backup `.bak` pre-edit, dry-run no mutation, unreadable/malformed → exit 1 no backup/write
- [x] 4.3 Tests: Gemini env both tokens, OpenCode scope routing, cwd custom absolute
- [x] 4.4 Tests: delegation — present→delegate, absent→file-edit, fail/timeout→fallback, opencode never delegates (mock `which`/`run`)
- [x] 4.5 Modify `tests/test_cli.py` — `sofer --help` has `mcp`, `mcp --help` has `add`/`remove`, `add/remove --help` flags (CLI-R09)
- [x] 5.1 Update `README.md` + `README_ES.md` — `sofer mcp add/remove --agent all`, per-agent paths, `.bak`, idempotency, cwd, env, TOML comment warning
- [x] 5.2 Verify delta specs `mcp-registration/spec.md` + `cli/spec.md` match impl; run `uv run pytest tests/ -q && uv run ruff check src/ tests/ && uv run mypy src/`

## Files Changed
| File | Action | What Was Done |
|------|--------|---------------|
| `src/sofer/mcp_registration.py` | Created | Module with 13 public helpers: resolve_config_path, read_config, build_entry, merge/remove_entry, backup, atomic_write, probe_native, delegate_add/remove, collect_env, validate_cwd; handles JSON/TOML, Codex normalize, Gemini explicit env, .bak + tmp+os.replace, which+timeout delegation |
| `src/sofer/cli.py` | Modified | Added mcp → add/remove subparsers (choices opencode\|codex\|gemini\|all, scope user\|project, cwd only on add, dry-run), implemented _cmd_mcp_add/_cmd_mcp_remove with probe→delegate fallback, containment validation, dry-run guard, backup/atomic, aggregate exit codes, orchestration docstrings |
| `tests/test_mcp_registration.py` | Created | 31 tests: idempotency byte-identical, preserve others, Codex normalize, atomic, backup .bak, dry-run, unreadable/malformed, Gemini env both tokens, scope routing, cwd custom, delegation present/absent/fail/timeout, remove idempotency (MCP-REG-01/02) |
| `tests/test_cli.py` | Modified | Added TestMcpCliHelp (5 tests): sofer --help has mcp, mcp --help has add/remove, add --help flags, remove --help flags, cwd not on remove (CLI-R09) |
| `README.md` | Modified | Added Register sofer-mcp section (per-agent table, idempotency, .bak, atomic, cwd containment, env, delegation, TOML warning); updated Command reference (mcp add/remove rows) and Flags at a glance (agent/scope, cwd, dry-run) |
| `README_ES.md` | Modified | Mirrored README changes in Spanish (same structure, prose translated, technical content in English) |
| `openspec/changes/feat-mcp-registration-automation/tasks.md` | Modified | Marked all 17 tasks [x] |
| `openspec/changes/feat-mcp-registration-automation/specs/mcp-registration/spec.md` | Verified | Delta spec matches impl (MCP-REG-01/02 scenarios covered by tests) |
| `openspec/changes/feat-mcp-registration-automation/specs/cli/spec.md` | Verified | CLI-R09 help scenarios covered |

## Deviations from Design
None — implementation matches design. One clarification: gemini project path uses `.gemini/settings.json` (consistent with adapter registry); codex project uses `.codex/config.toml`. TOML comment loss documented as warned.

## Issues Found
None. All 1149 tests pass (2 skipped). ruff and mypy green.

## Remaining Tasks
None — 17/17 complete.

## Workload / PR Boundary
- Mode: single PR (auto-chain pending but review_budget 3000 allows 431 net lines; 17 tasks fit under 600 forecast; splitting deferred per instruction "can split later if reviewer asks")
- Current work unit: all phases 1-5 (hybrid persist)
- Boundary: feat-mcp-registration-automation branch from dev 059636f → dev; work-unit commits staged
- Estimated review budget impact: ~431 lines net (mcp_registration.py ~280 + cli.py 270 + tests ~540 + docs ~104 - overhead) within 400-600 forecast; under 3000 budget

## Status
17/17 tasks complete. Ready for verify.

## Verification
- `uv run pytest tests/ -q` → 1149 passed, 2 skipped
- `uv run ruff check src/ tests/` → All checks passed!
- `uv run mypy src/` → Success
- `sofer --help` → mcp present; `sofer mcp --help` → add/remove; `sofer mcp add --help` → --agent/--scope/--cwd/--dry-run; `sofer mcp remove --help` → --agent/--scope/--dry-run (no --cwd)

## Spec Deltas Verified
- `mcp-registration/spec.md` ADDED Requirements MCP-REG-01/MCP-REG-02 scenarios map to tests (add all/single/idempotent/dry-run/backup/unreadable/cwd/gemini-env/codex-merge/scope/delegation + remove single/all/idempotent/dry-run/backup)
- `cli/spec.md` ADDED Requirement CLI-R09 (mcp in top help, lists children, add/remove help flags) map to TestMcpCliHelp
