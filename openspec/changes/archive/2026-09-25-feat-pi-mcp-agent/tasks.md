# Tasks: 2026-09-25-feat-pi-mcp-agent

## Phase 1 — Registry: Pi entry + capabilities (`mcp_registration.py`)

- [x] 1.1 Add `user_env_dir: str | None` to `Adapter`; add `"refs_braced"` to the
      `env` Literal; update the module and TypedDict docstrings.
- [x] 1.2 Declare `user_env_dir: None` on opencode/codex/gemini; add the `pi`
      entry (`fmt=json`, `key=mcpServers`, `.pi/agent/mcp.json` /
      `.pi/mcp.json`, `command=string`, `adds_type_local=False`,
      `env=refs_braced`, `delegates=False`, `user_env_dir=PI_CODING_AGENT_DIR`).
- [x] 1.3 `resolve_config_path`: user scope honours `user_env_dir` when the
      variable is set/non-empty (`<dir>/<user_parts[-1]>`), else `Path.home()`.
- [x] 1.4 `build_entry`: `refs_braced` emits `{k: "${k}"}`; keep `refs`/`allow_list`
      byte-identical.
- [x] 1.5 `_entries_equal`: branch on the adapter `env` capability instead of
      agent names (`allow_list` / `refs`+`refs_braced` / else).
- [x] 1.6 Docstrings: delegation is file-edit for opencode and pi.

## Phase 2 — CLI surface (`cli.py`)

- [x] 2.1 `mcp` and `mcp add` `help=`/`description=` name the four agents and
      Pi's `${KEY}` env form.
- [x] 2.2 Confirm both `choices` and both `all` expansions already derive from
      `AGENT_NAMES` (now four) — no logic edit needed.
- [x] 2.3 Update the `_cmd_mcp_add` docstring env-forwarding paragraph.

## Phase 3 — Docs

- [x] 3.1 `README.md`: command reference, flags table, section heading/examples
      ("all four"), agent table (pi user/project rows), env + delegation prose,
      approval-phrase anchor and prose.
- [x] 3.2 `README_ES.md`: mirror the same sections (technical content English,
      prose Spanish), including the updated heading anchor.

## Phase 4 — Specs

- [x] 4.1 Delta `specs/mcp-registration/spec.md`: MODIFIED MCP-REG-01/02/03
      (four agents, Pi entry/env/scopes, `all` → four).
- [x] 4.2 Delta `specs/cli/spec.md`: MODIFIED CLI-R09 (`--agent` includes pi;
      env-forwarding sentence includes pi).
- [x] 4.3 Sync both canonical specs (`openspec/specs/...`) with the deltas.

## Phase 5 — Tests

- [x] 5.1 `test_mcp_registration.py`: `TestPiAdapter` (registry, entry shape,
      braced env, scopes incl. `PI_CODING_AGENT_DIR` override/empty, no
      delegation, `_entries_equal`) and `TestPiCli` (user override write,
      project write, idempotent, dry-run, unreadable, remove preserve/idempotent).
- [x] 5.2 Update registry tests for the ninth adapter key and `refs_braced`.
- [x] 5.3 Update four-agent `all` assertions (dry-run, remove, warning-once) and
      the sentinel registry test.
- [x] 5.4 `test_cli.py`: help env-forwarding assertion names pi.

## Phase 6 — Verification

- [x] 6.1 `uv run pytest tests/test_mcp_registration.py tests/test_cli.py -q` — 265 passed.
- [x] 6.2 `uv run pytest tests/ -q` (full suite) — 1875 passed, 2 skipped.
- [x] 6.3 `ruff check` + `ruff format --check` — clean.
- [x] 6.4 `mypy src/ scripts/` and `pyright` — clean (1 pre-existing tomli warning).
- [x] 6.5 `scripts/check_test_mapping.py` and `scripts/check_core_coverage.sh` — OK / 4×100%.
- [x] 6.6 `coverage report`: `mcp_registration.py` 100%, TOTAL 93%.
- [x] 6.7 Independent read-only verification by a `general` subagent — PASS, no falsification.
