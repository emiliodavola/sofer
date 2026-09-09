# Tasks: feat-mcp-registration-automation

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 400-600 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR1 → PR2 stacked-to-main |
| Delivery strategy | auto-forecast → auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Core module + CLI wiring | PR1 → main | Adapters, cwd/env/delegation, cli handlers; `pytest tests/test_cli.py -q` |
| 2 | Tests + docs/spec sync | PR2 → main | After PR1; idempotency/backup/delegation/dry-run/README; `pytest -q` green |

## Phase 1: Foundation

- [x] 1.1 Create `src/sofer/mcp_registration.py` — module docstring, `AgentName`/`Scope` Literals, `ADAPTERS` TypedDict
- [x] 1.2 Implement `resolve_config_path(agent, scope, cwd)` — opencode/codex/gemini paths, user vs project, `Path.home()` Windows
- [x] 1.3 Implement `read_config`, `build_entry(agent,cwd,env)`, `merge(agent,existing,desired)` — Codex string/array normalize, preserve others, no-change check
- [x] 1.4 Implement `backup(path)` (copy2→`.bak` overwrite) + `atomic_write(path,doc,fmt)` (tmp+`os.replace`)

## Phase 2: Core Behavior

- [x] 2.1 Implement `probe_native` (`which`+`--help` timeout 3s) + `delegate_add`/`delegate_remove` (codex/gemini only; opencode always file-edit)
- [x] 2.2 Implement cwd containment — `Path.resolve()` + `is_relative_to` user/project else exit 1; store absolute cwd
- [x] 2.3 Implement env forwarding — `HF_TOKEN`/`SOFER_MCP_APPROVAL_PHRASE` → Codex `env_vars` list vs Gemini `env` dict

## Phase 3: CLI Wiring

- [x] 3.1 Modify `src/sofer/cli.py` — add `mcp` → `add`/`remove` subparsers with `--agent/--scope/--cwd/--dry-run` choices + help text
- [x] 3.2 Implement `_cmd_mcp_add/_cmd_mcp_remove` — expand `all`, loop probe→delegate or file-edit (read/build/merge/dry-run guard/backup/atomic), aggregate exit codes
- [x] 3.3 Add orchestration docstrings for `_cmd_*` handlers; `--cwd` only on `add`

## Phase 4: Testing

- [x] 4.1 Create `tests/test_mcp_registration.py` — idempotency byte-identical, preserve others, Codex normalize, atomic write
- [x] 4.2 Tests: backup `.bak` pre-edit, dry-run no mutation, unreadable/malformed → exit 1 no backup/write
- [x] 4.3 Tests: Gemini env both tokens, OpenCode scope routing, cwd custom absolute
- [x] 4.4 Tests: delegation — present→delegate, absent→file-edit, fail/timeout→fallback, opencode never delegates (mock `which`/`run`)
- [x] 4.5 Modify `tests/test_cli.py` — `sofer --help` has `mcp`, `mcp --help` has `add`/`remove`, `add/remove --help` flags (CLI-R09)

## Phase 5: Docs & Spec Deltas

- [x] 5.1 Update `README.md` + `README_ES.md` — `sofer mcp add/remove --agent all`, per-agent paths, `.bak`, idempotency, cwd, env, TOML comment warning
- [x] 5.2 Verify delta specs `mcp-registration/spec.md` + `cli/spec.md` match impl; run `uv run pytest tests/ -q && uv run ruff check src/ tests/ && uv run mypy src/`
