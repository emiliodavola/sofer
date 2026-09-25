# Apply Progress: 2026-09-25-feat-pi-mcp-agent

## Status

Implementation complete on branch `feat/142-pi-mcp-agent` (base `dev@b546db3`).

## What changed

### `src/sofer/mcp_registration.py`

- `Adapter` TypedDict: added `user_env_dir: str | None`; `env` Literal grew
  `"refs_braced"`. Module + TypedDict docstrings updated for Pi and the braced
  form.
- `ADAPTERS`: `user_env_dir: None` added to opencode/codex/gemini; new `pi`
  entry (`fmt=json`, `key=mcpServers`, `user_parts=(".pi","agent","mcp.json")`,
  `project_parts=(".pi","mcp.json")`, `command="string"`,
  `adds_type_local=False`, `env="refs_braced"`, `delegates=False`,
  `user_env_dir="PI_CODING_AGENT_DIR"`).
- `resolve_config_path`: user scope honours `user_env_dir` when set/non-empty
  (`<dir>/<user_parts[-1]>`), else `Path.home()`.
- `build_entry`: `refs_braced` emits `{k: "${k}"}`.
- `_entries_equal`: capability-driven (`allow_list` / `refs`+`refs_braced` /
  else) instead of the agent-name ladder.
- Delegation docstrings note opencode and pi are file-edit only.

### `src/sofer/cli.py`

- `mcp` parser `help=`/`description=` and `mcp add` description name the four
  agents and Pi's `${KEY}` env form; `_cmd_mcp_add` docstring updated.
- No logic change: `choices` and both `all` expansions already derive from
  `AGENT_NAMES`.

### Docs

- `README.md` / `README_ES.md`: command reference, flags table, section heading
  and examples ("all four"), Pi user/project table rows, env + delegation prose,
  approval-phrase anchor/prose.

### Specs

- `openspec/changes/2026-09-25-feat-pi-mcp-agent/specs/mcp-registration/spec.md`
  (MODIFIED MCP-REG-01/02/03) and `.../specs/cli/spec.md` (MODIFIED CLI-R09).
- Canonical `openspec/specs/mcp-registration/spec.md` and
  `openspec/specs/cli/spec.md` synced with the deltas.

### Tests

- `tests/test_mcp_registration.py`: new `TestPiAdapter` (9 tests) and
  `TestPiCli` (8 tests); registry tests updated for the ninth key and
  `refs_braced`; four-agent `all` assertions (dry-run, remove, warning-once) and
  the sentinel registry test updated.
- `tests/test_cli.py`: `add help documents env forwarding` assertion names pi.

## Commands run (local, Python 3.13)

```
$ uv run pytest tests/test_mcp_registration.py tests/test_cli.py -q
265 passed

$ uv run coverage run -m pytest -q
1875 passed, 2 skipped, 1 warning in 319.86s

$ uv run ruff check src/ tests/ scripts/
All checks passed!

$ uv run ruff format --check src/ tests/
70 files already formatted

$ uv run mypy src/ scripts/
Success: no issues found in 35 source files

$ uv run pyright
0 errors, 1 warning, 0 informations

$ uv run python scripts/check_test_mapping.py
OK: test-mapping contract holds
```

## Notes / gotchas

- A stale pre-existing local `.coverage` made
  `tests/test_coverage_contract.py::test_three_floor_modules_and_total_meet_90_when_data_file_present`
  read a partial database mid-run and fail on a spurious 65.8%. Removing the
  stale file and re-running `coverage run -m pytest` yields the true post-run
  numbers (100% for `mcp_registration.py`). The guard is designed to skip on a
  clean checkout.
- `mcp_server.py` `_APPROVAL_PHRASE_AGENT_ENTRY_KEYS` deliberately untouched
  (adjacent concern; follow-up).
